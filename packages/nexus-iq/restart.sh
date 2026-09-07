#!/usr/bin/env bash
#
# restart.sh — stop the stack, then start it again.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_CYAN=''; C_BOLD=''; C_RESET=''
fi
step() { printf '\n%s%s▸ %s%s\n' "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

step "Restart: stopping"
bash "${ROOT_DIR}/stop.sh"

step "Restart: starting"
exec bash "${ROOT_DIR}/start.sh"
