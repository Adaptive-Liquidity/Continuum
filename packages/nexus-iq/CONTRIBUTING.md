# Contributing

## Repository layout

- `install.sh`, `start.sh`, `stop.sh`, `restart.sh`, `reset.sh`, `uninstall.sh`, `doctor.sh`
- `docker-compose.yml`, `docker/Dockerfile.nexus`
- `connect-mcp.sh`, `generate-mcp-config.sh`, `verify-live-stack.sh`
- `scripts/` operational + smoke scripts
- `mcp/` example configs (`*.json.example`) and generated configs
- `.env*.example`, `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `TROUBLESHOOTING.md`
- `examples/` and workflow docs

## Local development setup

```bash
cp .env.example .env
./install.sh
./start.sh
./doctor.sh
./generate-mcp-config.sh
```

For local source iteration:

```bash
export NEXUSIQ_VENDOR_NEXUS=/path/to/Nexus
export NEXUSIQ_VENDOR_AEON=/path/to/AEON-IQ
./install.sh --start
```

## Verify before PR

Recommended command order:

- `./doctor.sh`
- `./scripts/smoke-nexus-execute.sh`
- `./scripts/smoke-memory-recall.sh`
- `./scripts/smoke-proof-capsule.sh`
- `./scripts/smoke-timeline.sh`
- `./run-live-example.sh`
- `./verify-live-stack.sh` (doctor + end-to-end flow)

Memory-related smoke checks require provider keys. MCP proof checks should run even without provider keys.

## PR conventions

- Keep changes scoped and explicit (no broad refactors).
- If you touch env behavior, update `.env*.example` and docs together.
- Document startup behavior changes in PR description with the exact commands and outcomes.
- Do not introduce or document an execution REST gateway for Nexus; MCP + socket boundary is the integration surface.
- Preserve script interfaces unless intentionally deprecating them.

## Support for contributors

- For runtime failures: include `.env` template used and logs from `./logs.sh`.
- For auth/secret issues: report exact output from `./doctor.sh` (and whether `ALLOW_UNAUTH_MANAGEMENT` is true).
