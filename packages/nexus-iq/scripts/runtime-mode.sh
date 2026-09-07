#!/usr/bin/env bash
#
# Shared, non-executing .env parser and NexusIQ runtime-mode resolver.
#
# Source this file, then call:
#   nexusiq_resolve_runtime_mode /path/to/.env
#
# On success it sets:
#   NEXUSIQ_MEMORY_MODE=enabled|disabled
#   NEXUSIQ_MEMORY_MODE_EXPLICIT=true|false
#
# The parser never sources, evals, expands, or prints .env values.

if [[ -z "${BASH_VERSINFO:-}" || "${BASH_VERSINFO[0]}" -lt 4 ]]; then
  printf 'runtime-mode: bash 4.0+ is required (found %s). On macOS, install a current Bash first.\n' \
    "${BASH_VERSION:-unknown}" >&2
  return 1 2>/dev/null || exit 1
fi

declare -A NEXUSIQ_ENV=()
declare -A NEXUSIQ_ENV_OCCURRENCES=()
NEXUSIQ_MEMORY_MODE=""
NEXUSIQ_MEMORY_MODE_EXPLICIT=""
NEXUSIQ_AEON_ENABLED_NORMALIZED=""

nexusiq_mode_error() {
  printf 'runtime-mode: %s\n' "$*" >&2
}

nexusiq_mode_warn() {
  printf 'runtime-mode: WARNING: %s\n' "$*" >&2
}

nexusiq_load_env() {
  local env_file="$1"
  local raw line key val

  if [[ ! -f "$env_file" ]]; then
    nexusiq_mode_error "environment file not found: ${env_file}"
    return 1
  fi

  NEXUSIQ_ENV=()
  NEXUSIQ_ENV_OCCURRENCES=()

  while IFS= read -r raw || [[ -n "$raw" ]]; do
    line="${raw%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue

    if [[ "$line" == export[[:space:]]* ]]; then
      line="${line#export}"
      line="${line#"${line%%[![:space:]]*}"}"
    fi
    [[ "$line" == *=* ]] || continue

    key="${line%%=*}"
    val="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue

    if [[ "$val" =~ ^[[:space:]]+# ]]; then
      val=""
    else
      val="${val#"${val%%[![:space:]]*}"}"
      if [[ "$val" == \"* ]]; then
        if [[ "$val" =~ ^\"(.*)\"[[:space:]]*(#.*)?$ ]]; then
          val="${BASH_REMATCH[1]}"
        fi
      elif [[ "$val" == \'* ]]; then
        if [[ "$val" =~ ^\'(.*)\'[[:space:]]*(#.*)?$ ]]; then
          val="${BASH_REMATCH[1]}"
        fi
      else
        # Compose starts an unquoted inline comment at whitespace + '#'.
        val="${val%%[[:space:]]#*}"
        val="${val%"${val##*[![:space:]]}"}"
      fi
    fi

    NEXUSIQ_ENV["$key"]="$val"
    NEXUSIQ_ENV_OCCURRENCES["$key"]=$(( ${NEXUSIQ_ENV_OCCURRENCES["$key"]:-0} + 1 ))
  done <"$env_file"
}

nexusiq_env_get() {
  printf '%s' "${NEXUSIQ_ENV[$1]:-}"
}

nexusiq_resolve_runtime_mode() {
  local env_file="$1"
  local occurrences raw normalized

  nexusiq_load_env "$env_file" || return 1
  occurrences="${NEXUSIQ_ENV_OCCURRENCES[NEXUS_AEON_ENABLED]:-0}"

  if [[ "$occurrences" -eq 0 ]]; then
    NEXUSIQ_MEMORY_MODE="enabled"
    NEXUSIQ_MEMORY_MODE_EXPLICIT="false"
    NEXUSIQ_AEON_ENABLED_NORMALIZED="true"
    nexusiq_mode_warn "NEXUS_AEON_ENABLED is absent; enabling memory for backward compatibility. Set NEXUS_AEON_ENABLED=true or false explicitly."
    return 0
  fi

  if [[ "$occurrences" -ne 1 ]]; then
    nexusiq_mode_error "NEXUS_AEON_ENABLED must appear exactly once; found ${occurrences} entries"
    return 1
  fi

  raw="${NEXUSIQ_ENV[NEXUS_AEON_ENABLED]}"
  normalized="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    true)
      NEXUSIQ_MEMORY_MODE="enabled"
      NEXUSIQ_MEMORY_MODE_EXPLICIT="true"
      NEXUSIQ_AEON_ENABLED_NORMALIZED="true"
      ;;
    false)
      NEXUSIQ_MEMORY_MODE="disabled"
      NEXUSIQ_MEMORY_MODE_EXPLICIT="true"
      NEXUSIQ_AEON_ENABLED_NORMALIZED="false"
      ;;
    "")
      nexusiq_mode_error "NEXUS_AEON_ENABLED is empty; expected exactly true or false"
      return 1
      ;;
    *)
      nexusiq_mode_error "NEXUS_AEON_ENABLED='${raw}' is invalid; expected exactly true or false (case-insensitive)"
      return 1
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
  if [[ "$#" -ne 1 ]]; then
    nexusiq_mode_error "usage: scripts/runtime-mode.sh /path/to/.env"
    exit 2
  fi
  nexusiq_resolve_runtime_mode "$1"
  printf '%s\n' "$NEXUSIQ_MEMORY_MODE"
fi
