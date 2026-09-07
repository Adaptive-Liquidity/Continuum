#!/usr/bin/env bash
#
# smoke-memory-recall.sh — live AEON-IQ memory search.
#
# Single concern: write a unique memory through AEON-IQ, then recall it with
# POST /api/v1/memories/search. This exercises the embedding path for both
# create and search, so it REQUIRES a real provider key. If the provider rejects
# either embedding call we surface the real HTTP status — we never fake a hit.
#
# Exit codes: 0 = AEON wrote and recalled the memory; 1 = failed (HTTP error,
# embedding failure, AEON unreachable, or recalled payload missing the marker).
# Set $SMOKE_QUERY to override the recall query.
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

# ---- safe .env loader (never executes the file) -----------------------------
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
MARKER="${SMOKE_MARKER:-live-$(date -u +%Y%m%dT%H%M%SZ)-${RANDOM}${RANDOM}}"
MEMORY_CONTENT="${SMOKE_MEMORY_CONTENT:-NexusIQ memory recall marker ${MARKER}: AEON wrote and recalled this pre-release smoke memory.}"
QUERY="${SMOKE_QUERY:-${MEMORY_CONTENT}}"

if [[ -z "$MGMT_KEY" ]]; then
  err "MANAGEMENT_API_KEY missing in .env — cannot authenticate to AEON."
  exit 1
fi

create_body="$(printf '{"content":"%s","memory_type":"episodic"}' "$MEMORY_CONTENT")"
create_resp="$(curl -sS -m 60 -w $'\n%{http_code}' \
  -X POST "${AEON_BASE}/api/v1/agents/${AGENT}/memories" \
  -H "X-Management-Key: ${MGMT_KEY}" \
  -H "Content-Type: application/json" \
  -d "$create_body" 2>/dev/null || true)"

if [[ -z "$create_resp" ]]; then
  err "memory-recall: AEON unreachable at ${AEON_BASE} during memory create"
  exit 1
fi

create_http_code="${create_resp##*$'\n'}"
create_payload="${create_resp%$'\n'*}"

if [[ "$create_http_code" != "200" ]]; then
  err "memory-recall: create returned HTTP ${create_http_code}"
  printf '%s%s%s\n' "$C_DIM" "$create_payload" "$C_RESET" >&2
  if printf '%s' "$create_payload" | grep -qiE 'embed|openai|api key|unauthorized.*provider|insufficient'; then
    warn "Looks like an embedding/provider failure — set a valid OPENAI_API_KEY (or configured provider) so AEON can embed new memories."
  fi
  exit 1
fi

ok "memory-recall: AEON created memory (agent=${AGENT}, marker=${MARKER})"
printf '%s%s%s\n' "$C_DIM" "$create_payload" "$C_RESET"

body="$(printf '{"agent_id":"%s","query":"%s","limit":5,"threshold":0.95}' "$AGENT" "$QUERY")"

# Capture body + HTTP status in one curl call.
resp="$(curl -sS -m 60 -w $'\n%{http_code}' \
  -X POST "${AEON_BASE}/api/v1/memories/search" \
  -H "X-Management-Key: ${MGMT_KEY}" \
  -H "Content-Type: application/json" \
  -d "$body" 2>/dev/null || true)"

if [[ -z "$resp" ]]; then
  err "memory-recall: AEON unreachable at ${AEON_BASE} (is the stack up?)"
  exit 1
fi

http_code="${resp##*$'\n'}"
payload="${resp%$'\n'*}"

if [[ "$http_code" != "200" ]]; then
  err "memory-recall: search returned HTTP ${http_code}"
  printf '%s%s%s\n' "$C_DIM" "$payload" "$C_RESET" >&2
  if printf '%s' "$payload" | grep -qiE 'embed|openai|api key|unauthorized.*provider|insufficient'; then
    warn "Looks like an embedding/provider failure — set a valid OPENAI_API_KEY (or configured provider) so search can embed the query."
  fi
  exit 1
fi

if ! printf '%s' "$payload" | grep -F "$MARKER" >/dev/null 2>&1; then
  err "memory-recall: search returned HTTP 200 but did not recall marker ${MARKER}"
  printf '%s%s%s\n' "$C_DIM" "$payload" "$C_RESET" >&2
  exit 1
fi

ok "memory-recall: AEON search returned HTTP 200 and recalled marker ${MARKER} (agent=${AGENT})"
printf '%s%s%s\n' "$C_DIM" "$payload" "$C_RESET"
