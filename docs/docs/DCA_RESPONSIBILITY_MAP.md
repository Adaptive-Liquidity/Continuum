# DCA Responsibility Map — Current Canonical Alignment

This map follows **Category Doctrine v1 (approved 2026-09-12)**. DCA defines seven normative responsibilities:

1. Environment
2. State
3. Authority
4. Execution
5. Evidence
6. Coordination
7. Cognition Boundary

The **Effect Boundary** is cross-cutting, not an eighth responsibility.

The package mappings below describe vendored lineage and current repository surfaces. They do **not** imply that every responsibility is completely implemented, integrated into Decision #2A, or production-ready.

## Responsibility 1 — Environment

- **Vendored lineage:** environment tree under `packages/` (historical directory name; retired product name omitted). Not composed into Decision #2A.
- **Orchestrator surface:** `POST /api/dca/placements/lease`, placement lifecycle / fencing (Mongo documents; untested).
- **Decision #2A evidence:** a named Continuum Computer ID is preserved across a process restart on the same host.

Environment answers: **Where does the principal operate, and what remains the environment when the underlying process changes?**

## Responsibility 2 — State

- **Vendored lineage:** `packages/aeon-iq`, Context Kernel lineage. Not Continuum state in Decision #2A.
- **Orchestrator surface:** `POST /api/dca/memory`, `GET /api/dca/memory/recall/{vera_id}` (untested).
- **Decision #2A evidence:** a value written before process restart is read after reconstitution without being supplied as model-context replay.

State answers: **What persists so the principal does not become a new entity at each cognition invocation?**

## Responsibility 3 — Authority

- **Vendored lineage:** `packages/genesis`. Not integrated in Decision #2A.
- **Orchestrator surface:** `POST /api/dca/authority/grants`, `/revoke` (untested).
- **Decision #2A evidence:** one explicit scoped grant allows the mediated effect while active; after revocation the same capability is refused.

Authority answers: **What is this principal authorized to do, under what scope, and can that authority be revoked?**

## Responsibility 4 — Execution

- **Vendored lineage:** `packages/nexus`, `packages/nexus-iq`. Decision #2A does not use them.
- **Orchestrator surface:** `POST /api/dca/effects/propose`, `POST /api/dca/effects/{id}/dispatch` (untested).
- **Decision #2A evidence:** the effect occurs after reconstitution through a local, non-model mediator (`in_process_sqlite_status_write`).

Execution answers: **How does authorized intent become a real effect through a controlled execution boundary?**

## Responsibility 5 — Evidence

- **Vendored lineage:** Nexus proof-capsule docs, Context Kernel. Context Kernel S0 re-audit is not cleared.
- **Orchestrator surface:** `GET /api/dca/evidence`, `GET /api/dca/evidence/verify` (untested).
- **Decision #2A evidence:** an inspector can independently recompute Computer ID, VERA ID, restart discontinuity, state write/read, grant, committed effect, revocation and denied retry.

Evidence answers: **What independently inspectable record shows what happened, under which authority, and with what outcome?**

## Responsibility 6 — Coordination

- **Vendored lineage:** none in this tree. An external coordination pin exists in `artifact/SOURCE_INDEX.md` only.
- **Orchestrator surface:** `POST /api/dca/sessions/open`, `/close`, `/handoff` (Mongo state; untested).
- **Decision #2A:** explicitly out of scope. The persistence slice does not establish multi-VERA coordination.

Coordination answers: **How can independently bounded principals or systems interact without collapsing identity, authority, state or responsibility?**

## Responsibility 7 — Cognition Boundary

- **Current architectural rule:** cognition is an external/changeable source of intelligence, not the store of principal identity, durable state, authority or runtime continuity.
- **Decision #2A evidence:** the process carrying the active computation is terminated and replaced while the same Continuum Computer ID, VERA identity, durable state and authority record persist.
- **Claim ceiling:** the current proof does not require or prove model-provider swap.

Cognition Boundary answers: **How can the intelligence source change without redefining the persistent principal and the systems around it?**

## VERA — cross-responsibility principal

A **VERA — Verifiable Entity with Revocable Authority** — is the canonical persistent autonomous principal. VERA is not an eighth DCA responsibility and is not synonymous with a model instance, process, session, workflow, VM or container.

## Effect Boundary — cross-cutting

> Cognition proposes. Authority constrains. Execution mediates. Evidence records.

## Decision #2A proof boundary

The reproducible proof under `proofs/continuum-persistence-slice/` demonstrates the bounded internal slice defined by Decision #2A.

Same-host clean process restart only: two sequential OS processes share one SQLite store; phase 1 exits normally (no kill or crash). The verifier is a separate, internal script by the same author, not third-party verification. The effect is a local, mediated SQLite write, not an external side effect. This does not demonstrate crash recovery, host migration, model/provider replacement, external effects, third-party verification, cryptographic notarization, or production readiness.
