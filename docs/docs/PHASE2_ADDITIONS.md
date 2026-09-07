# Phase 2 additions — 4 capabilities

## 1. Real Nexus Dispatch (wasmtime)

**File:** `backend/adapters/nexus.py` · **Payload:** `/api/dca/effects/propose`

- Ed25519-signed capability tokens minted from active grants (`mint_capability_token`)
- `wasmtime` python binding compiles + executes WASM under WASI preview1
- Snapshot-per-call: fresh `Store` per dispatch (no shared state)
- Filesystem/network: not exposed (no pre-opened dirs)
- Bundled demo module at `backend/wasm/hello.wasm` (WAT-compiled, calls `fd_write` to stdout)
- Capability trace attached to `effect.result.capability_trace`
- Fallback to `nexus.echo` when payload has no wasm

**Payload shapes:**
```json
{"use_demo": true}                            // uses bundled hello.wasm
{"wasm_b64": "AGFzbQEA...", "entry": "_start"}
{"wasm_path": "/absolute/path.wasm"}
```

**Result shape:** `{adapter, status, exit_code, stdout, module_digest, capability_trace[]}`

## 2. AEON-IQ Semantic Retrieval

**File:** `backend/adapters/aeon_iq.py`

Two-backend embedder matching aeon-iq's HNSW retrieval contract:

1. `openai` backend — `text-embedding-3-small` (1536-d) when `OPENAI_API_KEY` reaches an OpenAI endpoint with embedding support
2. `local` backend — deterministic 256-d char-3gram feature hashing (no external dep, real cosine similarity)

**Endpoints:**
- `GET /api/dca/memory/status` — backend + availability
- `GET /api/dca/memory/recall/{vera_id}?q=...&mode=auto|semantic|substring&limit=20`

Vectors stored per `MemoryFact.embedding`; recall computes cosine similarity in numpy and returns top-K with `similarity` on `source._similarity`.

## 3. Regency Console (governance, bound to R4)

**Router:** `/api/regency/*` · **Frontend:** `/regency`

- `Mandate` — governing instrument with envelope ceiling
- `Role` — named capability bundle, optionally under a mandate
- `RoleAssignment` — binds VERA↔role, materializes attenuated `AuthorityGrant`s per capability
- `POST /emergency-suspend` — cascading suspend: VERA→SUSPENDED, grants→SUSPENDED, placements→FENCED (epoch bumped), all with evidence entries

**Locked behavior per Foundation §6:** Regency Console cannot promise instantaneous global stop. Emergency-suspension is a request; reachable enforcement points act. Response includes a boundary note reminding operators.

## 4. Proof Capsule Export

**File:** `backend/capsule.py` · matches `packages/nexus-iq/PROOF_CAPSULES.md` fields

Contract fields present:
- `capsule_id`, `capsule_version`, `profile_digest`
- `module`, `action_id`, `vera_id`, `session_id`, `timestamp`, `duration_ms`
- `result` (from nexus dispatch)
- `capability_records[]` (grant provenance)
- `memory_evidence[]` (session-bound memories with content_hash)
- `evidence_subchain` (root, first_seq, last_seq, entries[]) — SHA256 over concatenated self_hashes
- `limitations[]`, `redaction_manifest`
- `signature_type: ed25519`, `signature` (hex), `signer_pubkey` (hex)
- `failure` block for DENIED / UNKNOWN outcomes

**Endpoints:**
- `POST /api/dca/effects/{id}/capsule` — build capsule (JSON body)
- `GET /api/dca/capsules/{id}` — same, with `Content-Disposition: attachment`
- `GET /api/dca/orchestrator/pubkey` — Ed25519 public key clients use to verify

Signing key is generated at first startup and persisted to `backend/.orchestrator_key.pem` (mode 0600).

## Verification

- WASM adapter executes `hello.wasm` in wasmtime → stdout `"hello from nexus adapter"` captured; capability_trace records verify_token → compile → wasi_init → instantiate → call
- Semantic recall ranks correctly: `"sandbox execution"` → Nexus (0.31), Effect Boundary (0.18), Continuum (0.14)
- Regency role assignment materializes N grants (verified via `/api/dca/authority/grants?vera_id=...`)
- Emergency suspend cascades: 1 vera → 3 grants suspended → 0 placements fenced (test case had no active placements)
- Proof Capsule signature verifies against `orchestrator/pubkey` (Ed25519)
