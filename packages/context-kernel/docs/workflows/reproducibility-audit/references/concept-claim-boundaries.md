# AEON Concept Claims and Evidence Boundaries

Use this reference when asked whether AEON has “proven” its idea. Convert the request into testable claims, run the corresponding deterministic evidence, and state the limitation beside every conclusion.

## Evidentiary rule

A passing AEON concept claim demonstrates that the **supplied implementation** satisfied an explicit, deterministic property under the tested fixtures, controlled runtime facts, and local simulator. It does not prove an unbounded general property.

> Claim success is evidence of a specified mechanism under a reproducible test design, not evidence that a model understood, attended to, or semantically complied with instructions.

## Demonstrable implementation claims

| ID | Claim the suite may support | Required evidence | What a pass means | What it does not mean |
|---|---|---|---|---|
| `C1` | Authority follows verifier-issued controlled provenance rather than segment prose or caller claims. | An external-untrusted segment containing an instruction-like claim is demoted to non-authoritative reference; a verifier-issued principal constraint remains authoritative, while a raw caller principal claim is rejected. | The admission and assembly implementation enforce this distinction for the fixture. | Any model will ignore adversarial text. |
| `C2` | Admission and assembly are deterministic for fixed typed inputs. | Repeated admission and assembly produce equal decisions, ordering, rendering, and hashes. | The tested implementation has stable behavior for that input. | All future integrations are deterministic. |
| `C3` | S0 compaction preserves verified principal required constraints under the current deterministic policy. | Under a tight budget, a verified principal required constraint remains resident and the compactor reports an unsatisfied budget instead of silently evicting it. Trusted invariant residency is deferred to S1 and is not demonstrated by this claim. | The tested S0 compaction policy preserves this bounded principal-constraint contract. | A model retains or attends to the information, or untrusted metadata can define protected residency. |
| `C4` | Enforcing invariants block violating simulated actions before effect dispatch. | Observe, warn, and enforce tests check decisions, outcomes, and simulator effect-log state. | Enforce mode did not call the in-memory effect adapter for the violating fixture. | Real tools, providers, or host systems were protected. |
| `C5` | Runtime approval and test-like evidence come from controlled artifacts, not textual claims. | A textual claim fails; a configured runtime token or artifact succeeds. | The tested predicates distinguish controlled evidence from prose. | Approval policy is sufficient for every business or legal context. |
| `C6` | Receipts and traces detect stored-event tampering and preserve logical replay semantics. | A changed event breaks verification; timestamp-only variation preserves the decision hash; a logical payload change alters it. | The local canonical trace and decision projection behave as specified. | Evidence is legally sufficient, externally witnessed, or immutable outside its storage boundary. |
| `C7` | The reusable concept-evidence lifecycle produces reproducible local smoke evidence. | Claim tests, project tests, a new smoke run, passive artifact audit, and replay of every smoke trace pass. A release/D0 gate separately requires replay of every published deterministic run. | The tested code and smoke matrix complete with coherent evidence. | The benchmark establishes production performance across vendors or substitutes for the D0 full published-run gate. |
| `C8` | The benchmark distinguishes expected invariant violations from safe-action false blocks. | The smoke metrics/receipts expose the expected fields and the enforcing arm blocks its deterministic violation without a false block. | The tested scoring design retains separate failure classes. | It measures broad real-world helpfulness, correctness, or safety. |

## Explicit non-claims

The suite must mark each item below **not established** rather than calling it failed or passed:

| ID | Non-claim | Why deterministic AEON evidence cannot establish it |
|---|---|---|
| `N1` | Model attention, understanding, or internal reasoning. | The implementation has no access to model internals. |
| `N2` | Semantic compliance in open-ended natural-language tasks. | Deterministic predicates check specified runtime facts, not all meanings. |
| `N3` | Security of live providers, tools, or production deployments. | Required tests use in-memory effects and no live-provider integration. |
| `N4` | Cross-vendor performance, safety, or superiority. | The benchmark uses a purpose-built deterministic simulator. |
| `N5` | Legal, regulatory, or audit compliance. | Context-delivery receipts are runtime records, not compliance attestations. |
| `N6` | Complete protection against arbitrary adversarial input. | The suite tests enumerated classes and fixtures only. |

## Evidence grade

Use the following labels in final reports:

| Grade | Meaning |
|---|---|
| **Demonstrated** | The claim-specific test and required integrated evidence passed. |
| **Not demonstrated** | A required test, smoke path, audit, or replay did not pass or was not run. |
| **Out of scope** | The statement is an explicit non-claim and cannot be inferred from this suite. |

Never use **proven** without the qualifier “for the tested deterministic implementation and stated fixtures.”

## Minimum concept-evidence run

The reusable runner must execute in a fresh output directory:

1. Project test suite, unless explicitly skipped and labeled.
2. Claim-specific test module.
3. New smoke benchmark run in the output directory.
4. Passive audit of the generated smoke directory.
5. Full replay of all generated smoke traces.
6. Machine-readable JSON and human-readable Markdown report with claims, commands, exits, artifact paths, and non-claims.

Keep all benchmark effects in memory. Do not add live providers, real tools, credentials, network calls, or destructive operations to the required concept-evidence path.
