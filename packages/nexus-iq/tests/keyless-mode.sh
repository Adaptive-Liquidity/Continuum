#!/usr/bin/env bash
#
# Deterministic contract tests for the keyless/core runtime-mode resolver and
# conditional environment validation. No provider credential is created.
#
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PASSES=0
FAILURES=0

pass() {
  printf 'PASS %s\n' "$1"
  PASSES=$((PASSES + 1))
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

assert_success() {
  local name="$1"
  shift
  if [[ "$#" -eq 0 ]]; then
    fail "${name} (no command supplied)"
    return
  fi
  if "$@" >"${TMP_DIR}/stdout" 2>"${TMP_DIR}/stderr"; then
    pass "$name"
  else
    fail "$name"
    sed 's/^/  /' "${TMP_DIR}/stderr" >&2
  fi
}

assert_failure_matching() {
  local name="$1" pattern="$2"
  shift 2
  if [[ "$#" -eq 0 ]]; then
    fail "${name} (no command supplied)"
    return
  fi
  if "$@" >"${TMP_DIR}/stdout" 2>"${TMP_DIR}/stderr"; then
    fail "${name} (unexpected success)"
  elif grep -Eiq -- "$pattern" "${TMP_DIR}/stdout" "${TMP_DIR}/stderr"; then
    pass "$name"
  else
    fail "${name} (missing diagnostic matching: ${pattern})"
    sed 's/^/  /' "${TMP_DIR}/stderr" >&2
  fi
}

write_env() {
  local destination="$1"
  shift
  printf '%s\n' "$@" >"$destination"
}

resolver_output_is() {
  local env_file="$1" expected="$2" warning_pattern="${3:-}"
  local output
  if ! output="$(bash "${ROOT_DIR}/scripts/runtime-mode.sh" "$env_file" 2>"${TMP_DIR}/resolver-stderr")"; then
    return 1
  fi
  [[ "$output" == "$expected" ]] || return 1
  if [[ -n "$warning_pattern" ]]; then
    grep -Eiq -- "$warning_pattern" "${TMP_DIR}/resolver-stderr"
  else
    [[ ! -s "${TMP_DIR}/resolver-stderr" ]]
  fi
}

resolver_value_is() {
  local env_file="$1" key="$2" expected="$3"
  # shellcheck source=scripts/runtime-mode.sh
  source "${ROOT_DIR}/scripts/runtime-mode.sh"
  nexusiq_resolve_runtime_mode "$env_file" >/dev/null
  [[ "$(nexusiq_env_get "$key")" == "$expected" ]]
}

resolver_normalized_is() {
  local env_file="$1" expected="$2"
  # shellcheck source=scripts/runtime-mode.sh
  source "${ROOT_DIR}/scripts/runtime-mode.sh"
  nexusiq_resolve_runtime_mode "$env_file" >/dev/null
  [[ "$NEXUSIQ_AEON_ENABLED_NORMALIZED" == "$expected" ]]
}
run_validator() {
  local env_file="$1" isolated="${TMP_DIR}/validator-$RANDOM"
  mkdir -p "${isolated}/scripts"
  cp "${ROOT_DIR}/scripts/validate-env.sh" "${isolated}/scripts/validate-env.sh"
  sed -i 's/\r$//' "${isolated}/scripts/validate-env.sh"
  if [[ -f "${ROOT_DIR}/scripts/runtime-mode.sh" ]]; then
    cp "${ROOT_DIR}/scripts/runtime-mode.sh" "${isolated}/scripts/runtime-mode.sh"
    sed -i 's/\r$//' "${isolated}/scripts/runtime-mode.sh"
  fi
  cp "$env_file" "${isolated}/.env"
  bash "${isolated}/scripts/validate-env.sh"
}

generate_secrets_preserves_line_boundary() {
  local isolated="${TMP_DIR}/generate-secrets"
  mkdir -p "${isolated}/scripts"
  cp "${ROOT_DIR}/scripts/generate-secrets.sh" "${isolated}/scripts/generate-secrets.sh"
  cp "${ROOT_DIR}/scripts/runtime-mode.sh" "${isolated}/scripts/runtime-mode.sh"
  printf 'NEXUS_AEON_ENABLED=false' >"${isolated}/.env"
  (cd "$isolated" && bash ./scripts/generate-secrets.sh >/dev/null)
  grep -qx 'NEXUS_AEON_ENABLED=false' "${isolated}/.env" &&
    grep -Eq '^NEXUS_AGENTD_AUTH_TOKEN=[0-9a-f]{64}$' "${isolated}/.env"
}

generate_secrets_parses_commented_blank() {
  local isolated="${TMP_DIR}/generate-secrets-comment"
  mkdir -p "${isolated}/scripts"
  cp "${ROOT_DIR}/scripts/generate-secrets.sh" "${isolated}/scripts/generate-secrets.sh"
  cp "${ROOT_DIR}/scripts/runtime-mode.sh" "${isolated}/scripts/runtime-mode.sh"
  write_env "${isolated}/.env" \
    'NEXUS_AEON_ENABLED=false' \
    'NEXUS_AGENTD_AUTH_TOKEN= # generate this internal token'
  (cd "$isolated" && bash ./scripts/generate-secrets.sh >/dev/null)
  grep -Eq '^NEXUS_AGENTD_AUTH_TOKEN=[0-9a-f]{64}$' "${isolated}/.env"
}

all_env_consumers_use_shared_parser() {
  local path
  for path in \
    run-live-example.sh \
    scripts/generate-secrets.sh \
    scripts/smoke-memory-recall.sh \
    scripts/smoke-timeline.sh
  do
    grep -Fq 'runtime-mode.sh' "${ROOT_DIR}/${path}" || return 1
    if grep -Eq 'declare -A ENVV|load_env\(\)' "${ROOT_DIR}/${path}"; then
      return 1
    fi
  done
}

disabled_start_stops_memory_before_validation_failure() {
  local isolated="${TMP_DIR}/start-order"
  local docker_log="${isolated}/docker.log"
  mkdir -p "${isolated}/scripts" "${isolated}/bin"
  cp "${ROOT_DIR}/start.sh" "${isolated}/start.sh"
  cp "${ROOT_DIR}/scripts/runtime-mode.sh" "${isolated}/scripts/runtime-mode.sh"
  cp "${ROOT_DIR}/scripts/validate-env.sh" "${isolated}/scripts/validate-env.sh"
  sed -i 's/\r$//' \
    "${isolated}/start.sh" \
    "${isolated}/scripts/runtime-mode.sh" \
    "${isolated}/scripts/validate-env.sh"
  write_env "${isolated}/.env" \
    'NEXUS_AEON_ENABLED=false' \
    'ALLOW_UNAUTH_MANAGEMENT=false'
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'printf "%s\n" "$*" >>"$NEXUSIQ_DOCKER_LOG"' \
    >"${isolated}/bin/docker"
  chmod +x "${isolated}/bin/docker"

  if (
    cd "$isolated"
    PATH="${isolated}/bin:${PATH}" \
      NEXUSIQ_DOCKER_LOG="$docker_log" \
      bash ./start.sh
  ) >"${isolated}/stdout" 2>"${isolated}/stderr"; then
    return 1
  fi

  grep -Fqx 'compose --profile memory stop aeon-worker aeon postgres' "$docker_log" &&
    ! grep -Eq '(^| )up( |$)' "$docker_log" &&
    grep -Eiq 'NEXUS_AGENTD_AUTH_TOKEN.*(missing|required)' \
      "${isolated}/stdout" "${isolated}/stderr"
}

TOKEN='0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
MGMT='abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789'
HMAC='1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'

FALSE_ENV="${TMP_DIR}/false.env"
write_env "$FALSE_ENV" \
  'NEXUS_AEON_ENABLED=FaLsE' \
  "NEXUS_AGENTD_AUTH_TOKEN=${TOKEN}" \
  'ALLOW_UNAUTH_MANAGEMENT=false'
assert_success "explicit false is memory-disabled, case-insensitive" \
  resolver_output_is "$FALSE_ENV" disabled
assert_success "case-insensitive false is canonicalized for Compose" \
  resolver_normalized_is "$FALSE_ENV" false

TRUE_ENV="${TMP_DIR}/true.env"
write_env "$TRUE_ENV" \
  'NEXUS_AEON_ENABLED=TRUE'
assert_success "explicit true is memory-enabled, case-insensitive" \
  resolver_output_is "$TRUE_ENV" enabled
assert_success "case-insensitive true is canonicalized for Compose" \
  resolver_normalized_is "$TRUE_ENV" true

LEGACY_ENV="${TMP_DIR}/legacy.env"
write_env "$LEGACY_ENV" \
  "NEXUS_AGENTD_AUTH_TOKEN=${TOKEN}"
assert_success "absent mode is legacy-enabled with a visible warning" \
  resolver_output_is "$LEGACY_ENV" enabled 'absent|legacy|explicit'

for malformed in '' yes 1 enabled off; do
  MALFORMED_ENV="${TMP_DIR}/malformed-${malformed:-empty}.env"
  write_env "$MALFORMED_ENV" "NEXUS_AEON_ENABLED=${malformed}"
  assert_failure_matching "malformed mode '${malformed:-empty}' is rejected" \
    'NEXUS_AEON_ENABLED.*(true|false|invalid|empty)' \
    bash "${ROOT_DIR}/scripts/runtime-mode.sh" "$MALFORMED_ENV"
done

PROVIDER_CONFIG_ENV="${TMP_DIR}/provider-config.env"
write_env "$PROVIDER_CONFIG_ENV" \
  'NEXUS_AEON_ENABLED=false' \
  'UPSTREAM_PROVIDER=ollama' \
  'UPSTREAM_BASE_URL=http://127.0.0.1:11434' \
  'OPENAI_API_KEY='
assert_success "provider configuration presence does not auto-enable memory" \
  resolver_output_is "$PROVIDER_CONFIG_ENV" disabled

COMMENTED_FALSE_ENV="${TMP_DIR}/commented-false.env"
write_env "$COMMENTED_FALSE_ENV" \
  'NEXUS_AEON_ENABLED=false # core mode' \
  "NEXUS_AGENTD_AUTH_TOKEN=${TOKEN}" \
  'ALLOW_UNAUTH_MANAGEMENT=false # authentication remains required'
assert_success "Compose-style inline comments preserve explicit false mode" \
  resolver_output_is "$COMMENTED_FALSE_ENV" disabled
assert_success "safe inline comments remain valid during core validation" \
  run_validator "$COMMENTED_FALSE_ENV"

assert_success "disabled validation needs only the execution-plane token" \
  run_validator "$FALSE_ENV"
if grep -Eiq 'memory.*disabled' "${TMP_DIR}/stdout"; then
  pass "disabled validator verdict is mode-specific"
else
  fail "disabled validator verdict is mode-specific"
fi
if ! grep -Eiq 'provider key OK' "${TMP_DIR}/stdout" "${TMP_DIR}/stderr"; then
  pass "disabled validator does not claim provider-key success"
else
  fail "disabled validator does not claim provider-key success"
fi
QUOTED_HASH_ENV="${TMP_DIR}/quoted-hash.env"
write_env "$QUOTED_HASH_ENV" \
  'NEXUS_AEON_ENABLED="false" # core mode' \
  'NEXUS_AGENTD_AUTH_TOKEN="value#keeps-hash"' \
  "ALLOW_UNAUTH_MANAGEMENT='false' # safe"
assert_success "quoted values preserve hash characters while trailing comments are removed" \
  resolver_value_is "$QUOTED_HASH_ENV" NEXUS_AGENTD_AUTH_TOKEN 'value#keeps-hash'


ENABLED_MISSING_PROVIDER="${TMP_DIR}/enabled-missing-provider.env"
write_env "$ENABLED_MISSING_PROVIDER" \
  'NEXUS_AEON_ENABLED=true' \
  'POSTGRES_USER=nexusiq' \
  "POSTGRES_PASSWORD=${TOKEN}" \
  'POSTGRES_DB=nexusiq' \
  "MANAGEMENT_API_KEY=${MGMT}" \
  "NEXUS_AEON_MANAGEMENT_KEY=${MGMT}" \
  "NEXUS_AEON_HMAC_KEY=${HMAC}" \
  "NEXUS_AGENTD_AUTH_TOKEN=${TOKEN}" \
  'ALLOW_UNAUTH_MANAGEMENT=false' \
  'UPSTREAM_PROVIDER=openai' \
  'OPENAI_API_KEY='
assert_failure_matching "enabled validation fails closed without its provider" \
  'openai.*OPENAI_API_KEY|OPENAI_API_KEY.*required' \
  run_validator "$ENABLED_MISSING_PROVIDER"

ANTHROPIC_MISSING_PROVIDER="${TMP_DIR}/anthropic-missing-provider.env"
sed 's/^UPSTREAM_PROVIDER=.*/UPSTREAM_PROVIDER=anthropic/' \
  "$ENABLED_MISSING_PROVIDER" >"$ANTHROPIC_MISSING_PROVIDER"
assert_failure_matching "enabled Anthropic mode preserves AEON's upstream-key requirement" \
  'anthropic.*OPENAI_API_KEY|OPENAI_API_KEY.*required' run_validator "$ANTHROPIC_MISSING_PROVIDER"

GEMINI_MISSING_PROVIDER="${TMP_DIR}/gemini-missing-provider.env"
sed 's/^UPSTREAM_PROVIDER=.*/UPSTREAM_PROVIDER=gemini/' \
  "$ENABLED_MISSING_PROVIDER" >"$GEMINI_MISSING_PROVIDER"
assert_failure_matching "enabled Gemini mode preserves AEON's upstream-key requirement" \
  'gemini.*OPENAI_API_KEY|OPENAI_API_KEY.*required' run_validator "$GEMINI_MISSING_PROVIDER"

ENABLED_COMPLETE="${TMP_DIR}/enabled-complete.env"
write_env "$ENABLED_COMPLETE" \
  'NEXUS_AEON_ENABLED=true' \
  'POSTGRES_USER=nexusiq' \
  "POSTGRES_PASSWORD=${TOKEN}" \
  'POSTGRES_DB=nexusiq' \
  "MANAGEMENT_API_KEY=${MGMT}" \
  "NEXUS_AEON_MANAGEMENT_KEY=${MGMT}" \
  "NEXUS_AEON_HMAC_KEY=${HMAC}" \
  "NEXUS_AGENTD_AUTH_TOKEN=${TOKEN}" \
  'ALLOW_UNAUTH_MANAGEMENT=false' \
  'UPSTREAM_PROVIDER=ollama' \
  'UPSTREAM_BASE_URL=http://127.0.0.1:11434'
assert_success "enabled validation accepts complete Ollama configuration without a fake key" \
  run_validator "$ENABLED_COMPLETE"

if grep -Eiq 'memory.*enabled' "${TMP_DIR}/stdout"; then
  pass "enabled validator verdict is mode-specific"
else
  fail "enabled validator verdict is mode-specific"
fi

MISSING_POSTGRES_USER_ENV="${TMP_DIR}/missing-postgres-user.env"
grep -v '^POSTGRES_USER=' "$ENABLED_COMPLETE" >"$MISSING_POSTGRES_USER_ENV"
assert_failure_matching "enabled mode requires POSTGRES_USER" \
  'POSTGRES_USER.*missing|POSTGRES_USER.*required' run_validator "$MISSING_POSTGRES_USER_ENV"

MISSING_POSTGRES_DB_ENV="${TMP_DIR}/missing-postgres-db.env"
grep -v '^POSTGRES_DB=' "$ENABLED_COMPLETE" >"$MISSING_POSTGRES_DB_ENV"
assert_failure_matching "enabled mode requires POSTGRES_DB" \
  'POSTGRES_DB.*missing|POSTGRES_DB.*required' run_validator "$MISSING_POSTGRES_DB_ENV"

LEGACY_COMPLETE="${TMP_DIR}/legacy-complete.env"
grep -v '^NEXUS_AEON_ENABLED=' "$ENABLED_COMPLETE" >"$LEGACY_COMPLETE"
assert_success "legacy absent mode retains full-memory validation" \
  run_validator "$LEGACY_COMPLETE"
if grep -Eiq 'absent|legacy|explicit' "${TMP_DIR}/stderr"; then
  pass "legacy validation emits the compatibility warning"
else
  fail "legacy validation emits the compatibility warning"
fi

MISMATCH_ENV="${TMP_DIR}/mismatch.env"
cp "$ENABLED_COMPLETE" "$MISMATCH_ENV"
sed -i 's/^NEXUS_AEON_MANAGEMENT_KEY=.*/NEXUS_AEON_MANAGEMENT_KEY=wrong/' "$MISMATCH_ENV"
assert_failure_matching "enabled mode preserves management-key cross-wiring" \
  'cross-wired|must equal|mismatch' run_validator "$MISMATCH_ENV"

SHORT_HMAC_ENV="${TMP_DIR}/short-hmac.env"
cp "$ENABLED_COMPLETE" "$SHORT_HMAC_ENV"
sed -i 's/^NEXUS_AEON_HMAC_KEY=.*/NEXUS_AEON_HMAC_KEY=abcd/' "$SHORT_HMAC_ENV"
assert_failure_matching "enabled mode preserves HMAC validation" \
  'HMAC.*(64|32 bytes|too short)' run_validator "$SHORT_HMAC_ENV"

UNAUTH_ENV="${TMP_DIR}/unauth.env"
cp "$FALSE_ENV" "$UNAUTH_ENV"
sed -i 's/^ALLOW_UNAUTH_MANAGEMENT=.*/ALLOW_UNAUTH_MANAGEMENT=true/' "$UNAUTH_ENV"
assert_failure_matching "core mode never permits unauthenticated management flags" \
  'ALLOW_UNAUTH_MANAGEMENT.*(forbidden|NOT be true|must.*false)' \
  run_validator "$UNAUTH_ENV"

COMMENTED_UNAUTH_ENV="${TMP_DIR}/commented-unauth.env"
cp "$FALSE_ENV" "$COMMENTED_UNAUTH_ENV"
sed -i 's/^ALLOW_UNAUTH_MANAGEMENT=.*/ALLOW_UNAUTH_MANAGEMENT=true # unsafe/' "$COMMENTED_UNAUTH_ENV"
assert_failure_matching "inline comments cannot conceal unauthenticated management" \
  'ALLOW_UNAUTH_MANAGEMENT.*(forbidden|must.*false)' run_validator "$COMMENTED_UNAUTH_ENV"

EMPTY_UNAUTH_ENV="${TMP_DIR}/empty-unauth.env"
cp "$FALSE_ENV" "$EMPTY_UNAUTH_ENV"
sed -i 's/^ALLOW_UNAUTH_MANAGEMENT=.*/ALLOW_UNAUTH_MANAGEMENT=/' "$EMPTY_UNAUTH_ENV"
assert_failure_matching "an explicitly empty unauthenticated-management setting fails closed" \
  'ALLOW_UNAUTH_MANAGEMENT.*must.*false' run_validator "$EMPTY_UNAUTH_ENV"

AMBIGUOUS_UNAUTH_ENV="${TMP_DIR}/ambiguous-unauth.env"
cp "$FALSE_ENV" "$AMBIGUOUS_UNAUTH_ENV"
sed -i 's/^ALLOW_UNAUTH_MANAGEMENT=.*/ALLOW_UNAUTH_MANAGEMENT=no/' "$AMBIGUOUS_UNAUTH_ENV"
assert_failure_matching "an ambiguous unauthenticated-management setting fails closed" \
  'ALLOW_UNAUTH_MANAGEMENT.*must.*false' run_validator "$AMBIGUOUS_UNAUTH_ENV"

MOCK_ENV="${TMP_DIR}/mock.env"
cp "$FALSE_ENV" "$MOCK_ENV"
printf '%s\n' 'MOCK_PROVIDER=true' >>"$MOCK_ENV"
assert_failure_matching "core mode preserves mock/test flag prohibition" \
  'mock/test.*not allowed|MOCK_PROVIDER' run_validator "$MOCK_ENV"

assert_success "secret generation preserves a missing final newline" \
  generate_secrets_preserves_line_boundary

assert_success "secret generation treats a commented blank as empty" \
  generate_secrets_parses_commented_blank

assert_success "all memory and lifecycle consumers use the shared env parser" \
  all_env_consumers_use_shared_parser

assert_success "disabled start stops memory before execution-plane validation fails" \
  disabled_start_stops_memory_before_validation_failure

printf '\n%d passed; %d failed\n' "$PASSES" "$FAILURES"
[[ "$FAILURES" -eq 0 ]]
