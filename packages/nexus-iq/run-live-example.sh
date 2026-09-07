#!/usr/bin/env bash
#
# run-live-example.sh — the REAL end-to-end NexusIQ user flow.
#
# No mocks, no synthetic data. Every step runs live against the running stack
# and prints what it did + where to inspect the result. Steps that can't run
# live FAIL CLEARLY (✗) with the real error.
#
# Flow:
#   (a) write a memory  → POST /api/v1/agents/$AGENT/memories
#   (b) recall          → POST /api/v1/memories/search
#   (c) Nexus execution → tools/call nexus_execute_proof (sample_tool.wasm)
#   (d) extract proof   → write ./data/proofs/<capsule_id>.json
#   (e) timeline        → POST returned events to /api/v1/agents/$AGENT/timeline
#   (f) print where to inspect proofs + how to query the timeline
#
# The memory legs (a,b) need a real embedding provider key; the Nexus legs
# (c,d) do not. A missing key fails (a)/(b) cleanly but the Nexus leg still runs.
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
step() { printf '\n%s%s▸ %s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }
dim()  { printf '%s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
ENV_FILE="${ROOT_DIR}/.env"
CONNECT="${ROOT_DIR}/connect-mcp.sh"
PROOF_DIR="${ROOT_DIR}/data/proofs"
MODULE_PATH="${SMOKE_MODULE:-/modules/sample_tool.wasm}"
HOST_MODULE="${ROOT_DIR}/data/modules/$(basename "$MODULE_PATH")"

mkdir -p "$PROOF_DIR"

# ---- safe .env loader -------------------------------------------------------
[[ -f "$ENV_FILE" ]] || { err "No .env at ${ENV_FILE} — run ./install.sh first."; exit 1; }
# shellcheck source=scripts/runtime-mode.sh
source "${ROOT_DIR}/scripts/runtime-mode.sh"
if ! nexusiq_resolve_runtime_mode "$ENV_FILE"; then
  err "Invalid runtime-mode configuration in ${ENV_FILE}."
  exit 1
fi
v() { nexusiq_env_get "$1"; }

AEON_PORT="$(v AEON_PORT)"; AEON_PORT="${AEON_PORT:-8080}"
AEON_BASE="http://127.0.0.1:${AEON_PORT}"
MGMT_KEY="$(v MANAGEMENT_API_KEY)"
AGENT="$(v NEXUS_AEON_AGENT_ID)"; AGENT="${AGENT:-nexusiq}"

# JSON extraction backend (jq preferred, python3 fallback).
HAVE_JQ=0; HAVE_PY=0
command -v jq      >/dev/null 2>&1 && HAVE_JQ=1
command -v python3 >/dev/null 2>&1 && HAVE_PY=1
if [[ "$HAVE_JQ" -eq 0 && "$HAVE_PY" -eq 0 ]]; then
  err "neither jq nor python3 available — cannot parse JSON responses."
  exit 1
fi

if [[ -z "$MGMT_KEY" ]]; then
  err "MANAGEMENT_API_KEY missing in .env — AEON legs (a,b,e) cannot authenticate."
fi

OVERALL_FAIL=0
note_fail() { OVERALL_FAIL=1; }

UNIQ="live-$(date -u +%Y%m%dT%H%M%SZ)-$$"
MEM_CONTENT="NexusIQ live validation marker ${UNIQ}: the self-host kit executed a WASM module and recorded a proof capsule."

# ════════════════════════════════════════════════════════════════════════════
# (a) WRITE A MEMORY
# ════════════════════════════════════════════════════════════════════════════
step "(a) Write a memory → POST /api/v1/agents/${AGENT}/memories"
if [[ -z "$MGMT_KEY" ]]; then
  err "skipped: no MANAGEMENT_API_KEY"
  note_fail
else
  write_body="$(printf '{"content":"%s","memory_type":"episodic"}' "$MEM_CONTENT")"
  resp="$(curl -sS -m 40 -w $'\n%{http_code}' \
    -X POST "${AEON_BASE}/api/v1/agents/${AGENT}/memories" \
    -H "X-Management-Key: ${MGMT_KEY}" \
    -H "Content-Type: application/json" \
    -d "$write_body" 2>/dev/null || true)"
  if [[ -z "$resp" ]]; then
    err "AEON unreachable at ${AEON_BASE} — is the stack up? (./start.sh)"
    note_fail
  else
    code="${resp##*$'\n'}"; payload="${resp%$'\n'*}"
    if [[ "$code" == 2?? ]]; then
      ok "memory written (HTTP ${code}); marker=${UNIQ}"
      dim "  ${payload}"
      dim "  Inspect counts: curl -fsS -H \"X-Management-Key: \$MANAGEMENT_API_KEY\" ${AEON_BASE}/api/v1/stats"
    else
      err "memory write FAILED (HTTP ${code})"
      dim "  ${payload}"
      if printf '%s' "$payload" | grep -qiE 'embed|openai|api key|provider|insufficient'; then
        warn "  This is an embedding/provider failure — set a valid OPENAI_API_KEY (or configured provider). Continuing to the Nexus leg, which does NOT need a key."
      fi
      note_fail
    fi
  fi
fi

# ════════════════════════════════════════════════════════════════════════════
# (b) RECALL
# ════════════════════════════════════════════════════════════════════════════
step "(b) Recall → POST /api/v1/memories/search"
if [[ -z "$MGMT_KEY" ]]; then
  err "skipped: no MANAGEMENT_API_KEY"
  note_fail
else
  search_body="$(printf '{"agent_id":"%s","query":"What did NexusIQ execute and prove?","limit":3}' "$AGENT")"
  resp="$(curl -sS -m 40 -w $'\n%{http_code}' \
    -X POST "${AEON_BASE}/api/v1/memories/search" \
    -H "X-Management-Key: ${MGMT_KEY}" \
    -H "Content-Type: application/json" \
    -d "$search_body" 2>/dev/null || true)"
  if [[ -z "$resp" ]]; then
    err "AEON unreachable at ${AEON_BASE}"
    note_fail
  else
    code="${resp##*$'\n'}"; payload="${resp%$'\n'*}"
    if [[ "$code" == "200" ]]; then
      ok "recall returned HTTP 200"
      if [[ "$HAVE_JQ" -eq 1 ]]; then
        hits="$(printf '%s' "$payload" | jq -r '(.results // .memories // .hits // [])
          | if length==0 then "  (no hits yet)" else (.[] | "  • " + ((.content // .text // (.memory.content) // "?")|tostring)) end' 2>/dev/null || true)"
      else
        hits="$(printf '%s' "$payload" | python3 -c '
import sys, json
try: d = json.load(sys.stdin)
except Exception: d = {}
arr = d.get("results") or d.get("memories") or d.get("hits") or []
if not arr:
    print("  (no hits yet)")
for h in arr:
    if isinstance(h, dict):
        c = h.get("content") or h.get("text") or (h.get("memory") or {}).get("content") or "?"
        print("  • " + str(c))
' 2>/dev/null || true)"
      fi
      [[ -n "$hits" ]] && printf '%s\n' "$hits" || dim "  ${payload}"
    else
      err "recall FAILED (HTTP ${code})"
      dim "  ${payload}"
      note_fail
    fi
  fi
fi

# ════════════════════════════════════════════════════════════════════════════
# (c) NEXUS EXECUTION + PROOF
# ════════════════════════════════════════════════════════════════════════════
step "(c) Nexus execution + proof → MCP tools/call nexus_execute_proof"
MCP_OUT=""
if [[ ! -f "$HOST_MODULE" ]]; then
  err "sample module not present on host: ${HOST_MODULE} (container path ${MODULE_PATH})"
  note_fail
else
  mcp_requests() {
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"nexusiq-live-example","version":"1.0.0"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
    printf '%s\n' "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"nexus_execute_proof\",\"arguments\":{\"wasm_path\":\"${MODULE_PATH}\",\"aeon_agent_id\":\"${AGENT}\"}}}"
  }
  MCP_OUT="$(mcp_requests | timeout 120 bash "$CONNECT" 2>/dev/null || true)"
  if [[ -z "$MCP_OUT" ]]; then
    err "no response from MCP server (is the stack up? ./start.sh)"
    note_fail
  else
    ok "nexus_execute_proof invoked over connect-mcp.sh (module=$(basename "$MODULE_PATH"))"
  fi
fi

# ════════════════════════════════════════════════════════════════════════════
# (d) EXTRACT PROOF CAPSULE → write ./data/proofs/<capsule_id>.json
# ════════════════════════════════════════════════════════════════════════════
step "(d) Extract proof_capsule → data/proofs/<capsule_id>.json"
CAPSULE_ID=""
EVENTS_JSON=""
if [[ -n "$MCP_OUT" ]]; then
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  CAP_FILE="${TMP}/capsule.json"; ID_FILE="${TMP}/id.txt"; EV_FILE="${TMP}/events.json"
  if [[ "$HAVE_PY" -eq 1 ]]; then
    printf '%s' "$MCP_OUT" | CAP_FILE="$CAP_FILE" ID_FILE="$ID_FILE" EV_FILE="$EV_FILE" python3 -c '
import sys, json, os
raw = sys.stdin.read()
def msgs(raw):
    for line in raw.splitlines():
        line=line.strip()
        if not line: continue
        try: yield json.loads(line)
        except Exception: continue
def blobs(obj):
    out=[]
    res = obj.get("result") if isinstance(obj,dict) else None
    if isinstance(res,dict):
        out.append(res)
        c=res.get("content")
        if isinstance(c,list):
            for it in c:
                if isinstance(it,dict) and isinstance(it.get("text"),str):
                    try: out.append(json.loads(it["text"]))
                    except Exception: pass
    return out
for obj in msgs(raw):
    for b in blobs(obj):
        if not isinstance(b,dict): continue
        cap = b.get("proof_capsule") or b.get("proofCapsule")
        if isinstance(cap,dict):
            cid = cap.get("capsule_id") or cap.get("id") or b.get("capsule_id")
            ev  = b.get("events") or cap.get("events") or []
            json.dump(cap, open(os.environ["CAP_FILE"],"w"), indent=2)
            if cid: open(os.environ["ID_FILE"],"w").write(str(cid))
            json.dump(ev, open(os.environ["EV_FILE"],"w"))
            sys.exit(0)
sys.exit(3)
' || true
  else
    # jq fallback
    res_lines="$(printf '%s\n' "$MCP_OUT" | jq -c 'select(type=="object") | .result' 2>/dev/null || true)"
    while IFS= read -r res; do
      [[ -z "$res" || "$res" == "null" ]] && continue
      cap="$(printf '%s' "$res" | jq -c '.proof_capsule // .proofCapsule // empty' 2>/dev/null || true)"
      ev="$(printf '%s' "$res" | jq -c '.events // empty' 2>/dev/null || true)"
      if [[ -z "$cap" || "$cap" == "null" ]]; then
        inner="$(printf '%s' "$res" | jq -r '.content[]?.text // empty' 2>/dev/null || true)"
        cap="$(printf '%s' "$inner" | jq -c '.proof_capsule // .proofCapsule // empty' 2>/dev/null || true)"
        ev="$(printf '%s' "$inner" | jq -c '.events // empty' 2>/dev/null || true)"
      fi
      if [[ -n "$cap" && "$cap" != "null" ]]; then
        printf '%s' "$cap" | jq '.' > "$CAP_FILE"
        printf '%s' "$cap" | jq -r '.capsule_id // .id // empty' > "$ID_FILE"
        [[ -n "$ev" && "$ev" != "null" ]] && printf '%s' "$ev" > "$EV_FILE" || printf '[]' > "$EV_FILE"
        break
      fi
    done <<< "$res_lines"
  fi

  if [[ -s "$CAP_FILE" ]]; then
    CAPSULE_ID="$(cat "$ID_FILE" 2>/dev/null || true)"
    [[ -z "$CAPSULE_ID" ]] && CAPSULE_ID="capsule-$(date +%Y%m%d-%H%M%S)"
    cp "$CAP_FILE" "${PROOF_DIR}/${CAPSULE_ID}.json"
    [[ -f "$EV_FILE" ]] && EVENTS_JSON="$(cat "$EV_FILE")"
    ok "proof captured"
    printf 'ProofCapsule written: data/proofs/%s.json\n' "$CAPSULE_ID"
  else
    err "no proof_capsule found in MCP response"
    dim "  raw (truncated): ${MCP_OUT:0:600}"
    note_fail
  fi
else
  err "skipped: no MCP output from step (c)"
fi

# ════════════════════════════════════════════════════════════════════════════
# (e) TIMELINE
# ════════════════════════════════════════════════════════════════════════════
step "(e) Timeline → POST events to /api/v1/agents/${AGENT}/timeline"
TL_STATUS="unavailable"
if [[ -z "$MGMT_KEY" ]]; then
  err "skipped: no MANAGEMENT_API_KEY"
  TL_STATUS="unavailable"
  note_fail
else
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # AEON's HypervisorTimelineEventBody fields: event_type (required), plus
  # optional session_id, capsule_digest, nexus_snapshot_id (Uuid), branch_id.
  # Bind this timeline event to the proof capsule via capsule_digest.
  SESSION="$(v NEXUS_AEON_SESSION_ID)"
  if [[ -n "$SESSION" ]]; then
    tl_body="$(printf '{"event_type":"proof_capsule_emitted","capsule_digest":"%s","session_id":"%s"}' \
      "${CAPSULE_ID:-unknown}" "$SESSION")"
  else
    tl_body="$(printf '{"event_type":"proof_capsule_emitted","capsule_digest":"%s"}' \
      "${CAPSULE_ID:-unknown}")"
  fi
  resp="$(curl -sS -m 30 -w $'\n%{http_code}' \
    -X POST "${AEON_BASE}/api/v1/agents/${AGENT}/timeline" \
    -H "X-Management-Key: ${MGMT_KEY}" \
    -H "Content-Type: application/json" \
    -d "$tl_body" 2>/dev/null || true)"
  if [[ -z "$resp" ]]; then
    TL_STATUS="unavailable"
    err "AEON unreachable — timeline event not delivered"
    note_fail
  else
    code="${resp##*$'\n'}"; payload="${resp%$'\n'*}"
    case "$code" in
      2??) TL_STATUS="delivered"; ok "timeline event recorded (HTTP ${code})" ;;
      000|"") TL_STATUS="unavailable"; err "AEON unreachable"; note_fail ;;
      *)   TL_STATUS="failed-open"; err "timeline write returned HTTP ${code}"; dim "  ${payload}"; note_fail ;;
    esac
  fi
fi
printf 'Timeline event status: %s\n' "$TL_STATUS"

# ════════════════════════════════════════════════════════════════════════════
# (f) WHERE TO INSPECT
# ════════════════════════════════════════════════════════════════════════════
step "(f) Where to inspect"
dim "Proof capsules (host):   ${PROOF_DIR}/"
[[ -n "$CAPSULE_ID" ]] && dim "  Latest:                ${PROOF_DIR}/${CAPSULE_ID}.json"
dim "List proofs:             ls -la data/proofs/"
dim "Stats:                   curl -fsS -H \"X-Management-Key: \$MANAGEMENT_API_KEY\" ${AEON_BASE}/api/v1/stats"
dim "Search memories:         curl -fsS -X POST ${AEON_BASE}/api/v1/memories/search -H \"X-Management-Key: \$MANAGEMENT_API_KEY\" -H 'Content-Type: application/json' -d '{\"agent_id\":\"${AGENT}\",\"query\":\"...\",\"limit\":5}'"
dim "Query timeline at time:  curl -fsS -H \"X-Management-Key: \$MANAGEMENT_API_KEY\" \"${AEON_BASE}/api/v1/agents/${AGENT}/timeline/at?timestamp=${ts:-<ISO8601>}\""

# ---- verdict ----------------------------------------------------------------
echo
if [[ "$OVERALL_FAIL" -eq 0 ]]; then
  ok "run-live-example: end-to-end flow completed."
  exit 0
else
  err "run-live-example: one or more legs FAILED (see ✗ above). This is a real failure, not a mock."
  exit 1
fi
