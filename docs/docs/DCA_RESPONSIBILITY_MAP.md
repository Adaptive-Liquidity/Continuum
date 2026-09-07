# DCA Responsibility Map — floks-pc integrated reference

Each row below identifies (a) the responsibility, (b) which upstream package
carries its primary lineage, (c) the orchestrator surface, and (d) the concrete
enforcement point exercised by the demo flow.

## Responsibility 1 — Principal Identity & Responsibility

- **Package:** `packages/genesis` (signed identity, delegation chains)
- **Orchestrator:** `POST /api/dca/veras`, lifecycle transitions
- **Enforcement:** VERA `state ∈ {ACTIVE, SUSPENDED, DECOMMISSIONED}`. Suspension
  cascades → all ACTIVE grants become SUSPENDED. Decommissioning cascades →
  grants REVOKED, placements TERMINATED. Identifier is never reassigned.

## Responsibility 2 — Environment & Runtime Continuity

- **Package:** `packages/floks-pc` (Runloop devbox v1 Agent Computer cloud)
- **Orchestrator:** `POST /api/dca/placements/lease`, `/fence`
- **Enforcement:** Placement `state ∈ {ACTIVE, FENCED, TERMINATED}` + monotonic
  `lease_epoch`. Fencing increments epoch; downstream Effect Boundary checks
  placement state before dispatch. Lease alone never grants effect authority
  (locked in `03_Asentxia_Regency_Product_Architecture_Baseline_RC-0.4.md#5`).

## Responsibility 3 — Durable State & Memory

- **Package:** `packages/aeon-iq` (MemoryOS transparent OpenAI proxy)
- **Orchestrator:** `POST /api/dca/memory`, `GET /api/dca/memory/recall/{vera_id}`
- **Enforcement:** Facts bound to `vera_id` + optional `session_id`. Kind ∈
  `{semantic, episodic, operational, derived}` per foundation §3. Source
  provenance stored per aeon-iq's provenance rules. Recall in the orchestrator
  is substring; production would delegate to aeon-iq's HNSW-backed retrieval.

## Responsibility 4 — Authority & Capability Governance

- **Package:** `packages/genesis` (attenuation chains, revocation)
- **Orchestrator:** `POST /api/dca/authority/grants`, `/revoke`
- **Enforcement:** Grant `state ∈ {ACTIVE, SUSPENDED, EXPIRED, REVOKED}`.
  Attenuation invariant — child grant's `capability` must equal parent's;
  parent must be ACTIVE. Revocation cascades to children. Envelope-Bounded
  Transition Safety (ADR-S14): authority stays within mission ceiling.

## Responsibility 5 — Effectful Execution

- **Package:** `packages/nexus` (WASM/WASI capability-gated sandbox) +
  `packages/nexus-iq` (self-host + Proof Capsules)
- **Orchestrator:** `POST /api/dca/effects/propose`, `POST /api/dca/effects/{id}/dispatch`
- **Enforcement:** `action_id` provides exactly-once semantics (duplicate proposal
  returns existing effect). Outcomes ∈ `{PREPARED, DISPATCHED, COMMITTED, DENIED,
  UNKNOWN, COMPENSATED}`. `UNKNOWN` is never blind-retried (foundation §4). The
  current adapter is `nexus.mock`; a production wire would issue a scoped Nexus
  capability token and invoke the Rust hypervisor.

## Responsibility 6 — Evidence, Verification & Recovery

- **Package:** `packages/context-kernel` (hash-chained JSONL trace,
  verifier-issued provenance, deterministic replay)
- **Orchestrator:** `GET /api/dca/evidence`, `GET /api/dca/evidence/verify`
- **Enforcement:** Every state transition across R1-R7 emits an entry with
  `seq`, `prev_hash`, `self_hash = SHA256(prev_hash || kind || subject_id ||
  canonical(payload))`. `/verify` re-derives every hash from GENESIS forward
  and reports `broken_at` if the chain is tampered.

## Responsibility 7 — Coordination & Interconnect

- **Package:** orchestrator sessions + `packages/floks-pc` mcp gateway lineage
- **Orchestrator:** `POST /api/dca/sessions/open`, `/close`, `/handoff`
- **Enforcement:** A session binds VERA↔placement; handoff transfers control
  to another ACTIVE VERA but preserves participant separation — no identity,
  private state, authority, or trust domain merges.

## Effect Boundary — cross-cutting (not R8)

The gate implemented inside `POST /effects/{id}/dispatch`:

```
1. Load effect → must be PREPARED or UNKNOWN
2. If session_id is bound → resolve placement → must be ACTIVE (not FENCED/TERMINATED)
3. Resolve authority → active grant covering capability_required and not expired
4. If gate passes → adapter dispatch (nexus.mock stub; real wire: nexus)
5. Append evidence.committed OR evidence.denied
6. Persist outcome atomically
```

Cognition proposes; authority decides; runtime contains; state persists; evidence records.
