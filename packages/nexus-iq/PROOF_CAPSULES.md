# Proof Capsules

This kit’s hardened execution flow produces a proof artifact for `nexus_execute_proof`.
Proof Capsules are returned by MCP in the tool response and are also written by scripts
into `./data/proofs/<capsule_id>.json`.

`proof_capsule` is the expected return field in live flows:

- `scripts/smoke-proof-capsule.sh` parses and checks it.
- `run-live-example.sh` parses and persists it as `data/proofs/<capsule_id>.json`.

## Execution contract (current behavior)

The current stack wiring expects:

- `capsule_id` (or `id`) for traceability.
- `module` for the executed target path.
- `result` and/or failure details.
- `timestamp`.
- At least one capability/grant record.
- A cryptographic binding (`hmac_binding` in current example output).

The repository’s PRD and implementation notes add a hardened capsule schema that includes:

- `limitations[]` (non-empty in hardened mode)
- `redaction_manifest`
- HMAC-bound `run`/`input` provenance fields
- `memory_evidence`
- `profile_digest`
- `duration_ms`
- `signature` / `signature_type` (signed capsule)

Where available, failures are surfaced as:

```json
{"failure":{"failure_category":"...","error_summary":"..."}}
```

`smoke-proof-capsule.sh` and `run-live-example.sh` treat any non-empty `failure` as an execution failure.

## Response shape and debug mode

In practice, the current example scripts consume a full `proof_capsule` object directly.
If your build returns a compact response shape, use debug/dev mode as supported by that Nexus build to request the full capsule payload before persistence.

## Verify command(s)

The repo provides these validation entry points:

- `./scripts/smoke-proof-capsule.sh`
- `./verify-live-stack.sh` (doctor + live example end-to-end)

Use file-level checks:

```bash
ls -la data/proofs
cat data/proofs/<capsule_id>.json
```

If your image includes the verification CLI, use:

- `nexus aeon verify-capsule <capsule_file_or_reference>`
- `iq-verify <capsule_file_or_reference>`

## Filesystem locations

- Capsules are persisted under `./data/proofs` by local tooling.
- Capsule identifiers are used when posting timeline events (`capsule_digest`).
- Management-protected AEON read APIs live at `http://127.0.0.1:8080/api/v1/...`.
