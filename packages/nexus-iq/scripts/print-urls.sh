#!/usr/bin/env bash
#
# print-urls.sh — print only endpoints enabled by the selected runtime mode.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  printf 'print-urls: .env is missing; run ./install.sh first.\n' >&2
  exit 1
fi

# shellcheck source=scripts/runtime-mode.sh
source "${SCRIPT_DIR}/runtime-mode.sh"
if ! nexusiq_resolve_runtime_mode "$ENV_FILE"; then
  printf 'print-urls: runtime mode configuration is invalid.\n' >&2
  exit 1
fi

printf '\n%s%sNexusIQ — active surfaces%s\n' "$C_BOLD" "$C_CYAN" "$C_RESET"
printf '  %sMemory%s              %s\n' "$C_BOLD" "$C_RESET" "$NEXUSIQ_MEMORY_MODE"
printf '  %sMCP (stdio)%s         ./connect-mcp.sh %s(agentd must already be healthy)%s\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
printf '  %sMCP config%s          ./generate-mcp-config.sh\n' "$C_BOLD" "$C_RESET"

if [[ "$NEXUSIQ_MEMORY_MODE" == "enabled" ]]; then
  AEON_PORT="$(nexusiq_env_get AEON_PORT)"
  AEON_PORT="${AEON_PORT:-8080}"
  AEON_BASE="http://127.0.0.1:${AEON_PORT}"
  printf '\n  %sAEON-IQ API%s         %s\n' "$C_BOLD" "$C_RESET" "$AEON_BASE"
  printf '  %sAEON health%s         %s/health\n' "$C_BOLD" "$C_RESET" "$AEON_BASE"
  printf '  %sManagement base%s     %s/api/v1 %s(X-Management-Key required)%s\n' \
    "$C_BOLD" "$C_RESET" "$AEON_BASE" "$C_DIM" "$C_RESET"
  printf '\n%sNote:%s PostgreSQL remains internal; AEON is loopback-only.\n' \
    "$C_BOLD" "$C_RESET"
else
  printf '\n%sMemory plane disabled by configuration.%s No AEON endpoint is active.\n' \
    "$C_DIM" "$C_RESET"
fi
echo
