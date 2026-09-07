# AEON Kernel Change Plan: S0-001 and S0-002 Remediation

## Requested behavior

The external S0 audit reported two trust-boundary defects. **S0-001** is confirmed by source inspection: `AdmissionPolicy.admit()` uses `now or segment.created_at`, allowing a caller-controlled segment field to select the provenance lifecycle clock when the runtime omits `now`; the shipped benchmark adapter omits it. **S0-002** is also confirmed by source inspection: compaction treats caller-controlled `segment.metadata["active_invariant"]` as protected residency. This remediation must remove both caller-controlled control paths while preserving simulator-only execution, verifier-issued authority, exact UID/hash joins, deterministic replay contracts, and all existing S0 non-claims.

## Change classification

| Field | Value |
|---|---|
| Primary area | Admission and compaction |
| Primary modules | `src/context_kernel/admission.py`, `src/context_kernel/compaction.py`, `src/survival_bench/adapters.py`, `src/survival_bench/runner.py` |
| Companion modules | `examples/basic_usage.py`, fixtures and admission/assembly/benchmark/receipt tests |
| Companion tests | `test_models_admission.py`, `test_assembly_compaction.py`, `test_benchmark.py`, `test_receipts_replay.py` |
| Generated artifacts affected | Potential receipt/trace timestamp fields only if runtime wiring consumes the controlled clock; decision semantics should remain unchanged for current fixtures |
| Real effects involved | No; simulator only |
| External audit disposition | S0 remains failed pending independent focused re-audit |

## Contracts to preserve

- Authority remains verifier-issued and never derives from prose, metadata, a logical ID, a submitted timestamp, or a caller-selected lifecycle clock.
- External-untrusted material remains non-authoritative and in the external reference region.
- S0 principal required instruction/constraint/output-contract segments remain protected from compaction under the documented deterministic policy.
- S0 does **not** claim S1 trusted-invariant residency; untrusted metadata must not add residency protection.
- Enforce decisions occur before any simulated effect.
- Deterministic ordering, canonical serialization, controlled time, and seeded randomness remain intact.
- Trace-chain integrity and logical decision-trace equality remain separate checks.
- Simulator evidence remains non-efficacy, non-provider, and non-compliance evidence.

## Proposed implementation

### S0-001: trusted verification time

1. Change `AdmissionPolicy.admit()` and `AdmissionPolicy.admit_many()` so `verification_time: datetime` is required and timezone-aware; remove the `None` default and remove all use of `segment.created_at` as a verification-time fallback.
2. Thread this required value through `BenchmarkAdapter.admit()` as a required named argument.
3. In `ScenarioRunner`, provide `clock.peek()` from the runner-owned `ControlledClock` for both initial and delayed admissions. `peek()` deliberately avoids consuming an extra tick, so current trace-event timestamp sequencing remains stable while admission uses a controlled runtime time.
4. Update examples and tests to supply an explicit fixed/runtime verification time. Tests must never hide the contract through a helper default derived from the submitted segment.
5. Reject a naive `datetime` when supplied to admission rather than letting it reach the verifier ambiguously.

### S0-002: metadata cannot protect compaction residency

1. Remove the `segment.metadata.get("active_invariant") is True` protection condition from `_is_protected()`.
2. Retain S0 protection only for verifier-confirmed `principal` segments whose semantic and priority meet the existing required-principal condition.
3. Do not replace the metadata marker with a new generic flag. A trusted invariant registry is explicitly deferred to S1. This patch closes the caller-control path rather than claiming the deferred S1 mechanism exists.
4. Update fixtures to stop using `active_invariant` as evidence of compaction protection. If fixture metadata still contains it for unrelated test text, it must have no effect on compaction.

## Version and hash assessment

| Identity or hash | Expected effect | Rationale |
|---|---|---|
| Package version | Patch security release after protected merge | Fixes two S0 trust-boundary defects without adding S1 capability. |
| Predicate version/set hash | None | No predicate changes. |
| Scenario version/scaffold hash | None expected | Scenario semantics are unchanged; remove only ineffective/untrusted fixture metadata if necessary. |
| Adapter version | Patch/explicit update if public method signature changes | `admit()` now requires a trusted verification time. |
| Harness or simulator version | Update only if deterministic run behavior or public run contract changes | Current runner clock should preserve current decision behavior. |
| Assembly/trace/decision hashes | Decision hashes should remain unchanged for valid current fixtures; trace/event hashes must be compared rather than assumed | The runner uses `clock.peek()` to avoid incidental event-clock shifts. |

## Test matrix

| Case | Expected result | Test location |
|---|---|---|
| Positive valid provenance at a trusted runtime time | Admitted with the same verified trust semantics as before | `test_models_admission.py` |
| Expired attestation with caller-created segment timestamp inside its former validity window | Rejected when trusted runtime time is after expiry; caller timestamp cannot change outcome | `test_models_admission.py` |
| Future-dated attestation with caller-created segment timestamp inside its former validity window | Rejected as not-yet-valid against trusted runtime time | `test_models_admission.py` |
| Omitted admission verification time | Type/API failure before provenance evaluation; no segment-derived fallback | `test_models_admission.py` |
| Naive verification time | Rejected with a clear timezone-aware error | `test_models_admission.py` |
| Benchmark initial and delayed admission | Both receive runner-controlled `clock.peek()` and remain deterministic | `test_benchmark.py` |
| Untrusted/external segment with `metadata={"active_invariant": true}` under pressure | It is still summarized or evicted according to normal candidate order; metadata does not protect it | `test_assembly_compaction.py` |
| Verified required-principal constraint under pressure | Remains protected; an unsatisfied budget reports `budget_satisfied=false` rather than evicting it | `test_assembly_compaction.py` |
| Deterministic repeat | Same valid input/runtime time produces identical admission decisions | admission and benchmark tests |
| Replay/artifact impact | Fresh smoke plus full trace replay; compare decision-trace hashes and record any justified version/hash changes | reproducibility evidence step |

## Verification record

```text
Focused reproduction of S0-001:
Focused reproduction of S0-002:
Focused tests:
Full relevant test files:
Pytest:
Ruff:
Mypy:
Example/demo:
Smoke benchmark:
Pilot/full benchmark, if justified:
Replay/audit, if artifacts changed:
Independent focused re-audit:
```

## Residual risk

This patch does not create a production clock service, durable multi-process replay prevention, key custody/rotation, an authenticated evidence root, real effects, model-facing injection resistance, or S1 trusted-invariant registry semantics. The Docker NVIDIA-registry connection refusal is treated as a separate environment/network issue unless a reviewer shows that it is required for the S0 simulator path.
