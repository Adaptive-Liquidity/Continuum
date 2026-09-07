#!/usr/bin/env bash
#
# smoke-timeline.sh — live AEON-IQ timeline write.
#
# Single concern: POST a timeline event to
# /api/v1/agents/<agent>/timeline and report the delivery status. Timeline
# recording does not embed text, so it does NOT require a provider key — but it
# DOES require the management key for auth.
#
# Prints exactly one of:
#   Timeline event status: delivered    (HTTP 2xx)
#   Timeline event status: failed-open  (AEON returned an error but accepted)
#   Timeline event status: unavailable  (AEON unreachable)
#
# Exit codes: 0 = delivered; 1 = failed-open or unavailable.
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
ENV_FILE="${ROOT_DIR}/.env"

# ---- safe .env loader -------------------------------------------------------
[[ -f "$ENV_FILE" ]] || { err "No .env at ${ENV_FILE} — run install.sh first."; exit 1; }
# shellcheck source=scripts/runtime-mode.sh
source "${SCRIPT_DIR}/runtime-mode.sh"
if ! nexusiq_resolve_runtime_mode "$ENV_FILE"; then
  err "Invalid runtime-mode configuration in ${ENV_FILE}."
  exit 1
fi
v() { nexusiq_env_get "$1"; }

AEON_PORT="$(v AEON_PORT)"; AEON_PORT="${AEON_PORT:-8080}"
AEON_BASE="http://127.0.0.1:${AEON_PORT}"
MGMT_KEY="$(v MANAGEMENT_API_KEY)"
AGENT="$(v NEXUS_AEON_AGENT_ID)"; AGENT="${AGENT:-nexusiq}"

if [[ -z "$MGMT_KEY" ]]; then
  err "MANAGEMENT_API_KEY missing in .env — cannot authenticate to AEON."
  printf 'Timeline event status: unavailable\n'
  exit 1
fi

# Event payload. Override the whole body via $SMOKE_TIMELINE_BODY (e.g. the
# example flow passes the events returned by nexus_execute_proof).
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
body="${SMOKE_TIMELINE_BODY:-$(printf '{"event_type":"proof_capsule_emitted","capsule_digest":"smoke-%s"}' "$ts")}"

resp="$(curl -sS -m 20 -w $'\n%{http_code}' \
  -X POST "${AEON_BASE}/api/v1/agents/${AGENT}/timeline" \
  -H "X-Management-Key: ${MGMT_KEY}" \
  -H "Content-Type: application/json" \
  -d "$body" 2>/dev/null || true)"

if [[ -z "$resp" ]]; then
  err "timeline: AEON unreachable at ${AEON_BASE}"
  printf 'Timeline event status: unavailable\n'
  exit 1
fi

http_code="${resp##*$'\n'}"
payload="${resp%$'\n'*}"

case "$http_code" in
  2??)
    ok "timeline: event recorded for agent=${AGENT} at ${ts}"
    printf 'Timeline event status: delivered\n'
    printf '%sQuery it:%s curl -fsS -H "X-Management-Key: \$MANAGEMENT_API_KEY" "%s/api/v1/agents/%s/timeline/at?...”\n' \
      "$C_DIM" "$C_RESET" "$AEON_BASE" "$AGENT"
    exit 0
    ;;
  000|"")
    err "timeline: AEON unreachable at ${AEON_BASE}"
    printf 'Timeline event status: unavailable\n'
    exit 1
    ;;
  *)
    err "timeline: AEON returned HTTP ${http_code}"
    printf '%s%s%s\n' "$C_DIM" "$payload" "$C_RESET" >&2
    printf 'Timeline event status: failed-open\n'
    exit 1
    ;;
esac
