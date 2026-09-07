# S0 Runner-Clock Correction Change Plan

## Trigger and boundary

Post-merge review identified S0-003 in the v0.2.2 remediation: `ScenarioRunner` passed a controlled clock that started before deterministic fixture attestation issuance. This plan corrects only runner-time alignment and adds lifecycle integration assertions. S0 remains failed pending independent focused re-audit.

## Preserved contracts

- Admission lifecycle verification continues to use a required policy-injected trusted clock; it never falls back to `segment.created_at`.
- Scenario segments and attestations remain immutable; no submitted segment field selects runner time.
- S0 compaction protection remains limited to verified-principal required instruction, constraint, and output-contract segments.
- Effects remain simulated only; no provider, real-effect, S1, or model-efficacy path is added.

## Controlled design

`ScenarioTemplate.materialize()` computes `ScenarioVariant.runtime_start` from trusted catalog/harness state. It is two seconds after the catalog fixture set's latest issuance time, including delayed material. `ScenarioRunner` initializes its `ControlledClock` with that field. The runner clock therefore reflects controlled scenario lifecycle state, rather than a submitted segment or provenance field consumed by admission.

## Required negative and positive tests

| Test | Expected result |
|---|---|
| Reproduce pre-fix nonzero scenario | Initial and delayed provenance reject as not-yet-valid under a clock before issuance. |
| Corrected nonzero scenario | All expected initial segments and scheduled delayed segment admit under `runtime_start`. |
| Expired/future attestation with attacker timestamp | Rejects against the injected runtime clock. |
| Missing/naive runtime clock | Fails closed. |
| External `active_invariant` metadata | Does not create compaction protection. |
| Required verified-principal segment under impossible budget | Remains protected and reports unsatisfied budget. |
| Deterministic smoke/replay | Fresh artifacts pass passive audit and logical replay. |

## Version and evidence effects

Bump package identity to `0.2.3` and harness identity to `2.0.2`. Keep simulator identity unchanged. Produce fresh simulator smoke evidence under a new ignored root; do not rewrite historical v0.2.1/v0.2.2 artifacts. Update public audit records to state that v0.2.2 is superseded and v0.2.3 requires focused independent review of S0-001, S0-002, and S0-003.
