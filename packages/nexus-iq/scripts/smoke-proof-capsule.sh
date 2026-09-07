#!/usr/bin/env bash
#
# smoke-proof-capsule.sh — live Nexus proof-of-execution.
#
# Single concern: call the MCP tool `nexus_execute_proof` (running the sample
# WASM module) over the STDIO pipe, extract the returned proof_capsule from the
# JSON-RPC response, and write it to ./data/proofs/<capsule_id>.json. The proof
# is returned IN the response — Nexus does not write it — so this script is what
# persists it.
#
# Exit codes: 0 = capsule captured + written; 1 = execution failed / no capsule.
# No provider key required (pure Nexus execution path).
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
PROOF_DIR="${ROOT_DIR}/data/proofs"

# Container path to the sample module (mounted from ./data/modules).
MODULE_PATH="${SMOKE_MODULE:-/modules/sample_tool.wasm}"
HOST_MODULE="${ROOT_DIR}/data/modules/$(basename "$MODULE_PATH")"

if [[ ! -f "$CONNECT" ]]; then err "connect-mcp.sh not found at ${CONNECT}"; exit 1; fi
if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  err "neither jq nor python3 available — cannot parse/extract the proof capsule."
  exit 1
fi
if [[ ! -f "$HOST_MODULE" ]]; then
  err "sample module not present on host: ${HOST_MODULE}"
  warn "The container expects it at ${MODULE_PATH} (mounted from ./data/modules)."
  exit 1
fi
mkdir -p "$PROOF_DIR"

# ---- JSON-RPC: handshake then tools/call nexus_execute_proof ----------------
mcp_proof_requests() {
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"nexusiq-smoke","version":"1.0.0"}}}'
  printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  printf '%s\n' "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"nexus_execute_proof\",\"arguments\":{\"wasm_path\":\"${MODULE_PATH}\"}}}"
}

out="$(mcp_proof_requests | timeout 120 bash "$CONNECT" 2>/dev/null || true)"

if [[ -z "$out" ]]; then
  err "proof-capsule: no response from MCP server (is the stack up?)."
  exit 1
fi

# ---- extract proof_capsule + capsule_id from the tools/call result ----------
# MCP tool results commonly arrive as result.content[].text holding JSON, but
# some servers return result directly. We search both shapes for a
# proof_capsule object and a capsule id.
PARSED_DIR="$(mktemp -d)"
trap 'rm -rf "$PARSED_DIR"' EXIT
CAPSULE_FILE="${PARSED_DIR}/capsule.json"
ID_FILE="${PARSED_DIR}/id.txt"

if command -v python3 >/dev/null 2>&1; then
  printf '%s' "$out" | CAPSULE_FILE="$CAPSULE_FILE" ID_FILE="$ID_FILE" python3 -c '
import sys, json, os
raw = sys.stdin.read()
capsule_out = os.environ["CAPSULE_FILE"]
id_out = os.environ["ID_FILE"]

def candidates(raw):
    # Each non-empty line may be a JSON-RPC message.
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue

def find_capsule(obj):
    # Walk result -> (content[].text JSON) or result directly.
    res = obj.get("result") if isinstance(obj, dict) else None
    blobs = []
    if isinstance(res, dict):
        blobs.append(res)
        content = res.get("content")
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and isinstance(c.get("text"), str):
                    try:
                        blobs.append(json.loads(c["text"]))
                    except Exception:
                        pass
    for b in blobs:
        if not isinstance(b, dict):
            continue
        cap = b.get("proof_capsule") or b.get("proofCapsule")
        if isinstance(cap, dict):
            return cap, b
    return None, None

for obj in candidates(raw):
    cap, parent = find_capsule(obj)
    if cap is not None:
        cid = (cap.get("capsule_id") or cap.get("id")
               or (parent.get("capsule_id") if isinstance(parent, dict) else None))
        with open(capsule_out, "w") as f:
            json.dump(cap, f, indent=2)
        if cid:
            with open(id_out, "w") as f:
                f.write(str(cid))
        sys.exit(0)
sys.exit(3)
' || true
else
  # jq fallback: try result.content[].text as JSON, else result itself.
  printf '%s\n' "$out" | jq -c 'select(type=="object") | .result' 2>/dev/null \
    | while IFS= read -r res; do
        cap="$(printf '%s' "$res" | jq -c '.proof_capsule // .proofCapsule // empty' 2>/dev/null || true)"
        if [[ -z "$cap" || "$cap" == "null" ]]; then
          cap="$(printf '%s' "$res" | jq -r '.content[]?.text // empty' 2>/dev/null \
                 | jq -c '.proof_capsule // .proofCapsule // empty' 2>/dev/null || true)"
        fi
        if [[ -n "$cap" && "$cap" != "null" ]]; then
          printf '%s' "$cap" | jq '.' > "$CAPSULE_FILE"
          printf '%s' "$cap" | jq -r '.capsule_id // .id // empty' > "$ID_FILE"
          break
        fi
      done
fi

if [[ ! -s "$CAPSULE_FILE" ]]; then
  err "proof-capsule: no proof_capsule found in the MCP response."
  printf '%sraw response (truncated):%s\n' "$C_DIM" "$C_RESET" >&2
  printf '%s%.1000s%s\n' "$C_DIM" "$out" "$C_RESET" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  failure_summary="$(python3 - "$CAPSULE_FILE" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    capsule = json.load(f)
failure = capsule.get("failure")
if failure:
    category = failure.get("failure_category") or "UNKNOWN"
    summary = failure.get("error_summary") or "execution failed"
    print(f"{category}: {summary}")
    sys.exit(1)
PY
)" || {
    err "proof-capsule: capsule reports execution failure (${failure_summary})."
    exit 1
  }
elif jq -e '.failure != null' "$CAPSULE_FILE" >/dev/null 2>&1; then
  failure_summary="$(jq -r '.failure.failure_category + ": " + .failure.error_summary' "$CAPSULE_FILE" 2>/dev/null || true)"
  err "proof-capsule: capsule reports execution failure (${failure_summary:-execution failed})."
  exit 1
fi

CAPSULE_ID="$(cat "$ID_FILE" 2>/dev/null || true)"
[[ -z "$CAPSULE_ID" ]] && CAPSULE_ID="capsule-$(date +%Y%m%d-%H%M%S)"

DEST="${PROOF_DIR}/${CAPSULE_ID}.json"
cp "$CAPSULE_FILE" "$DEST"

ok "proof-capsule: captured proof of execution (module=$(basename "$MODULE_PATH"))."
printf 'ProofCapsule written: data/proofs/%s.json\n' "$CAPSULE_ID"
