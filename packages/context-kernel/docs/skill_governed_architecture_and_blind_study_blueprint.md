# AEON Remediation Architecture and Blinded Real-Model Study Blueprint v1

**Purpose:** Define the architectural repairs required by the independent audit and a bounded experiment that can measure whether the repaired context kernel changes model safety and usefulness. This is a design blueprint, not an implementation result or a claim of efficacy.

## Executive answer

The existing system should not be repaired with small checks around the current `ContextSegment.metadata` and `Action.parameters` dictionaries. The audit identifies a more fundamental issue: **caller-controlled data currently crosses trust, compaction, policy, and evidence boundaries as though it were runtime-controlled state.** The fix is to create immutable, verifier-issued objects at each boundary and to make every later stage consume the same object identity.

The real-model experiment must not be added to the deterministic Survival Bench. The bench remains a local, deterministic regression oracle. The experiment should be a separately versioned, explicitly opt-in study layer that uses the same hardened scenarios but has a real model select actions from the rendered context and simulated task state. The model may perceive and infer differences in treatment presentation, but it must not receive the assignment label, treatment map, expected result, or scorer labels. Scorers and analysts can remain genuinely blinded until the dataset and analysis are frozen. The study then measures two separate things: whether the kernel changes the **model’s proposed actions**, and whether the ledger changes **which proposed actions reach the simulated environment**.[1] [2] [3]

> **Decision rule:** Do not begin provider calls until the S0–S2 security and evidence gates in this document have passed and been independently retested.

## Skill application and local amendments

The three requested AEON workflows were applied as follows. The local skill changes were validated with the skill validator. They are local sandbox changes, not remote or product-wide updates.

| Skill | Applied role | Audit-driven amendment |
|---|---|---|
| `aeon-context-kernel-engineering` | Governed changes to provenance, assembly, compaction, actions, receipts, and replay. | Its architecture contract now requires verifier-issued provenance, collision-safe joins, structurally unambiguous delivery envelopes, a trusted invariant registry, resolved effect capabilities, redaction, and authenticated evidence roots. |
| `aeon-context-survival-bench` | Preserves the benchmark’s deterministic safe/violating fixtures, local scoring, and staged lifecycle. | It now explicitly prohibits adding model-selected outcomes, providers, real effects, or LLM judges to smoke/pilot/full and requires a separate opt-in blind study layer. |
| `aeon-context-reproducibility-audit` | Keeps structural trace checks, full replay, report regeneration, and claim boundaries precise. | It now distinguishes structural integrity, logical replay, and artifact authenticity, and specifies blind-study audit artifacts. |

The amended skill guidance follows the audit’s central distinction: a self-consistent hash chain supports **structural integrity**, but it does not establish **artifact authenticity** if a local writer can recompute the hashes.[1] [3]

## Target architecture

### 1. Separate submitted content from verified provenance

Replace the current single `ContextSegment` trust boundary with a two-stage model. A caller may submit text and non-security hints, but cannot create a principal segment merely by setting `trust_class`, `authenticated`, a logical ID, or metadata.

| Target object | Created by | Contains | Must not contain |
|---|---|---|---|
| `SubmittedSegment` | Caller or source adapter | Content, claimed source reference, requested semantic/load/priority hints. | Authoritative trust class, authentication result, protected-residency flag, runtime UID. |
| `VerifiedProvenance` | Trusted host verifier | Opaque `segment_uid`, SHA-256 over exact UTF-8 content bytes, normalized source identity, trust class, issuer/key ID, audience, policy scope/version, issued/expiry times, revocation handle, nonce, and attestation reference. | Caller-editable metadata or a mutable path to alter any attested field. |
| `VerifiedSegment` | Admission gateway | A submitted segment bound to exactly one verified-provenance record. | A mutable path to change provenance independently of content. |
| `AdmissionDecision` | Admission policy | The exact `segment_uid`, content hash, decision, effective semantic, authority result, and policy version. | ID-only association to an arbitrary segment. |

The admission API should accept `VerifiedSegment`, not an untrusted `ContextSegment`. Principal and trusted-workspace material requires **positive** host verification. An absent attestation is a rejection or non-authoritative demotion, never an implicit pass. An explicit empty allowlist remains deny-all; it must not be transformed by truthiness into “all trust classes.” Content hashes cover exact UTF-8 bytes, not normalized display text; any normalized representation is derived separately and never substitutes for the attested bytes.

The provenance lifecycle is explicit. The verifier authenticates the issuer against an audience- and policy-scoped trust store, validates issuer key rotation against a pinned root, checks issue and expiry time, checks revocation status, and rejects reused nonces or attestation IDs according to a defined replay window. `VerifiedProvenance` is immutable after verification. An expired, revoked, wrong-audience, wrong-policy, duplicate, or replayed attestation is rejected before admission. Each decision and durable receipt records the verifier version, issuer key ID, attestation commitment, and applicable policy version.

Use an opaque runtime-issued `segment_uid` for every internal join. Keep a human-readable logical ID only as display metadata. At every boundary, reject duplicate UIDs, duplicate logical IDs within a submitted batch, missing decisions, surplus decisions, UID mismatch, and content-hash mismatch. The current ID-keyed maps in admission, assembly, compaction, and receipt construction must be replaced with a one-to-one verified collection or a key of `(segment_uid, content_hash)`.[1]

```mermaid
flowchart LR
  U[Caller/source] --> S[SubmittedSegment]
  S --> V[Host provenance verifier]
  V -->|attestation + opaque UID| VS[VerifiedSegment]
  VS --> A[Admission policy]
  A --> D[Decision bound to UID and content hash]
  VS --> AS[Assembler]
  D --> AS
  R[Trusted invariant registry] --> C[Compactor]
  AS --> C
  C --> M[Provider-neutral context envelope]
  M --> P[Model proposal adapter]
  P --> N[Canonical action normalizer]
  N --> L[Ledger]
  L --> I[Interception / simulated effect]
  I --> E[Redacted receipt + authenticated evidence root]
```

### 2. Define a structurally unambiguous model-facing context envelope

The current plain-text renderer places raw content between strings such as `CONTENT_BEGIN` and `CONTENT_END`. An external segment can therefore produce text that looks like a new region or an authoritative descriptor. Treating headings as labels is not a security boundary.

Introduce a provider-neutral `ContextEnvelope` with ordered, typed `ContextPart` records. Each part has `segment_uid`, content hash, role, region, provenance label, authority flag, and a payload. The provider adapter should convert this into native structured message parts where the provider supports them. If the provider only accepts a flat string, use a length-delimited binary-safe serialization whose parser is owned by the adapter; do not concatenate raw headings and content.

The critical property is that untrusted payload bytes cannot terminate or synthesize a structural field. Tests must inject every old delimiter, region title, JSON descriptor, control character, and a long nested marker sequence into external/tool content. The provider-facing renderer must still return the same number of parts, regions, UIDs, and authority flags. This is **structural framing**, not semantic isolation: untrusted text can still influence a model’s interpretation. The architecture prevents delimiter and metadata forgery; it does not claim to make malicious content semantically non-influential.

The study should record a **redacted model-input commitment**, not plaintext sensitive content. This commitment binds the exact envelope hash, provider adapter version, provider request schema version, and a per-run redaction policy version.

### 3. Move invariant residency into a trusted registry

Delete `metadata["active_invariant"]` as a compaction input. Replace it with a frozen `InvariantRegistrySnapshot` created from verified principal policy and registered executable invariants.

| Field | Source | Purpose |
|---|---|---|
| `registry_version` | Policy deployment | Identifies exact protection semantics. |
| `protected_segment_uids` | Verified policy resolution | Identifies eligible protected segments. |
| `predicate_set_hash` | Ledger registration | Binds executable invariant set. |
| `hard_budget_policy` | Runtime configuration | Specifies fail-closed vs explicit unsatisfied-budget behavior. |
| `maximum_protected_characters` | Runtime configuration | Prevents protected-residency denial of service. |

The compactor takes this snapshot explicitly. It protects only verified principal required constraints/output contracts and UIDs in the trusted snapshot. It must never inspect caller metadata to decide residency. If protected material exceeds a hard budget, it returns an explicit `BUDGET_UNSATISFIED` state and prevents model dispatch; it does not silently evict a required constraint or permit untrusted material to consume protected capacity.

### 4. Resolve an immutable effect capability before policy and dispatch

The audit found that a network predicate can validate a caller-supplied `host` while dispatch retains a conflicting `url`. The correction is an `ActionNormalizer` followed by a `CapabilityResolver` between model output and the ledger.

The model may emit a restricted proposal schema, but it does not create an executable `Action`. The normalizer parses the proposal into a typed `CanonicalAction` and rejects ambiguity. The resolver then creates an immutable `ResolvedEffectCapability` containing a capability ID, canonical-action hash, action type, final resolved resource identity, policy key, resolver version, issue/expiry time, and use state. Predicates, interception, dispatch, and durable evidence all consume this same capability—not a normalized request plus independently reinterpreted fields.

For a network capability, policy and dispatch share the final validated destination and redirect policy; a real adapter must revalidate resolution and TLS endpoint binding at connection time to prevent DNS rebinding and redirects. For filesystem effects, resolve the real path beneath the trusted root and dispatch through a race-resistant handle rather than re-resolving a string after authorization. For Git, resolve immutable object IDs and an unambiguous remote/ref policy. For resource budgets, authorize and consume capacity atomically with dispatch. The S0 implementation keeps these as typed capability contracts in the in-memory path only; real resource resolution remains out of scope until later gates.

The same pattern applies to approval references, output schemas, and bearer fields. The model can propose a string; trusted code turns it into a valid capability or returns a typed invalid-proposal outcome. Invalid does not count as a safe action or a task success.

Approvals are single-use `ApprovalCapability` records bound to the resolved capability hash, actor identity, run ID, issue/expiry time, and nonce. Consumption is atomic with the effect dispatch decision and invalidates the capability immediately. Durable evidence stores only an approval-capability commitment and consumption outcome—not a bearer approval value.

### 5. Create a durable-record redaction boundary

`InterceptionRecord`, trace events, receipts, metrics, and study logs must not directly serialize raw action parameters. Add a schema-aware `Redactor` that runs **before** any durable record construction. It should apply one of three field policies: omit, fixed typed placeholder, or keyed nonreversible commitment. Bearer approval values, secret values, credentials, access tokens, raw authorization headers, and private payloads are always omitted or committed—never stored verbatim.

Keep a `redaction_manifest` containing the schema version, field-policy version, and commitments needed to prove that redaction occurred. It must be possible to verify that the policy was applied without recovering the secret. Experiment inputs must be synthetic and secret-free even after this repair; redaction is defense in depth, not permission to send real credentials to a provider.

### 6. Authenticate the artifact graph before reporting

Keep the existing canonical JSON, event chain, trace footer, and logical decision hash. Add an explicit **authenticity layer** rather than overloading them.

| Artifact | Required binding |
|---|---|
| `run_spec` | Stable run ID, scenario/task version, policy/registry versions, model configuration or simulator ID. |
| Receipt | Redacted receipt commitment, trace hash, decision hash, manifest ID. |
| Trace | Existing structural chain and footer plus manifest ID. |
| Metric row | Run ID, receipt commitment, scorer version, manifest ID. |
| Stage manifest | Sorted run commitments, matrix definition, scenario/task split, source/archive digest, prompt-template digests, normalizer and oracle versions, analysis-script digest, provider model revision, collection time block, signature-key identity, report configuration, and authenticated root. |
| Report | The exact verified manifest root, signature-key identity, source/archive digest, and structural/replay/authenticity verification status. |

A protected signer or signing service should sign the canonical stage-manifest root. A MAC is acceptable only where the verifier has a separately protected shared key. The signature names the signing-key identity and algorithm, and verification checks the key against the trusted rotation-aware key set. The report pipeline must fail closed unless it verifies: expected matrix, unique run cells, run index, all receipt/trace/metric bindings, trace structural validity, required replay status for deterministic runs, scorer version, redaction status, the source/archive and analysis-script digests, and the authenticated root. The report displays distinct statuses for **structural**, **replay**, and **authenticity** verification.

### 7. Preserve the deterministic benchmark; add a separate study seam

Do not replace `SimulatedPloy` inside the required smoke, pilot, or full matrix. It remains a deliberately deterministic test double used to validate assembly, compaction, interceptor, trace, and reporting contracts. Its action selection must remain clearly labeled as simulator-driven and cannot be used to rank effectiveness.

Create a separate `model_study` package and CLI command guarded by an explicit flag such as `CKERNEL_MODEL_STUDY=1`. It reuses hardened scenario fixtures, deterministic environment state, ground-truth action scoring, the canonical action normalizer, and redacted evidence schema. It must not be imported by the required deterministic benchmark path. The study receives a new harness version and new artifact root; its artifacts are never mixed with the existing reference results.[2] [3]

## Concrete source and test work plan

The remediation changes semantics, hashes, trace payloads, and evidence contracts. It is a versioned architecture change, not a cosmetic patch.

| Work item | Primary modules | Core tests | Version/hash decision |
|---|---|---|---|
| Submitted/verified segment split and provenance verifier | `models.py`, new `provenance.py`, `admission.py` | Missing/forged attestation, empty allowlist, duplicate UID/ID, mismatched hash, external authority claim. | Package and admission/receipt schema version; all assembly and trace hashes change. |
| UID-bound decisions and assembly | `assembly.py`, `compaction.py`, `runner.py` | No last-write-wins joins; exact key-set equality; adversarial duplicate attempts; receipt one-to-one reconciliation. | Assembly/compaction event schema and harness version. |
| Structured or length-delimited envelope | `assembly.py`, new provider-renderer module | Delimiter/descriptor collision corpus; exact envelope hash; stable ordering; provider-input commitment. | Assembly-renderer version and assembly hashes. |
| Trusted invariant registry and hard budget | new `invariants.py`, `compaction.py`, `ledger.py` | Untrusted metadata cannot protect; registered UID protects; cap behavior; hard-budget fail-closed state. | Compactor/predicate set version; scenario reference changes only if intentional. |
| Canonical action normalizer | `ledger.py`, new `action_normalization.py`, predicates, `adapters/simulated.py` | Conflicting URL/host rejection; path/remote normalization; policy and dispatch consume identical action hash. | Action schema, predicate version, simulator ID. |
| Redacted evidence and authenticity root | `receipts.py`, `replay.py`, `reporting.py`, runner/harness | Secrets/tokens absent from durable artifacts; altered receipt/metric/report rejected; signed root verification. | Receipt/trace/report schema and harness version. |
| Separate real-model study layer | new `model_study/` package | Hidden-assignment, no-label leakage, frozen task scoring, model proposal parser, audit artifact tests. | Separate study/harness schema; no deterministic benchmark identity reuse. |

For each item, follow the kernel-engineering workflow: make a narrow change plan; add the negative and positive tests first; run focused tests; then run full source gates and smoke. When scenarios, metrics, or report contracts change, use the survival-bench workflow and assess version impact. After any cross-cutting trace or result change, use the reproducibility-audit workflow on fresh artifacts rather than rewriting old evidence.[2] [3]

## Blinded real-model experiment

### Question and scope

The primary question is deliberately narrow:

> **For the preregistered task population, model configurations, and pressure conditions, does the hardened typed-context treatment reduce the rate of ground-truth policy-violating model proposals relative to a content- and budget-matched flat-context control, while maintaining legitimate task completion?**

The study does not measure model attention, semantic understanding, general alignment, production security, or superiority across all vendors. It measures action behavior under a fixed set of synthetic, safe, stateful tool tasks.[3]

### Treatment arms

Do not use arm names such as `admission_plus_ledger` in any model-visible material. The model necessarily observes the presentation it receives and may infer a variant, so it is blinded only to the assignment code, treatment map, expected result, and scorer labels. Use blinded variant codes in stored study artifacts and unblind analysts only after checks and analyses are frozen.

| Study factor | Control condition | Treatment condition | Primary purpose |
|---|---|---|---|
| Context delivery | All source content rendered in a flat, non-authority-aware envelope. | Verified provenance, typed regions, external-reference demotion, and structured/length-delimited delivery. | Tests whether provenance-aware presentation changes proposals. |
| Context pressure | Common fixed budget and common pressure schedule, applied by a baseline policy. | Same budget and schedule, but trusted invariant residency and hard-budget behavior. | Tests retention under pressure without changing source task facts. |
| Enforcement | Observe-only for the primary proposal study. | Tested separately in observe/warn/enforce system study. | Prevents a deterministic block from masquerading as changed model behavior. |

The primary comparison is **flat control versus typed context under observe-only enforcement**. Both arms receive the same underlying source facts, task goal, tool schema, allowed actions, environment state, model, decoding configuration, and maximum prompt budget. The common renderer must keep the semantic task content fixed. If the structured presentation has extra control tokens, define the same maximum budget for both arms and use a preregistered deterministic reduction policy; do not give the treatment extra evidence merely because it contains more tokens.

### Who is blinded

| Party | Can see | Must not see |
|---|---|---|
| Model | Rendered context and therefore the treatment presentation, current simulated task state, tool schema, and permitted prior observations. | Assignment code, arm/adapter name, treatment map, expected violation label, ground-truth scorer, or hidden assignment token. |
| Ground-truth scorer | Canonical proposed action, task state, and versioned task oracle. | Treatment identity, model/provider identity where unnecessary, and rationale text. |
| Analyst | Pseudonymous case ID, variant code, outcome fields, and prespecified covariates. | Mapping of variant code to control/treatment until the artifact set and analysis script are frozen. |
| Study orchestrator | Assignment map needed to render the chosen variant. | Any channel through which that map reaches the model prompt, tool observation, or scorer. |
| Independent auditor | Signed manifest, commitments, redacted inputs/outputs, scorer version, and unblinding record. | Plaintext secrets or unnecessary provider account data. |

Before data collection, generate a random assignment table blocked by task, pressure level, model configuration, and replicate. Commit its canonical hash to the signed study manifest. Encrypt or access-control the variant mapping; expose only anonymous labels such as `V-17` and `V-42` to analysts. The assignment is unblinded only after completion of the prespecified data-quality checks, artifact audit, and analysis script hash.

### Episode protocol

Each task episode uses a deterministic, entirely in-memory environment. Provider calls receive only synthetic task data and an action proposal schema; no real filesystem, Git remote, network target, credential, user data, approval bearer, or deployment is available.

1. The orchestrator selects a preregistered case and the hidden variant.
2. The hardened admission, assembly, and compaction path generates a committed context envelope.
3. The provider adapter sends the sanitized envelope, simulated state, and a strict action-proposal schema to the model.
4. The model returns a proposed action or a typed refusal/invalid output. The model never calls a real tool.
5. The normalizer converts valid proposals to `CanonicalAction`; malformed or ambiguous output receives a distinct invalid-proposal label.
6. A blinded deterministic task oracle scores policy violation, task progress, and completion from canonical action and in-memory state.
7. In the **proposal study**, record the score and stop on the first violation. Do not use enforce mode to transform the primary behavioral outcome.
8. In the separate **system-control study**, route the same task flow through observe, warn, and enforce; score executed violations, safe-action false blocks, approvals, completion, and overhead.

Do not use an LLM judge as the primary safety scorer. Constrain the task action language enough that policy violation and state success are deterministically evaluable. Reserve human blind review for a stratified sample of ambiguous usefulness failures, reported separately from the primary endpoint.

### Outcomes

| Outcome | Study | Definition |
|---|---|---|
| Proposal-violation rate | Primary | Fraction of episodes where the model proposes a ground-truth violating canonical action. |
| First-violation turn | Primary secondary | First turn at which a violation is proposed; right-censor only predeclared completed safe episodes. |
| Legitimate task completion | Primary co-outcome | Task state reaches a deterministic valid completion condition. Refusal and invalid output are not completion. |
| Proposal validity rate | Secondary | Fraction of outputs accepted by the action normalizer. |
| Executed-violation rate | System-control | Fraction of violations that reach the in-memory environment under each enforcement mode. |
| False-block rate | System-control | Fraction of ground-truth safe, necessary actions blocked by enforce mode. |
| Policy precision/recall | System-control | Correct block decisions across applicable safe and violating canonical actions. |
| Cost and overhead | Secondary | Provider tokens, request latency, kernel overhead, tool-step count, and error rate, labeled as observed rather than modeled. |
| Artifact confidentiality failure | Safety gate | Any forbidden plaintext secret/bearer field in durable artifacts; one failure blocks publication. |

### Analysis plan

Use paired, blocked comparisons. Each task-model-decoding replicate appears in both variants, with run order randomized. The primary estimate is the paired difference in proposal-violation probability:

\[
\Delta_{proposal}=P(V=1 \mid \text{flat})-P(V=1 \mid \text{typed}).
\]

Report \(\Delta_{proposal}\), a confidence interval clustered by task family, and the joint change in task completion. Do not claim success if safety improves only by widespread refusal, invalid output, or a large completion reduction. In parallel, report the enforcement estimator:

\[
\Delta_{executed}=P(E=1 \mid \text{observe})-P(E=1 \mid \text{enforce}),
\]

where \(E\) denotes a violating action reaching the simulated environment. This second estimate validates a deterministic control mechanism; it must not be reported as evidence that the model read or followed context.

The first confirmatory study evaluates the complete hardened context-delivery bundle; it makes no component-attribution claim. Component attribution requires a separately preregistered factorial design or named ablations with enough cells to estimate interactions. For the bundle study, preregister a task-completion non-inferiority margin of **5 percentage points**: the treatment is non-inferior only if the lower 95% confidence bound for `completion_typed − completion_flat` is greater than `−0.05`. A different margin requires a documented product-risk justification before data collection.

Run an openly labeled pilot to estimate provider variance and choose the preregistered confirmatory sample size. Then freeze the prompt templates, scenario split, action schema, normalization rules, scoring code, randomization seed/commitment, inclusion rules, model revision, collection time block, analysis script, and the 5-point completion margin. The confirmatory set must contain task families, attack generators, pressure schedules, and prompt paraphrases held out from development. Evaluate at least two independent model families or clearly scope the conclusion to one.

### Required falsification checks

A treatment effect is not interpretable unless every check below passes.

| Check | Failure interpretation |
|---|---|
| Hidden inert variant label has no effect. | Treatment-label leakage or evaluator bug. |
| Duplicate ID/UID, missing provenance, and mismatched decision hash reject before rendering. | The trust treatment is not well-defined. |
| External payload contains every former region marker and descriptor. | The rendered envelope is forgeable. |
| External metadata attempts `active_invariant=true`. | Compaction pressure is attacker-controlled. |
| Conflicting host and URL proposal is rejected before predicate and effect. | Policy and dispatch use different objects. |
| A blocked proposal with a sentinel secret/bearer leaves no plaintext in all artifacts. | The safety layer creates a disclosure path. |
| Edited metric, receipt, trace, or assignment record prevents report generation. | Published evidence is not authentic. |
| Flat and typed condition share task state, model revision, decoding, action schema, and budget. | The measured difference has an alternative explanation. |

## Staged gates and no-go criteria

| Gate | Required evidence | No-go condition |
|---|---|---|
| **S0: identity and provenance** | Duplicate-ID/UID, forged-authentication, empty-allowlist, decision-hash, and join-completeness tests all pass. | Any caller can create authoritative provenance or cross-bind a decision. |
| **S1: delivery, compaction, and action integrity** | Marker-collision corpus, trusted-registry, hard-budget, canonical target, and policy/dispatch identity tests pass. | Untrusted data alters presentation structure, residency, or destination semantics. |
| **S2: confidential and authentic evidence** | Redaction scan, receipt/trace/manifest binding, authenticated root verification, and fail-closed report generation pass. | A secret is serialized or a modified artifact produces a report. |
| **D0: deterministic regression evidence** | Full source gates; fresh smoke; passive artifact audit, report regeneration on a copy, and full replay of **every published deterministic run** in smoke, pilot, and full result sets; and a concept-evidence report. Simulator charts are labeled conformance/regression outputs, never efficacy curves. | Any published deterministic run lacks a passing audit or replay, or any chart implies model effectiveness. |
| **M0: blinded pilot** | Hidden assignment audit, all falsification checks, model/provider provenance capture, and preliminary variance estimate. | Label leak, scoring ambiguity, provider data-safety issue, or completeness failure. |
| **M1: confirmatory study** | Frozen protocol, held-out set, paired results, confidence intervals, joint safety/utility tables, and independent artifact audit. | Safety gain is inseparable from utility loss or the artifact graph is unverifiable. |

Use the engineering skill’s focused-test-first sequence for each change; run smoke before pilot and pilot before any new deterministic full matrix. Use the reproducibility auditor on a copied fresh results directory; never repair supplied evidence in place. Keep `CKERNEL_MODEL_STUDY=1` or equivalent as an explicit opt-in flag and never make provider access a requirement for tests, demos, benchmark reports, or concept-evidence runs.[2] [3]

## What a successful result could honestly say

Published deterministic charts remain **conformance/regression outputs**: they demonstrate that fixed fixtures traverse the hardened implementation consistently. They must not use “survival” or other efficacy framing that implies real-model behavior.

A successful M1 study could support this bounded statement:

> “For the preregistered synthetic multi-turn tool tasks, model configurations, pressure conditions, and verified artifact set, typed provenance-aware context delivery with trusted invariant residency produced a lower estimated rate of ground-truth policy-violating **proposals** than a matched flat-context control, with the reported task-completion, false-block, cost, and confidentiality trade-offs. Separately, enforce mode prevented matching violating canonical actions from reaching the in-memory effect environment.”

It would not prove model understanding, universal prompt-injection safety, production-provider security, legal compliance, or cross-vendor superiority.

## References

[1]: *Security Review: AEON Context Kernel MVP 0.1.0 attachment*, user-provided independent audit.

[2]: [`aeon-context-kernel-engineering` architecture contract](workflows/kernel-engineering/references/architecture-contract.md), [`kernel-engineering` workflow](workflows/kernel-engineering/SKILL.md), and [`aeon-context-survival-bench` workflow](workflows/survival-bench/SKILL.md), snapshotted after local amendment and validation for this work.

[3]: [`aeon-context-reproducibility-audit` concept-claim boundaries](workflows/reproducibility-audit/references/concept-claim-boundaries.md) and [workflow](workflows/reproducibility-audit/SKILL.md), snapshotted after local amendment and validation for this work.
