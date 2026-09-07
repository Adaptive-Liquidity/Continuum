# Operations

## Runtime mode

`scripts/runtime-mode.sh` is the authoritative, non-executing `.env` parser.
Only case-insensitive `true` and `false` are accepted for
`NEXUS_AEON_ENABLED`. A missing setting in a legacy/custom `.env` enables
memory with a visible compatibility warning. Empty or malformed values fail.

## Stack lifecycle

- `./install.sh`: validates the selected mode, generates only its required
  internal secrets, vendors/builds or pulls the selected services, and creates
  data directories.
- `./start.sh`: validates before changing containers. Core mode stops memory
  containers while preserving volumes and starts agentd only. Memory mode
  health-gates PostgreSQL, AEON, and the worker before agentd.
- `./stop.sh`: stops default, tools, and memory-profile services; data remains.
- `./restart.sh`: stop then mode-aware start.
- `./logs.sh [service]`: follows logs across all profiles.
- `./doctor.sh`: verifies exactly the configured service set.
- `./reset.sh`: removes all named volumes after confirmation.
- `./uninstall.sh`: removes the stack and optionally local files.

`nexus-mcp` remains in the `tools` profile and is launched per session.
`connect-mcp.sh` uses `--no-deps` and requires a healthy running agentd.

## Verification flows

Core mode:

```bash
./doctor.sh
./scripts/smoke-nexus-execute.sh
./scripts/smoke-proof-capsule.sh
./verify-live-stack.sh
```

Memory mode (`NEXUS_AEON_ENABLED=true` with a real provider):

```bash
./doctor.sh
./scripts/smoke-memory-recall.sh
./scripts/smoke-nexus-execute.sh
./scripts/smoke-proof-capsule.sh
./scripts/smoke-timeline.sh
./run-live-example.sh
./verify-live-stack.sh
```

Disabled memory checks are reported as disabled, never as successful recall.

## Secret rotation

`NEXUS_AGENTD_AUTH_TOKEN` is always required. PostgreSQL, AEON management,
HMAC, and evidence-signing material is required/generated only in memory mode.
To rotate active-mode secrets, clear them in `.env`, run
`./scripts/generate-secrets.sh`, and restart. Rotating the PostgreSQL password
requires coordinated database handling or a deliberate data reset.

## Postgres + pgvector backup/restore

Data is internal only and not exposed on host ports.

Backup:

```bash
docker compose --profile memory exec -T postgres pg_dump -U nexusiq -d nexusiq > /tmp/nexusiq.sql
```

Restore (service down window recommended):

```bash
cat /tmp/nexusiq.sql | docker compose --profile memory exec -T postgres psql -U nexusiq -d nexusiq
```

## HNSW maintenance

There is no bundled pgvector maintenance CLI in the root kit scripts, but ANN index upkeep should be done explicitly:

- Run ANN/HNSW rebuild/reindex tasks during maintenance windows, before long `VACUUM` windows on heavy workloads.
- Keep this as a worker-only job, not request-path inline work.
- Serialize maintenance with a lock to prevent concurrent index writes.

Example pattern:

```bash
docker compose --profile memory exec -T postgres psql -U nexusiq -d nexusiq -c "REINDEX INDEX CONCURRENTLY <hnsw_index_name>;"
```

If index maintenance collides with ongoing writes, choose conservative timings and monitor query impact.


## AEON-IQ role split (proxy vs worker)

The stack runs AEON-IQ as two services sharing one database:

| Service | `MEMORYOS_ROLE` | Runs | Pool budget |
|---|---|---|---|
| `aeon` | `proxy` | request serving only (chat proxy + management API) | `DB_MAX_CONNECTIONS` (default 20) |
| `aeon-worker` | `worker` | archival, extraction outbox, RMK/AMP sweeps, HNSW maintenance; serves `/health` + `/metrics` only, no host port | `WORKER_DB_MAX_CONNECTIONS` (default 5) |

Rationale: background sweeps over large corpora previously shared the hot
path's connection pool and produced a measured p99 latency tail. The split
caps background work at its own small budget so it can never starve request
serving. To run everything in one container (small machines), remove
`aeon-worker` and set `MEMORYOS_ROLE=all` (or unset it) on `aeon`.
