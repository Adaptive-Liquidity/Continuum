# NexusIQ — Quick Start

The default install is provider-keyless core mode: Nexus execution, sandboxing,
MCP, and Proof Capsules without the AEON memory plane.

---

## Prerequisites

- Docker Engine + Compose v2 plugin ([install](https://docs.docker.com/engine/install/))
- Bash 4.0 or newer, `curl`, and `git` on the host

No model-provider credential is required.

---

## Steps

### 1. Install and start core mode

```bash
git clone https://github.com/Adaptive-Liquidity/Nexus-IQ-temp.git
cd Nexus-IQ-temp
./install.sh --start
```

The installer creates `.env` with `NEXUS_AEON_ENABLED=false`, generates the
internal agentd authentication token, vendors/builds only Nexus, and bakes the
sample WASM module. Subsequent source builds use the Docker cache.

### 2. Verify

```bash
./doctor.sh
```

Every line should show `PASS`. If anything shows `FAIL`, see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### 3. Connect your MCP client

```bash
./generate-mcp-config.sh
```

Writes `mcp/claude-desktop.json`, `mcp/cursor.json`, `mcp/openhands.json`,
and `mcp/generic-mcp.json` with absolute paths baked in.

Paste the contents of the appropriate file into your MCP client config, then
restart the client. The `nexusiq` server will appear in the tools list.

---

Core mode is now running. Your MCP client can invoke `nexus_execute_proof` and
related tools; memory write and recall are intentionally unavailable.

Verify execution, a real Proof Capsule, and the selected service set:

```bash
./scripts/smoke-nexus-execute.sh
./scripts/smoke-proof-capsule.sh
./verify-live-stack.sh
```

---

## What runs in core mode

| Service | State |
|---|---|
| Nexus daemon | Running on its container-internal Unix socket |
| Nexus MCP server | Launched on demand through `connect-mcp.sh` |
| PostgreSQL | Not started |
| AEON proxy | Not started |
| AEON worker | Not started |

## Enable memory explicitly

Memory mode requires a real supported provider configuration. Configure the
provider in `.env`, set `NEXUS_AEON_ENABLED=true`, and then run:

```bash
./install.sh
./start.sh
./doctor.sh
```

Validation fails before vendoring, building, pulling, or starting if an
explicit memory request is missing its provider or required security settings.
See [INSTALL.md](INSTALL.md) and [OPERATIONS.md](OPERATIONS.md) for details.
