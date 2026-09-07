#!/usr/bin/env bash
#
# start.sh — start exactly the services selected by NEXUS_AEON_ENABLED.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_CYAN=$'\033[36m'
  C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
step() { printf '\n%s%s▸ %s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
ENV_FILE="${ROOT_DIR}/.env"

compose() { docker compose "$@"; }

if [[ ! -f "$ENV_FILE" ]]; then
  err "No .env found. Run ./install.sh first."
  exit 1
fi

# shellcheck source=scripts/runtime-mode.sh
source "${ROOT_DIR}/scripts/runtime-mode.sh"
nexusiq_resolve_runtime_mode "$ENV_FILE"
export NEXUS_AEON_ENABLED="$NEXUSIQ_AEON_ENABLED_NORMALIZED"

if [[ "$NEXUSIQ_MEMORY_MODE" == "disabled" ]]; then
  step "Stopping memory services disabled by configuration (volumes preserved)"
  if ! compose --profile memory stop aeon-worker aeon postgres; then
    err "Could not stop the disabled memory services."
    exit 1
  fi
  ok "memory containers stopped; PostgreSQL volume preserved"
fi

# Fail before starting any container. In explicit core mode, disabled memory
# services are stopped first so an unrelated execution-plane configuration
# error cannot leave the memory plane running.
bash "${ROOT_DIR}/scripts/validate-env.sh"

if [[ "$NEXUSIQ_MEMORY_MODE" == "enabled" ]]; then
  step "Starting memory services (postgres, aeon, aeon-worker)"
  if ! compose --profile memory up -d postgres aeon aeon-worker; then
    err "Memory service startup failed."
    exit 1
  fi
  bash "${ROOT_DIR}/scripts/wait-for-health.sh" postgres aeon aeon-worker

  step "Starting Nexus execution service"
  if ! compose up -d --no-deps nexus-agentd; then
    err "nexus-agentd startup failed."
    exit 1
  fi
else
  step "Starting Nexus execution service only"
  if ! compose up -d --no-deps nexus-agentd; then
    err "nexus-agentd startup failed."
    exit 1
  fi
fi

step "Waiting for nexus-agentd health"
bash "${ROOT_DIR}/scripts/wait-for-health.sh" nexus-agentd

step "Endpoints"
bash "${ROOT_DIR}/scripts/print-urls.sh"

printf '%sMCP:%s generate a client config with %s./generate-mcp-config.sh%s\n' \
  "$C_BOLD" "$C_RESET" "$C_DIM" "$C_RESET"
echo
ok "NexusIQ is up with memory ${NEXUSIQ_MEMORY_MODE}."
