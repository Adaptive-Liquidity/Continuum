# Audit Addendum: How the Security Review Changes the Causal-Validation Plan

**Purpose:** This addendum compares the user-provided independent security review with the earlier causal-validation research report. It does not independently rerun the audit. It treats the audit’s stated static tracing and safe reproductions as evidence to be addressed before any new effectiveness claim is made.

## Bottom line

The audit **confirms the direction** of the causal-validation report but makes its sequencing materially stricter. The earlier report argued that the existing chart is harness plumbing, not causal evidence, because the simulated Ploy selects behavior from adapter identity rather than assembled context. The audit adds a second, prior problem: several of the trust, compaction, effect-policy, receipt, and publication boundaries are themselves not secure or evidentially sound enough to serve as the foundation of a causal study.[1] [2]

The implication is not merely “run a better benchmark.” The correct order is now:

> **Harden authority, canonical-object, rendering, redaction, and evidence-integrity boundaries; independently verify those repairs; then run the randomized model-behavior study.**

Without that order, a positive behavioral result would remain ambiguous. It could reflect a forged principal segment, an attacker-controlled compaction exemption, a flat-prompt marker injection, a destination mismatch between policy and dispatch, or a fabricated result artifact—not the intended context-kernel mechanism.

| Earlier report conclusion | Audit effect | Revised conclusion |
|---|---|---|
| The existing survival plot validates plumbing, not context survival. | **Confirmed and strengthened.** Reports can be generated from standalone `metrics.json`, and receipts are not bound to an authentic trace root. | The plot is only an internal workflow demonstration; it is not even tamper-resistant evidence under the stated local-modification threat model. |
| Authority must come from authenticated provenance, not text. | **Confirmed as an unmet prerequisite.** The audit reports caller-controlled principal trust and missing positive authentication. | No behavioral study may claim trusted authority until provenance is runtime-attested, not self-asserted by `ContextSegment` fields. |
| Model-driven paired randomization can test typed context delivery. | **Refined.** Plain-text assembly allows external content to forge control markers. | The treatment must be delivered through an unambiguous, model-facing structured or length-delimited envelope before it can be experimentally tested. |
| Deterministic simulators are useful if agents cause state changes. | **Refined.** The network policy and future dispatch can disagree about destination, and untrusted metadata can alter compaction residency. | Simulator state remains useful only after policy and dispatch consume the same canonical action object and compaction protection derives from trusted state. |
| Evaluate security jointly with completion and false blocks. | **Expanded.** Blocked secrets and approval tokens are retained in durable traces. | Add confidentiality and artifact-safety metrics; no production-like secret or bearer value may enter experiment traces. |

## Finding-by-finding mapping

| Audit finding | Earlier report section affected | Why it changes the plan | Required gate before causal efficacy work |
|---|---|---|---|
| **1. Duplicate segment IDs cause authority confusion** | “Non-negotiable repair,” “Falsification and mechanism checks” | A provenance-swap experiment is invalid if joins can associate a tool segment’s text with a principal decision. The nominal treatment is not well-defined. | Reject duplicate IDs at all boundaries; require one-to-one segment/decision key sets; verify joined content hashes; add adversarial collision tests. |
| **2. Caller-asserted provenance becomes principal authority** | “Causal question and estimand,” “Threats to validity” | The report assumed trust treatment was randomized by the runner. The audit says callers can self-assert it. That defeats the core authority hypothesis before a model sees context. | Separate caller content from a verifier-issued provenance attestation; require positive verification for trusted classes; make an empty allowlist deny all; independently re-audit. |
| **3. Untrusted text forges assembly markers** | “Model-driven proposal interface,” “Content-preserving provenance swap” | Changing regions in a plain-text prompt does not cleanly manipulate provenance when untrusted text can synthesize region delimiters. | Use provider-structured message parts where supported; otherwise use length-delimited/escaped rendering and explicit adversarial delimiter tests. Archive exactly what the model received. |
| **4. Reports trust standalone metrics** | “Outcome definitions and reporting,” “Statistical design” | A chart can be fabricated by editing `metrics.json` without changing traces. Therefore a published treatment effect would not be auditable. | Build a report-verification gate: validate manifest matrix, unique cells, run index, receipts, traces, and replay status before loading metrics. Reject missing, extra, or mismatched artifacts. |
| **5. Receipts lack an authentic trace root** | “Claims supportable after a successful study” | Self-consistent public hashes are not evidence authenticity under local write access. Replay is useful but not a signature or receipt binding. | Distinguish structural, replay, and authenticity verification; bind receipt contents to a signed or MACed root using a separately protected key or trusted attestor; pin expected run identity and root. |
| **6. Host/URL conflict bypasses the allowlist** | “Experiment B: deterministic execution control” | A stated policy block cannot be trusted if policy validates one field while dispatch uses another. A future real adapter would amplify the problem. | Canonicalize and validate one destination object once; reject inconsistent host/URL fields; pass the same object to predicate and adapter; test policy/dispatch identity. |
| **7. Any segment self-protects from compaction** | “Compaction dose response,” “Long-horizon retention” | An adversary can alter the independent variable—context pressure and residency—by setting metadata. The compaction study is confounded. | Move protection to a trusted invariant registry; disallow untrusted metadata from affecting residency; cap protected space; fail closed or return an explicit hard-budget result. |
| **8. Blocked secrets and approvals persist in artifacts** | “Outcome definitions,” “Realistic safe environments,” “Optional live smoke” | Safety experiments can create a second disclosure path. This blocks use of production-like credentials and weakens the audit-trail value proposition. | Redact or keyed-hash sensitive fields before durable serialization; never persist bearer approval values; use restrictive file permissions; scan generated artifacts in CI. |

## What the audit means for the original thesis

The audit does **not** refute the conceptual thesis that typed admission, invariant residency, and effect-boundary enforcement could improve agent safety. It does refute any claim that the current MVP already realizes the thesis securely enough for real adapters or evidentially enough for published effectiveness results. In particular, the first two high-severity findings mean the present system does not yet satisfy its own foundation: authority is not reliably derived from authenticated runtime provenance.[1]

The distinction between deterministic control and model behavior remains essential. A fixed predicate can still be made correct and effective at a simulated effect boundary after the canonical-action and provenance repairs. That would establish a narrow enforcement claim. It says nothing yet about whether typed context changes the model’s *proposal distribution*. The latter requires the model-driven randomized experiment described in the earlier report, but only after the model-facing context envelope itself is non-forgeable and the treatment is well-defined.[2]

## Revised evidence ladder

The prior L0–L3 sequence must be preceded by a security and evidence-integrity layer.

| Revised level | Question | Minimum evidence | Claim allowed |
|---|---|---|---|
| **S0: object identity** | Are authority, decisions, and dispatched effects bound to the same canonical objects? | Duplicate-ID, mismatched-hash, host/URL disagreement, and trust-forgery tests fail closed. | “Object joins and policy-dispatch identity are verified for the supported schema.” |
| **S1: presentation and memory integrity** | Can untrusted data alter authority presentation or compaction residency? | Delimiter-injection, metadata-abuse, protected-budget, and exact-rendered-input tests pass. | “The documented delivery envelope and residency policy resist these tested confusions.” |
| **S2: audit-evidence integrity** | Can a report be traced to authentic, complete runs? | Manifest, receipt, trace, replay, redaction, and authenticated-root verification pass before report generation. | “The published artifact set has the stated verification status.” |
| **C0: plumbing** | Does the safe harness execute and replay? | Existing simulator tests, clearly labeled. | “The harness operates.” |
| **C1: causal behavior** | Does treatment change model proposals under matched, hidden randomization? | Proposal-only paired randomized experiment with ground truth. | “The treatment had an estimated effect within this study population.” |
| **C2: utility and generalization** | Does the effect persist without unacceptable task or confidentiality cost? | Held-out families, multiple models, completion, false-block, and artifact-safety results. | “Evidence supports bounded effectiveness across the studied distribution.” |

A study must not skip from C0 to C1. The audit’s first seven findings mean that several manipulated variables and outcome records are not yet reliable. A study must not skip from C1 to C2 either: a lower unsafe-proposal rate without task completion, false-block, or data-handling results is not a practical improvement.

## Specific revisions to the causal experiment design

### 1. Define treatment through a trusted context envelope

The experiment should not pass raw `ContextSegment` objects directly from callers into admission. It should create a runner-owned `ContextEnvelope` containing opaque runtime-issued segment identities, immutable content digests, verified provenance attestations, and an invariant-registry reference. The agent-facing representation must be generated solely from that envelope. Untrusted content belongs in data fields that cannot syntactically close a region or emit a counterfeit descriptor.

This adjustment changes the earlier provenance-swap test. Hold the text constant, but have the **trusted experiment runner** issue the provenance attestation and rendered placement. Do not let a test-case supplier choose `trust_class`, `authenticated`, an opaque ID, or `active_invariant`. The resulting manipulation is then identifiable: the treatment differs in verified provenance policy and rendering, not in a caller-controlled flag.

### 2. Treat compaction as a trusted intervention, not segment metadata

The earlier recommendation to sweep budget and compaction schedule remains useful, but it now requires a trusted invariant registry. Required residency must be determined from an authenticated principal constraint or ledger registration, never from arbitrary metadata. The experiment should record both the logical context set and the exact active envelope per turn, plus a deterministic assertion that no untrusted segment gained protected residency.

### 3. Split proposal, enforcement, and confidentiality outcomes

The original two-experiment model becomes a three-part design.

| Experiment | Agent action path | Main outcome | New audit condition |
|---|---|---|---|
| **A. Context behavior** | Model proposes; no enforce transformation of primary outcome. | Ground-truth proposal violation and task completion. | Exact rendered input is persisted in a safe redacted form and tied to trusted envelope IDs. |
| **B. Effect control** | Same proposals pass through observe/warn/enforce using a canonical action target. | Executed violation, false blocks, and policy precision/recall. | Predicate and dispatcher consume the same parsed target object. |
| **C. Evidence safety** | All runs and reports are verified before publication. | Artifact completeness, replay, authenticity state, and sensitive-field leakage rate. | Report fails closed on a missing, untrusted, altered, or secret-bearing artifact. |

Experiment C is not administrative overhead. It is part of the product’s core value proposition: a context-delivery receipt has no differentiating audit value if it can be silently altered, detached from its trace, or used to persist a secret that enforcement stopped from leaving through the intended channel.

### 4. Add negative controls that target audit findings

In addition to the earlier inert-label negative control, add the following preregistered checks. A passing efficacy result should be rejected if any of these controls fails.

| Negative control | Expected result |
|---|---|
| Duplicate external and principal IDs | Rejection before assembly; no region is rendered. |
| Principal claim without verifier-issued attestation | Rejection or demotion; never authoritative. |
| External text containing region markers and fake descriptors | Rendered as opaque data; cannot change parser-visible envelope structure. |
| External `active_invariant` metadata | No protected residency or budget influence. |
| Allowlisted `host` plus non-allowlisted `url` | Rejection before policy pass or adapter invocation. |
| Blocked action containing secret or approval bearer | Durable trace/receipt contains only a redacted or nonreversible commitment, never plaintext. |
| Edited metrics, receipt, or trace | Report generation fails with an explicit verification-status error. |

## Revised acceptance criteria for a publishable effectiveness result

An effectiveness chart is publishable only if all of the following hold.

1. **Security foundation:** all S0 and S1 tests pass, including independent reproduction of the eight audit remediations.
2. **Evidence foundation:** reporting verifies an authenticated and complete artifact graph; the report labels structural, replay, and authenticity status separately.
3. **Causal foundation:** the model receives no arm label, expected action label, or scorer information; assignment is randomized and paired; primary proposals are scored from task ground truth.
4. **Fair comparison:** control and treatment are matched on task state, model, decoding configuration, token budget, semantic information, and action affordances. The intended kernel factor is the only changed variable.
5. **Utility foundation:** task completion, false blocks, approvals, latency, cost, and artifact confidentiality are reported next to violation prevention.
6. **Generalization foundation:** the final estimate is evaluated on held-out tasks, attack generators, pressure schedules, and at least two model families, with raw redacted traces and confidence intervals.

## Priority order

The audit changes the first engineering milestone from “add a model adapter” to “make the trusted boundary real.” The recommended order is: resolve Findings 1 and 2 first; then Findings 3, 6, and 7 before any model-facing or live-effect adapter; then Findings 4, 5, and 8 before publishing an effectiveness result or accepting sensitive inputs. After each group, obtain an independent retest. Only then build the hidden-treatment, model-driven causal harness.

This order also answers the audit’s two open questions. The first real host adapter needs an explicit authenticated provenance mechanism issued outside caller-controlled segment metadata. The first model integration should preserve region structure through native structured message parts if the provider allows it; if not, it needs a length-delimited data envelope plus adversarial parser-collision tests. A plain concatenated prompt is not an adequate security boundary.[1]

## References

[1]: *Security Review: AEON Context Kernel MVP 0.1.0 attachment*, user-provided audit, lines 1–467.

[2]: [*From Harness Plumbing to Causal Evidence: A Research Plan for the AEON Context Kernel*](causal_validation_research_report.md).
