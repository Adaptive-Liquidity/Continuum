# Continuum Persistence Slice — Decision #2A

Internal, reproducible proof for the bounded Continuum Genesis Proof defined by Decision #2A.

## Limits

Same-host clean process restart only: two sequential OS processes share one SQLite store; phase 1 exits normally (no kill or crash). The verifier is a separate, internal script by the same author, not third-party verification. The effect is a local, mediated SQLite write, not an external side effect. This does not demonstrate crash recovery, host migration, model/provider replacement, external effects, third-party verification, cryptographic notarization, or production readiness.

## What it demonstrates

One named Continuum Computer and one named VERA survive a process restart on the same host. Durable state written before restart is read afterward. A mediated in-process SQLite status write commits while an explicit scoped grant is active, the grant is revoked, and the same capability is refused afterward. A structured evidence artifact records the discontinuity and all acceptance observables.

The producer writes acceptance flags for inspection. The verifier **recomputes** AC-1 through AC-8 from raw fields (`identity_continuity`, events, grant/effect outcomes, `excluded_scope`, host observations) and ignores stored booleans.

## Acceptance criteria

Each predicate is independently computable and can fail on its own.

| ID | Meaning | Raw fields |
|---|---|---|
| AC-1 | Same Continuum Computer ID across the restart | `computer_id` equals `computer.created` and `identity_continuity.pre/post_computer_id`; PIDs differ |
| AC-2 | Same VERA ID across the restart | `vera_id` equals `vera.created` and `identity_continuity.pre/post_vera_id`; PIDs differ |
| AC-3 | Durable marker written before restart is read after | `state.written` / `state.read` / `state.value` match; write seq &lt; restart seq &lt; read seq |
| AC-4 | Active grant commits; revocation denies | `effect.committed` &lt; `grant.revoked` &lt; `effect.denied`; `authority.final_state` is `REVOKED` |
| AC-5 | Post-restart effect through a non-model mediator | committed effect PID is post-restart; `execution.mediator` and `effect_class` are the local boundary |
| AC-6 | Structured event sequence is recomputable | required kinds present; `seq` is `1..n` with no gaps |
| AC-7 | VERA remains bound to the same Computer | `vera.created.computer_id` equals `computer.created` and `identity_continuity.bound_computer_id` |
| AC-8 | Excluded scope is not represented as proven | every `excluded_scope` flag is `false`; recorded hosts match; discontinuity type is `process_restart_same_host`; scope/ceiling stay bounded |

### How AC-8 is computed

AC-8 is not a literal `true`. It is the conjunction of:

1. `excluded_scope` contains every required key (`host_migration`, `crash_recovery`, `model_provider_replacement`, `external_side_effect`, `third_party_verification`, `cryptographic_notarization`, `production_readiness`) and each value is JSON `false` (not proven).
2. `discontinuity.pre_restart_host` equals `discontinuity.post_restart_host`, both are present, and `discontinuity.type` is `process_restart_same_host`.
3. `scope` mentions same-host process restart and `claim_ceiling` states that no claim is made beyond AC-1 through AC-8.

Marking `excluded_scope.host_migration` true fails AC-8 only. Matching hostnames do not prove host migration; they only keep this run inside the declared ceiling.

## Commands

From the Continuum repository root. Stdlib only; no network, secrets, or extra packages.

### Test

```bash
python3 -m unittest -v proofs/continuum-persistence-slice/test_proof.py
```

Expected: every test `ok`, final line `OK`. Failure: a criterion that should pass failed, or a negative mutation did not isolate the intended AC.

### Run (two OS processes)

```bash
python3 proofs/continuum-persistence-slice/proof.py run \
  --workdir proofs/continuum-persistence-slice/.run
```

Expected stdout includes `"verification": { "valid": true, ... }`, `"producer_acceptance_ignored": true`, AC-1 through AC-8 all `true`, and at least 11 evidence events with a contiguous sequence. Writes:

- `proofs/continuum-persistence-slice/.run/continuum-persistence-slice.sqlite3`
- `proofs/continuum-persistence-slice/.run/continuum-persistence-slice-2a.json`

Failure: process 2 cannot reconstitute identity/state, or recomputed acceptance is not all true (`proof verification failed`).

### Verify (recompute; ignore stored flags)

```bash
python3 proofs/continuum-persistence-slice/proof.py verify \
  --artifact proofs/continuum-persistence-slice/.run/continuum-persistence-slice-2a.json
```

Expected: exit status `0` and `"valid": true`. Exit status `1` with `"valid": false` if any recomputed AC fails or required top-level fields/schema are missing.

Archived evidence:

```bash
python3 proofs/continuum-persistence-slice/proof.py verify \
  --artifact docs/evidence/continuum-persistence-slice-2a.json
```

### Appendix A / reproduce target

This repository does **not** contain P00 LaTeX. Manuscript compilation cannot run here. The Decision #2A path is:

```bash
make reproduce-p00
```

That target is an alias of `make reproduce-p00-harness`: unit tests, a fresh two-process run, then verify of the `.run` artifact.

```bash
make verify-evidence
```

recomputes acceptance against `docs/evidence/continuum-persistence-slice-2a.json` only.

Success: `make reproduce-p00` prints the unittest `OK`, a `valid: true` run object, and a `valid: true` verify object; exit status `0`. Failure: any of those steps is non-zero.

## Regenerating archived evidence

If the verifier schema changes, regenerate the archived artifact from a real run. Do not hand-edit it.

```bash
python3 proofs/continuum-persistence-slice/proof.py run \
  --workdir proofs/continuum-persistence-slice/.run
cp proofs/continuum-persistence-slice/.run/continuum-persistence-slice-2a.json \
  docs/evidence/continuum-persistence-slice-2a.json
```
