# AEON Kernel Change Plan

## Requested behavior

Describe the observable behavior in one paragraph. State what must change and what must remain unchanged.

## Change classification

| Field | Value |
|---|---|
| Primary area | Admission / assembly / compaction / ledger / interception / simulator / receipts / replay / CLI |
| Primary modules | |
| Companion tests | |
| Generated artifacts affected | None / receipts / traces / metrics / reports |
| Real effects involved | No; simulator only unless separately authorized |

## Contracts to preserve

Record the applicable contracts:

- Authority remains provenance-based rather than prose-based.
- External-untrusted material remains non-authoritative and region D.
- Required principal constraints and active invariants remain protected from compaction.
- Enforce decisions occur before any simulated effect.
- Deterministic ordering, canonical serialization, controlled time, and seeded randomness remain intact.
- Trace-chain integrity and logical decision-trace equality remain separate checks.
- Simulator evidence is not described as production-model or compliance evidence.

## Proposed implementation

Describe the smallest code change that satisfies the request. Identify any schema, reason-code, public-configuration, or dispatch changes.

## Version and hash assessment

| Identity or hash | Expected effect | Rationale |
|---|---|---|
| Predicate version/set hash | |
| Scenario version/scaffold hash | |
| Adapter version | |
| Harness or simulator version | |
| Assembly/trace/decision hashes | |

## Test matrix

| Case | Expected result | Test location |
|---|---|---|
| Positive/allowed path | |
| Negative/violating path | |
| Not-applicable path | |
| Observe mode | |
| Warn mode | |
| Enforce mode and zero effect | |
| Deterministic repeat | |
| Replay or artifact impact | |

Remove rows that genuinely do not apply; do not remove negative or deterministic cases merely for convenience.

## Verification record

```text
Focused test:
Full relevant test file:
Pytest:
Ruff:
Mypy:
Smoke benchmark:
Pilot/full benchmark, if justified:
Replay/audit, if artifacts changed:
```

## Residual risk

State unrun gates, compatibility concerns, migration needs, or assumptions. Use “none identified” only after completing the matrix.
