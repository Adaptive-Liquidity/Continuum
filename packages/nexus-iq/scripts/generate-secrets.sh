#!/usr/bin/env bash
#
# generate-secrets.sh — fill blank secrets required by the selected mode.
#
# NEXUS_AGENTD_AUTH_TOKEN is always generated. AEON/PostgreSQL management,
# signing, and storage secrets are generated only when memory is enabled.
# Secret values are never printed.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
warn() { printf '%s⚠%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  err "No .env at ${ENV_FILE} — run install.sh first."
  exit 1
fi

# shellcheck source=scripts/runtime-mode.sh
source "${SCRIPT_DIR}/runtime-mode.sh"
nexusiq_resolve_runtime_mode "$ENV_FILE"

rand_hex() {
  local bytes="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$bytes"
  elif command -v xxd >/dev/null 2>&1; then
    head -c "$bytes" /dev/urandom | xxd -p | tr -d '\n'
  elif command -v od >/dev/null 2>&1; then
    head -c "$bytes" /dev/urandom | od -An -tx1 | tr -d ' \n'
  else
    err "No openssl, xxd, or od available to generate randomness."
    exit 1
  fi
}

get_val() {
  nexusiq_load_env "$ENV_FILE"
  nexusiq_env_get "$1"
}

has_key() {
  grep -qE "^$1=" "$ENV_FILE"
}

set_val() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
  if has_key "$key"; then
    KEY="$key" VALUE="$value" awk '
      BEGIN { k = ENVIRON["KEY"]; v = ENVIRON["VALUE"]; done = 0 }
      {
        if ($0 ~ "^" k "=") { print k "=" v; done = 1 }
        else { print }
      }
      END { if (!done) print k "=" v }
    ' "$ENV_FILE" >"$tmp"
  else
    cp "$ENV_FILE" "$tmp"
    if [[ -s "$tmp" && -n "$(tail -c 1 "$tmp")" ]]; then
      printf '\n' >>"$tmp"
    fi
    KEY="$key" VALUE="$value" awk \
      'BEGIN { print ENVIRON["KEY"] "=" ENVIRON["VALUE"] }' >>"$tmp"
  fi
  chmod 600 "$tmp" 2>/dev/null || true
  mv "$tmp" "$ENV_FILE"
}

ensure_secret() {
  local key="$1" bytes="${2:-32}" cur
  cur="$(get_val "$key")"
  if [[ -z "$cur" ]]; then
    set_val "$key" "$(rand_hex "$bytes")"
    ok "generated ${key}"
  else
    warn "${key} already set — left unchanged"
  fi
}

echo "Generating secrets required for memory ${NEXUSIQ_MEMORY_MODE} (values are never printed)..."

# Required in both core and memory modes.
ensure_secret NEXUS_AGENTD_AUTH_TOKEN 32

if [[ "$NEXUSIQ_MEMORY_MODE" == "enabled" ]]; then
  ensure_secret POSTGRES_PASSWORD 32
  ensure_secret MANAGEMENT_API_KEY 32

  hmac_cur="$(get_val NEXUS_AEON_HMAC_KEY)"
  if [[ -z "$hmac_cur" ]]; then
    set_val NEXUS_AEON_HMAC_KEY "$(rand_hex 32)"
    ok "generated NEXUS_AEON_HMAC_KEY"
  elif [[ ${#hmac_cur} -lt 64 || ! "$hmac_cur" =~ ^[0-9a-fA-F]+$ ]]; then
    set_val NEXUS_AEON_HMAC_KEY "$(rand_hex 32)"
    warn "NEXUS_AEON_HMAC_KEY was invalid — regenerated"
  else
    warn "NEXUS_AEON_HMAC_KEY already set — left unchanged"
  fi

  ensure_secret AEON_EVIDENCE_SIGNING_KEY 32

  mgmt_val="$(get_val MANAGEMENT_API_KEY)"
  if [[ -z "$mgmt_val" ]]; then
    err "MANAGEMENT_API_KEY is empty after generation — cannot cross-wire Nexus."
    exit 1
  fi
  aeon_mgmt_cur="$(get_val NEXUS_AEON_MANAGEMENT_KEY)"
  if [[ "$aeon_mgmt_cur" != "$mgmt_val" ]]; then
    set_val NEXUS_AEON_MANAGEMENT_KEY "$mgmt_val"
    ok "cross-wired NEXUS_AEON_MANAGEMENT_KEY = MANAGEMENT_API_KEY"
  else
    ok "NEXUS_AEON_MANAGEMENT_KEY already matches MANAGEMENT_API_KEY"
  fi

  db_url="$(get_val DATABASE_URL)"
  if [[ -n "$db_url" && "$db_url" != *'${POSTGRES_PASSWORD}'* && "$db_url" == *':'*'@'* ]]; then
    warn "DATABASE_URL appears to embed a literal password — prefer compose interpolation."
  fi
else
  ok "memory disabled — AEON/PostgreSQL secrets were not generated"
fi

chmod 600 "$ENV_FILE"
ok "secured ${ENV_FILE} (chmod 600)"
echo "Secret generation complete."
