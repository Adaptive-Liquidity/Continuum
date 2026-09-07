#!/usr/bin/env bash
#
# doctor.sh — mode-aware live health report for the NexusIQ self-host kit.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
  C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
ENV_FILE="${ROOT_DIR}/.env"
MGMT_HEADER_FILE=""

cleanup_doctor() {
  [[ -z "${MGMT_HEADER_FILE:-}" ]] || rm -f -- "$MGMT_HEADER_FILE"
}
trap cleanup_doctor EXIT

FAILS=0
WARNS=0
pass() { printf '%s✓%s %sPASS%s %s\n' "$C_GREEN" "$C_RESET" "$C_GREEN" "$C_RESET" "$*"; }
fail() { printf '%s✗%s %sFAIL%s %s\n' "$C_RED" "$C_RESET" "$C_RED" "$C_RESET" "$*" >&2; FAILS=$((FAILS + 1)); }
warn() { printf '%s⚠%s %sWARN%s %s\n' "$C_YELLOW" "$C_RESET" "$C_YELLOW" "$C_RESET" "$*"; WARNS=$((WARNS + 1)); }
info() { printf '%sINFO%s %s\n' "$C_CYAN" "$C_RESET" "$*"; }
heading() { printf '\n%s%s%s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

compose() { docker compose "$@"; }

heading "NexusIQ doctor — live health report"
if [[ ! -f "$ENV_FILE" ]]; then
  fail ".env missing at ${ENV_FILE} — run ./install.sh first"
  NEXUSIQ_MEMORY_MODE="unknown"
else
  pass ".env present and readable"
  # shellcheck source=scripts/runtime-mode.sh
  source "${ROOT_DIR}/scripts/runtime-mode.sh"
  if nexusiq_resolve_runtime_mode "$ENV_FILE"; then
    export NEXUS_AEON_ENABLED="$NEXUSIQ_AEON_ENABLED_NORMALIZED"
    info "selected mode: memory ${NEXUSIQ_MEMORY_MODE}"
  else
    fail "runtime mode configuration is invalid"
    NEXUSIQ_MEMORY_MODE="invalid"
  fi
fi

v() {
  if declare -F nexusiq_env_get >/dev/null 2>&1; then
    nexusiq_env_get "$1"
  fi
}

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  pass "Docker daemon running"
else
  fail "Docker daemon not running (or docker is not on PATH)"
fi
if docker compose version >/dev/null 2>&1; then
  pass "docker compose available"
else
  fail "docker compose plugin not available"
fi

if [[ -f "$ENV_FILE" ]]; then
  if bash "${ROOT_DIR}/scripts/validate-env.sh" >/dev/null; then
    pass "configuration valid for memory ${NEXUSIQ_MEMORY_MODE}"
  else
    fail "configuration invalid for memory ${NEXUSIQ_MEMORY_MODE:-unknown}; run ./scripts/validate-env.sh"
  fi
fi

default_services="$(compose config --services 2>/dev/null | sort || true)"
tools_services="$(compose --profile tools config --services 2>/dev/null | sort || true)"
memory_tools_services="$(compose --profile memory --profile tools config --services 2>/dev/null | sort || true)"
if [[ "$default_services" == "nexus-agentd" ]]; then
  pass "default Compose profile contains only nexus-agentd"
else
  fail "default Compose profile service set is unexpected"
fi
if [[ "$tools_services" == $'nexus-agentd\nnexus-mcp' ]]; then
  pass "tools profile adds nexus-mcp without memory services"
else
  fail "tools Compose profile service set is unexpected"
fi
for service in postgres aeon aeon-worker nexus-agentd nexus-mcp; do
  if grep -qx "$service" <<<"$memory_tools_services"; then
    pass "compose service defined: ${service}"
  else
    fail "compose service not defined in memory + tools profiles: ${service}"
  fi
done

if MSYS2_ARG_CONV_EXCL='/run/nexus' compose exec -T nexus-agentd \
  nexus daemon ping --socket /run/nexus/nexus-agentd.sock >/dev/null 2>&1; then
  pass "nexus-agentd live (daemon ping)"
elif MSYS2_ARG_CONV_EXCL='/run/nexus' compose exec -T nexus-agentd \
  test -S /run/nexus/nexus-agentd.sock >/dev/null 2>&1; then
  pass "nexus-agentd live (socket present)"
else
  fail "nexus-agentd not live"
fi

if bash "${ROOT_DIR}/scripts/smoke-nexus-execute.sh" >/dev/null 2>&1; then
  pass "nexus-mcp live (initialize and tools/list)"
else
  fail "nexus-mcp handshake or tool listing failed"
fi

for directory in data/proofs data/timeline data/modules; do
  absolute="${ROOT_DIR}/${directory}"
  mkdir -p "$absolute" 2>/dev/null || true
  marker="${absolute}/.doctor-write-test"
  if [[ -d "$absolute" ]] && touch "$marker" 2>/dev/null; then
    rm -f "$marker" 2>/dev/null || true
    pass "${directory} writable"
  else
    fail "${directory} not writable"
  fi
done

if [[ "$NEXUSIQ_MEMORY_MODE" == "disabled" ]]; then
  heading "Memory plane"
  info "memory plane disabled by configuration"
  for service in postgres aeon aeon-worker; do
    container_id="$(compose --profile memory ps -a -q "$service" 2>/dev/null | head -n1 || true)"
    running="false"
    if [[ -n "$container_id" ]]; then
      running="$(docker inspect -f '{{.State.Running}}' "$container_id" 2>/dev/null || true)"
    fi
    if [[ "$running" == "true" ]]; then
      fail "${service} is running while memory is disabled"
    else
      pass "${service} is not running"
    fi
  done
elif [[ "$NEXUSIQ_MEMORY_MODE" == "enabled" ]]; then
  heading "Memory plane"
  PG_USER="$(v POSTGRES_USER)"; PG_USER="${PG_USER:-nexusiq}"
  PG_DB="$(v POSTGRES_DB)"; PG_DB="${PG_DB:-nexusiq}"
  if compose --profile memory exec -T postgres \
    pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
    pass "PostgreSQL healthy (pg_isready)"
  else
    fail "PostgreSQL not accepting connections"
  fi

  AEON_PORT="$(v AEON_PORT)"; AEON_PORT="${AEON_PORT:-8080}"
  AEON_BASE="http://127.0.0.1:${AEON_PORT}"
  health_code="$(curl -sS -m 10 -o /dev/null -w '%{http_code}' "${AEON_BASE}/health" 2>/dev/null || true)"
  if [[ "$health_code" == "200" ]]; then
    pass "AEON-IQ /health returns 200"
  else
    fail "AEON-IQ /health did not return 200"
  fi
  if compose --profile memory exec -T aeon-worker \
    curl -sf -m 10 http://localhost:8080/health >/dev/null 2>&1; then
    pass "AEON-IQ worker /health returns 200"
  else
    fail "AEON-IQ worker health check failed"
  fi

  MGMT_KEY="$(v MANAGEMENT_API_KEY)"
  if [[ -z "$MGMT_KEY" ]]; then
    fail "MANAGEMENT_API_KEY missing — cannot test AEON authentication"
  else
    MGMT_HEADER_FILE="$(mktemp)"
    chmod 600 "$MGMT_HEADER_FILE"
    printf 'X-Management-Key: %s\n' "$MGMT_KEY" >"$MGMT_HEADER_FILE"
    authed_code="$(curl -sS -m 10 -o /dev/null -w '%{http_code}' \
      -H "@${MGMT_HEADER_FILE}" "${AEON_BASE}/api/v1/stats" 2>/dev/null || true)"
    unauth_code="$(curl -sS -m 10 -o /dev/null -w '%{http_code}' \
      "${AEON_BASE}/api/v1/stats" 2>/dev/null || true)"
    if [[ "$authed_code" == "200" ]]; then
      pass "AEON-IQ management API accepts the configured key"
    else
      fail "AEON-IQ authenticated management request failed"
    fi
    if [[ "$unauth_code" == "401" || "$unauth_code" == "403" ]]; then
      pass "AEON-IQ management API rejects unauthenticated requests"
    else
      fail "AEON-IQ management API did not reject an unauthenticated request"
    fi
  fi

  provider="$(printf '%s' "$(v UPSTREAM_PROVIDER)" | tr '[:upper:]' '[:lower:]')"
  case "$provider" in
    openai|anthropic|gemini) provider_value="$(v OPENAI_API_KEY)" ;;
    ollama) provider_value="$(v UPSTREAM_BASE_URL)" ;;
    *) provider_value="" ;;
  esac
  if [[ -n "$provider_value" ]]; then
    pass "provider configuration present for UPSTREAM_PROVIDER=${provider}"
  else
    fail "provider configuration missing for UPSTREAM_PROVIDER=${provider:-unset}"
  fi

  verifying_key="$(v NEXUS_AEON_VERIFYING_KEY)"
  if [[ -z "$verifying_key" ]]; then
    warn "NEXUS_AEON_VERIFYING_KEY is not pinned; memory evidence remains Advisory"
  else
    reported=""
    if [[ -n "$MGMT_HEADER_FILE" ]]; then
      reported="$(curl -sf -m 10 -H "@${MGMT_HEADER_FILE}" \
        "${AEON_BASE}/api/v1/evidence/verifying-key" 2>/dev/null || true)"
    fi
    reported_key="$(printf '%s' "$reported" | sed -n 's/.*"key_id":"\([0-9a-f]*\)".*/\1/p')"
    reported_persistent="$(printf '%s' "$reported" | grep -o '"persistent":[a-z]*' | cut -d: -f2)"
    if [[ -z "$reported_key" ]]; then
      warn "could not read AEON-IQ evidence verifying key"
    elif [[ "$reported_key" != "$verifying_key" ]]; then
      fail "NEXUS_AEON_VERIFYING_KEY does not match AEON-IQ"
    elif [[ "$reported_persistent" != "true" ]]; then
      fail "AEON-IQ evidence signing key is ephemeral"
    else
      pass "evidence verifying key is pinned, matching, and persistent"
    fi
  fi
fi

heading "Summary"
if [[ "$FAILS" -eq 0 ]]; then
  printf '%s✓ doctor: all required checks passed for memory %s%s' \
    "$C_GREEN" "$NEXUSIQ_MEMORY_MODE" "$C_RESET"
  [[ "$WARNS" -gt 0 ]] && printf ' (%d warning(s))' "$WARNS"
  printf '\n'
  exit 0
fi
printf '%s✗ doctor: %d required check(s) failed%s\n' "$C_RED" "$FAILS" "$C_RESET"
exit 1
