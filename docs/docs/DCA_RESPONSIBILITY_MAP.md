# DCA Responsibility Map — Current Canonical Alignment

This map follows **Category Doctrine v1 (approved 2026-09-12)**. DCA defines seven normative responsibilities:

1. Environment
2. State
3. Authority
4. Execution
5. Evidence
6. Coordination
7. Cognition Boundary

The package mappings below describe implementation lineage and current repository surfaces. They do **not** imply that every responsibility is completely implemented or production-ready.

## Responsibility 1 — Environment

- **Primary lineage:** `packages/floks-pc`
- **Orchestrator surface:** `POST /api/dca/placements/lease`, placement lifecycle / fencing
- **Current enforcement surface:** placement state, persistent computer identifier, provider reference, lease epoch, and execution fencing.
- **Decision #2A evidence:** a named Continuum Computer ID is preserved across a process restart on the same host.

Environment answers: **Where does the principal operate, and what remains the environment when the underlying process changes?**

## Responsibility 2 — State

- **Primary lineage:** `packages/aeon-iq`, Context Kernel lineage, orchestrator durable records
- **Orchestrator surface:** `POST /api/dca/memory`, `GET /api/dca/memory/recall/{vera_id}`
- **Current enforcement surface:** VERA-bound durable state and memory records with provenance-oriented fields.
- **Decision #2A evidence:** a value written before process restart is read after reconstitution without being supplied as model-context replay.

State answers: **What persists so the principal does not become a new entity at each cognition invocation?**

## Responsibility 3 — Authority

- **Primary lineage:** `packages/genesis`, AEON Program, authority research
- **Orchestrator surface:** `POST /api/dca/authority/grants`, `/revoke`
- **Current enforcement surface:** scoped grants, expiry, parent/child attenuation constraints, revocation, VERA lifecycle interactions.
- **Decision #2A evidence:** one explicit scoped grant allows the mediated effect while active; after revocation the same capability is refused.

Authority answers: **What is this principal authorized to do, under what scope, and can that authority be revoked?**

## Responsibility 4 — Execution

- **Primary lineage:** `packages/nexus`, `packages/nexus-iq`
- **Orchestrator surface:** `POST /api/dca/effects/propose`, `POST /api/dca/effects/{id}/dispatch`
- **Current enforcement surface:** effect preparation, authority resolution, placement fencing, mediated dispatch, bounded outcomes and evidence emission.
- **Decision #2A evidence:** the effect occurs after reconstitution through a mediator that is distinct from cognition.

Execution answers: **How does authorized intent become a real effect through a controlled execution boundary?**

## Responsibility 5 — Evidence

- **Primary lineage:** Nexus Proof Capsules, AEON receipts, Context Kernel, SPX402 lineage, Continuum evidence records
- **Orchestrator surface:** `GET /api/dca/evidence`, `GET /api/dca/evidence/verify`
- **Current enforcement surface:** structured transition/effect records and repository-specific proof artifacts.
- **Decision #2A evidence:** an inspector can independently read the Computer ID, VERA ID, restart discontinuity, state write/read, grant, committed effect, revocation and denied retry.

Evidence answers: **What independently inspectable record shows what happened, under which authority, and with what outcome?**

## Responsibility 6 — Coordination

- **Primary lineage:** Agent-Bridge, orchestrator session/handoff structures, related coordination research
- **Orchestrator surface:** `POST /api/dca/sessions/open`, `/close`, `/handoff`
- **Current enforcement surface:** bounded session and handoff structures that preserve principal separation.
- **Decision #2A:** explicitly out of scope. The persistence slice does not establish multi-VERA coordination.

Coordination answers: **How can independently bounded principals or systems interact without collapsing identity, authority, state or responsibility?**

## Responsibility 7 — Cognition Boundary

- **Primary lineage:** model/provider-neutral interfaces across Continuum, AEON-IQ and related systems
- **Current architectural rule:** cognition is an external/changeable source of intelligence, not the store of principal identity, durable state, authority or runtime continuity.
- **Decision #2A evidence:** the process carrying the active computation is terminated and replaced while the same Continuum Computer ID, VERA identity, durable state and authority record persist.
- **Claim ceiling:** the current proof does not require or prove model-provider swap.

Cognition Boundary answers: **How can the intelligence source change without redefining the persistent principal and the systems around it?**

## VERA — cross-responsibility principal

A **VERA — Verifiable Entity with Revocable Authority** — is the canonical persistent autonomous principal. VERA is not an eighth DCA responsibility and is not synonymous with a model instance, process, session, workflow, VM or container.

Current Continuum models keep the VERA identity separate from runtime placements, memory/state, authority grants, effects and sessions.

## Effect Boundary — cross-cutting, not an eighth responsibility

The current Continuum execution gate resolves the effect, applicable placement state and current authority before dispatch, then records the resulting outcome. NEXUS and related execution lineage provide the deeper sandbox/capability implementation surfaces.

The governing separation is:

> Cognition proposes. Authority constrains. Execution mediates. Evidence records.

## Decision #2A proof boundary

The reproducible proof under `proofs/continuum-persistence-slice/` currently demonstrates the bounded internal slice defined by Decision #2A: process restart on the same host, persistence beyond process/session, durable state, scoped revocable authority, one post-reconstitution mediated effect and an independently inspectable evidence record.

It does not establish complete implementation of all seven DCA responsibilities, host/machine migration, model-provider swap, production-scale coordination, universal recovery or production readiness.
