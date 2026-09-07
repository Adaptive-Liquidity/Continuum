# S0 Implementation and Re-Audit Record

**Status:** Completed as a bounded local implementation milestone. **S1, provider work, real-effect work, AEON-IQ integration, and real-model experimentation remain blocked.**

## Scope and decision

Architecture Blueprint v1 was frozen with the review refinements. This implementation performs **only S0: identity and provenance**. It does not claim to solve structural prompt influence, trusted invariant residency, real-effect resolution, authenticated evidence roots, approvals as capabilities, or empirical model safety/usefulness.

> The successful audit evidence below is **deterministic implementation and regression evidence** for the local simulator. It is not an external security assessment, production identity-service assessment, real-model experiment, or efficacy result.

## Completed S0 behavior

| Requirement | Implemented S0 behavior | Evidence |
|---|---|---|
| Caller trust claims do not create authority | Raw `ContextSegment` claims receive an explicit `PROVENANCE_REQUIRED` rejection. The admission path consumes `VerifiedSegment`. | Adversarial admission tests. |
| Provenance binds identity and exact bytes | `VerifiedProvenance` binds opaque UID, logical/source IDs, SHA-256 exact-content hash, trust class, issuer key ID, audience, policy scope, issued/expiry times, nonce, attestation ID, and signature. | `provenance.py` verification tests. |
| Provenance lifecycle checks exist | The local verifier checks trusted key identity, signature, audience, policy scope, issue/expiry time, revocation set, content/source/logical-ID binding, and same-session attestation replay. | Positive and negative admission cases. |
| Collision-safe joins | Admission batches, assemblies, final runner reconciliation, and receipts reject duplicate logical IDs or verified UIDs and require exact UID/hash/trust bindings. | Admission, assembly, receipt, and runner tests. |
| Later stages do not use claimed trust | Assembly placement and entries derive trust class from `AdmissionDecision.verified_trust_class`, not `ContextSegment.trust_class`. | Region-separation tests and benchmark runs. |
| Evidence identifies verified segments | Assembly entries, compaction records/events, receipts, and trace payloads carry verified UIDs. | Fresh S0 smoke/pilot/full artifacts. |
| Simulator claims are not efficacy claims | Reports and charts now use **deterministic conformance/regression** language and state that no real-model safety, usefulness, or provider superiority is measured. | Final chart visual inspection and passive report checks. |

The public package, scenario, adapter, harness, and simulator identities were versioned to `0.2.0`/`2.0.0` where the S0 schema and decision behavior changed. Historical v1 artifacts were preserved; fresh S0 artifacts were written under a separate evidence root.

## Source and test changes

| Area | Key files |
|---|---|
| Provenance model and verifier | `src/context_kernel/models.py`, `src/context_kernel/provenance.py`, `src/context_kernel/admission.py` |
| Exact identity joins | `src/context_kernel/assembly.py`, `src/context_kernel/compaction.py`, `src/survival_bench/runner.py`, `src/context_kernel/receipts.py` |
| Deterministic fixture issuance | `src/survival_bench/scenarios/catalog.py`, `src/survival_bench/adapters.py`, `examples/basic_usage.py` |
| Adversarial and regression coverage | `tests/conftest.py`, `tests/test_models_admission.py`, `tests/test_assembly_compaction.py`, `tests/test_receipts_replay.py` |
| Report claim boundary | `src/survival_bench/reporting.py` |
| Local workflow maintenance | The three AEON skill packages; the reproducibility concept fixture and passive report validator were updated to the S0 contract and skill-validated. |

## Quality gates

| Gate | Result |
|---|---:|
| Focused S0 tests: admission, assembly/compaction, receipts/replay | **24 passed** |
| Complete project tests | **122 passed** |
| Formatting | **33 files already formatted** |
| Ruff lint | **Passed** |
| Strict Mypy | **Passed; 25 source files** |
| Coverage diagnostic | **91% total**; admission 100%, provenance 72% (diagnostic only) |
| Local example | Passed; external reference rendered in region D and unsafe simulated write blocked before effect |
| Observe/warn/enforce demo | Passed; enforce left simulated effect count at zero |
| Local AEON skill validation | All three packages valid |

## v0.2.1 audit-environment security patch

After the official repository was published, GitHub and an independent `pip-audit` scan identified `PYSEC-2026-1845` (`GHSA-6w46-j5rx-g56g`) in the locked pytest `8.4.2` development dependency. The OSV advisory states that pytest through `9.0.2` on UNIX used predictable temporary-directory handling that could allow a local denial of service or possible privilege gain; `9.0.3` is the first fixed release.[1]

Version `0.2.1` requires pytest `>=9.0.3,<10`; the regenerated lock resolves pytest `9.1.1`. The synchronized environment then passed all 122 tests, Ruff formatting/lint, strict Mypy, the local example, the observe/warn/enforce demo, repository metadata/link validation, and a fresh deterministic smoke stage. A repeat dependency scan reported no known third-party-package vulnerabilities. No S0 runtime behavior, scenario, adapter, predicate, or deterministic decision contract changed.

## Fresh deterministic evidence and reproducibility audit

Fresh artifacts are deliberately excluded from source control and preserved in the [v0.2.1 audit release](https://github.com/Adaptive-Liquidity/aeon-context-kernel/releases/tag/v0.2.1), with the audit-package contents and scope recorded in [`docs/releases/v0.2.1-s0.md`](releases/v0.2.1-s0.md). The published chart/report copies were generated from saved metrics after report regeneration; the original fresh execution root was retained separately during the local evidence run.

| Stage | Runs | Passive artifact audit | Full logical replays | Result |
|---|---:|---:|---:|---|
| Smoke | 4 | Pass, 0 errors / 0 warnings | 4 / 4 | Pass |
| Pilot | 48 | Pass, 0 errors / 0 warnings | 48 / 48 | Pass |
| Full | 240 | Pass, 0 errors / 0 warnings | 240 / 240 | Pass |
| Total | 292 | Every published final stage audited | 292 / 292 | Pass |

The passive auditor is a standard-library, non-project-import structural check. It reconciled manifests, run IDs, JSON/JSONL structure, receipts, metrics, report derivations, event chains, trace footers, and decision hashes. Full replay then re-executed every final stored trace with the project CLI and reproduced its canonical decision-trace hash. This satisfies a **tool-independent reproducibility check**, but is not an external independent security review.

The finalized reusable concept-evidence suite also passed. It ran project tests, S0 claim-specific tests, a separately fresh four-run smoke stage, a passive audit, and four full replays. Its machine-readable and rendered reports are preserved in the v0.2.1 audit-release evidence archive rather than the source tree.

The first attempt exposed an obsolete claim-test template that used raw caller trust and the pre-S0 admission API. That output was preserved in the non-final evidence root. The local audit skill was then updated to construct verifier-issued segments and to scope C3 to **verified principal required constraints only**; it no longer represents trusted invariant residency as demonstrated. The refreshed skill package and final concept-evidence run passed.

## Visual validation

The full-stage chart and visual-validation record are preserved in the v0.2.1 audit-release evidence archive. The chart reads **“Deterministic Context-Kernel Conformance,”** identifies local simulator conformance/regression output, and labels the y-axis as scheduled fixture violations. It does not present itself as an efficacy or real-model survival curve.

## Explicit residual risks and stop gate

| Deferred item | Why it remains open |
|---|---|
| S1 structurally unambiguous model envelope | Delimiter/descriptor framing and semantic influence are not repaired in S0. Untrusted text may still influence a model. |
| S1 trusted invariant registry | Legacy simulator compaction still contains `metadata["active_invariant"]` behavior for old deterministic fixtures. S0 does **not** claim it is a trusted policy source. |
| Real-effect capability resolution | DNS rebinding, redirects, symlink races, Git ref ambiguity, and atomic resource accounting are not implemented. |
| Approval capability | Single-use, actor/run/hash-bound approvals with atomic consumption are not implemented. |
| Evidence authenticity root | Current hash chains and replay provide structural/replay integrity only. A protected signer, signature-key identity, and manifest source/script bindings are deferred. |
| Production provenance service | The in-memory HMAC authority is a deterministic fixture trust root, not production key custody, issuer federation, durable nonce storage, or live revocation/key-rotation service. |
| Blind real-model study | No provider calls, model studies, external tools, real credentials, or AEON-IQ integration were started. |
| External independent re-audit | The reproducibility audit is independent of project imports for structural checks, but it is not a third-party security assessment. |

**Stop decision:** Do not proceed to S1 or any provider, real-effect, AEON-IQ, or model-study work on the strength of these results alone. The next permitted action is an external or separately staffed security re-audit of S0 and acceptance of its findings. Only after that acceptance should S1 be planned.

## Reference

[1] [OSV, “PYSEC-2026-1845: pytest has vulnerable tmpdir handling”](https://osv.dev/vulnerability/PYSEC-2026-1845)
