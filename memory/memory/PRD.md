# floks-pc — DCA Reference · PRD

## Original problem statement
Combine `Adaptive-Liquidity/Nexus` + `Adaptive-Liquidity/AEON-IQ` into `Adaptive-Liquidity/floks-pc` plus any other practically-done Adaptive-Liquidity repos that resonate with and enhance the overall project. Owner shipped 15 governing docs (DCA Foundation Lock v2, ADR Register v2, Regency Architecture RC-0.4, Website IA Lock v1, Portfolio Placement Lock v2, Open Decisions v2, Superpowers Context, Standards & Source Boundaries, DCA Architecture, Proof Cards, Product Page Update Pack, Company Update Pack, Website IA v2, README, SHA256SUMS).

## Architecture (locked)

- **Hierarchy:** Asentxia Systems → DCA → Continuum (floks-pc lineage) → VERA → The Regency
- **Vocabulary locks:** VERA (not `Operator`), Continuum (not FLOKS as active product), seven mandatory responsibilities (not six layers)
- **Isolation rule:** each package under `packages/` is untouched; orchestrator wires without editing internals

## Combined packages

| Package         | Origin                                    | Role        | Lang        |
|-----------------|-------------------------------------------|-------------|-------------|
| floks-pc        | Adaptive-Liquidity/floks-pc               | R2          | TS          |
| aeon-iq         | Adaptive-Liquidity/AEON-IQ-temp           | R3          | Rust        |
| nexus           | Adaptive-Liquidity/Nexus-temp             | R5          | Rust/WASM   |
| nexus-iq        | Adaptive-Liquidity/Nexus-IQ-temp          | R5+R6       | Docker      |
| genesis         | Adaptive-Liquidity/genesis-runtime        | R1+R4       | Rust        |
| context-kernel  | Adaptive-Liquidity/aeon-context-kernel    | R6          | Python 3.12 |

## Implemented in this session (2026-09-05)

- `/app/backend/` — FastAPI DCA orchestrator, 7 responsibility routers + cross-cutting Effect Boundary
- `/app/frontend/` — React ops dashboard (dark institutional aesthetic), 9 routes, data-testid on all interactive elements
- `/app/packages/` — six upstream repos merged in place, .git stripped, unmodified internals
- `/app/docs/DCA_RESPONSIBILITY_MAP.md` — canonical 7-responsibility → package/route/enforcement map
- `/app/README.md` — hierarchy, isolation rule, running instructions, evidence-first stance
- Hash-chained evidence ledger (SHA256 self-hash of prev_hash‖kind‖subject_id‖canonical(payload)) with `/verify` endpoint
- Seed endpoint stages a complete R1→R7 flow so the dashboard demonstrates end-to-end wiring immediately
- Effect Boundary verified: allow path (with active grant) → COMMITTED + evidence; deny path (no grant) → DENIED + evidence; chain re-verifies through both

## Verification performed

- Backend `/api/dca/seed` → 7 evidence entries, chain verified
- Denial path (VERA-B, no grant) → DENIED with reason `no_active_grant`, chain still verifies (12 entries)
- Frontend UI renders sidebar + all pages; evidence table shows real linked hashes from GENESIS forward

## Backlog / Open

- Real AEON-IQ provider embeddings/HNSW retrieval when the configured gateway exposes an embedding model
- Dynamic claim-ledger data at `/horizons` and `/evidence`
- floks-pc Runloop devbox proxy for actual computer provisioning
- Contract 1–7 ratification (per `06_Open_Decisions.md`) remains upstream owner work

## Session 2 additions (2026-09-05)

**All 4 phased enhancements implemented**:

1. **Real Nexus Dispatch** — `backend/adapters/nexus.py` uses `wasmtime` python binding. Ed25519 capability tokens minted from grants; WASM executes with WASI preview1 (no fs/net); capability trace + stdout captured. Bundled `hello.wasm` demo.
2. **AEON-IQ Semantic Retrieval** — `backend/adapters/aeon_iq.py`. Two-backend embedder (OpenAI text-embedding-3-small when available; local 256-d char-3gram feature hashing fallback). Cosine similarity ranking. `?mode=auto|semantic|substring`.
3. **Regency Console** — `/api/regency` router + `/regency` UI page. Mandates + Roles + Assignments + Emergency-suspend cascading action. Role assignment materializes attenuated AuthorityGrants per capability.
4. **Proof Capsule Export** — Ed25519-signed capsules per `nexus-iq/PROOF_CAPSULES.md` spec. `POST /effects/{id}/capsule` and `GET /capsules/{id}` (download). Signing key persisted at `backend/.orchestrator_key.pem`.

**Verified end-to-end**:
- WASM adapter: `hello.wasm` executes under wasmtime, stdout captured, capability trace logged
- Semantic recall: correctly ranks "sandbox execution" → Nexus fact (0.31 similarity)
- Regency: role assignment produces N grants; emergency-suspend cascades and emits evidence
- Capsule download from UI: 18-field signed JSON with evidence subchain root

**Files added**:
- `backend/capsule.py` — Ed25519 signing + capsule builder
- `backend/adapters/nexus.py` — wasmtime dispatch + capability tokens
- `backend/adapters/aeon_iq.py` — dual-backend embeddings + cosine
- `backend/wasm/hello.wasm` — bundled demo module (179 bytes)
- `docs/PHASE2_ADDITIONS.md` — implementation notes

**Backlog remaining**:
- Wire real aeon-iq HTTP contract (`/agents/{id}/memories`) via reverse-proxy when the Rust binary is running
- Mandate lifecycle transitions (SUSPENDED, DISSOLVED)
- Role withdrawal cascading (revoke materialized grants when assignment withdrawn)

## Session 3 continuation (2026-09-06)

- Verified the live `nexus-agentd` wire: daemon reachable at the configured Unix socket, authenticated, and reported version `1.0.0`.
- Corrected the AEON-IQ adapter to use the configured Emergent gateway URL and key together before selecting its deterministic fallback.
- Gateway probe confirmed `text-embedding-3-small` is not currently available; **MOCKED** local 256-d character-trigram embeddings remain active without interrupting memory recall.
- Added provider/fallback status metadata so the Memory console reports why local retrieval is in use.
- Manually verified the DCA status API, evidence chain (37 valid entries), Nexus status endpoint, Python compilation, and optimized React build.

## Prioritized roadmap

### P0 — Completed validation
- Live pure-compute WASM effect validated through the dashboard and exported as an Ed25519-signed Proof Capsule.

### P1 — Retrieval quality
- Switch AEON-IQ to a real gateway-supported embedding model and re-embed existing memory documents in a separate provider-vector field.
- Wire the upstream AEON-IQ memory HTTP contract when its Rust service is available.

### P2 — Data and governance depth
- Replace assumed/seeded Horizons and evidence views with dynamic claim-ledger data.
- Add mandate lifecycle transitions and cascading role-withdrawal revocation.
- Expand Nexus WASM capabilities only for concrete, authorized module requirements.

## Session 4 — Live Nexus dashboard validation (2026-09-06)

- Diagnosed a cross-engine module-cache fault in multi-hypervisor daemon operation; configured the preview `nexus-agentd` with one hypervisor so each cached module stays paired with its execution engine.
- Corrected the R5 effect boundary to commit only `status=committed`; any adapter execution fault now persists as `UNKNOWN`, is inspectable, and appends `effect.unknown` evidence.
- Corrected the earlier false-committed test record using an additional append-only evidence entry, preserving audit history.
- Updated the Effects console default to the pure-compute `use_nexus_demo` module and labelled its live-daemon path.
- Dashboard validation passed: a new effect ran with `adapter=nexus.live`, `status=committed`, `success=true`; its capsule download succeeded and its Ed25519 signature, live result, and evidence subchain were independently verified.
- Full evidence chain verifies with 42 entries. Backend compilation and optimized React build both pass.
