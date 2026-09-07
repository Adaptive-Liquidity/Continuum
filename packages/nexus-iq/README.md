# NexusIQ Self-Host Kit

Run Nexus WASM workloads and produce cryptographic Proof Capsules with a
provider-keyless default install. The PostgreSQL + AEON memory plane is an
explicit opt-in.

## Quickstart

```bash
git clone https://github.com/Adaptive-Liquidity/Nexus-IQ-temp.git
cd Nexus-IQ-temp
./install.sh --start
./doctor.sh
```

No model-provider credential is needed. `install.sh` creates `.env` with
`NEXUS_AEON_ENABLED=false`, generates the internal agentd authentication
token, vendors/builds Nexus only, and bakes the sample WASM module.

Generate MCP client configuration when ready:

```bash
./generate-mcp-config.sh
```

## Operating modes

Core mode (default):

- Nexus execution and sandboxing;
- Proof Capsule generation;
- on-demand MCP through the running authenticated `nexus-agentd`;
- no PostgreSQL, AEON proxy, AEON worker, memory write, or memory recall.

Memory mode (explicit opt-in):

- set `NEXUS_AEON_ENABLED=true`;
- configure a supported provider;
- re-run `./install.sh`, then `./start.sh`;
- adds PostgreSQL, AEON memory write/recall, the AEON worker, and related
  evidence checks.

Provider configuration never auto-enables memory.

## Architecture

Compose defines five services on an isolated network. Core mode starts only `nexus-agentd`; `nexus-mcp` runs on demand. The three memory-profile services below start only when memory is explicitly enabled:

```
 ┌───────────────────────────────────────────────────────────────┐
 │  host (you)                                                   │
 │                                                               │
 │  MCP client ──── connect-mcp.sh ─── stdin/stdout ──┐         │
 │  (Claude Desktop / Cursor / OpenHands)              │         │
 │                                               ┌─────▼──────┐ │
 │  curl / browser ─── 127.0.0.1:8080 ─────────▶│   aeon     │ │
 │                                               │(proxy, REST│ │
 │                                               │    API)    │ │
 └───────────────────────────────────────────────┴─────┬───┬──┘ │
                                                       │   │
 ┌─ Docker internal network (nexusiq) ─────────────────│───│────┐
 │                                                     │   │    │
 │  ┌────────────────┐   unix socket  ┌────────────┐   │   │    │
 │  │  nexus-mcp     │◀──────────────▶│nexus-agentd│   │   │    │
 │  │  (STDIO only;  │                │(long-lived │   │   │    │
 │  │  on-demand)    │                │ daemon)    │   │   │    │
 │  └────────────────┘                └────────────┘   │   │    │
 │                                         │           │   │    │
 │  ┌─────────────────────────────────────────────┐    │   │    │
 │  │  postgres (pgvector, internal only, no port)│◀──┬─┘   │    │
 │  └─────────────────────────────────────────────┘   │     │    │
 │             ▲                                       │     │    │
 │             └───────────────────────────┐   ┌───────┘     │    │
 │                                          │   │             │    │
 │                              ┌───────────▼───▼──┐          │    │
 │                              │   aeon-worker     │          │    │
 │                              │ (archival, RMK/AMP│          │    │
 │                              │  sweeps, extraction│          │    │
 │                              │  outbox drain)     │          │    │
 │                              └────────────────────┘          │    │
 │             └──────────────────────────────────────────────┘    │
 └─────────────────────────────────────────────────────────────┘
```

| Service | Role | Host exposure |
|---|---|---|
| `postgres` | pgvector storage for AEON-IQ | None (internal only) |
| `aeon` | AEON-IQ REST API — hot request path only (`MEMORYOS_ROLE=proxy`) | `127.0.0.1:8080` |
| `aeon-worker` | AEON-IQ background jobs: archival, RMK/AMP sweeps, extraction-outbox drain (`MEMORYOS_ROLE=worker`) | None (internal only) |
| `nexus-agentd` | Nexus execution daemon | Unix socket (shared volume) |
| `nexus-mcp` | STDIO MCP server | None — launched on demand |

`nexus-mcp` is **not** a long-running port. MCP clients launch it via `connect-mcp.sh`, which runs `docker compose --profile tools run --rm --no-deps -T nexus-mcp` and speaks JSON-RPC 2.0 over stdin/stdout. There is no HTTP MCP endpoint.

`aeon-worker` matters even though it serves no client traffic directly: extraction jobs are enqueued by `aeon` and only drained by `aeon-worker` (`EXTRACTION_OUTBOX_ENABLED` defaults to `true`), so a dead worker means memory writes silently stop while chat completions keep succeeding. `./doctor.sh` and `./start.sh`'s health wait both check `aeon-worker`'s `/health` explicitly for this reason.

---

## System requirements

- Docker Engine 24+ with the Compose v2 plugin;
- about 2 GB RAM for core mode (more for memory mode);
- Bash 4.0 or newer, `curl`, and `git`;
- `jq` or `python3` for smoke scripts.

A provider credential is required only for explicitly enabled memory mode.

## Installation behavior

In core mode, `./install.sh`:

- creates `.env` from `.env.example` when absent;
- generates `NEXUS_AGENTD_AUTH_TOKEN`;
- vendors only the pinned Nexus source;
- builds or pulls only the Nexus image;
- creates `data/{proofs,timeline,modules,logs,run}`;
- bakes `data/modules/sample_tool.wasm`.

It does not clone/build/pull AEON-IQ and does not pull PostgreSQL.

To enable memory:

```bash
# Configure a supported provider and set NEXUS_AEON_ENABLED=true in .env first.
./install.sh
./start.sh
./doctor.sh
```

An explicit memory request fails validation before vendoring, building,
pulling, or starting if its provider or required secrets are unavailable.

## Configuring the LLM provider

This section applies only when `NEXUS_AEON_ENABLED=true`. AEON-IQ uses a provider to embed memories and extract structured data. The default memory-mode provider is OpenAI.

> **SSRF egress guard:** AEON-IQ validates provider base URLs at startup. By default it requires `https` and blocks loopback, private, and link-local addresses. For the default cloud providers (OpenAI, Anthropic, Gemini — all `https`) this is completely transparent; no action needed. If you point AEON at a **local or self-hosted LLM** (Ollama on `localhost`, an `http://` proxy, a provider on a private IP), the `aeon` container will refuse to start unless you add `AEON_ALLOW_INSECURE_PROVIDER_URLS=true` to your `.env`. Note: even with this flag set, the cloud-metadata endpoint remains blocked.

### OpenAI (default)

Use `.env.example` or `.env.openai.example`. Set:

```
UPSTREAM_PROVIDER=openai
```

Set `OPENAI_API_KEY` to a real OpenAI credential through your normal secret
management process before enabling memory.

Default models: `text-embedding-3-small` (1536 dimensions), `gpt-4o-mini` extractor. These are configured in `.env.openai.example`.

### Anthropic

```bash
cp .env.anthropic.example .env
```

Then set `OPENAI_API_KEY` to your **Anthropic** API key. (AEON-IQ uses a single upstream-key variable regardless of provider.)

Note: Anthropic does not serve embeddings, while this kit exposes one upstream-key slot. A split-key Anthropic + OpenAI deployment therefore requires an operator-managed compatible proxy; the preset alone cannot carry two independent credentials.

### Gemini

```bash
cp .env.gemini.example .env
```

Set `OPENAI_API_KEY` to your Google AI / Gemini API key.

Important: Gemini's default embedding model (`text-embedding-004`) produces 768-dimensional vectors, but AEON-IQ's pgvector column is hard-coded to `vector(1536)`. If you use a 768-dim model you must also change the schema. See `.env.gemini.example` for the full note.

### Ollama (ADVANCED / EXPERIMENTAL)

```bash
cp .env.ollama.example .env
```

Ollama local models do **not** produce 1536-dim vectors. You must change AEON-IQ's pgvector schema (`migrations/0001_initial.sql`) to match your chosen model's dimension **before the database is first initialized**. Changing the schema after data exists requires dropping and re-migrating the embedding column.

Because Ollama runs locally over `http://`, you must also add the following to your `.env`:

```
AEON_ALLOW_INSECURE_PROVIDER_URLS=true
```

Without this flag, the `aeon` container will refuse to start when it detects a non-`https` or loopback provider URL. See `.env.ollama.example` for the full warning and procedure. This path is not supported for first-time users.

---

## Evidence attestation

AEON-IQ Ed25519-counter-signs every search response (`AEON_EVIDENCE_SIGNING_KEY`, auto-generated by `install.sh`); Nexus verifies that signature before a proof capsule is allowed to claim `Attested` / `AttestedWithRecall` instead of the unverified `Advisory` fallback.

`AEON_EVIDENCE_SIGNING_KEY` is generated for you, but its corresponding public key (`NEXUS_AEON_VERIFYING_KEY`) is **not** — it must be pinned manually after the stack is running, once:

```bash
curl -s -H "X-Management-Key: $MANAGEMENT_API_KEY" \
  http://127.0.0.1:8080/api/v1/evidence/verifying-key
```

Copy the returned `key_id` into `.env` as `NEXUS_AEON_VERIFYING_KEY`, then `./stop.sh && ./start.sh`. Until this is set, `./doctor.sh` warns (it does not fail the check) and capsules stay at `Advisory` — verification is additive security, not required for the stack to function.

---

## Prebuilt images

```bash
NEXUSIQ_USE_PREBUILT=true NEXUSIQ_IMAGE_TAG=<release-tag> ./install.sh
```

Core mode pulls only the Nexus image. Memory mode pulls the Nexus, AEON, and
PostgreSQL images. No release image is claimed available by this repository;
use the source-build default until a matching release exists.

## Starting and stopping the stack

```bash
./start.sh
./logs.sh
./stop.sh
```

With memory disabled, `start.sh` stops any previously running `aeon`,
`aeon-worker`, and `postgres` containers without deleting volumes, then starts
and waits for `nexus-agentd`. With memory enabled, it starts and health-checks
the three memory services before starting agentd.

`connect-mcp.sh` never starts dependencies. It fails clearly unless the
already-running agentd is healthy.

## Verifying with doctor

`./doctor.sh` is mode-aware.

Core mode requires Docker/Compose, valid agentd authentication, a healthy
agentd, MCP initialize/tool listing, writable data directories, and all memory
containers stopped. It prints `memory plane disabled by configuration` and
does not label memory functionality as passed.

Memory mode additionally requires healthy PostgreSQL, AEON proxy and worker,
management authentication, provider configuration, and the existing evidence
key checks.

For a complete proof of the selected service set:

```bash
./verify-live-stack.sh
```

Core verification runs the Nexus execution and Proof Capsule smokes only.
Memory verification preserves the full live example.

## Connecting MCP clients

MCP transport is **STDIO only**. Clients launch `connect-mcp.sh`, which starts a `nexus-mcp` container per session. There is no HTTP MCP port.

Run this once after install:

```bash
./generate-mcp-config.sh
```

It writes configs with absolute paths into `./mcp/`.

### Claude Desktop

Paste the contents of `mcp/claude-desktop.json` into:

| Platform | Config path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Restart Claude Desktop. `nexusiq` should appear in the tools list.

### Cursor

Paste `mcp/cursor.json` into:
- Per-project: `<project>/.cursor/mcp.json`
- Global: `~/.cursor/mcp.json`

### OpenHands

Paste `mcp/openhands.json` contents into Settings → MCP, key `nexusiq`.

### Any other MCP client

Use `mcp/generic-mcp.json`. The server entry specifies:
- `command`: absolute path to `connect-mcp.sh`
- `env.NEXUSIQ_SELFHOST_DIR`: absolute path to the kit directory
- Transport: STDIO

If your client cannot find `connect-mcp.sh`, use its absolute path.

---

## Running the live example

`./run-live-example.sh` is the memory-enabled write/recall/timeline flow. Run
it only after setting `NEXUS_AEON_ENABLED=true`, configuring a real provider,
and passing `./doctor.sh`.

For core mode, use:

```bash
./verify-live-stack.sh
```

That verifies real WASM execution and writes a real Proof Capsule without
claiming memory recall.

## Viewing proof capsules

Proof Capsules are written to `./data/proofs/` on the host as `<capsule_id>.json` files.

```bash
ls -la data/proofs/
cat data/proofs/<capsule_id>.json
```

Each capsule contains the module path, execution result, a capability grant record, a timestamp, and a cryptographic binding. Treat these files as execution metadata — they may contain details about what modules ran.

---

## Viewing timeline events

This section applies only to memory mode. Timeline events are stored in AEON-IQ's PostgreSQL database and queryable with `MANAGEMENT_API_KEY`.

```bash
# Query timeline at or before a given time
curl -fsS \
  -H "X-Management-Key: $MANAGEMENT_API_KEY" \
  "http://127.0.0.1:8080/api/v1/agents/nexusiq/timeline/at?timestamp=<ISO8601>"

# Stats (memory counts, etc.)
curl -fsS \
  -H "X-Management-Key: $MANAGEMENT_API_KEY" \
  http://127.0.0.1:8080/api/v1/stats

# Search memories
curl -fsS -X POST http://127.0.0.1:8080/api/v1/memories/search \
  -H "X-Management-Key: $MANAGEMENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"nexusiq","query":"what did Nexus execute?","limit":5}'
```

---

## Stop / update / uninstall

```bash
# Stop (preserves volumes and data)
./stop.sh

# Update
./stop.sh && git pull && ./install.sh && ./start.sh

# Full data reset (removes volumes and all stored data — irreversible)
./reset.sh

# Full uninstall (removes containers, volumes, and locally built images)
./uninstall.sh
```

---

## Known limitations

- No versioned kit release has been tagged yet, so `NEXUSIQ_USE_PREBUILT=true` can only pull the unpinned `:latest` tag (see [Prebuilt images](#prebuilt-images)) — source build remains the default and reproducible path.
- Ollama support requires a manual schema change and is experimental.
- The AEON pgvector column is fixed at `vector(1536)`. Non-1536-dim embedding models require a schema migration.
- Anthropic does not provide embeddings, and the kit has one upstream-key slot; split-key deployments require an operator-managed compatible proxy.
- `nexus-mcp` is single-session per container invocation — each MCP client session launches a fresh container.

---

## Security notes

See [SECURITY.md](SECURITY.md) for the full security reference.

Short version:
- All host ports are bound to `127.0.0.1` only.
- Postgres is not published to the host at all.
- Internal secrets required by the selected mode are generated by `install.sh` and stored only in `.env`.
- Do not commit `.env`.
- Do not expose the AEON API (`127.0.0.1:8080`) or Postgres to the network without a reverse proxy and TLS.
- Proof Capsules and timeline events contain execution metadata — treat them as sensitive.

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

For a step-by-step first-run guide, see [QUICKSTART.md](QUICKSTART.md).
