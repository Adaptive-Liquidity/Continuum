# NexusIQ Architecture

---

## Components

### nexus-agentd

A long-lived Rust daemon that runs as a Docker service (`restart:
unless-stopped`). It hosts the Nexus hypervisor with the `aeon-memory` feature
compiled in. All WASM module execution happens here. The daemon listens on a
Unix socket (`/run/nexus/nexus-agentd.sock`) inside a named Docker volume
(`agentd_run`) that is shared with `nexus-mcp`.

### nexus-mcp

A STDIO MCP server. It is **not** a long-running port — it is defined in
compose with `profiles: ["tools"]` so `docker compose up` does not start it.
MCP clients invoke it per-session via `connect-mcp.sh`, which runs:

```
docker compose run --rm -T nexus-mcp
```

The `-T` flag suppresses TTY allocation so the JSON-RPC byte stream passes
cleanly over stdin/stdout. Each MCP session gets its own container that exits
when the client disconnects.

`nexus-mcp` connects to `nexus-agentd` over the shared Unix socket. It does
not run WASM itself — it is a thin transport that forwards execution requests
to the daemon.

### aeon (AEON-IQ memoryos)

A Rust/Axum HTTP service that provides:
- Memory storage and semantic retrieval (via pgvector cosine similarity)
- MemoryEvidence records tied to Proof Capsules
- Agent timeline (ordered execution events)
- Extraction of structured memory from free-form text

It listens on port 8080 inside the Docker network, bound to `127.0.0.1:8080`
on the host. All management endpoints require the `X-Management-Key` header.

### postgres (pgvector)

Standard Postgres 16 with the `pgvector` extension. Used only by AEON-IQ.
Not published to the host. AEON connects to it using the hostname `postgres`
on the internal `nexusiq` bridge network.

---

## Data flow: MCP client call

```
MCP client (Claude Desktop / Cursor / OpenHands)
    │
    │  stdin/stdout  (JSON-RPC 2.0)
    ▼
connect-mcp.sh
    │
    │  exec → docker compose run --rm -T nexus-mcp
    ▼
nexus-mcp  (STDIO MCP server, one container per session)
    │
    │  Unix socket  /run/nexus/nexus-agentd.sock
    │  (shared agentd_run volume)
    ▼
nexus-agentd  (Nexus hypervisor, long-lived daemon)
    │
    │  HTTP  (internal Docker network)
    │  NEXUS_AEON_BASE_URL = http://aeon:8080
    │  Header: X-Management-Key  (request auth; no per-request HMAC)
    ▼
aeon  (AEON-IQ memoryos-kernel)
    │
    │  SQL + pgvector  (internal Docker network)
    ▼
postgres  (pgvector, not host-published)
    │
    │  HTTP (egress to provider)
    ▼
upstream LLM  (OpenAI / Anthropic / Gemini / Ollama)
    embeddings + extraction
```

---

## Two Nexus transports

| Transport | Used by | How |
|---|---|---|
| STDIO MCP | MCP clients (Claude Desktop, Cursor, OpenHands, …) | `connect-mcp.sh` → `docker compose run --rm -T nexus-mcp` |
| Unix socket daemon | Internal / scripted callers | Direct connection to `/run/nexus/nexus-agentd.sock` via the shared volume |

The MCP surface routes through the daemon. There is no HTTP MCP endpoint.

---

## Where proof capsules and timeline events live

**Proof Capsules** are returned in the MCP tool response payload
(`proof_capsule` field). `run-live-example.sh` (and any caller that handles
the response) writes them to `./data/proofs/<capsule_id>.json` on the host.
The `data/proofs` directory is bind-mounted into both `nexus-agentd` and
`nexus-mcp` at `/data/proofs`.

**Timeline events** are POSTed to AEON-IQ at
`/api/v1/agents/<agent_id>/timeline` and stored in Postgres. They are
queryable via the AEON REST API. If the AEON call fails (network error,
provider down), the execution continues — timeline delivery is fail-open.

---

## Shared-secret cross-wiring

Two secrets must be identical on both sides of the Nexus ↔ AEON boundary:

| Secret | AEON side variable | Nexus side variable |
|---|---|---|
| Management API key | `MANAGEMENT_API_KEY` | `NEXUS_AEON_MANAGEMENT_KEY` (set to `${MANAGEMENT_API_KEY}` in compose) |
| HMAC signing key | binds MemoryEvidence provenance (not request auth) | `NEXUS_AEON_HMAC_KEY` |

`docker-compose.yml` wires `NEXUS_AEON_MANAGEMENT_KEY` to `${MANAGEMENT_API_KEY}`
so there is a single value to set in `.env`. `install.sh` generates both
secrets in one pass, keeping them in sync. Do not set `NEXUS_AEON_MANAGEMENT_KEY`
as a separate variable — it will be ignored.

---

## nexus-mcp is spawned per-session, not a port

This is the most common point of confusion. Some MCP servers run as an HTTP
service on a fixed port. NexusIQ's MCP server does not. The flow is:

1. MCP client reads its config: `command = /path/to/connect-mcp.sh`
2. Client forks `connect-mcp.sh` as a child process
3. `connect-mcp.sh` runs `docker compose run --rm -T nexus-mcp`
4. That starts a fresh `nexus-mcp` container
5. The client's stdin/stdout are piped directly to the container's
   stdin/stdout
6. When the client disconnects, `--rm` removes the container

The `nexus-agentd` daemon (which does all the real work) is long-lived and
pre-started by `./start.sh`. Only the thin MCP front-end is per-session.

---

## Dependency startup order

```
postgres  →  aeon  →  nexus-agentd  →  (nexus-mcp, on demand)
```

Each service depends on the prior one being healthy before it starts.
`./start.sh` waits for all three core services to become healthy before
returning.
