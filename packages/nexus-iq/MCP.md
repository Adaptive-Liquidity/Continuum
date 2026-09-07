# MCP Integration

This repo exposes execution only through MCP over STDIO. There is **no** REST execution gateway.

- Entry point: `./connect-mcp.sh`
- Server container: `docker compose --profile tools run --rm -T nexus-mcp`
- Shared socket: `/run/nexus/nexus-agentd.sock` in `./data/run`

## Generate MCP client configs

Use:

```bash
./generate-mcp-config.sh
```

This writes:

- `mcp/claude-desktop.json`
- `mcp/cursor.json`
- `mcp/openhands.json`
- `mcp/generic-mcp.json`

Each config contains:

```json
{
  "mcpServers": {
    "nexusiq": {
      "command": "/absolute/path/to/nexusiq/connect-mcp.sh",
      "args": [],
      "env": {
        "NEXUSIQ_SELFHOST_DIR": "/absolute/path/to/nexusiq"
      }
    }
  }
}
```

## Config files (example set)

- `mcp/claude-desktop.json.example`
- `mcp/cursor.json.example`
- `mcp/openhands.json.example`
- `mcp/generic-mcp.json.example`

They are identical shape and only differ in where each client expects the MCP server block.

## Runtime behavior

`connect-mcp.sh`:

- logs diagnostics to `stderr`
- executes `docker compose ... run --rm -T nexus-mcp`
- keeps the MCP conversation on stdin/stdout JSON-RPC 2.0

`nexus-mcp` is started per MCP session and exits when the client disconnects.

## Tool list

Smoke checks validate these at minimum:

- `nexus_execute_proof`
- `nexus_get_stats`

Current docs and implementation also list:

- `nexus_attenuate_token`
- memory capabilities/operations tied to `ReadMemory` / `WriteMemory`

Use:

- `./scripts/smoke-nexus-execute.sh`
- `./scripts/smoke-proof-capsule.sh`
- `./scripts/smoke-timeline.sh`
- `./run-live-example.sh`

## Client installation

- Claude Desktop: `mcp/claude-desktop.json`
- Cursor: `mcp/cursor.json`
- OpenHands: `mcp/openhands.json`
- Generic: `mcp/generic-mcp.json`

For all clients, the command must point to a valid absolute `connect-mcp.sh`.
