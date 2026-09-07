#!/usr/bin/env bash
#
# stop.sh — stop the NexusIQ stack, preserving volumes (and thus data).
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_RED"   "$C_RESET" "$*" >&2; }
step() { printf '\n%s%s▸ %s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

compose() { docker compose "$@"; }

step "Stopping services (volumes preserved)"
if ! compose --profile memory --profile tools stop; then
  err "docker compose stop failed."
  exit 1
fi
ok "stack stopped. Data volumes are intact — './start.sh' to resume."
