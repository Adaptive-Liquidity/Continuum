#!/usr/bin/env bash
#
# validate-env.sh — assert the selected NexusIQ runtime mode is complete,
# internally consistent, authenticated, and free of mock/test switches.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_RESET=''
fi
ok()  { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
err() { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

# shellcheck source=scripts/runtime-mode.sh
source "${SCRIPT_DIR}/runtime-mode.sh"

if [[ ! -f "$ENV_FILE" ]]; then
  err "No .env at ${ENV_FILE} — run install.sh first."
  exit 1
fi
if ! nexusiq_resolve_runtime_mode "$ENV_FILE"; then
  exit 1
fi

v() { nexusiq_env_get "$1"; }

ERRORS=0
fail() {
  err "$*"
  ERRORS=$((ERRORS + 1))
}

require_nonempty() {
  local key="$1"
  if [[ -z "$(v "$key")" ]]; then
    fail "required variable ${key} is missing or empty"
  fi
}

is_truthy() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    true|1|yes|on|enabled) return 0 ;;
    *) return 1 ;;
  esac
}

# The execution plane is always authenticated, including memory-disabled mode.
require_nonempty NEXUS_AGENTD_AUTH_TOKEN

# Unauthenticated management and mock/test/synthetic switches are forbidden in
# every mode, even when the affected service is intentionally not running.
allow_unauth="$(printf '%s' "$(v ALLOW_UNAUTH_MANAGEMENT)" | tr '[:upper:]' '[:lower:]')"
allow_unauth_count="${NEXUSIQ_ENV_OCCURRENCES[ALLOW_UNAUTH_MANAGEMENT]:-0}"
if [[ "$allow_unauth_count" -gt 0 && "$allow_unauth" != "false" ]]; then
  fail "ALLOW_UNAUTH_MANAGEMENT must be exactly false when set (unauthenticated management is forbidden)"
fi
for key in "${!NEXUSIQ_ENV[@]}"; do
  case "$key" in
    MOCK_*|*SYNTHETIC*|TEST_MODE|BENCH_MODE)
      if is_truthy "${NEXUSIQ_ENV[$key]}"; then
        fail "mock/test variable ${key} is truthy — not allowed in a real deployment"
      fi
      ;;
  esac
done

if [[ "$NEXUSIQ_MEMORY_MODE" == "enabled" ]]; then
  for key in \
    POSTGRES_PASSWORD \
    MANAGEMENT_API_KEY \
    POSTGRES_USER \
    POSTGRES_DB \
    NEXUS_AEON_MANAGEMENT_KEY \
    NEXUS_AEON_HMAC_KEY \
    UPSTREAM_PROVIDER
  do
    require_nonempty "$key"
  done

  hmac="$(v NEXUS_AEON_HMAC_KEY)"
  if [[ -n "$hmac" ]]; then
    if [[ ${#hmac} -lt 64 ]]; then
      fail "NEXUS_AEON_HMAC_KEY must be >=64 hex chars (>=32 bytes); got ${#hmac} chars"
    elif [[ ! "$hmac" =~ ^[0-9a-fA-F]+$ ]]; then
      fail "NEXUS_AEON_HMAC_KEY must be hexadecimal"
    fi
  fi

  mgmt="$(v MANAGEMENT_API_KEY)"
  aeon_mgmt="$(v NEXUS_AEON_MANAGEMENT_KEY)"
  if [[ -n "$mgmt" && "$aeon_mgmt" != "$mgmt" ]]; then
    fail "NEXUS_AEON_MANAGEMENT_KEY must equal MANAGEMENT_API_KEY (cross-wired secret mismatch)"
  fi

  provider="$(v UPSTREAM_PROVIDER)"
  provider_lc="$(printf '%s' "$provider" | tr '[:upper:]' '[:lower:]')"
  case "$provider_lc" in
    openai|anthropic|gemini)
      [[ -z "$(v OPENAI_API_KEY)" ]] &&
        fail "UPSTREAM_PROVIDER=${provider_lc} requires OPENAI_API_KEY (AEON's single upstream-key slot) to be set"
      ;;
    ollama)
      [[ -z "$(v UPSTREAM_BASE_URL)" ]] &&
        fail "UPSTREAM_PROVIDER=ollama requires UPSTREAM_BASE_URL to be set"
      ;;
    "")
      # The required-variable check above owns the missing-provider diagnostic.
      ;;
    *)
      fail "UPSTREAM_PROVIDER='${provider}' is not recognized (expected: openai, anthropic, gemini, ollama)"
      ;;
  esac
fi

if [[ "$ERRORS" -ne 0 ]]; then
  echo
  err "validate-env: ${ERRORS} problem(s) found for memory ${NEXUSIQ_MEMORY_MODE} — fix the above and re-run."
  exit 1
fi

if [[ "$NEXUSIQ_MEMORY_MODE" == "disabled" ]]; then
  ok "validate-env: memory disabled; execution-plane authentication and safety checks passed. No provider credential is required."
else
  ok "validate-env: memory enabled; AEON/PostgreSQL secrets, provider configuration, cross-wiring, and safety checks passed."
fi
