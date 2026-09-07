#!/usr/bin/env bash
#
# logs.sh — follow logs for the stack (or a single service).
#
# Usage:
#   ./logs.sh                 # all services
#   ./logs.sh aeon            # just the aeon service
#   ./logs.sh aeon nexus-agentd
#
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Follow logs with a bounded backscroll. Any service args are passed through.
exec docker compose --profile memory --profile tools logs -f --tail=200 "$@"
