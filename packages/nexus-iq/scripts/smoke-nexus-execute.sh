#!/usr/bin/env bash
#
# smoke-nexus-execute.sh — live Nexus MCP handshake + tool listing.
#
# Single concern: open the STDIO MCP pipe via connect-mcp.sh, perform the
# JSON-RPC handshake (initialize → notifications/initialized → tools/list),
# and assert the server advertises the expected Nexus tools. This proves the
# MCP server is alive and the nexus-mcp ↔ nexus-agentd wiring is reachable.
# It does NOT need a provider key (no embeddings involved).
#
# Exit codes: 0 = tools listed; 1 = handshake failed / no tools.
#
set -euo pipefail

# ---- colored helpers --------------------------------------------------------
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_DIM=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n'  "$C_GREEN"  "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n'  "$C_RED"    "$C_RESET" "$*" >&2; }
warn() { printf '%s⚠%s %s\n'  "$C_YELLOW" "$C_RESET" "$*"; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONNECT="${ROOT_DIR}/connect-mcp.sh"

if [[ ! -x "$CONNECT" && ! -f "$CONNECT" ]]; then
  err "connect-mcp.sh not found at ${CONNECT}"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  err "neither jq nor python3 available — cannot parse the JSON-RPC response."
  exit 1
fi

# ---- JSON-RPC request stream (handshake) ------------------------------------
# One JSON object per line (newline-delimited). The MCP server reads requests
# from stdin and writes responses to stdout.
mcp_handshake_requests() {
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"nexusiq-smoke","version":"1.0.0"}}}'
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  printf '%s\n' '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
}

# Run the pipe. connect-mcp.sh logs to stderr only; capture stdout (JSON-RPC).
out="$(mcp_handshake_requests | timeout 90 bash "$CONNECT" 2>/dev/null || true)"

if [[ -z "$out" ]]; then
  err "nexus-execute: no response from MCP server (connect-mcp.sh produced no stdout)."
  warn "Is the stack up?  Try: ./start.sh  then re-run."
  exit 1
fi

# ---- extract tool names from the tools/list response ------------------------
# The MCP server may emit several JSON objects (one per line). Find the one
# whose result has a .tools array and collect the names.
extract_tools() {
  if command -v jq >/dev/null 2>&1; then
    # Slurp every line that is valid JSON; pick objects with .result.tools.
    printf '%s\n' "$out" \
      | jq -rc 'select(type=="object") | .result.tools[]?.name' 2>/dev/null
  else
    printf '%s\n' "$out" | python3 -c '
import sys, json
names = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if isinstance(obj, dict):
        tools = (obj.get("result") or {}).get("tools")
        if isinstance(tools, list):
            for t in tools:
                if isinstance(t, dict) and t.get("name"):
                    names.append(t["name"])
for n in names:
    print(n)
'
  fi
}

mapfile -t TOOLS < <(extract_tools)

if [[ "${#TOOLS[@]}" -eq 0 ]]; then
  err "nexus-execute: handshake produced no tools list."
  printf '%sraw response (truncated):%s\n' "$C_DIM" "$C_RESET" >&2
  printf '%s%.800s%s\n' "$C_DIM" "$out" "$C_RESET" >&2
  exit 1
fi

ok "nexus-execute: MCP server live — ${#TOOLS[@]} tool(s) advertised."
printf '%s  %s%s\n' "$C_DIM" "$(printf '%s, ' "${TOOLS[@]}" | sed 's/, $//')" "$C_RESET"

# Sanity: the proof/execute tools we depend on should be present.
need=(nexus_execute_proof nexus_get_stats)
missing=()
for t in "${need[@]}"; do
  printf '%s\n' "${TOOLS[@]}" | grep -qx "$t" || missing+=("$t")
done
if [[ "${#missing[@]}" -ne 0 ]]; then
  warn "expected tool(s) not advertised: ${missing[*]} (server may be a different build)."
fi
