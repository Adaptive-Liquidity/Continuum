#!/usr/bin/env bash
#
# connect-mcp.sh — launch one STDIO nexus-mcp process against an already-live
# nexus-agentd. It never starts agentd or any memory service as a dependency.
#
set -euo pipefail

log() { printf '%s\n' "connect-mcp: $*" >&2; }

_source="${BASH_SOURCE[0]}"
while [[ -h "$_source" ]]; do
  _dir="$(cd -P "$(dirname -- "$_source")" >/dev/null 2>&1 && pwd)"
  _source="$(readlink -- "$_source")"
  [[ "$_source" != /* ]] && _source="${_dir}/${_source}"
done
SCRIPT_DIR="$(cd -P "$(dirname -- "$_source")" >/dev/null 2>&1 && pwd)"

NEXUSIQ_SELFHOST_DIR="${NEXUSIQ_SELFHOST_DIR:-$SCRIPT_DIR}"
COMPOSE_FILE="${NEXUSIQ_SELFHOST_DIR%/}/docker-compose.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  log "FATAL: docker-compose.yml not found at ${COMPOSE_FILE}"
  log "       Set NEXUSIQ_SELFHOST_DIR to the absolute NexusIQ kit path."
  exit 1
fi
ENV_FILE="${NEXUSIQ_SELFHOST_DIR%/}/.env"
MODE_RESOLVER="${NEXUSIQ_SELFHOST_DIR%/}/scripts/runtime-mode.sh"
if [[ ! -f "$ENV_FILE" || ! -f "$MODE_RESOLVER" ]]; then
  log "FATAL: .env or scripts/runtime-mode.sh is missing. Run ./install.sh."
  exit 1
fi
# shellcheck source=scripts/runtime-mode.sh
source "$MODE_RESOLVER"
if ! nexusiq_resolve_runtime_mode "$ENV_FILE"; then
  log "FATAL: invalid runtime mode configuration."
  exit 1
fi
export NEXUS_AEON_ENABLED="$NEXUSIQ_AEON_ENABLED_NORMALIZED"
if ! command -v docker >/dev/null 2>&1; then
  log "FATAL: docker not found on PATH."
  exit 1
fi

compose=(docker compose -f "$COMPOSE_FILE")
agentd_id="$("${compose[@]}" ps -q nexus-agentd 2>/dev/null | head -n1 || true)"
if [[ -z "$agentd_id" ]] ||
   [[ "$(docker inspect -f '{{.State.Running}}' "$agentd_id" 2>/dev/null || true)" != "true" ]]; then
  log "FATAL: nexus-agentd is not running. Run ./start.sh first."
  exit 1
fi
if ! MSYS2_ARG_CONV_EXCL='/run/nexus' "${compose[@]}" exec -T nexus-agentd \
  nexus daemon ping --socket /run/nexus/nexus-agentd.sock \
    </dev/null >/dev/null 2>&1; then
  log "FATAL: nexus-agentd is running but not ready. Check ./logs.sh nexus-agentd."
  exit 1
fi

log "launching nexus-mcp against the running nexus-agentd"
exec "${compose[@]}" --profile tools run --rm --no-deps -T nexus-mcp
