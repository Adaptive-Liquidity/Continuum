#!/usr/bin/env bash
#
# uninstall.sh — remove the NexusIQ stack, its volumes, and locally built
# images. Optionally also remove .env, vendor/, and data/.
#
# Confirmation is required. By default ONLY containers, networks, volumes, and
# locally built images are removed; on-disk kit files (.env, vendor, data) are
# kept unless you opt in.
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

printf '%s%s⚠ uninstall will remove containers, networks, volumes, and locally built images.%s\n' \
  "$C_BOLD" "$C_RED" "$C_RESET"
echo
printf 'Type %suninstall%s to confirm: ' "$C_BOLD" "$C_RESET"
read -r confirm
if [[ "$confirm" != "uninstall" ]]; then
  err "Aborted (you typed '${confirm}', expected 'uninstall')."
  exit 1
fi

printf '\n%s▸ Removing stack, volumes, and locally built images%s\n' "$C_BOLD" "$C_RESET"
if ! compose --profile memory --profile tools down -v --rmi local; then
  err "docker compose down -v --rmi local failed."
  exit 1
fi
ok "containers, networks, volumes, and local images removed"

# ---- optional file removal --------------------------------------------------
remove_path_if_confirmed() {
  local path="$1" label="$2"
  [[ -e "$path" || -L "$path" ]] || return 0
  printf 'Also remove %s (%s)? Type %syes%s to delete: ' "$label" "$path" "$C_BOLD" "$C_RESET"
  read -r ans
  if [[ "$ans" == "yes" ]]; then
    rm -rf "$path"
    ok "removed ${label}"
  else
    warn "kept ${label}"
  fi
}

echo
remove_path_if_confirmed "${ROOT_DIR}/.env"    ".env (secrets)"
remove_path_if_confirmed "${ROOT_DIR}/vendor"  "vendor/ (Nexus + AEON-IQ build contexts)"
remove_path_if_confirmed "${ROOT_DIR}/data"    "data/ (proofs, timeline, modules, logs)"

echo
ok "uninstall complete."
