# Continuum capabilities — in progress and not yet proven

The root [README](../README.md) lists Decision #2A capabilities that are **working and tested**. This page inventories everything else in the tree.

**Working and tested** means Continuum tests in this repository exercise the claim. Vendored package tests are not Continuum integration proofs.

## Working but untested

| Capability | Code | Notes |
|---|---|---|
| Orchestrator VERA / grant / effect / evidence APIs | [`backend/server.py`](../backend/server.py), [`backend/models.py`](../backend/models.py) | No `backend/` tests. Requires Mongo (`MONGO_URL`, `DB_NAME`). |
| Orchestrator hash-chained evidence + capsules | [`backend/evidence.py`](../backend/evidence.py), [`backend/capsule.py`](../backend/capsule.py) | None |
| Orchestrator memory adapter | [`backend/adapters/aeon_iq.py`](../backend/adapters/aeon_iq.py) | Not AEON-IQ Postgres |
| Orchestrator execution adapter | [`backend/adapters/nexus.py`](../backend/adapters/nexus.py) | wasmtime optional; echo fallback |
| Sessions / handoff | `/api/dca/sessions/*` | Mongo state updates. Not multi-agent coordination. |
| The Regency (mandates, roles, emergency suspend) | `/api/regency/*`, [`frontend/src/App.js`](../frontend/src/App.js) | None |
| Ops dashboard | [`frontend/`](../frontend/) | No `*.test.*` files |

## Scaffold or stub

| Capability | Code | Notes |
|---|---|---|
| Vite landing shell | [`src/App.jsx`](../src/App.jsx) | Visual mock; figures on that page are not measurements |
| Placement as a real remote computer | Orchestrator writes synthetic `computer_id`s | Vendored environment tree is not called |

## Design goal

| Capability | Notes |
|---|---|
| Coordination / multi-VERA | Session documents only. Decision #2A is out of scope. |
| Crash recovery, host migration | Explicitly unproven (`excluded_scope`). AC-8 fails if marked proven. |
| Model / provider replacement | Process restart only. |
| Production readiness | Not claimed. |

Vendored trees under [`packages/`](../packages/) (AEON-IQ, Genesis, NEXUS, Context Kernel, and an environment lineage directory) keep their own tests. They are not integrated into Decision #2A. See [artifact/CLAIMS.md](../artifact/CLAIMS.md).

Limits for the verified slice: [README — Limits and non-goals](../README.md#limits-and-non-goals).
