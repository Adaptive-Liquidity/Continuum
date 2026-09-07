#!/usr/bin/env bash
#
# generate-mcp-config.sh — emit ready-to-paste MCP client configs for NexusIQ.
#
# Writes concrete JSON (absolute paths baked in) into ./mcp/ for:
#   - Claude Desktop   (mcp/claude-desktop.json)
#   - Cursor           (mcp/cursor.json)
#   - OpenHands        (mcp/openhands.json)
#   - generic MCP      (mcp/generic-mcp.json)
#
# Then prints the platform-specific locations to install each one. The
# `command` is the ABSOLUTE path to connect-mcp.sh and env.NEXUSIQ_SELFHOST_DIR
# is the absolute kit directory, so the config works regardless of the client's
# working directory.
#
set -euo pipefail

# ---- colored helpers --------------------------------------------------------
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
  C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n'  "$C_GREEN"  "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n'  "$C_RED"    "$C_RESET" "$*" >&2; }
warn() { printf '%s⚠%s %s\n'  "$C_YELLOW" "$C_RESET" "$*"; }
head() { printf '\n%s%s%s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

# ---- resolve absolute kit directory -----------------------------------------
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONNECT="${ROOT_DIR}/connect-mcp.sh"
MCP_DIR="${ROOT_DIR}/mcp"

if [[ ! -f "$CONNECT" ]]; then
  err "connect-mcp.sh not found at ${CONNECT} — cannot generate configs."
  exit 1
fi
chmod +x "$CONNECT" 2>/dev/null || true
mkdir -p "$MCP_DIR"

# ---- JSON string escaper (paths may contain spaces / backslashes) -----------
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"   # backslash
  s="${s//\"/\\\"}"   # double quote
  printf '%s' "$s"
}
CONNECT_J="$(json_escape "$CONNECT")"
ROOT_J="$(json_escape "$ROOT_DIR")"

# ---- the canonical config block (same shape as mcp/*.json.example) ----------
emit_config() {
  cat <<JSON
{
  "mcpServers": {
    "nexusiq": {
      "command": "${CONNECT_J}",
      "args": [],
      "env": {
        "NEXUSIQ_SELFHOST_DIR": "${ROOT_J}"
      }
    }
  }
}
JSON
}

head "Generating MCP client configs in ${MCP_DIR}"
for client in claude-desktop cursor openhands generic-mcp; do
  out="${MCP_DIR}/${client}.json"
  emit_config > "$out"
  ok "wrote ${out#"$ROOT_DIR"/}"
done

# ---- print platform-specific install locations ------------------------------
head "Where to install each config"

printf '\n%sClaude Desktop%s — paste the contents of %smcp/claude-desktop.json%s into:\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
printf '  %smacOS:%s   ~/Library/Application Support/Claude/claude_desktop_config.json\n' "$C_DIM" "$C_RESET"
printf '  %sWindows:%s %%APPDATA%%/Claude/claude_desktop_config.json\n' "$C_DIM" "$C_RESET"
printf '  %sLinux:%s   ~/.config/Claude/claude_desktop_config.json\n' "$C_DIM" "$C_RESET"

printf '\n%sCursor%s — paste the contents of %smcp/cursor.json%s into:\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
printf '  %sProject:%s <project>/.cursor/mcp.json\n' "$C_DIM" "$C_RESET"
printf '  %sGlobal:%s  ~/.cursor/mcp.json\n' "$C_DIM" "$C_RESET"

printf '\n%sOpenHands%s — paste the contents of %smcp/openhands.json%s into your\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
printf '  OpenHands MCP settings (config.toml [mcp] / Settings → MCP), key %snexusiq%s.\n' "$C_DIM" "$C_RESET"

printf '\n%sGeneric MCP client%s — use %smcp/generic-mcp.json%s as the server entry\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
printf '  (server key %snexusiq%s; STDIO transport; command is connect-mcp.sh).\n' "$C_DIM" "$C_RESET"

if [[ "$ROOT_DIR" == *" "* ]]; then
  warn "Kit path contains spaces; the JSON is escaped but verify your client tolerates it."
fi

printf '\n'
ok "MCP configs generated. The command path is absolute: ${CONNECT}"
printf '%sTest the pipe with:%s ./doctor.sh   (runs an initialize+tools/list handshake)\n' \
  "$C_DIM" "$C_RESET"
