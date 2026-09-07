# S0-003: Runner Clock Lifecycle Regression

> **Status:** Reported by post-check automated review after PR #15 merged; reproduction required. **S0 remains failed/blocked.** This finding supersedes any implication that the v0.2.2 remediation is ready for focused external re-audit.

## Reported condition

The merged S0-001 remediation passes `ScenarioRunner`'s `ControlledClock.peek()` into admission. The runner clock starts at `2026-01-01T00:00:00Z` and advances in milliseconds only when trace/action code reads it. Scenario materialization issues provenance at scenario-index offsets measured in whole seconds, and delayed material is issued one additional second later. A runner whose controlled time has not reached the attestation issue time rejects those items as `attestation_not_yet_valid`.

## Why this matters

The change correctly removed caller-controlled time, but may have replaced it with a runner clock that is not aligned with the fixture authority lifecycle. The typed benchmark can then reject valid, verifier-issued segments. Existing end-to-end tests checked run completion and replay but did not assert that expected initial and delayed segments were admitted, so the regression could remain invisible.

## Required disposition

1. Reproduce with scenarios whose issued times exceed the runner's initial clock.
2. Define a trusted runner lifecycle time that is at least the host-controlled fixture issuance time without deriving from submitted segment data.
3. Add initial and delayed end-to-end admission assertions across scenario-index and adapter cases.
4. Keep lifecycle time controlled by the scenario runner/harness, not by a segment, attestation field, or user caller.
5. Correct the merge workflow record: the review thread was not resolved before PR #15 merged, so auto-merge behavior must be examined separately after the source fix.
6. Update the focused re-audit scope to cover S0-001, S0-002, and this regression correction.

## Stop boundary

Do not release v0.2.2, call the remediation complete, or begin S1, provider work, real effects, AEON-IQ, or real-model evaluation until the corrective pull request merges and an independent reviewer evaluates the final fixed commit.
