# Continuum architecture

This note expands the root README. It is descriptive of **this repository**, not a production architecture claim.

## Hierarchy

**Asentxia Systems** is the company.

**Distributed Cognitive Architecture (DCA)** is the Asentxia-defined reference architecture. It has seven responsibilities:

1. Environment
2. State
3. Authority
4. Execution
5. Evidence
6. Coordination
7. Cognition Boundary

The **Effect Boundary** is cross-cutting. It is not an eighth responsibility. Authorized intent is mediated, then recorded. Cognition proposes; it does not write ambient effects.

**Continuum** is the flagship implementation and runtime in this repository.

**VERA** (Verifiable Entity with Revocable Authority) is the persistent principal. A VERA is not a model instance, process, session, VM, or container.

**Continuum Computer** is the persistent logical environment associated with a VERA.

**The Regency** is a governance *surface* in the Mongo orchestrator (`/api/regency/*` and the ops dashboard). Mandates, roles, assignments, and emergency suspend exist as code. There are no Continuum tests for them. Treat that surface as working but untested, not as proven multi-VERA governance.

## Two stacks

This repository contains two Continuum-facing stacks. They are not the same system.

| Stack | What it is | Persistence | Tests in this repo |
|---|---|---|---|
| Decision #2A proof | Stdlib Python harness: two OS processes, one SQLite file | Local SQLite | Working and tested (`make reproduce-p00`) |
| Mongo orchestrator | FastAPI + Motor models and routes; CRA ops dashboard | MongoDB (`MONGO_URL`, `DB_NAME`) | Working but untested (no `backend/` or `frontend/` tests) |

Decision #2A does not start Mongo, does not import `backend/`, and does not call vendored lineage runtimes.

The orchestrator does not reproduce Decision #2A. Placements are Mongo documents with generated computer IDs. Memory facts stay in Mongo. The NEXUS adapter can fall back to `nexus.echo` when wasmtime is missing. Seed demo effects can be recorded as committed without going through `dispatch_effect`.

A third UI, the Vite landing shell under `src/` / `index.html`, is a visual mock. It is not wired to the API and displays invented figures. Do not treat those figures as measurements.

## Responsibility numbering

Category Doctrine and the root README number the seven responsibilities as Environment … Cognition Boundary.

`backend/server.py` uses a different R1–R7 map (R1 = VERA registry, R7 = sessions). The ops dashboard follows the server map. When you read `R3` in the dashboard, it is memory, not Authority.

## Effect Boundary

In the proof, the mediator is `continuum-persistence-slice-effect-boundary` and the effect class is `in_process_sqlite_status_write`.

In the orchestrator, `POST /api/dca/effects/{id}/dispatch` is intended to resolve grant + placement, call `backend/adapters/nexus.py`, and append evidence. That path is untested in this repository.

## Vendored lineage

`packages/` holds upstream trees with their own READMEs, tests, and (where present) licenses. They are **component evidence**, not a composed Continuum product:

- State lineage: `packages/aeon-iq`
- Authority lineage: `packages/genesis`
- Execution lineage: `packages/nexus`, `packages/nexus-iq`
- Evidence lineage: `packages/context-kernel` (S0 independent re-audit is not cleared)
- Environment lineage: a historical directory under `packages/` (retired product name omitted; not integrated in Decision #2A)

An external coordination pin (Agent-Bridge) appears in `artifact/SOURCE_INDEX.md`. That repository is **not** vendored here. Orchestrator sessions/handoff are local Mongo updates.

## Orchestrator routes (untested)

Defined in `backend/server.py` and `backend/models.py`:

| Surface | Paths |
|---|---|
| VERA | `/api/dca/veras` |
| Placements | `/api/dca/placements/lease`, `/fence` |
| Memory | `/api/dca/memory`, `/recall/{vera_id}` |
| Authority | `/api/dca/authority/grants`, `/revoke` |
| Effects | `/api/dca/effects/propose`, `/dispatch` |
| Evidence | `/api/dca/evidence`, `/verify` |
| Sessions | `/api/dca/sessions/open`, `/close`, `/handoff` |
| Capsules | `/api/dca/effects/{id}/capsule` |
| Regency | `/api/regency/mandates`, `/roles`, `/assignments`, `/emergency-suspend` |

These require Mongo. There is no root Docker Compose and no `.env.example` for the orchestrator. They are omitted from the root README quickstart for that reason.

## Claims

Authoritative verified claims: [`evidence/CURRENT_CLAIMS_AND_MATURITY_LEDGER.md`](evidence/CURRENT_CLAIMS_AND_MATURITY_LEDGER.md) and [`../artifact/CLAIMS.md`](../artifact/CLAIMS.md).
