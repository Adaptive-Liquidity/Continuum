#!/usr/bin/env bash
#
# wait-for-health.sh — wait for an explicit, caller-selected service list.
#
# Usage:
#   ./scripts/wait-for-health.sh nexus-agentd
#   ./scripts/wait-for-health.sh postgres aeon aeon-worker
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
cd "$ROOT_DIR"

if [[ "$#" -eq 0 ]]; then
  err "No services requested. Pass an explicit service list."
  exit 2
fi

SERVICES=("$@")
for service in "${SERVICES[@]}"; do
  case "$service" in
    postgres|aeon|aeon-worker|nexus-agentd) ;;
    *)
      err "Unsupported health target: ${service}"
      exit 2
      ;;
  esac
done

TIMEOUT="${WAIT_TIMEOUT:-120}"
INTERVAL="${WAIT_INTERVAL:-3}"
compose() { docker compose --profile memory --profile tools "$@"; }

service_state() {
  local svc="$1" cid health state
  cid="$(compose ps -q "$svc" 2>/dev/null | head -n1 || true)"
  if [[ -z "$cid" ]]; then
    printf 'missing'
    return
  fi
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || printf 'unknown')"
  state="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || printf 'unknown')"
  if [[ "$state" == "exited" || "$state" == "dead" ]]; then
    printf 'exited'
    return
  fi
  case "$health" in
    healthy) printf 'healthy' ;;
    unhealthy) printf 'unhealthy' ;;
    starting) printf 'starting' ;;
    none)
      if [[ "$state" == "running" ]]; then
        printf 'no-healthcheck'
      else
        printf '%s' "$state"
      fi
      ;;
    *) printf '%s' "${state:-unknown}" ;;
  esac
}

is_ready() {
  case "$1" in
    healthy|no-healthcheck) return 0 ;;
    *) return 1 ;;
  esac
}

echo "Waiting for services (timeout ${TIMEOUT}s): ${SERVICES[*]}"
deadline=$(( $(date +%s) + TIMEOUT ))
declare -A LAST
for service in "${SERVICES[@]}"; do
  LAST["$service"]=""
done

while true; do
  all_ready=1
  for service in "${SERVICES[@]}"; do
    state="$(service_state "$service")"
    if [[ "${LAST[$service]}" != "$state" ]]; then
      case "$state" in
        healthy|no-healthcheck) ok "${service}: ${state}" ;;
        unhealthy|exited|missing) err "${service}: ${state}" ;;
        *) warn "${service}: ${state}" ;;
      esac
      LAST["$service"]="$state"
    fi
    is_ready "$state" || all_ready=0
  done

  if [[ "$all_ready" -eq 1 ]]; then
    ok "Requested services are healthy: ${SERVICES[*]}"
    exit 0
  fi

  if [[ "$(date +%s)" -ge "$deadline" ]]; then
    err "Timed out after ${TIMEOUT}s waiting for: ${SERVICES[*]}"
    compose ps || true
    exit 1
  fi
  sleep "$INTERVAL"
done
