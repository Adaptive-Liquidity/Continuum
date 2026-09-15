# Continuum

### The flagship DCA implementation for persistent autonomous intelligence.

**Continuum** is Asentxia Systems' flagship implementation of **Distributed Cognitive Architecture (DCA)** and its persistent machine-native runtime substrate.

DCA is the Asentxia-defined systems-level reference architecture for autonomous intelligence that must remain one accountable principal while models, sessions, credentials, processes, runtimes, computers, and hosts change.

> **The principal persists. The components may change.**

## Current canonical model

**Asentxia Systems → Distributed Cognitive Architecture → Continuum → VERA → The Regency**

This is a relationship model, not a literal nesting of software components.

- **DCA** defines seven normative architectural responsibilities.
- **Continuum** is the flagship implementation through which those responsibilities are progressively composed and demonstrated.
- **VERA** — **Verifiable Entity with Revocable Authority** — is the canonical persistent autonomous principal.
- **Continuum Computer** is the persistent logical compute environment associated with autonomous operation.
- **The Regency** is the governance and organizational system for VERAs and multi-VERA structures.

## Seven DCA responsibilities

1. **Environment** — the persistent computational boundary and place of operation.
2. **State** — durable operational, temporal, episodic, and semantic state with lineage and recovery information.
3. **Authority** — explicit, scoped, revocable authority distinct from technical tool availability.
4. **Execution** — controlled transformation of authorized intent into real effects.
5. **Evidence** — independently inspectable records of state transitions, authority, execution, and outcomes.
6. **Coordination** — structured interaction among independently bounded principals and systems while preserving separation.
7. **Cognition Boundary** — the explicit interface separating changing intelligence providers from persistent identity, state, authority, and continuity.

DCA does not define intelligence itself and does not replace models, agent frameworks, or orchestration systems.

## Implementation lineage

Continuum integrates and inherits technical lineage from multiple systems. These lineage names are not automatically current standalone public products.

| Responsibility | Primary implementation lineage |
|---|---|
| Environment | FLOKS / Agent Computer lineage |
| State | AEON-IQ / Context Kernel lineage |
| Authority | Genesis Runtime / AEON Program / authority research |
| Execution | NEXUS / Nexus-IQ |
| Evidence | Proof Capsules, receipts, Context Kernel, SPX402 lineage |
| Coordination | Agent-Bridge and related coordination research |
| Cognition Boundary | Model/provider-neutral interfaces across the architecture |

## Decision #2A — Continuum Persistence Slice

The current internal genesis proof intentionally demonstrates a narrow subset of the Continuum thesis:

- one Continuum Computer
- one VERA
- one process restart on the same host
- durable state written before restart and read afterward
- one explicit scoped revocable grant
- one mediated post-reconstitution effect
- refusal of the same capability after revocation
- one independently inspectable structured evidence record

The reproducible proof harness is in [`proofs/continuum-persistence-slice`](proofs/continuum-persistence-slice).

This proof establishes persistence beyond the tested process/session discontinuity only. It does **not** establish host or machine migration, model-provider swap, coordination completeness, universal recovery, production readiness, or complete implementation of all seven DCA responsibilities.

## Current implementation surfaces

The repository currently contains implementation surfaces for:

- VERA identity and lifecycle state
- runtime placement / Continuum Computer lineage
- durable memory and state
- scoped authority grants and revocation
- mediated effects
- evidence records and proof artifacts
- sessions and handoff structures
- Regency governance models
- packaged lineage implementations including NEXUS, AEON-IQ, FLOKS-PC, Genesis, Nexus-IQ, and Context Kernel

Implementation existence and architecture requirements are separate from maturity claims. Public maturity statements must be tied to the current claims and evidence ledger.

## Claim discipline

Do not infer from this repository that:

- DCA is an externally established industry standard;
- Continuum completely implements all seven responsibilities;
- every VERA continuity property has been demonstrated across every substrate;
- host/machine migration or model-provider swap is verified;
- all lineage research has been integrated;
- security, isolation, recovery, or coordination are universal or production-complete.

See the evidence records and current claims ledger before making capability or maturity claims.
