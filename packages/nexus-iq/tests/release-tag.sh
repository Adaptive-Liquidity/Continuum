#!/usr/bin/env bash
# Deterministic release-tag validation contracts for manifest generation.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="${ROOT_DIR}/scripts/validate-release-tag.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

passes=0
failures=0

pass() {
  printf 'PASS %s\n' "$1"
  passes=$((passes + 1))
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  failures=$((failures + 1))
}

for tag in v0.1.0 v1.1.0 v123.45.6; do
  if output="$("$VALIDATOR" "$tag" 2>"${TMP_DIR}/stderr")" &&
    [[ "$output" == "$tag" ]]; then
    pass "accepts release tag ${tag}"
  else
    fail "accepts release tag ${tag}"
  fi
done

invalid_tags=(
  ''
  '1.2.3'
  'v1.2'
  'v01.2.3'
  'v1.2.3-rc1'
  'v1.2.3+build'
  'v1.2.3;/usr/bin/id#e;#'
  $'v1.2.3\nmalicious'
)

for tag in "${invalid_tags[@]}"; do
  if "$VALIDATOR" "$tag" >"${TMP_DIR}/stdout" 2>"${TMP_DIR}/stderr"; then
    fail "rejects unsafe release tag ${tag@Q}"
  else
    pass "rejects unsafe release tag ${tag@Q}"
  fi
done

if grep -Fq 'TAG="$(./scripts/validate-release-tag.sh "${GITHUB_REF_NAME}")"' \
  "${ROOT_DIR}/.github/workflows/release-manifest.yml"; then
  pass "release workflow uses the validated tag value"
else
  fail "release workflow uses the validated tag value"
fi

printf '\n%d passed; %d failed\n' "$passes" "$failures"
[[ "$failures" -eq 0 ]]
