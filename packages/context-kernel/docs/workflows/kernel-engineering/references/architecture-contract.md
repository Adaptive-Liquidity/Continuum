# AEON Kernel Architecture Contract

Use this reference when a change crosses trust, context residency, policy evaluation, effects, or evidence generation.

## Lifecycle

Preserve the lifecycle:

```text
submit typed segments
  -> validate exact content hashes
  -> admit from controlled provenance and load mode
  -> assemble deterministic typed regions
  -> compact only at controlled turns and budgets
  -> propose an action
  -> evaluate all registered predicates
  -> block before effect, or dispatch to the simulator
  -> record receipt and hash-chained trace
  -> reproduce logical decisions during replay
```

Do not collapse these stages. Each stage exposes evidence used by later stages.

## Typed context contract

`ContextSegment` is frozen and rejects unknown fields. Preserve exact-content SHA-256 validation, timezone-aware `created_at`, and the controlled enumerations for semantics, priority, load mode, and trust class.

| Controlled field | Contract |
|---|---|
| `trust_class` | Derive from runtime provenance, never from content text. |
| `semantic` | Describe intended logical use; allow admission to replace it with a safer `effective_semantic`. |
| `priority` | Control deterministic ordering and compaction candidacy, not authority. |
| `load_mode` | Map to eager, on-demand, or retrieval admission status. |
| `metadata` | Treat as untrusted caller data unless a separately typed, verifier-issued runtime object declares a controlled fact. Never derive authority, invariant residency, approval, or authentication from this mapping. |
| `content_hash` | Hash exact content and reject supplied mismatches. |

Represent submitted content separately from verified provenance. The host must issue an opaque immutable `segment_uid`; a `VerifiedProvenance` record binds that UID, content hash, source identity, trust class, verifier identity, verification time, and policy scope. Require positive verification for principal and trusted-workspace authority. Do not accept caller-supplied `authenticated=true`, `trust_class=principal`, or a caller-selected UID as evidence. Reject duplicate UIDs, duplicate logical segment IDs, missing decisions, extra decisions, and any decision whose segment hash or UID does not match the joined segment. Treat an explicit `enabled=false` from controlled policy as omission. Keep accepted admission decisions in the controlled submission order.

## Authority contract

Keep authority separate from language. Principal segments may be authoritative only for authority-bearing semantics: instruction, constraint, output contract, or approval. Trusted workspace instructions gain authority only through an explicit policy option. Tool output remains evidence. External-untrusted material always becomes non-authoritative reference, even when its prose claims system, approval, or instruction status.

Never add a text parser that promotes authority based on words such as `SYSTEM`, `approved`, `tests passed`, or similar claims.

## Assembly contract

Maintain the five explicit regions and their order:

| Order | Region | Intended contents |
|---:|---|---|
| A | Principal instructions and required constraints | Authoritative principal material except the output contract. |
| B | Trusted workspace context | Non-authoritative workspace material. |
| C | Tool outputs | Non-authoritative tool observations and handoffs. |
| D | External-untrusted reference material | External data, always reference-only. |
| E | Output contract | Authoritative principal output contract. |

Within regions, order entries by required, important, supporting priority and then stable segment ID. Activate on-demand and retrieval segments only through explicit IDs. Keep unloaded IDs visible in assembly metadata.

When changing rendering, remember that the rendered representation determines `assembly_hash`. Change formatting only intentionally and test stable output. Do not treat plain textual section headings, `CONTENT_BEGIN`/`CONTENT_END` markers, or descriptor prose as a security boundary. Preserve region provenance through provider-native structured message parts where available. Otherwise encode each entry in an unambiguous length-delimited envelope and test adversarial content that includes every delimiter, heading, and descriptor form. Archive a redacted exact model-input commitment for each delivery.

## Compaction contract

Run compaction only with an explicit positive character budget and controlled turn. Preserve the summarize-then-evict order. Use stable assembly order and priority buckets; do not use model summarization, wall-clock timing, or nondeterministic selection in the required path.

Protect a segment only when a trusted policy registry identifies its verified UID as a required active invariant, or when it is a verified principal, required segment with instruction, constraint, or output-contract semantics. Never derive protection from caller metadata, segment prose, or an external segment's claimed semantic label. Cap registry-protected residency under an explicit policy and fail closed when a hard budget cannot be satisfied; do not permit an untrusted segment to consume protected space. Record the registry version and protected UIDs with before/after hashes, character counts, affected segments, actions, and reason codes.

## Ledger and predicate contract

Implement every predicate as a side-effect-free function of `Action` and `PredicateContext`. Assign a globally stable `predicate_id` and semantic `predicate_version`. Return stable reason codes for not-applicable, allowed, and violating paths.

Expose every public behavior-affecting option through `configuration()`. The predicate descriptor—ID, version, mode, and configuration—contributes to the predicate-set hash. Keep predicate IDs unique within a ledger.

Sort registrations by predicate ID, version, and mode before evaluation. Preserve mode mapping:

| Semantic result | Observe | Warn | Enforce |
|---|---|---|---|
| Satisfied or not applicable | `pass` | `pass` | `pass` |
| Applicable and unsatisfied | `pass` with violation recorded | `warn` | `block` |

## Effect-boundary contract

Evaluate the complete ledger before invoking the adapter. If any evaluation blocks, return immediately with no simulator effect. If none blocks, apply exactly one simulator effect and map any warning to a warned outcome.

Normalize a proposed action into one canonical typed action object before policy evaluation. For destinations such as URLs, parse once, reject conflicting raw fields, and give the same canonical target to every predicate and dispatcher. Keep required paths in memory. The simulator may update its controlled state—files, pushes, requests, approval actions, outputs, protected actions, resource usage, and effect log—but must not mutate the host filesystem, push Git remotes, make network calls, deploy, or access real secrets. Redact or nonreversibly commit secret-bearing and bearer-token parameters before any receipt, trace, metric, or log serialization.

When adding an action type, update the action enum, simulator state/handler/dispatch, relevant predicate applicability, receipt coverage if needed, and positive/negative tests. Reject unsupported actions explicitly.

## Receipt and trace contract

Keep a context-delivery receipt complete enough to explain admission, assembly, compaction, action policy, performance estimates, and outcome. Require exactly one driver identifier: `model_id` or `simulator_id`. Bind every redacted receipt to its trace, run manifest, and immutable run-spec commitment. A self-consistent public hash chain is a structural-integrity check, not artifact authenticity; publish a separately verifiable authenticated root (for example, a signing-service signature or MAC under a protected key) over the manifest, receipt commitment, trace hash, and decision-trace hash.

Write traces as canonical JSONL events plus a footer. Preserve one-based contiguous sequences, previous-event hashes, per-event SHA-256 hashes, the footer `trace_hash`, and the `decision_trace_hash`.

Canonical JSON must use UTF-8, sorted keys, compact separators, deterministic UTC timestamps, stable enum values, stable path representation, and deterministic set ordering.

Keep `trace_hash` and `decision_trace_hash` conceptually distinct. The chain/footer hash validates the stored event representation. The decision hash projects out explicitly incidental keys such as timestamps, modeled latency, and footer hashes so a logically identical re-execution may use new timestamps.

Do not add fields to the excluded decision-key set merely to make a failing replay pass. Exclude a field only when it is demonstrably incidental to the logical decision and document the reason.

## Replay contract

Verify structural integrity before re-execution. Reconstruct the run from the stored `run_spec`, verify the reproduced trace structure, and compare decision-trace hashes. Report structural errors and logical mismatch separately.

Never repair or rewrite a supplied trace in place during audit. Preserve it as evidence and reproduce into a separate artifact when diagnosis is necessary.

## Interpretation boundary

State that the kernel records runtime context and policy events. Do not claim that regioning proves model attention, that receipts prove semantic understanding, or that deterministic simulator outcomes establish vendor performance or compliance.
