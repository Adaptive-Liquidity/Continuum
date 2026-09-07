# S0-001 and S0-002 External Finding Intake

> **Status:** The prior v0.2.1 S0 audit gate is failed. This document records the user-provided external review summary and the subsequent source-level confirmation used to create the v0.2.2 remediation candidate. It is not a replacement for the reviewer’s original report or a focused re-audit decision.

## Reported findings

| ID | Severity in external summary | Summary |
|---|---:|---|
| S0-001 | High | If admission omitted `now`, verification used `segment.created_at`; a submitted timestamp could make expired or future attestations appear lifecycle-valid. The benchmark adapter omitted `now`. |
| S0-002 | Low | A segment could set `metadata.active_invariant=true` and receive compaction residency protection. |

## Source-level confirmation before remediation

The pre-remediation `AdmissionPolicy.admit()` selected `now or segment.created_at`, and `BenchmarkAdapter.admit()` called `admit_many()` without a `now` value. The pre-remediation compactor protected a segment when the caller-controlled `active_invariant` metadata flag was true. These observations confirmed that both reported control paths existed in the audited source.

## Remediation candidate boundary

The v0.2.2 candidate removes both paths. Admission now requires a policy-injected, timezone-aware runtime clock; benchmark adapters require that clock and the runner supplies `ControlledClock.peek()`. S0 compaction now protects only verifier-confirmed principal required instruction, constraint, and output-contract segments. It does not claim an S1 trusted invariant registry.

Internal regression tests and fresh simulator evidence support the remediation record, but they do not clear the audit gate. A focused independent reviewer must reproduce the prior conditions, inspect every clock call path, and issue a new written decision using [`docs/releases/v0.2.2-s0-remediation.md`](../../releases/v0.2.2-s0-remediation.md).

## Docker environment note

The external summary also included a failed pull of `nvidia/cuda:12.2.2-runtime-ubuntu22.04` caused by a connection refusal to Docker Hub. This is classified as a network/registry environment failure, not an S0 finding, because the agreed S0 simulator does not require an NVIDIA container image. The focused reviewer should record it only if their chosen audit environment requires the image for a documented S0 check.
