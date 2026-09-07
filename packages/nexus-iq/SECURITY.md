# NexusIQ Security Reference

---

## Network defaults

All host-bound ports are loopback-only (`127.0.0.1`). No service is accessible
from the network by default.

| Service | Host binding |
|---|---|
| AEON-IQ REST API | `127.0.0.1:8080` (configurable via `AEON_PORT`) |
| Postgres | Not published to the host at all |
| nexus-agentd | Unix socket inside a named Docker volume only |
| nexus-mcp | No port — STDIO only, launched on demand |

No Docker socket is mounted into any container.

---

## What NOT to expose publicly

**Postgres** — never publish the Postgres port to the host or network. It is
intentionally absent from the compose port bindings. If you need external
access to the database, use an SSH tunnel or a bastion host.

**AEON management API** (`/api/v1/*`) — the management endpoints create,
delete, and query memories and timeline events. They require the
`X-Management-Key` header. Do not expose port 8080 to the LAN or internet
without a reverse proxy that enforces TLS and ideally an additional
authentication layer (e.g. HTTP Basic Auth at the proxy).

**`ALLOW_UNAUTH_MANAGEMENT`** — this flag disables management API
authentication entirely. It exists for development convenience only and must
never be `true` in any deployment reachable by other users or machines.
`./doctor.sh` will fail if it is set to a truthy value.

---

## How secrets are generated

`./install.sh` calls `./scripts/generate-secrets.sh`, which fills in the
following variables in `.env` with cryptographically random values (using
`openssl rand -hex 32` or equivalent):

| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Postgres superuser password |
| `MANAGEMENT_API_KEY` | Authenticates calls to the AEON management API |
| `NEXUS_AEON_HMAC_KEY` | HMAC-signs MemoryEvidence digests (provenance binding, not request auth) |
| `NEXUS_AGENTD_AUTH_TOKEN` | Authenticates `nexus-mcp` connections to `nexus-agentd` |

The `MANAGEMENT_API_KEY` is wired to both the AEON service and the Nexus
clients automatically via `docker-compose.yml` — you set it once, it flows
to all consumers.

Secrets are stored only in `.env`. They are never printed to stdout, never
committed to git (`.env` is in `.gitignore`), and never echoed in install
output.

### Rotating secrets

To rotate all secrets: blank the four variables in `.env` (leave other vars
like `OPENAI_API_KEY` intact), then run:

```bash
./scripts/generate-secrets.sh
./stop.sh && ./start.sh
```

This invalidates all existing sessions. The Postgres password rotation also
requires updating the password inside the running Postgres instance; the
simplest approach is a full reset:

```bash
./reset.sh    # stops the stack and wipes all volumes
./install.sh
./start.sh
```

---

## HMAC key purpose

`NEXUS_AEON_HMAC_KEY` is used by `nexus-agentd` and `nexus-mcp` to
HMAC-sign the **MemoryEvidence digests** they record, binding each piece of
memory evidence to the Nexus instance that produced it so a stored memory's
provenance can be verified later. It does **not** authenticate the HTTP
requests to AEON: request authentication uses the management API key
(`X-Management-Key`), and AEON does not verify a per-request HMAC. The key is
shared between the two Nexus-side services (daemon and MCP) and is separate
from the management API key.

> Per-request HMAC signing/verification (an `X-HMAC-Signature` header on the
> wire) is **not implemented**: requests between Nexus and AEON are
> authenticated only by the management key over the private internal network.

---

## Reverse proxy / TLS for remote access

If you need to access the AEON API from another machine, place a reverse proxy
in front of it. Example with Caddy:

```
api.yourdomain.example {
    reverse_proxy 127.0.0.1:8080
}
```

With nginx:

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.example;
    # ... TLS config ...
    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

Do not bind `AEON_PORT` to `0.0.0.0` directly — keep the loopback binding and
let the proxy handle TLS termination and external exposure.

---

## Proof capsules and timeline events

Proof Capsules (`data/proofs/*.json`) and timeline events stored in AEON
contain execution metadata: module paths, capability grants, timestamps,
capsule identifiers, and execution results. Treat these files as sensitive:

- Do not commit `data/proofs/` to a public repository.
- If NexusIQ is shared among users on a machine, ensure `data/proofs/` and
  `data/timeline/` are not world-readable (`chmod 700 data/`).
- Timeline events are queryable via the management API; protect that API key.

---

## Reporting security issues

To report a security vulnerability in NexusIQ or AEON-IQ, email:

    security@adaptiveliquidity.com

Please include a description of the issue, steps to reproduce, and any
relevant log output or proof-of-concept. Do not open a public GitHub issue for
security vulnerabilities. We aim to respond within 5 business days.
