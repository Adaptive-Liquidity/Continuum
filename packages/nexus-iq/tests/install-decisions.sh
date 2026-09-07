#!/usr/bin/env bash
#
# Installer decision tests. Docker is stubbed deliberately: these tests prove
# which build/pull operations are selected without claiming a live image pull.
#
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

make_kit_copy() {
  local destination="$1"
  mkdir -p "$destination"
  (
    cd "$ROOT_DIR"
    tar --exclude=.git --exclude=.env --exclude=vendor --exclude=data -cf - .
  ) | tar -C "$destination" -xf -
}

make_docker_stub() {
  local bin_dir="$1" log_file="$2"
  mkdir -p "$bin_dir"
  cat >"${bin_dir}/docker" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${DOCKER_CALL_LOG}"
case "${1:-}" in
  --version) printf 'Docker version test\n' ;;
  info) ;;
  compose)
    if [[ "${2:-}" == "version" ]]; then
      if [[ "${3:-}" == "--short" ]]; then printf '2.test\n'; else printf 'Docker Compose version test\n'; fi
    fi
    ;;
esac
STUB
  chmod +x "${bin_dir}/docker"
  : >"$log_file"
}

make_fake_sources() {
  local source_root="$1"
  mkdir -p "${source_root}/nexus" "${source_root}/aeon"
  printf '%s\n' 'FROM scratch' >"${source_root}/aeon/Dockerfile"
}

set_env_value() {
  local file="$1" key="$2" value="$3"
  KEY="$key" VALUE="$value" awk '
    BEGIN { key = ENVIRON["KEY"]; value = ENVIRON["VALUE"] }
    $0 ~ "^" key "=" { print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "$file" >"${file}.new"
  mv "${file}.new" "$file"
}

assert_absent() {
  local pattern="$1" file="$2" message="$3"
  if grep -Eq -- "$pattern" "$file"; then
    printf 'FAIL %s\n' "$message" >&2
    grep -E -- "$pattern" "$file" >&2 || true
    exit 1
  fi
  printf 'PASS %s\n' "$message"
}

assert_present() {
  local pattern="$1" file="$2" message="$3"
  if ! grep -Eq -- "$pattern" "$file"; then
    printf 'FAIL %s\n' "$message" >&2
    exit 1
  fi
  printf 'PASS %s\n' "$message"
}

BIN_DIR="${TMP_DIR}/bin"
DOCKER_CALL_LOG="${TMP_DIR}/docker-calls"
export DOCKER_CALL_LOG
make_docker_stub "$BIN_DIR" "$DOCKER_CALL_LOG"
make_fake_sources "${TMP_DIR}/sources"
export PATH="${BIN_DIR}:${PATH}"

# Fresh source-build core mode.
CORE_KIT="${TMP_DIR}/core-kit"
make_kit_copy "$CORE_KIT"
(
  cd "$CORE_KIT"
  NEXUSIQ_VENDOR_NEXUS="${TMP_DIR}/sources/nexus" ./install.sh >"${TMP_DIR}/core-output"
)
[[ ! -e "${CORE_KIT}/vendor/aeon-iq" ]] ||
  { printf 'FAIL core source install created vendor/aeon-iq\n' >&2; exit 1; }
printf 'PASS core source install does not vendor AEON-IQ\n'
assert_present 'compose build nexus-agentd|compose .*build nexus-agentd' \
  "$DOCKER_CALL_LOG" "core source install builds nexus-agentd"
assert_absent 'build .*aeon|pull .*postgres|pull .*aeon' \
  "$DOCKER_CALL_LOG" "core source install selects no AEON/PostgreSQL build or pull"
assert_absent '^(OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY)=.+' \
  "${CORE_KIT}/.env" "core install writes no provider credential"
assert_present '^Memory: disabled$' "${TMP_DIR}/core-output" \
  "core installer reports memory disabled"

# Fresh prebuilt core mode: prove the pull plan without claiming a live pull.
: >"$DOCKER_CALL_LOG"
PREBUILT_KIT="${TMP_DIR}/prebuilt-kit"
make_kit_copy "$PREBUILT_KIT"
(
  cd "$PREBUILT_KIT"
  NEXUSIQ_USE_PREBUILT=true NEXUSIQ_IMAGE_TAG=test-plan ./install.sh \
    >"${TMP_DIR}/prebuilt-output"
)
assert_present 'compose pull nexus-agentd|compose .*pull nexus-agentd' \
  "$DOCKER_CALL_LOG" "core prebuilt mode pulls nexus-agentd"
assert_absent 'pull .*postgres|pull .*aeon' "$DOCKER_CALL_LOG" \
  "core prebuilt mode excludes AEON and PostgreSQL"

# Explicit memory enablement without a provider must fail before build/pull.
: >"$DOCKER_CALL_LOG"
MISSING_KIT="${TMP_DIR}/missing-provider-kit"
make_kit_copy "$MISSING_KIT"
cp "${MISSING_KIT}/.env.example" "${MISSING_KIT}/.env"
set_env_value "${MISSING_KIT}/.env" NEXUS_AEON_ENABLED true
if (
  cd "$MISSING_KIT"
  NEXUSIQ_VENDOR_NEXUS="${TMP_DIR}/sources/nexus" \
    NEXUSIQ_VENDOR_AEON="${TMP_DIR}/sources/aeon" \
    ./install.sh >"${TMP_DIR}/missing-output" 2>"${TMP_DIR}/missing-error"
); then
  printf 'FAIL memory-enabled install unexpectedly accepted missing provider\n' >&2
  exit 1
fi
assert_present 'OPENAI_API_KEY' "${TMP_DIR}/missing-error" \
  "memory-enabled install names the missing provider requirement"
assert_absent 'compose .*build|compose .*pull' "$DOCKER_CALL_LOG" \
  "memory-enabled missing-provider failure occurs before build or pull"

# Complete local-provider configuration preserves the full source-build plan.
: >"$DOCKER_CALL_LOG"
MEMORY_KIT="${TMP_DIR}/memory-kit"
make_kit_copy "$MEMORY_KIT"
cp "${MEMORY_KIT}/.env.example" "${MEMORY_KIT}/.env"
set_env_value "${MEMORY_KIT}/.env" NEXUS_AEON_ENABLED true
set_env_value "${MEMORY_KIT}/.env" UPSTREAM_PROVIDER ollama
set_env_value "${MEMORY_KIT}/.env" UPSTREAM_BASE_URL http://127.0.0.1:11434
(
  cd "$MEMORY_KIT"
  NEXUSIQ_VENDOR_NEXUS="${TMP_DIR}/sources/nexus" \
    NEXUSIQ_VENDOR_AEON="${TMP_DIR}/sources/aeon" \
    ./install.sh >"${TMP_DIR}/memory-output"
)
assert_present 'compose --profile memory build nexus-agentd aeon aeon-worker' \
  "$DOCKER_CALL_LOG" "memory-enabled source install selects the full app build"
assert_present 'compose --profile memory pull --ignore-buildable postgres' \
  "$DOCKER_CALL_LOG" "memory-enabled source install selects the PostgreSQL pull"
assert_present '^Memory: enabled$' "${TMP_DIR}/memory-output" \
  "memory-enabled installer reports the selected mode"
