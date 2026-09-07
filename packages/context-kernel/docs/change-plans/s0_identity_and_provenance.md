# AEON Kernel Change Plan: S0 Identity and Provenance

## Requested behavior

Implement only the S0 identity-and-provenance foundation. A caller must not obtain principal or trusted-workspace authority by selecting `trust_class`, setting metadata, or reusing a logical segment ID. Every admission decision must bind to one verifier-issued opaque segment UID and the exact current segment content hash. The implementation must reject duplicate logical IDs and UIDs, missing or extra decisions, UID/hash mismatch, expired or wrong-scope attestations, and self-asserted trusted provenance. It must preserve deterministic local simulator execution, the five assembly regions, pre-effect enforcement, and current safe-versus-violating benchmark fixtures. It must not implement S1 structured rendering, trusted invariant residency, real-effect capabilities, evidence signatures, provider calls, or AEON-IQ integration.

## Change classification

| Field | Value |
|---|---|
| Primary area | Segment schema, trust, admission, assembly, compaction joins, runner receipt joins |
| Primary modules | `models.py`, new `provenance.py`, `admission.py`, `assembly.py`, `compaction.py`, `survival_bench/adapters.py`, `survival_bench/runner.py`, scenario catalog, tests |
| Companion tests | `test_models_admission.py`, `test_assembly_compaction.py`, `test_benchmark.py`, receipt/replay regression tests |
| Generated artifacts affected | Admissions, assemblies, compaction records, receipts, traces, metrics, reports |
| Real effects involved | No; all effects remain in memory and no provider integration is added |

## Contracts to preserve

- Authority remains derived from verified runtime provenance rather than prose.
- External-untrusted material remains non-authoritative and in region D.
- Required principal constraints remain protected by the existing deterministic policy; S1 registry changes are explicitly deferred.
- Enforce decisions occur before any simulated effect.
- Deterministic ordering, canonical serialization, controlled time, and seeded randomness remain intact.
- Trace-chain integrity and logical decision-trace equality remain separate checks.
- Simulator outputs remain conformance/regression evidence, not model or production evidence.

## Proposed implementation

Introduce immutable submitted-versus-verified provenance data. `ContextSegment` remains the logical content object for S0 compatibility but carries no authority-bearing result. A `VerifiedProvenance` record is issued by an injected trusted in-memory verifier for local fixtures. It binds an opaque deterministic UID, exact UTF-8 content hash, source ID, trust class, issuer key ID, audience, policy scope, issued/expiry times, nonce, and signature commitment. The verifier validates issuer key identity, scope, expiry, revocation list, nonce replay, source ID, and exact content hash.

`AdmissionPolicy` accepts a verifier and a provenance record for each segment. It rejects omitted, mismatched, expired, revoked, wrong-audience, wrong-policy, or replayed provenance before authority evaluation. Trust and authentication fields in segment metadata are ignored for security decisions. The policy produces decisions bound to `segment_uid` and the verified trust class. Batches require a complete one-to-one segment/provenance/decision key set and reject duplicate logical IDs or UIDs.

Assembly, compaction, runner, and receipts join through a shared identity key `(segment_uid, segment_hash)` and reject cardinality or binding mismatch rather than performing last-write-wins dictionary collapse. The deterministic scenario harness gets a trusted local issuer owned by the runner; scenario fixtures provide content claims only. This issuer is a local simulator trust root, not a production identity solution.

## Version and hash assessment

| Identity or hash | Expected effect | Rationale |
|---|---|---|
| Package version | `0.2.0` candidate | Public admission and decision schemas gain verified UID/provenance semantics. |
| Predicate version/set hash | No intended change | S0 does not change predicates or their configuration. |
| Scenario version/scaffold hash | `2.0.0` candidate | Scenario materialization moves trust issuance into the controlled harness. |
| Adapter version | `2.0.0` candidate | Typed admission lifecycle requires verified provenance batches. |
| Harness or simulator version | `2.0.0` candidate | Run specification and receipt identity binding change. |
| Assembly/trace/decision hashes | Expected to change | Entries and decisions include verified UIDs; existing result artifacts remain historical and are not rewritten. |

## Test matrix

| Case | Expected result | Test location |
|---|---|---|
| Positive principal provenance | Verifier-issued principal attestation admits an authoritative required constraint. | `test_models_admission.py` |
| Positive external provenance | Verifier-issued external instruction is demoted to non-authoritative region D. | `test_models_admission.py`, `test_assembly_compaction.py` |
| Caller self-asserts principal | Unattested caller content is rejected before authority decision. | `test_models_admission.py` |
| Empty allowlist | Deny all rather than fall back to all trust classes. | `test_models_admission.py` |
| Expired/wrong audience/replayed attestation | Rejected with stable provenance reason code. | `test_models_admission.py` |
| Duplicate logical ID or UID | Batch rejects before assembly/compaction. | `test_models_admission.py`, `test_assembly_compaction.py` |
| Mismatched decision UID/hash | Assembly and compaction reject before rendering or mutation. | `test_assembly_compaction.py` |
| Deterministic repetition | Identical fixture and issuer inputs produce equal admission/assembly/trace decisions. | Focused and benchmark tests |
| Replay/artifact impact | Fresh stage has consistent identities, passive audit passes, and replay reproduces logical decisions. | Benchmark/reproducibility audit |

## Verification record

```text
Baseline focused tests: 11 passed (test_models_admission.py + test_assembly_compaction.py)
Focused test:
Full relevant test file:
Pytest:
Ruff:
Mypy:
Smoke benchmark:
Pilot/full benchmark, if justified: D0 requires all published deterministic runs; do not run until source gates pass
Replay/audit, if artifacts changed:
```

## Residual risk

S0 does not provide structural model-facing framing, trusted invariant residency, resolved real-effect capabilities, redaction, authenticated artifact roots, real models, or real-effect adapters. An in-memory deterministic issuer verifies the local simulator contract only; it does not establish a production issuer, key-management, or revocation service. S1 and later gates remain explicitly blocked pending the S0 independent re-audit.
