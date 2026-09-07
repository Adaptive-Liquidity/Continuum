#!/usr/bin/env bash
# Validate and return the only release-tag form safe for artifact generation.
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf 'release tag validator requires exactly one argument\n' >&2
  exit 1
fi

tag="$1"
if [[ ! "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
  printf 'release tag must match vMAJOR.MINOR.PATCH with numeric components\n' >&2
  exit 1
fi

printf '%s\n' "$tag"
