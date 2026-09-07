#!/usr/bin/env bash
#
# reset.sh — DANGER: tear the stack down and DROP ALL VOLUMES.
#
# This deletes Postgres data, AEON-IQ state, and any other named volumes.
# The .env file is preserved. You must type `reset` to confirm.
#
set -euo pipefail

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
  C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_RED=''; C_YELLOW=''; C_BOLD=''; C_RESET=''
fi
ok()   { printf '%s✓%s %s\n' "$C_GREEN"  "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_RED"    "$C_RESET" "$*" >&2; }
warn() { printf '%s⚠%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

compose() { docker compose "$@"; }

printf '%s%s⚠ DANGER: reset will DESTROY ALL DATA VOLUMES.%s\n' "$C_BOLD" "$C_RED" "$C_RESET"
warn "This drops Postgres data and all AEON-IQ persisted state."
warn "Your .env (secrets) will be kept."
echo

printf 'Type %sreset%s to confirm: ' "$C_BOLD" "$C_RESET"
read -r confirm
if [[ "$confirm" != "reset" ]]; then
  err "Aborted (you typed '${confirm}', expected 'reset')."
  exit 1
fi

printf '\n%s▸ Tearing down stack and removing volumes%s\n' "$C_BOLD" "$C_RESET"
if ! compose --profile memory --profile tools down -v; then
  err "docker compose down -v failed."
  exit 1
fi
ok "stack removed and volumes dropped. .env preserved."
ok "Run './start.sh' to recreate a fresh stack."
