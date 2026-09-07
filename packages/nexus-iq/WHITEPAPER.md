# Nexus-IQ: A Verifiable Execution and Persistent-Memory Substrate for Autonomous AI Agents

**Adaptive Liquidity Research**
`contact@adaptiveliquidity.com`

Version 1.0 — July 2026
Status: Technical white paper (living document; audited baseline Nexus `85780b8a` / AEON-IQ `852f7cb` / kit `09c500a`; §8.3/§9/§10 refreshed against the v1.0-rc branch — Nexus `3b7e7ec`, AEON-IQ `76f09b4`)

---

## Abstract

Autonomous AI agents increasingly write and execute code, accumulate long-lived state, and act on behalf of users — yet the substrate they run on offers neither *recoverability* when they fail nor *evidence* of what they actually did. We present **Nexus-IQ**, a self-hostable substrate that composes two systems: **Nexus**, a WebAssembly sandbox hypervisor providing microsecond-scale isolation, fuel-metered execution, native snapshot/rollback of guest state, and cryptographically signed **Proof Capsules**; and **AEON-IQ**, a persistent memory plane that gives any OpenAI-compatible agent tiered episodic/semantic memory with decay-weighted vector retrieval, closed-loop memory-pressure control, and a per-agent learned retrieval policy. The two are bound by an integrity layer — **MemoryEvidence** — that ties every memory injection to the execution it influenced via canonical, HMAC-scoped, Ed25519-signed attestations, without ever exposing raw memory content.

We give a formal account of the system's core mechanisms: the capability attenuation lattice and its monotonic-narrowing guarantee; the rollback-necessity classification of a 19-variant typed failure taxonomy; content-addressed snapshot digests with byte-reproducible canonical encoding; the three-factor decay retrieval score and its ranking properties; the bounded PI controller that regulates memory pressure; and the unforgeability and determinism arguments for Proof Capsules and MemoryEvidence. We prove thirteen propositions about these mechanisms, report a reproducible evaluation — including a new ranked-retrieval benchmark (360 queries over a 1,120-memory corpus with MRR@10 and nDCG@10) and re-measured latency at 10,000-memory scale — and state, explicitly, what the system does *not* yet establish. We close with a roadmap toward counter-signed attestation, sensitivity-enforced retrieval, semantic-embedding benchmarks, and independent audit.

**Keywords:** AI agents, WebAssembly, sandboxing, snapshot/rollback, agent memory, vector retrieval, attestation, capability systems, verifiable computing

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Related Work](#2-related-work)
3. [System Overview](#3-system-overview)
4. [The Nexus Execution Substrate](#4-the-nexus-execution-substrate)
5. [The AEON-IQ Memory Plane](#5-the-aeon-iq-memory-plane)
6. [The Integrity Layer: Proof Capsules and MemoryEvidence](#6-the-integrity-layer-proof-capsules-and-memoryevidence)
7. [Security Model and Threat Analysis](#7-security-model-and-threat-analysis)
8. [Evaluation](#8-evaluation)
9. [Limitations and Honest Claims](#9-limitations-and-honest-claims)
10. [Roadmap](#10-roadmap)
11. [Conclusion](#11-conclusion)
12. [References](#references)
- [Appendix A: Notation](#appendix-a-notation)
- [Appendix B: Configuration Defaults](#appendix-b-configuration-defaults)
- [Appendix C: Reproduction](#appendix-c-reproduction)

---

## 1. Introduction

### 1.1 The problem

Large-language-model agents fail in ways traditional infrastructure was not designed to absorb. Three failure classes dominate operational experience:

1. **Runaway execution.** Agent-generated code loops forever or exhausts resources. Containers and microVMs bound *wall-clock time and memory*, but cannot bound *instructions* deterministically, and killing a container discards all intermediate state.
2. **State corruption.** A partially executed tool call leaves the workspace in an inconsistent state. The agent, lacking a checkpoint, either compounds the corruption or starts over, losing the work and the tokens spent producing it.
3. **Amnesia and unaccountability.** Agent memory today is either a context window (ephemeral, expensive) or an ad-hoc RAG pipeline (unversioned, unaudited). When an agent acts on remembered information, there is generally *no record* of which memories influenced which action — a gap that grows more serious as agents take consequential actions and as governance frameworks (NIST AI RMF [15], OWASP LLM Top 10 [16]) demand traceability.

These failures share a root cause: the execution substrate treats an agent step as an opaque process, not as a **transaction with evidence**.

### 1.2 Our approach

Nexus-IQ reframes each agent tool execution as an atomic, attested transaction:

```
snapshot → execute (fuel-metered, capability-gated WASM) → validate health
        → commit  ⊕  rollback to the exact pre-error state
        → emit a signed Proof Capsule
        → link retrieved memories to the run via MemoryEvidence
        → append to a queryable agent timeline
```

Concretely, the substrate is the composition of two independently useful systems and a bridge that binds them:

- **Nexus** (§4) — a WASM sandbox hypervisor built on Wasmtime. It contributes deterministic instruction metering ("fuel"), a wall-clock epoch watchdog, capability tokens with a formal attenuation lattice, full and differential snapshots with content-addressed digests, a typed 19-variant failure taxonomy with mechanically derived recovery decisions, and learned recovery suggestions with Laplace-smoothed confidence.
- **AEON-IQ** (§5) — a persistent memory plane exposed as a transparent OpenAI-compatible proxy. It contributes three-tier memory (working / episodic / archival), decay- and importance-weighted pgvector retrieval, provenance-capped confidence, reversible narrative archival, complete version history with time-travel queries, a retrieval audit log, and two closed-loop controllers: Adaptive Memory Pressure (AMP) and the Reflexive Memory Kernel (RMK).
- **The bridge** (§6) — a deliberately minimal crate (`aeon_nexus_bridge`) owning stable wire types and crypto helpers. Every execution's Proof Capsule can carry a `MemoryEvidenceRef`: a canonical SHA-256 digest over the exact set of injected memories (content digests and fixed-point scores only — never raw text), scoped to an HMAC-derived agent handle so evidence cannot be forged across tenants.

### 1.3 Contributions

1. **A transactional execution model for agents** in which snapshot, execution, health validation, and rollback are a single atomic unit, and in which the decision *whether* rollback is required is derived mechanically from a typed failure taxonomy (Proposition 2).
2. **A formal capability model** with a subset lattice over file, network, and memory scopes; Ed25519-signed delegation chains that provably only narrow (Proposition 1(a)–(d)); and a bounded, assertion-guarded capability-denial negotiation protocol.
3. **A memory plane with controllable dynamics**: a three-factor retrieval score whose ranking properties we characterize (Proposition 5), a bounded co-access re-ranking term (Proposition 6), a PI-controlled soft-eviction loop with proven state bounds and hysteresis (Proposition 7), and a per-agent learned policy vector with clamped exploration (Proposition 10).
4. **An attestation format for memory-influenced execution** — Proof Capsules + MemoryEvidence — with determinism, unforgeability, and cross-tenant-binding arguments (Propositions 11–13), and with *mandatory machine-readable limitations* baked into every artifact.
5. **A reproducible evaluation** that upgrades the project's prior benchmark methodology: ranked-retrieval metrics (MRR@10, nDCG@10, per-query-type breakdowns) over a 1,120-memory corpus with 360 queries; proxy and retrieval latency re-measured at 100/1,000/10,000-memory scale with 200-request samples; and end-to-end correctness proofs for temporal versioning and narrative archival — together with an explicit threats-to-validity analysis (§8.7).

### 1.4 Design philosophy: evidence over claims

A recurring pattern in this system — unusual enough to name — is **structural honesty**. Every Proof Capsule *must* carry a non-empty `limitations` array (§6.5) declaring what it does not prove. The benchmark suite maintains a "Claims Not Supported" table and downgrades its own proof status when artifacts are missing. Marketing numbers that measured the wrong thing ("23 µs cold start") were formally *retired* in the repository rather than silently replaced. This paper follows the same discipline: §9 enumerates every known gap between documentation and implementation, and §8.7 lists the ways our own evaluation could mislead.

---

## 2. Related Work

**Sandboxing and isolation.** Containers (Docker) and microVMs (Firecracker [1], ~125 ms boot) isolate at the OS/hypervisor boundary; gVisor [2] interposes a user-space kernel. E2B [3] provisions cloud sandboxes for agents (~150 ms). Wassette (WAMR-based) and Pyodide target WASM/browser isolation. None of these provide *instruction-deterministic* metering, native sub-millisecond state rollback, or execution attestation; Nexus trades their generality (arbitrary Linux binaries, GPUs) for those properties inside a WASM/WASI boundary (§4.1). Firecracker snapshots (~1.5 s create / ~4 ms restore) operate at VM granularity; Nexus snapshots are guest-linear-memory granular (76 µs restore at 1 MiB; §8.2).

**Agent memory systems.** MemGPT [4] introduced OS-inspired paged memory for LLMs; mem0 [5], Zep [6], and LangChain/LangGraph memory offer managed memory layers; Letta, Cognee, and Memobase explore variations. AEON-IQ differs in four ways: (i) it is a *transparent wire-level proxy* — agents keep using the OpenAI SDK unchanged; (ii) memory dynamics are *controlled*, not just accumulated — a PI controller regulates active-set size and a learned per-agent policy adapts retrieval parameters; (iii) every memory carries provenance-capped confidence, versioned history, and status/sensitivity fields; (iv) retrieval is *audited* — every injection is logged with scores and can be attested into an execution proof. Published evaluations of memory systems (e.g., LoCoMo [7], LongMemEval [8]) target semantic recall with real embeddings; our evaluation (§8) deliberately measures the *mechanical* layer deterministically and defers semantic benchmarks to the roadmap (§10).

**Attestation and supply-chain integrity.** SLSA [9] and in-toto [10] attest software *build* provenance; Sigstore [11] provides signing infrastructure; TEE remote attestation (SGX/SEV/Nitro) proves *platform* identity. Proof Capsules attest a different object — a single *runtime execution* inside a userspace sandbox — and are explicitly *not* SLSA-compliant, not zero-knowledge, and bounded by trust in the Nexus process itself (§6.5). in-toto/Sigstore compatibility is a stated v2 direction.

**Capability systems.** Object-capability discipline (E, Capsicum [12], seL4 [13]) and macaroons [14] (HMAC-chained caveats) inspire the Nexus token model: Ed25519-signed tokens with bounded delegation depth, subset-only attenuation, and expiry clamping (§4.4). Unlike macaroons, chains are verified against a single issuing authority key and a persistent revocation set.

**Retrieval.** AEON-IQ's ANN layer is pgvector HNSW [17]; its decay-weighted scoring is related to time-aware ranking and to ACT-R's activation decay [18]; the co-access graph is an instance of associative spreading-activation applied to RAG re-ranking.

---

## 3. System Overview

### 3.1 Deployment topology

A Nexus-IQ installation is four services on one isolated Docker bridge network, with loopback-only host exposure:

```
 MCP client (Claude Desktop / Cursor / OpenHands)
     │  JSON-RPC 2.0 over stdio (per-session container)
     ▼
 nexus-mcp ───unix socket──▶ nexus-agentd ──HTTP + mgmt key──▶ aeon ──SQL──▶ postgres
 (thin MCP transport)        (hypervisor daemon)              (memory plane,   (pgvector,
                              cap_drop ALL, non-root,          REST :8080)     no host port)
                              pids≤512, fuel≤10⁹)                 │
                                                                  ▼ HTTPS (SSRF-guarded)
                                                            upstream LLM provider
```

| Service | Role | Host exposure |
|---|---|---|
| `postgres` | pgvector storage | none (internal) |
| `aeon` | AEON-IQ REST API + LLM proxy | `127.0.0.1:8080` |
| `nexus-agentd` | long-lived execution daemon | Unix socket only |
| `nexus-mcp` | stdio MCP server | none — launched per client session |

Key properties: there is **no HTTP execution gateway** — the only execution surface is MCP over stdio; the Nexus containers are hardened (`no-new-privileges`, non-root uid 10001, `cap_drop: ALL`, `pids_limit: 512`, memory limits, read-only module mount for the MCP surface); no Docker socket is mounted anywhere; and AEON-IQ's egress to the LLM provider passes an SSRF guard that requires HTTPS and blocks loopback/private/link-local/cloud-metadata destinations.

### 3.2 Composition mechanism

The integration is **compile-time**: Nexus is built with the `aeon-memory` cargo feature, which links the `aeon_nexus_bridge` crate and extends the Proof Capsule schema with `memory_evidence: Option<MemoryEvidenceRef>` and `memory_mode: Option<MemoryAttestationMode>`. The bridge crate depends on *neither* system's internals — it owns only stable wire types and crypto helpers, so either side can evolve independently against a frozen evidence contract (`aeon-nexus-memory-evidence-v1`).

Two shared secrets wire the boundary: the AEON management key (request authentication) and the `NEXUS_AEON_HMAC_KEY` (evidence provenance — §6.4). These serve different purposes and are deliberately separate; per-request HMAC signing is an explicitly documented non-feature (§7.3).

### 3.3 Life of a request

**Execution path.** An MCP client calls `nexus_execute_proof` with a WASM module reference. `nexus-mcp` forwards over the Unix socket to `nexus-agentd`, which: takes a pre-execution snapshot; optionally recalls memory from AEON-IQ (capability-gated by `MemoryRecall`, rate-limited per agent); executes the module in an isolated Wasmtime store under fuel and epoch limits with capability-mapped WASI preopens; validates post-execution health; commits or rolls back; builds, redacts, and signs a Proof Capsule embedding the MemoryEvidence reference; and posts a `proof_capsule_emitted` event to the AEON timeline (fail-open, best-effort).

**Memory path.** Any agent pointing its OpenAI-compatible SDK at AEON-IQ gets, per chat request: embedding of the last user message; two-CTE decay-weighted pgvector retrieval (plus optional graph-walk and co-access re-ranking); injection of results as a `<retrieved_memories>` system message; forwarding to the configured provider; and background extraction of new structured facts (provenance-tagged, batch-embedded, dedup-checked) plus retrieval-audit logging — all without any change to the calling code beyond a base URL and an `x-agent-id` header.

---

## 4. The Nexus Execution Substrate

### 4.1 Sandbox model

Each execution runs in a fresh Wasmtime store with three independent resource bounds:

- **Fuel** — deterministic instruction metering (`consume_fuel`), default budget 10⁷ instructions, adaptively tuned per tool (§4.6). Fuel exhaustion is a *typed, retryable* failure (`FuelExhausted`), making infinite loops a recoverable event rather than a hung process.
- **Epoch watchdog** — a wall-clock deadline via Wasmtime epoch interruption, covering time spent outside metered instructions (e.g., blocked host calls). Execution runs on a worker thread with a timeout-bounded receiver; on timeout the engine epoch is advanced to interrupt the guest cooperatively.
- **Linear memory cap** — default 512 pages (32 MiB) per guest.

Two execution paths exist with different guarantees. The **pure-compute** path (`execute_tool`) uses an empty linker: no host functions, fully deterministic, replayable. The **WASI** path (`execute_tool_wasi[_with_config]`) maps capability tokens to pre-opened directories (read-only for `ReadFile`, read-write for `WriteFile`); determinism is forfeited at the IO boundary. Isolation rests on WASM linear-memory confinement plus these bounds — it is *userspace* isolation, not a kernel or hardware VM boundary, and the threat model says so (§7).

### 4.2 Snapshot and rollback

**Full snapshots** capture guest linear memory (zstd level 3), exported mutable globals, and exported table sizes — explicitly *not* stack or registers. Each snapshot stores a SHA-256 checksum of the *uncompressed* memory and lives in a ring buffer (default capacity 100) with an index that is rebuilt on eviction. Restore decompresses, grows the target memory if needed, and copies; only mutable globals are restored.

**Differential snapshots** compare 4,096-byte pages against a base, compressing only dirty pages — cost proportional to *mutation*, not total memory. Diff chains fold oldest→newest at restore; a chain auto-promotes to a full snapshot when its generation exceeds `MAX_DIFF_DEPTH = 8`, bounding both restore latency and failure blast radius. Persisted snapshots are capped at 256 MiB against deserialization DoS.

**Content-addressed identity.** Every snapshot has a byte-reproducible digest (§6.1 uses the same canonicalization discipline):

```
digest = SHA-256( "NEXUS-SNAPSHOT-DIGEST-v1" ‖ u32(schema_version)
                  ‖ len_prefixed(SHA-256(raw_memory)) ‖ u64(original_size)
                  ‖ canonical_tail(globals, tables) )
```

The encoding is hand-specified (little-endian, length-prefixed, floats by raw IEEE-754 bits) and pinned by a hand-derived test vector. It deliberately **excludes** the compressed bytes and compressed size (identity must be invariant to the zstd level), the random snapshot UUID, and the timestamp. Verification is constant-time.

**Proposition 3 (Digest stability and binding).** *Let S₁, S₂ be snapshots. (i) If S₁ and S₂ have identical logical content (raw memory, size, globals, tables) they have equal digests, regardless of compression settings, UUIDs, or timestamps. (ii) If digests are equal but logical content differs, a SHA-256 collision has been produced.*

*Proof.* (i) The preimage is a deterministic function of exactly the logical content: the domain separator and schema version are constants; the memory enters only via its SHA-256 and original size; the tail encoding is a fixed injective serialization of globals and tables (every variable-length field is length-prefixed, every primitive fixed-width, enum variants tag-byte-discriminated, so distinct tails produce distinct byte strings). Excluded fields never enter the preimage. (ii) Injectivity of the encoding means differing logical content yields differing preimages; equal digests over differing preimages is a SHA-256 collision. ∎

**Proposition 4 (Sync safety).** *In the snapshot-sync protocol (Advertise/Want/Snapshot/Ack/Nack), an honest node's store never contains a snapshot whose content does not match its digest key, and re-delivery of a valid snapshot is idempotent.*

*Proof.* The store is keyed by the node's *own recomputation* of the digest, never a caller-supplied key. On receiving `Snapshot(d, S)`, the node computes `digest(S)`; on mismatch with `d` it replies `Nack(DigestMismatch)` and does not insert — so a tampered payload cannot enter under the advertised key, and by Proposition 3(ii) it cannot match under any other content's key without a hash collision. If `digest(S)` is already present, the node replies `Ack` without re-inserting (idempotency). ∎

### 4.3 Typed failure taxonomy and mechanical recovery decisions

`FailureMode` has 19 variants: `Timeout{limit,observed}`, `FuelExhausted{limit}`, twelve typed WASM traps (unreachable, div-by-zero, integer overflow, stack overflow, OOB memory, misaligned heap, table OOB, indirect-call-to-null, bad signature, null reference, cast failure, bad int conversion), `TrapOther`, `MemoryLimitExceeded`, `InvalidModule`, `MissingEntrypoint`, and `HostError`. Three decision functions are *derived mechanically* from the variant, and unit tests enforce their totality and distinctness:

- `is_deterministic()` — traps and load-time failures are non-retryable (they will recur); `Timeout`/`FuelExhausted` are retryable with a larger budget.
- `requires_rollback()` — see Proposition 2.
- health mapping — only `HostError` maps to `Corrupted` (the host boundary, not the guest, is the only place unmodelled corruption can arise); `FuelExhausted` maps to the category string `INFINITE_LOOP_PREVENTED`.

**Proposition 2 (Rollback-necessity classification).** *Define M₀ = {InvalidModule, MissingEntrypoint}. Rollback is required exactly for failures ∉ M₀, and this is sound: failures in M₀ cannot have mutated guest state.*

*Proof.* Failures in M₀ occur at module *load/link* time — validation of the binary or resolution of the entrypoint — strictly before the first guest instruction executes. Guest state (linear memory, globals, tables) is only mutable by guest instructions or host functions invoked by the guest; neither has run, so the pre-execution snapshot and current state are identical and rollback is a no-op. Every other variant is raised during or after execution of at least one instruction, at which point mutation cannot be excluded, so the transactional contract (state on failure = state before) requires restoring the snapshot. The implementation encodes exactly this predicate (`!matches!(self, InvalidModule | MissingEntrypoint)`), and the test suite pins it. ∎

Recovery advice is layered: a `StaticPolicy` that is *exhaustive over the taxonomy by construction* (adding a variant without advice is a compile error) beneath an optional learned `InstinctPolicy` (§4.6), combined with de-duplication in a `LayeredPolicy`. Actions carry confidence ∈ [0,1], a `non_retryable` flag aligned with `is_deterministic()`, and a source tag (`Static | Instinct | Llm`).

### 4.4 The capability model

**Structure.** Capabilities form a partially ordered set under `is_subset_of`, with lattice ends `None ⊑ c ⊑ All` for every capability c. File capabilities are ordered by *lexical* path containment (`.`/`..` normalized component-wise; symlinks deliberately not resolved — a documented trust boundary with an escape hatch: canonical-path `WasiToolConfig` mounts for untrusted trees). Write implies read on the same subtree; write–write requires exact path equality. HTTP and binary-execution capabilities compare by exact pattern. Memory capabilities are scoped by a sub-lattice: `Session{a,s} ⊑ Agent{a} ⊑ Namespace{n}` (name-equal), with `WriteMemory(σ)` dominating `ReadMemory(σ′)` iff σ′ ⊑ σ.

**Tokens.** A `CapabilityToken` binds `(id, capability, granted_by, issued_at, expires_at, parent_id, chain_depth)` under an Ed25519 signature by the issuing authority. Delegation (`attenuate`) creates a child token; chains are bounded at depth 5.

**Proposition 1 (Attenuation soundness).** *For any token chain t₀ (root) → t₁ → … → tₙ accepted by `validate_chain`:*
*(a) **Monotonic narrowing:** cap(tᵢ) ⊑ cap(tᵢ₋₁) for all i, hence cap(tₙ) ⊑ cap(t₀);*
*(b) **Bounded delegation:** n ≤ 5, and depth(tᵢ) = i exactly;*
*(c) **Lifetime containment:** expires(tᵢ) ≤ expires(tᵢ₋₁), so no descendant outlives any ancestor;*
*(d) **No forgery:** every tᵢ carries a valid authority signature over its full binding tuple, and revoked tokens invalidate every chain through them.*

*Proof.* (a) `attenuate` rejects any child whose capability is not `is_subset_of` the parent's, and `validate_chain` re-checks the subset relation on every adjacent pair at use time; transitivity of ⊑ (it is the `allows` preorder restricted to the constructors, with reflexivity by exact match and antisymmetric ends pinned by tests) gives the composition. (b) `attenuate` sets depth(child) = depth(parent)+1 and rejects when it would exceed the maximum; `validate_chain` independently verifies depth(tᵢ) = depth(tᵢ₋₁)+1 on every link, so a forged gap or re-rooting is rejected even if signatures were somehow valid. (c) `attenuate` computes expires(child) = min(now + validity, expires(parent)); induction gives containment along the chain, and `validate_chain` additionally rejects any expired ancestor at use time. (d) Signature verification over the bincode-serialized binding tuple is performed per link against the authority key (wrong-length signatures are rejected outright rather than zero-padded — a deliberate anti-exploit choice); revocation is checked per link against the persistent revoked set *before* lookup, so revoking any ancestor severs all descendants. Under EUF-CMA security of Ed25519, producing an accepted token not issued by the authority requires a signature forgery. ∎

**Authorization.** `authorize(tokens, required)` demands that *every* required capability be dominated by at least one valid, unexpired, non-revoked token; the first unsatisfied requirement denies. A valid Proof Capsule additionally records the semantic invariant `required ⊆ granted` (§6.1).

**Bounded denial negotiation.** When execution is denied for missing capabilities (with the memory feature enabled), Nexus may consult AEON-IQ memory for prior grants and *narrow* the request — never widen it. The negotiation is capped at 2 rounds, and two invariants are enforced by `assert!` kept in release builds: the negotiated set is drawn only from the originally required set (no escalation), and it strictly shrinks. Memory unavailability fails open to ordinary denial.

### 4.5 Speculative execution

`fork_and_race` races up to `max_branches = 4` alternative continuations, each within a timeout (default 5 s), under two strategies: `FirstSuccess` (first successful branch wins; dropping the future set cancels losers) and `WaitAll`. All branches fork from a *single shared base snapshot*, so forking cost is O(dirty pages), not O(total memory) — an invariant pinned by test. The winning branch, branch counts, and the shared base snapshot id are recorded in the Proof Capsule's `BranchRaceEvidence`. (Current implementation races on one sandbox; true multi-sandbox parallelism is roadmap.)

### 4.6 Learned components with bounded influence

Two learning mechanisms improve behavior over time; both are *advisory* and structurally prevented from expanding authority.

**Adaptive fuel budgeting.** Per tool, a ring of the last ≤100 fuel samples yields nearest-rank percentiles; once ≥5 samples exist,

```
budget(tool) = max(100_000, p95(tool) × 1.5)
```

with anomaly flagging at fuel > 3·p95. This keeps budgets tight enough to catch loops quickly but headroomed against normal variance; unknown tools fall back to the global cap.

**Instinct memory (Laplace-smoothed recovery confidence).** Learned recovery suggestions carry

```
confidence = (support + 1) / (support + failure + 2)
```

**Proposition 9 (Instinct confidence properties).** *(i) confidence ∈ (0,1) always; a new instinct starts at 1/2. (ii) confidence equals the posterior mean of a Beta(1,1) (uniform) prior over the success probability after `support` successes and `failure` failures. (iii) If outcomes are i.i.d. Bernoulli(p), confidence → p almost surely.*

*Proof.* (i) Numerator and denominator are positive and numerator < denominator. (ii) The Beta(1,1) posterior after s successes, f failures is Beta(1+s, 1+f), whose mean is (s+1)/(s+f+2). (iii) Write confidence = (s/n + 1/n)/(1 + 2/n) with n = s+f; by SLLN s/n → p a.s., and the perturbation terms vanish. ∎

Telemetry pattern-learning uses *saturating decrement* on failure (a single bad run erodes rather than wipes history), and instinct suggestions enter recovery only through the layered policy — they can propose, never authorize.

---

## 5. The AEON-IQ Memory Plane

### 5.1 Tiered memory model

| Tier | Backing | Content | Dynamics |
|---|---|---|---|
| **L1** | `working_memory` (per session) | rolling summary + structured state JSONB (`active_entities`, `current_goal`, `open_questions`) | rewritten every turn |
| **L2** | `memories` (tier='L2') | individual extracted facts with provenance, confidence, importance | default tier; dedup on insert; decay-eligible |
| **L3** | `memories` (tier='L3') | LLM-compressed archival facts + a *narrative* memory per batch | confidence ≤ 0.7; produced by the archival job |

Extraction is a background LLM pass over each turn: facts are provenance-tagged and confidence-capped (`user_stated` ≤ 0.95, `assistant_derived` ≤ 0.70, `inferred` ≤ 0.50 — an epistemic-humility encoding of hallucination risk), require a `cited_line`, are batch-embedded in a single call, and are linked to entities extracted in the same turn (a knowledge graph of subject–predicate–object triples with Levenshtein-≤2 entity disambiguation).

**Reversible archival.** A scheduled job compacts stale, zero-access L2 facts into 3–5 L3 facts *plus a 2–3-sentence narrative memory*, tombstoning (never deleting) the sources. Every compaction is an **archival batch**: batch-level restore un-tombstones the L2 sources and re-tombstones the L3 replacements, with an idempotency guard. Memories with importance ≥ 0.9 are never auto-archived. Every mutation — insert, patch, status change, archival — writes a complete snapshot to `memory_versions`, enabling **time-travel** (`GET /memories/at?timestamp=…`) and **temporal diff** (`added/modified/archived/status_changed` between any two instants). Every retrieval writes an audit row (query hash, candidate/injected/suppressed id arrays, per-memory scores, latency).

### 5.2 Retrieval scoring

The core retrieval is a two-CTE pgvector query. With cosine distance d(q,m) ∈ [0,2], staleness τ(m) in days since last access (creation if never accessed), and importance ι(m) ∈ [0,1]:

```
score(q,m) = d(q,m) · exp(λ·τ(m)) · (1 + β·(1 − ι(m)))            (1)
```

where λ = `MEMORY_DECAY_RATE` ≥ 0 and β = `IMPORTANCE_BOOST_FACTOR` ≥ 0. Results with score(q,m) < θ (the retrieval threshold) are returned in ascending order. The SQL additionally filters `archived_at IS NULL AND soft_evicted = FALSE AND status = 'active'`, and — on the LLM-injection path only — excludes `sensitivity ∈ {private, secret}` at the query level.

**Proposition 5 (Ranking properties of (1)).**
*(i) **Neutral collapse:** if λ = β = 0 (the defaults), score = d — pure cosine ranking.*
*(ii) **Staleness monotonicity:** score is strictly increasing in τ for λ > 0, d > 0; the staleness penalty is smooth and multiplicative, so it can only demote, never promote.*
*(iii) **Importance monotonicity:** score is strictly decreasing in ι for β > 0, d > 0 — more important memories rank earlier, ceteris paribus.*
*(iv) **Order preservation within cohorts:** among memories with equal τ and ι, the ranking is exactly the cosine ranking (the modifier is a common positive factor).*
*(v) **Threshold semantics:** θ upper-bounds the modified score, so a stale or unimportant memory needs proportionally higher raw similarity to be admitted at all.*

*Proof.* All parts are direct: (i) exp(0)=1 and (1+0)=1. (ii) ∂score/∂τ = λ·score > 0. (iii) ∂score/∂ι = −β·d·exp(λτ) < 0. (iv) the factor exp(λτ)(1+β(1−ι)) is constant on the cohort and positive, preserving order. (v) score < θ ⇔ d < θ / [exp(λτ)(1+β(1−ι))], a threshold shrinking in τ and (1−ι). ∎

The exponential form (migration 0019+) replaced an earlier linear `(1 + λτ)` penalty: both are monotone, but the exponential composes multiplicatively over time (score after τ₁+τ₂ = score·e^{λτ₁}·e^{λτ₂}) and dominates every polynomial, giving a well-defined "forgetting horizon" under any fixed θ. *(Note: the repository README still shows the retired linear form; the code and this paper are authoritative — see §9.)*

**Refresh-on-read.** Every retrieval bumps `access_count`, sets `last_accessed_at = NOW()` (resetting τ to 0), and increments importance by `IMPORTANCE_REFRESH_BOOST = 0.05` capped at 1.0 — a spacing-effect reinforcement: memories that keep being useful become both fresher and more important, compounding through (1).

### 5.3 Importance and provenance

Importance is assigned at extraction from three signals in strict priority: caller override via `x-memory-importance` header (`user_stated`), agent-marked `<important>` spans (floored at 0.9), else an LLM rubric (1.0 critical/permanent; 0.8–0.99 key business facts; 0.5–0.79 standard; <0.5 filler). Importance ≥ 0.9 additionally confers **archival immunity**. Provenance caps confidence as in §5.1 — the system structurally refuses to be *certain* of anything the user did not say.

### 5.4 Adaptive Memory Pressure (AMP)

AMP closes the loop between memory accumulation and retrieval quality. Each memory gets a **pressure**

```
p(m) = min( a·τ(m) + b·(1 − u(m)), 1 )                            (2)
```

with staleness τ as above, utility EMA u(m) ∈ [0,1] (§ below), and defaults a = 0.02/day, b = 0.4. Memories with pressure above a threshold are **soft-evicted** (hidden from retrieval, trivially restorable — nothing is deleted); memories below a lower threshold are restored.

**Utility EMA.** After every retrieval, each injected memory receives feedback 1.0 into

```
u ← α·feedback + (1−α)·u,   α = 0.2                                (3)
```

**Proposition 8 (EMA bounds and forgetting rate).** *(i) If all feedback ∈ [0,1] then u ∈ [0,1] invariantly. (ii) The weight of a feedback event t updates ago is α(1−α)ᵗ — geometric forgetting with half-life ln 2 / ln(1/(1−α)) ≈ 3.1 updates at α = 0.2. (iii) Under constant feedback c, u → c geometrically at rate (1−α).*

*Proof.* (i) u′ is a convex combination of u and feedback. (ii)(iii) Unrolling (3): uₜ = α·Σᵢ (1−α)ⁱ·fₜ₋ᵢ + (1−α)ᵗ·u₀; with fᵢ ≡ c the sum telescopes to c(1−(1−α)ᵗ). ∎

**The PI controller.** A per-sweep controller drives the soft-eviction threshold toward a target active-set size N* (default 1,000). With e = (N − N*)/max(N*,1):

```
I ← clamp(I + e·dt, −10, 10)        (only if |e| ≥ deadband, with anti-windup)
Δ = clamp(k_p·e + k_i·I, −0.1, +0.1)
A ← clamp(A + Δ, 0, 1)
θ_high = 1 − A;   θ_low = max(θ_high − 0.05, 0)
```

defaults k_p = 0.15, k_i = 0.02, deadband = 0.02, hysteresis gap 0.05, max change per cycle 0.1. Eviction requires *both* p(m) > θ_high *and* age ≥ 24 h (a newborn-protection floor); restore triggers at p(m) < θ_low.

**Proposition 7 (Controller state bounds and hysteresis).** *(i) A ∈ [0,1], I ∈ [−10,10], and |Δθ_high| ≤ 0.1 per cycle, invariantly — the controller can never demand an unbounded or discontinuous policy change. (ii) The deadband makes the target an equilibrium band: for |e| < 0.02 the integral freezes, so bounded noise near the target cannot wind the controller. (iii) Hysteresis prevents evict/restore chatter: a memory with stationary pressure p̂ oscillates only if the *controller* moves θ_high across p̂ by more than the 0.05 gap, which by (i) requires |e| large for multiple consecutive cycles — single-cycle noise cannot flip a memory twice.*

*Proof.* (i) Each state variable is passed through an explicit clamp at every update; Δ is clamped before application. (ii) The integral update is gated on |e| ≥ deadband and on non-saturation in the error direction (anti-windup), so within the band both P and I contributions to *change* vanish (P contributes k_p·e ≤ 0.003 < any meaningful threshold motion only transiently, I is frozen). (iii) Evict requires p̂ > θ_high; subsequent restore requires p̂ < θ_high − 0.05; so a flip-flop needs θ_high to traverse an interval of width > 0.05 around p̂ in opposite directions, and by (i) each cycle moves θ_high at most 0.1 with sign determined by e — sustained sign-alternation of e at magnitude ≥ deadband contradicts stationarity of the population pressure that determines e. ∎

*(Scope note: each pressure sweep constructs a fresh controller from persisted memory state — aggressiveness is not yet persisted across sweeps; convergence to N* is therefore per-sweep proportional control plus within-sweep integral action. Persisting controller state is a one-line roadmap item; the bounds above hold either way.)*

**Co-access graph.** Retrieval records pairwise co-occurrence edges over the injected set (undirected, normalized (min-uuid, max-uuid), weight +1 per co-retrieval capped at 5.0, nightly decay ×(1−0.05) with pruning below 0.01). At query time, when AMP/RMK is enabled, a re-ranker subtracts an associative bonus:

```
score′(m) = max( score(m) − w·min(Σ_{n∈N(m)} weight(m,n), C), 0 ),   C = maxBonus/w   (4)
```

defaults w = 0.15, maxBonus = 1.0. Neighbor sums are fetched in one batched UNION-ALL query.

**Proposition 6 (Bounded associative influence).** *For any memory, the re-ranking adjustment satisfies 0 ≤ score − score′ ≤ maxBonus; scores remain non-negative; and with w = 0 re-ranking is the identity. Hence the pheromone graph can promote a memory by at most a constant additive margin — it can never override an arbitrarily large similarity deficit, and a cold-start system (empty graph) ranks exactly by (1).*

*Proof.* The neighbor sum is capped at C before scaling, so the subtracted term is at most w·C = maxBonus; the outer max(·,0) enforces non-negativity; empty N(m) gives a zero bonus; the w ≤ 0 short-circuit returns raw scores. ∎

### 5.5 The Reflexive Memory Kernel (RMK)

RMK replaces static tuning constants with a **per-agent learned policy vector**

```
θ = [ a, b, k_p, k_i, w, θ_retrieval ]
```

(pressure weights, controller gains, graph bonus weight, retrieval threshold), versioned in `rmk_policies`. Each proxied turn logs an **episode** with reward

```
R = 1.0·task_success + 0.5·token_savings + 1.0·precision − 0.1·eviction_cost   (5)
```

A background worker (hourly cooldown; ≥20 episodes per agent) proposes ε-greedy perturbations: with probability ε = 0.1, each dimension receives uniform noise of at most ±10% of its *bounded range*, then is clamped to hard per-dimension bounds (e.g., k_p ∈ [0.01, 1.0], θ_retrieval ∈ [0.05, 0.99]).

**Proposition 10 (Containment of policy exploration).** *Every policy ever produced by the meta-learner lies in the compact box B = ∏ᵢ [loᵢ, hiᵢ]; each update moves each coordinate at most 0.1·(hiᵢ−loᵢ); consequently every downstream parameter consumed by AMP (via the adapter) is bounded, and all invariants of Propositions 5–7 hold under any reachable policy.*

*Proof.* The perturbation is noise ~ U(−0.1, 0.1)·(hi−lo) followed by clamp to [lo, hi] per dimension; induction from the in-box default policy keeps every iterate in B, and the per-step displacement bound is the noise bound. The adapter writes θ into per-request *clones* of the AMP parameter structs (global state is never mutated), and Propositions 5–7 assumed only non-negativity/finiteness of those parameters, which B guarantees. ∎

**Honest status (see also §9):** in the current release the reward's `task_success` input is a constant 1.0 (the proxy cannot observe task outcomes; the `/api/v1/feedback` endpoint exists to supply the real signal), `precision` is a top-5 fill-rate proxy, `token_savings` is the injected-share of the prompt, and the hill-climbing accept/rollback step exists but is not wired into the DB-backed worker — exploration currently persists unconditionally. RMK should therefore be understood as *bounded stochastic search infrastructure with the reward channel plumbed end-to-end*, not yet as a validated optimizer. The Phase-2 design (episode buffer, PPO-style updates, feedback-driven task success) is reserved in the codebase.

### 5.6 Operational retrieval-quality invariant (HNSW under tombstones)

AEON-IQ's ANN index is pgvector HNSW (m = 16, ef_construction = 64, cosine). Because deletions are *soft* (tombstones remain in the graph; SQL filters after ANN), effective live-recall at fixed `ef_search` degrades as tombstones accumulate — a documented invariant with a documented remedy (raise `ef_search` from the default 40 to 64–100 for tombstone-heavy agents; REINDEX when the dead-tuple ratio exceeds 0.2 or p99 drifts >25%; maintenance runs worker-only under a Postgres advisory lock). We surface this because "the index works" and "recall is preserved" are different claims — a distinction memory systems rarely make explicit.

---

## 6. The Integrity Layer: Proof Capsules and MemoryEvidence

### 6.1 The Proof Capsule

A Proof Capsule is a **signed, redacted attestation of one tool execution** — deliberately *not* a proof of correct execution, not deterministic replay, and not SLSA provenance (§6.5). Schema version "1" (forward-compatible deserialization; two enforcement-mode variants are RESERVED and never emitted):

```
ProofCapsule {
  version, capsule_id,
  subject   { run_id, tool_name, started_at, finished_at, duration_ms },
  tool      { module_digest: TypedDigest, module_name, entrypoint },
  input     { digest: TypedDigest, media_type, raw_included: false },
  policy    { profile_digest?, profile_name?, mode: PolicyEnforcementMode },
  capabilities { required[], granted[], mismatch?, negotiation_rounds? },
  snapshot? { snapshot_id, kind: LatestRuntime|EmptyBaseline|Diff,
              memory_digest, original_size, compressed_size },
  failure?  { failure_category, requires_rollback, deterministic?, error_summary },
  rollback? { occurred, from_snapshot_id?, reason? },
  branches? { source_snapshot_id?, winner_branch_id, branches_tried, branches_succeeded },
  redaction { hashed_fields[], truncated_fields[], removed_fields[], hmac_fields[] },
  limitations[]                    // MANDATORY, non-empty
  memory_evidence?: MemoryEvidenceRef,      // aeon-memory feature
  memory_mode?: Advisory|Attested|AttestedNoHit|AttestedWithRecall|Degraded|Absent,
  signature?: { signer, key_id, signature, signed_payload_digest }
}
```

A semantic validity condition accompanies the cryptographic one: `required ⊆ granted` must hold (the capsule records the mismatch set if not). Capsules are returned in the MCP tool response; persistence is the caller's (or the kit scripts') responsibility.

### 6.2 Canonicalization and signing

The signed payload is the **canonical JSON** of the capsule with `signature = None`: serialize → recursively sort every object's keys → hash. Signing is Ed25519 (`ed25519-dalek`), signer `"nexus-hypervisor"`, with a **dedicated proof key** (fresh per hypervisor by default, or a 32-byte seed from `NEXUS_PROOF_SIGNING_KEY`) that is deliberately separate from the capability-issuing key — compromise of one authority does not counterfeit the other's artifacts. Verification checks, in order: signature presence; recomputed canonical digest == `signed_payload_digest`; `key_id` == expected verifying key; Ed25519 validity.

**Proposition 12 (Evidence determinism).** *Two capsules (or MemoryEvidence values) with identical logical content produce identical signed payloads and digests, regardless of field emission order or floating-point formatting environment.*

*Proof.* Canonicalization sorts all object keys recursively, eliminating order sensitivity. The only numeric fields that originate as floats — memory relevance scores — are converted at the bridge boundary into **fixed-point integer micros** (`MemoryScore`, i64, constructor rejects non-finite and out-of-range values), so no float-to-string formatting ever enters a digest preimage. All remaining fields are strings, integers, UUIDs, booleans, or enums with fixed serializations. ∎

**Proposition 11 (Capsule unforgeability, bounded).** *Assume Ed25519 is EUF-CMA-secure and SHA-256 collision-resistant. An adversary without the proof signing key cannot produce a capsule that `verify_capsule` accepts under key_id K, and cannot repurpose a legitimately signed capsule for different content.*

*Proof sketch.* Acceptance requires a valid Ed25519 signature over the canonical payload under K's key; producing one for any *new* payload is an EUF-CMA forgery. Replaying a legitimate signature over modified content requires the modified capsule to canonicalize to the same payload bytes (impossible for differing logical content, by Proposition 12's injectivity of canonical encoding) or a SHA-256 collision on `signed_payload_digest`. What the signature *means* is strictly bounded: it proves the capsule was emitted by a process holding the proof key — i.e., the trust anchor is the Nexus runtime and its host boundary, exactly as declared in the capsule's own `limitations`. ∎

### 6.3 Redaction: the low-entropy rule

Capsules are redacted **before** signing (the signed artifact is the redacted one, so verification never requires secrets). The rule set is worth stating as an invariant because it prevents a subtle class of leaks:

> **A low-entropy sensitive value (host path, agent id, prompt, env value, token) must never be passed directly to SHA-256.** Public SHA-256 of a guessable value is a dictionary-attack oracle. Such values are either HMAC-digested under a private key (`HmacSha256Private`, marked `public_recomputable = false`) or replaced by `RedactedNoDigest`.

High-entropy artifacts (WASM module bytes, input payloads, snapshot memory) use public SHA-256 (`public_recomputable = true`) so third parties *can* recompute them. Env values are removed; capability tokens appear as opaque ids; error strings truncate at 256 chars; and the snapshot-preview field (`preview_base64`) is excluded from every capsule field by a forbidden-field test suite. Missing HMAC keys **fail closed to redaction** (a test-only zero-key mode refuses to activate outside `cfg(test)`).

### 6.4 MemoryEvidence: attesting memory-influenced execution

When memory participates in an execution, the capsule embeds:

```
MemoryEvidence {
  version: "aeon-nexus-memory-evidence-v1",
  agent_handle: HMAC-SHA256(K_hmac, aeon_agent_id),      // never the plaintext id
  session_id?,
  injected_hits: [ { memory_id, score: integer-micros, content_digest: SHA-256(content) } ]
}
MemoryEvidenceRef {   // what the capsule actually carries
  evidence_version, digest = canonical-SHA-256(MemoryEvidence),
  agent_handle, session_id?, injected_count
}
```

Raw memory text never appears — only content digests, fixed-point scores, and a count. Retrieval on the recall path is itself gated (`Capability::MemoryRecall`), rate-limited per agent, and its *attestation mode* is recorded honestly: `Advisory` (memory not consulted or evidence not verifiable), `AttestedNoHit`/`AttestedWithRecall` (HMAC key present), `Degraded`, or `Absent`. Notably, release 1.0.0 *downgraded* self-issued evidence from `Attested` to `Advisory` on the digest-only daemon path — the system chose to claim less until counter-signature verification lands (§10).

**Proposition 13 (Cross-tenant evidence binding).** *Assume HMAC-SHA-256 is a PRF. An adversary who does not know K_hmac cannot construct MemoryEvidence whose `agent_handle` verifies for a chosen agent id, and evidence generated for agent A cannot be re-attributed to agent B ≠ A without detection.*

*Proof sketch.* `verify_agent_id_hmac` recomputes HMAC(K_hmac, id) and compares in constant time, additionally rejecting any digest not marked `hmac-sha256`/non-recomputable (so a public SHA-256 of a guessed id cannot masquerade as a handle). Producing a verifying handle for a new id without K_hmac contradicts PRF security; re-attribution changes the handle input and hence the evidence digest, which is bound into the signed capsule (Prop. 11). The policy layer independently denies cross-agent/cross-session evidence linkage. ∎

The two keys' separation of duties is explicit: `MANAGEMENT_API_KEY` authenticates *requests* on the private network; `NEXUS_AEON_HMAC_KEY` (≥32 bytes, production-mandatory) binds *provenance*. Per-request wire HMAC is a documented non-feature — transport authenticity relies on the isolated network (§7.3).

### 6.5 Mandatory limitations: the artifact declares its own epistemics

Every capsule must carry a non-empty `limitations[]`; the defaults include:

```
runtime_attestation_only
does_not_prove_correct_execution
does_not_prove_absence_of_external_side_effects
does_not_include_raw_snapshot_memory
does_not_guarantee_full_deterministic_replay
does_not_restore_stack_or_registers
execution_state_is_memory_globals_and_table_metadata
blocked_sync_wasi_io_cancellation_is_cooperative
trusts_nexus_runtime_and_host_boundary
```

This converts the usual white-paper fine print into a machine-readable property of the artifact itself: any downstream verifier, dashboard, or auditor sees exactly the same epistemic boundary we state here. We believe attestation formats for AI systems should adopt this pattern generally.

---

## 7. Security Model and Threat Analysis

### 7.1 Trust boundaries

| # | Boundary | Mechanism | Failure direction |
|---|---|---|---|
| 1 | MCP client ↔ nexus-mcp | stdio, per-session container, tool allowlist (fail-closed: absent policy ⇒ deny) | fail-closed |
| 2 | nexus-mcp ↔ nexus-agentd | Unix socket + auth token; module reads confined to module dir (read-only to MCP) | fail-closed |
| 3 | guest ↔ host (WASI) | linear-memory confinement; fuel; epoch watchdog; capability-mapped preopens; lexical containment (canonical-path mode for untrusted trees) | fail-closed |
| 4 | Nexus ↔ AEON-IQ | management key over isolated network; recall capability-gated + rate-limited; recalled memory **advisory only** | recall fails **open** (to no-memory), timeline fail-open |
| 5 | AEON-IQ ↔ LLM provider | SSRF egress guard: HTTPS required; loopback/private/link-local/CGNAT/benchmark ranges and metadata hostnames blocked; DNS-rebinding-aware (all resolved IPs checked); cloud-metadata blocked even under the local-provider opt-out | fail-closed |
| 6 | operator ↔ management API | constant-time key comparison; startup refuses to run keyless unless dev flag; doctor fails on the dev flag | fail-closed |

Deliberate fail-open choices are confined to *availability-of-evidence* paths (memory recall, timeline delivery): execution never blocks on the memory plane, and the capsule's `memory_mode` records degradation honestly rather than silently.

### 7.2 What the isolation is — and is not

Isolation is userspace WASM confinement (Wasmtime) plus resource bounds plus container hardening (non-root, `cap_drop ALL`, `no-new-privileges`, pids and memory limits, no Docker socket, loopback-only ports, digest-pinned base images). It is **not** a hardware VM boundary; a Wasmtime escape or a malicious host defeats it, which is exactly what `trusts_nexus_runtime_and_host_boundary` declares. Snapshots contain raw guest memory and are handled as confidential artifacts. The capability model's path containment is lexical by design (symlinks unresolved) with the documented canonical-path alternative for untrusted mounts.

### 7.3 Secrets and their separation

Four generated secrets with distinct duties: Postgres password (DB), `MANAGEMENT_API_KEY` (AEON request auth), `NEXUS_AEON_HMAC_KEY` (evidence provenance), `NEXUS_AGENTD_AUTH_TOKEN` (MCP→daemon). The proof-signing key and capability-authority key are additionally separate inside Nexus. Compromise compartmentalization follows: leaking the management key permits memory API calls but not evidence forgery (Prop. 13) nor capsule forgery (Prop. 11); leaking the HMAC key permits handle forgery but not capsule signatures; and so on.

### 7.4 Residual risks (declared)

(i) No per-request wire authentication between Nexus and AEON beyond the shared key and network isolation. (ii) The `sensitivity` field does not yet gate provider egress — private memories are embedded/extracted via the configured LLM provider today (roadmap Phase 1; §10). (iii) **No external security audit has been performed**; internal threat models exist and an external audit is planned before v1.1.0. (iv) Self-issued memory evidence is deliberately downgraded to `Advisory` pending counter-signature verification. (v) The dashboard's NextAuth deployment ships development defaults that must be rotated.

---

## 8. Evaluation

### 8.1 Methodology

We report two bodies of measurement and are explicit about the difference:

- **Prior published results** — the AEON-IQ v0.1.0 benchmark proof (CI, GitHub-hosted runners) and the Nexus validation report (2026-06-07, WSL2, AMD Ryzen 7 7800X3D). We cite them as historical context.
- **A fresh re-run executed for this paper** with upgraded parameters, addressing the methodological gaps we identified in the existing suite: sample sizes raised from 30 to 200 requests per latency scenario; the optional 10,000-memory scale tier enabled; and a **new ranked-retrieval benchmark** (now `benchmarks/scripts/run_recall_extended.py` in the AEON-IQ repository) replacing the 7-memory/14-query recall check with 120 target facts across 12 topical clusters seeded among 1,000 lexically-confusable distractors (1,120 memories in one agent), 3 query variants per fact (360 queries), and proper ranked metrics — recall@{1,3,5,10}, MRR@10, nDCG@10 — with per-query-type and per-cluster breakdowns.

**Fresh-run environment.** 4-vCPU Intel Xeon @ 2.80 GHz cloud container (no CPU-governor control — a stated limitation), 15 GiB RAM, Linux 6.18.5, PostgreSQL 16.13 + pgvector 0.6.0 (native, not containerized), Rust release builds (rustc 1.94.1), AEON-IQ at `852f7cb`, Nexus at `85780b8a`. The kernel ran with the CI benchmark configuration: mock deterministic upstream (`MOCK_EMBEDDING_MODE=hash`), retrieval threshold 0.95, `AMP_ENABLED=true`, `RMK_ENABLED=true`, decay and importance boost at their neutral defaults (λ = β = 0).

**What determinism buys and costs.** The mock upstream and hash embeddings (bag-of-words → SHA-256 → 1,536-dim bucket vector, unit-normed) make every number below exactly reproducible and free of provider noise and cost. The price is semantic validity: *recall results measure the retrieval pipeline — SQL ranking, thresholding, ANN behaviour, injection, audit logging — under lexical similarity, not the quality of any real embedding model.* Semantic benchmarks (LongMemEval, LoCoMo, real embeddings) are roadmap (§10). We consider this trade the correct one for a *systems* paper and label every affected claim.

### 8.2 Nexus execution-substrate microbenchmarks

Criterion.rs, this paper's environment (4-vCPU Xeon 2.80 GHz), LCG-pseudo-random (incompressible) memory buffers so zstd cannot flatter the numbers. p95 is computed from the raw per-iteration sample distributions; the full Criterion output is committed under `artifacts/raw/` in the Nexus repository.

| Benchmark | n | Mean | Median | p95 |
|---|--:|--:|--:|--:|
| cold_start/sandbox_new | 100 | **1.86 µs** | 1.85 µs | 1.96 µs |
| cold_start/hypervisor_new | 100 | 2.95 ms | 2.91 ms | 3.27 ms |
| execute_tool/trivial_wasm_start | 60 | **1.01 ms** | 1.01 ms | 1.04 ms |
| execute_tool_real_memory/1 MiB | 30 | 1.73 ms | 1.71 ms | 1.83 ms |
| execute_tool_real_memory/10 MiB | 30 | 2.09 ms | 2.09 ms | 2.30 ms |
| execute_tool_real_memory/100 MiB | 30 | 1.81 ms | 1.82 ms | 1.91 ms |
| integrated_capability_checked (valid token) | 60 | 1.70 ms | 1.68 ms | 1.77 ms |
| integrated_input_fed (JSON input) | 60 | 1.58 ms | 1.57 ms | 1.68 ms |
| integrated_precompiled (recompile each call) | 60 | 1.62 ms | 1.63 ms | 1.75 ms |
| integrated_precompiled (**cached module**) | 60 | **172.4 µs** | 169.1 µs | 191.8 µs |
| integrated_full_stack (snapshot+execute+validate) | 60 | **234.6 µs** | 231.2 µs | 255.8 µs |
| snapshot_create/1 MiB | 50 | 5.81 ms | 5.76 ms | 6.03 ms |
| snapshot_create/10 MiB | 50 | 62.17 ms | 61.81 ms | 65.06 ms |
| snapshot_create/100 MiB | 50 | 708.09 ms | 705.63 ms | 727.68 ms |
| snapshot_rollback/1 MiB | 50 | **202.4 µs** | 200.2 µs | 213.2 µs |
| snapshot_rollback/10 MiB | 50 | 1.85 ms | 1.83 ms | 1.95 ms |
| snapshot_rollback/100 MiB | 50 | 87.67 ms | 87.42 ms | 90.88 ms |

Four observations, including one methodological one:

(i) **Rollback is the cheap operation by design.** Restoring 1 MiB costs ~0.20 ms — ~29× cheaper than creating the same snapshot — because restore is decompress+copy while create is compress+hash. Even at 100 MiB, rollback (~88 ms) costs an order of magnitude less than snapshot creation (~708 ms). The economics of "snapshot before every execution, roll back on failure" rest on exactly this asymmetry: the expensive half happens unconditionally but off the failure path's critical latency, and the failure path itself is fast.

(ii) **The warm path is microseconds.** Sandbox instantiation is 1.9 µs; with a cached precompiled module, a capability-checked execute is ~172 µs, and the full integrated cycle — snapshot, execute, health-validate — is ~235 µs. Module *compilation* dominates the cold execute path (~1.0–1.7 ms): caching it wins ~9.4×. This is the quantitative case for the daemon architecture (`nexus-agentd` + module cache) that the kit deploys; the published hyperfine comparison (cold CLI 140 ms; daemon 70 ms; Docker-wrapped wasmtime 677 ms) shows the same effect end-to-end.

(iii) **Execution cost is flat in guest memory size** (1.7–2.1 ms across 1–100 MiB): the sandbox touches pages, it does not copy the allocation. Snapshot cost, by contrast, is linear in size — which is what makes differential snapshots (§4.2, cost ∝ dirty pages) the right default for large states.

(iv) **Cross-environment comparison is operation-class-dependent — a caution against single-machine benchmark tables.** Against the published WSL2/Ryzen-7800X3D validation run: cold-start numbers are nearly identical (2.95 vs 3.08 ms; 1.86 vs 1.71 µs); compression-bound snapshot operations are 2.3–4.3× *slower* here (single-core zstd+SHA-256 throughput of a shared 2.8 GHz server core); but the execute path is 3–6× *faster* here (5.07 → 1.01 ms trivial execute), consistent with WSL2's thread-scheduling and syscall overhead taxing the worker-thread execution path. Ratios *within* an operation class are stable across environments; ratios *between* classes are not. We therefore treat "rollback ≪ snapshot-create," "warm ≪ cold," and "execution flat in memory size" as the portable claims, and all absolute numbers as environment-indexed.

For historical context, the retired-claims discipline applies to this table too: these are *benchmarked primitives*, not end-to-end agent latencies, and the 2026-06-07 report's cross-platform hyperfine phase (cold CLI 140 ms; daemon 70 ms; raw wasmtime 52 ms; Docker+wasmtime 677 ms) remains the honest end-to-end anchor.

**Resilience (from the published Phase-3 validation, unchanged code paths):** all 10 failing-WASM scenarios (infinite loop, div-by-zero, unreachable, OOB, stack overflow, invalid module, missing entrypoint, …) were classified into the correct typed `FailureMode`; every failure requiring rollback triggered it and no load-time failure did — the runtime behaviour of Proposition 2. LLM-scored recovery-action soundness rose from 26% to 91% after the Phase-A defect closures (typed taxonomy + distinct per-mode advice).

### 8.3 AEON-IQ proxy and retrieval latency (fresh, n = 200/scenario)

| Scenario | p50 | p95 | p99 | mean | max |
|---|--:|--:|--:|--:|--:|
| direct mock upstream (baseline) | 0.54 ms | 0.65 ms | 0.78 ms | 0.51 ms | 2.9 ms |
| proxy, empty memory | 3.39 ms | 6.18 ms | 101.9 ms | 5.61 ms | 121.8 ms |
| proxy, 100 seeded memories | 10.08 ms | 29.48 ms | 1,030.8 ms | 56.1 ms | 3,023.4 ms |
| proxy, seeded + retrieval-log read (n=66) | 9.62 ms | 14.30 ms | 17.5 ms | 9.93 ms | 18.9 ms |

Server-side retrieval time recorded in the audit log for the seeded scenario: p50 4.0 ms, p95 7.75 ms, with exactly 5 candidates and 5 injections per request.

The headline: **median memory overhead is ~3 ms (empty) to ~10 ms (seeded) per request**, in line with the published p95 figures at n=30. The larger sample, however, exposes what n=30 could not: a **heavy tail** (p99 ≈ 1 s, max ≈ 3 s on the seeded path) that the published table missed entirely. The tail correlates with background work sharing the 4-vCPU host — per-turn extraction spawns, the AMP pressure sweep (which at the time of the run was scoring 11,000+ seeded memories every 5 minutes), and RMK episode writes. This is exactly the kind of finding that justifies academic-grade sample sizes, and it produces a concrete engineering action (isolate background sweeps from the hot path via a worker role or connection-pool partitioning) rather than a marketing number.

**Retrieval scale (semantic search endpoint, k=5):**

| Corpus size | p50 | p95 | p99 | n |
|--:|--:|--:|--:|--:|
| 100 | 2.85 ms | 3.35 ms | 3.51 ms | 100 |
| 1,000 | 10.72 ms | 13.83 ms | 17.93 ms | 100 |
| 10,000 | 95.07 ms | 101.72 ms | 123.71 ms | 50 |

The published suite stopped at 1,000. Extending to 10,000 — and inspecting the plan — surfaced a real scaling defect: **the decay-weighted `ORDER BY` expression defeats the HNSW index.** `EXPLAIN ANALYZE` shows a sequential scan with a top-N heapsort over all 10,000 rows; pgvector can only serve ANN queries whose sort key is the bare `embedding <=> $q`, and formula (1) wraps that operator in `exp()`/importance arithmetic. Latency is therefore linear in corpus size (≈2.9 → 10.7 → 95 ms), and the HNSW index documented in the operations runbook is not actually reached by the hot path at any scale. The remedy is standard: a two-stage plan — ANN probe on raw cosine for the top-K (K ≈ 100, index-served), then apply (1) to re-rank K rows. Proposition 5(iv) guarantees the two-stage result is exact whenever the decay/importance modifier is cohort-constant, and bounded-error otherwise; with the neutral defaults (λ=β=0) it is exact always.

**Status: fixed and re-measured.** The two-stage query shipped (`ANN_CANDIDATE_LIMIT`=100, `SET LOCAL hnsw.ef_search` per retrieval transaction, guarded by an `EXPLAIN`-plan regression test that fails CI if the index scan is ever lost). Post-fix, same environment and parameters: **10,000-memory search p50 6.31 ms** (was 95.07 ms — 15×), p95 9.08 ms, with flat scaling across 100/1k/10k (3.82 / 9.81 / 6.31 ms p50). The p99 latency tail was likewise fixed by batching the pressure sweep's per-row UPDATE loop into one UNNEST statement: seeded-path **p99 1,031 ms → 108 ms, max 3,023 ms → 110 ms** (n=200). Raw artifacts: `benchmarks/results/post-fix-run/` in the AEON-IQ repository.

### 8.4 Ranked retrieval quality (new benchmark, 360 queries, 1,120-memory corpus)

| Metric | Overall | Full paraphrase | Keyword | Reduced-overlap paraphrase |
|---|--:|--:|--:|--:|
| recall@1 | **0.9306** | 1.000 | 0.9917 | 0.800 |
| recall@3 | 0.9611 | 1.000 | 1.000 | 0.8833 |
| recall@5 | 0.9611 | 1.000 | 1.000 | 0.8833 |
| recall@10 | 0.9611 | 1.000 | 1.000 | 0.8833 |
| MRR@10 | **0.9454** | 1.000 | 0.9958 | 0.8403 |
| nDCG@10 | 0.9495 | 1.000 | 0.9969 | 0.8515 |

Search latency across the 360 evaluation queries at the 1,120-row corpus: p50 8.5 ms, p95 12.2 ms, zero errors. The original 7-memory benchmark's recall@1 (0.9286) is statistically consistent with the new 360-query figure (0.9306) — but the new benchmark *localizes the failure mode*: all 14 misses are reduced-overlap paraphrases, and 10 of 14 fall in a single cluster where the query's inflected form ("rotation") shares no token with the stored fact ("rotate") — hash embeddings perform no stemming. Under a real embedding model this class of miss is precisely what should disappear; the benchmark thus doubles as a falsifiable prediction for the semantic-evaluation roadmap item.

Distractor resistance is the other new signal: with 1,000 same-vocabulary distractors present, exact-overlap queries still resolve at rank 1 with probability ≥ 0.99 — the ranking layer, not corpus sparsity, is doing the work. (The base suite's injected-expected-memory rate — whether the right memory actually reaches the LLM prompt — re-measured at 1.0.)

### 8.5 Pipeline correctness (fresh)

- **Temporal versioning:** 14/14 checks pass — snapshots before/after create, update, status change, and archive reconstruct exactly the right state; diffs report added/modified/status-changed/archived; version chains include initial/patch/status entries.
- **Narrative archival:** 8/8 checks pass — compaction produced exactly one narrative L3 memory, versioned, batch-linked with its sibling facts; all L2 sources tombstoned; batch closed `completed`.
- **Suite gate:** `proof_status: pass` (required + dependency-gated artifacts green; k6 optional, not run — no k6 binary in the environment, noted rather than hidden).

### 8.6 Token accounting (fresh, cl100k_base)

| Scenario | Baseline (full history) | AEON-IQ (injected memories) | Δ |
|---|--:|--:|--:|
| profile recall | 73 tokens | 46 tokens | **−37.0%** |
| archival question | 61 tokens | 47 tokens | **−23.0%** |
| small-context overhead | 16 tokens | 53 tokens | **+231%** (worse) |

The suite intentionally ships the negative case: when the live context is tiny, injecting memories *costs* tokens. Token savings are a function of history length versus injection size — the honest claim is "savings scale with conversation length past a crossover," not "AEON-IQ saves tokens." The correct forward-looking metric — savings on realistic multi-session workloads — belongs to the semantic-benchmark roadmap item.

### 8.7 Threats to validity

1. **Lexical embeddings.** All recall metrics use deterministic hash embeddings. They validate ranking mechanics, thresholds, and injection plumbing — not semantic retrieval. (§8.4 states which misses this explains.)
2. **Mock upstream.** Proxy latencies exclude real provider inference time; overheads are additive costs on top of whatever the provider takes, and their *relative* weight in production is much smaller than these tables suggest.
3. **Shared-tenancy hardware, no governor control.** Absolute numbers vary run-to-run; we report medians and tails and rely on within-run baselines (direct-vs-proxy, corpus-size sweeps) whose *deltas* are robust.
4. **Synthetic corpora.** The extended dataset controls lexical overlap by construction; real memory streams are messier in both directions (more redundancy, more ambiguity).
5. **No cross-system baseline.** We do not benchmark MemGPT/mem0/Zep here: a fair comparison requires a shared semantic task suite and live embeddings, which this deterministic methodology deliberately excludes. The repository's own "Claims Not Supported" table makes the same refusal; we adopt it.
6. **Single-node scale.** 10,000 memories/agent is the largest tier measured; the seq-scan finding (§8.3) means extrapolation beyond it is currently unfavourable and must be re-measured after the two-stage retrieval fix.

---

## 9. Limitations and Honest Claims

We enumerate every known gap between what a reader might infer and what is true. Several were found during the audit performed for this paper and are stated here *before* they are fixed, in keeping with the system's own retired-claims discipline.

**Documentation/implementation divergences (bugs of description):**
1. ~~The AEON-IQ README displayed the retired *linear* staleness form~~ — **closed**: README now shows the exponential form with the co-access re-rank described as a post-query step.
2. ~~RMK policy default 0.20 vs env default 0.80~~ — **closed**: both defaults are unified at 0.80 via a shared constant, with a regression test.
3. ~~Migrations 0022–0024 beyond documented architecture~~ — **corrected**: the cognitive-hypervisor timeline is in fact fully implemented and integration-tested (hash-chained events with server-computed `prev_event_digest`, branch-aware resolution); the endpoints are now documented in the architecture reference.

**Aspiration/implementation gaps (roadmap items that could be mistaken for features):**
4. ~~`sensitivity` gates nothing beyond injection filtering~~ — **substantially closed**: archival and conflict-detection candidate selection exclude `private`/`secret`; PATCH re-embed routes labeled content through a scoped local embedding lane (`LOCAL_EMBEDDING_BASE_URL`, loopback/private permitted for that variable only) or refuses with 409. Residual: first-pass extraction still embeds via the provider — safe today only because sensitivity is assigned post-hoc; insert-time labeling would require extending the guard.
5. ~~Hill-climb accept/reject unwired; `task_success ≡ 1.0` forever~~ — **closed**: the worker now compares per-policy mean episode rewards and rejects regressions (re-rolling from the last known-good policy), and a background job backfills `task_success` from `/api/v1/feedback` via each episode's recorded injected-memory set (24 h attribution window; un-fed-back episodes keep the documented assumed default). Residual: `precision` remains a fill-rate proxy, and the learning has not yet been *evaluated* — containment (Prop. 10) is proven, effectiveness is not.
6. ~~PI controller state resets every sweep~~ — **closed**: per-agent `aggressiveness`/`integral_error` persist (`amp_controller_state`) and restore clamped to the Proposition-7 invariant ranges.
7. Nexus's `fork_and_race` races futures over one sandbox; true parallel multi-sandbox speculation is roadmap. *(unchanged)*
8. ~~Self-issued memory evidence capped at `Advisory`~~ — **closed**: AEON-IQ Ed25519 counter-signs the served hit set; Nexus verifies against a pinned `NEXUS_AEON_VERIFYING_KEY` before reporting `Attested*` (missing/invalid signatures drop the hits and degrade the outcome), and the receipt path upgrades to `Attested` only on in-process verification that daemon wire callers cannot forge.

**Structural limitations (inherent to the current design, declared in the artifacts themselves):**
9. Proof Capsules attest that *the Nexus runtime observed and signed these facts* — they do not prove correct execution, absence of external side effects, or replay determinism (WASI path), and they are not SLSA/in-toto artifacts yet. The `limitations[]` array in every capsule says so machine-readably.
10. Isolation is userspace WASM confinement, not hardware virtualization; capability path containment is lexical (symlink-unaware) by documented default.
11. **No external security audit has been completed.** Internal threat models exist; an external audit is planned before v1.1.0.
12. ~~Retrieval at ≥10k memories/agent degrades linearly (HNSW bypass)~~ — **closed**: two-stage ANN retrieval, re-measured flat at 6.31 ms p50 @10k (§8.3), with a CI plan-regression guard.
13. The evaluation is deterministic/lexical end-to-end (§8.7); no semantic-recall or cross-system claims are made.

---

## 10. Roadmap

Ordered by leverage per unit of engineering, each item names the property it converts from "claimed" to "checked":

**R1. Two-stage decay retrieval — SHIPPED.** ANN probe on the bare `embedding <=> $q` (top-K=100, `hnsw.ef_search` per transaction) + exact re-rank over K rows; re-measured flat at 6.31 ms p50 @10k with a CI plan-regression test (§8.3).
**R2. Sensitivity enforcement — SHIPPED (core).** Archival/conflict candidates exclude `private`/`secret`; PATCH re-embed uses the scoped `LOCAL_EMBEDDING_BASE_URL` lane or refuses. Remaining: local-model presets and insert-time labeling support.
**R3. RMK loop closure — SHIPPED (mechanism).** Feedback-derived `task_success` backfill + per-policy hill-climb accept/reject with regression rollback + persisted controller state. Remaining: feedback-labelled precision, and *evaluating* the learning (effectiveness, not just containment).
**R4. Counter-signed memory attestation — SHIPPED.** AEON-IQ Ed25519-signs served hit sets (`aeon-evidence-sig-v1`); Nexus verifies against a pinned key before any `Attested*` mode; tampered or unsigned responses degrade and drop. Third-party verifiable agent-memory audits are now possible.
**R5. Semantic evaluation — HARNESS SHIPPED, RUNS PENDING.** `run_semantic_quality.py` (API-first, env/cost-gated, LongMemEval + LoCoMo loaders, stratified sampling, full ranked metrics) is validated end-to-end on synthetic fixtures; the live runs against real embedding models — and the §8.4 miss-cluster prediction test — await an API key and dataset access.
**R6. Attestation interop — PARTIALLY SHIPPED.** `nexus aeon export-dsse` emits capsules as signed DSSE envelopes (spec PAE, payloadType `application/vnd.nexus.proof-capsule+json`). Remaining: Sigstore/Rekor transparency log, SLSA predicate alignment.
**R7. Provider router + cost ledger** (PRD Phase 2): multi-provider routing with per-run cost recorded into the capsule and timeline — the "governed, inspectable, recoverable, exportable" loop closed with economics.
**R8. Timeline branching / cognitive hypervisor** (schema already at migrations 0023–0024): first-class branch-and-merge of agent timelines over snapshot lineage — speculative *cognition*, not just speculative execution.
**R9. Scale-out and tenancy:** Postgres RLS multi-tenancy, OpenTelemetry traces, distributed snapshot sync (RFC 0001 Phase 3+) with the content-addressed digests of §4.2 as the transfer keys.
**R10. External audit + reproduction bounty** before v1.1.0, per AUDIT.md — the only item that can move trust from "we say" to "they checked." *(Audit-scope package prepared; engagement is a pending human action.)*

---

## 11. Conclusion

Nexus-IQ's thesis is that agent infrastructure should make **failure cheap and history verifiable**. Nexus makes failure cheap: a typed taxonomy decides mechanically what a failure means, a snapshot taken before every execution makes rollback a sub-millisecond default rather than a disaster response, and capabilities can only ever narrow as they delegate. AEON-IQ makes history usable: memory persists across sessions behind an unchanged SDK, decays and revives under explicit, bounded control laws, and every version, retrieval, and archival act is queryable after the fact. The bridge makes both *attestable*: an Ed25519-signed, canonically-encoded capsule binds what ran, under which authority, over which memories — while carrying, in its own body, a machine-readable statement of what it does not prove.

The formal content of this paper is modest by design: thirteen propositions that pin the system's *invariants* — narrowing, boundedness, determinism, unforgeability — rather than aspirational optimality theorems. The evaluation is deterministic by design, and it earned its keep: raising sample sizes exposed a latency tail, extending scale exposed an ANN-bypass defect, and the new ranked-retrieval benchmark localized every miss to a nameable lexical phenomenon. We commend this pattern — bounded learning, mandatory limitations, benchmarks that can fail — to anyone building the accountable agent infrastructure the next few years will demand.

---

## References

[1] A. Agache et al., "Firecracker: Lightweight Virtualization for Serverless Applications," *NSDI*, 2020.
[2] Google, "gVisor: A User-Space Kernel," technical report / documentation, 2018–.
[3] E2B, "Sandboxed Cloud Environments for AI Agents," documentation, 2024–.
[4] C. Packer et al., "MemGPT: Towards LLMs as Operating Systems," arXiv:2310.08560, 2023.
[5] mem0.ai, "Mem0: The Memory Layer for AI Agents," documentation, 2024–.
[6] Zep, "Temporal Knowledge Graph Memory for Agents," documentation, 2024–.
[7] A. Maharana et al., "Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo)," arXiv:2402.17753, 2024.
[8] D. Wu et al., "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory," arXiv:2410.10813, 2024.
[9] OpenSSF, "SLSA: Supply-chain Levels for Software Artifacts," specification v1.0, 2023.
[10] S. Torres-Arias et al., "in-toto: Providing Farm-to-Table Guarantees for Bits and Bytes," *USENIX Security*, 2019.
[11] Z. Newman et al., "Sigstore: Software Signing for Everybody," *CCS*, 2022.
[12] R. Watson et al., "Capsicum: Practical Capabilities for UNIX," *USENIX Security*, 2010.
[13] G. Klein et al., "seL4: Formal Verification of an OS Kernel," *SOSP*, 2009.
[14] A. Birgisson et al., "Macaroons: Cookies with Contextual Caveats," *NDSS*, 2014.
[15] NIST, "Artificial Intelligence Risk Management Framework (AI RMF 1.0)," 2023.
[16] OWASP, "Top 10 for Large Language Model Applications," 2023–2025.
[17] Y. Malkov and D. Yashunin, "Efficient and Robust Approximate Nearest Neighbor Search Using HNSW Graphs," *IEEE TPAMI*, 2018.
[18] J. R. Anderson and L. J. Schooler, "Reflections of the Environment in Memory," *Psychological Science*, 1991.
[19] Bytecode Alliance, "Wasmtime: A Fast and Secure Runtime for WebAssembly," documentation, 2019–.
[20] D. J. Bernstein et al., "High-Speed High-Security Signatures (Ed25519)," *Journal of Cryptographic Engineering*, 2012.

Project sources: Nexus (`github.com/adaptiveliquidity/Nexus`, commit `85780b8a`), AEON-IQ (`github.com/adaptiveliquidity/AEON-IQ`, commit `852f7cb`), Nexus-IQ self-host kit (`github.com/adaptiveliquidity/Nexus-IQ`, commit `09c500a`), including: RFC 0005 "Runtime Proof Capsules"; RFC 0001 "Snapshot Sync"; `docs/HNSW_MAINTENANCE.md`; `docs/BENCHMARKS.md`; `VALIDATION_REPORT.md`; the AEON–Nexus threat models; and the benchmark artifacts committed alongside this paper.

---

## Appendix A: Notation

| Symbol | Meaning | Default |
|---|---|---|
| d(q,m) | cosine distance between query and memory embeddings | — |
| τ(m) | staleness: days since last access (or creation) | — |
| ι(m) | importance score ∈ [0,1] | extractor-assigned |
| λ | memory decay rate (day⁻¹) | 0.0 |
| β | importance boost factor | 0.0 |
| θ | retrieval threshold (upper bound on modified score) | 0.80 (env) / 0.95 (bench) |
| u(m) | utility EMA ∈ [0,1] | α = 0.2 |
| p(m) | memory pressure, eq. (2) | a = 0.02, b = 0.4 |
| A, I | controller aggressiveness, integral state | A∈[0,1], I∈[−10,10] |
| k_p, k_i | PI gains | 0.15, 0.02 |
| w, C | co-access bonus weight, neighbor-sum cap | 0.15, maxBonus/w |
| θ⃗ (RMK) | learned policy [a, b, k_p, k_i, w, θ] | per-agent, box-bounded |
| ⊑ | capability subset relation (§4.4) | — |

## Appendix B: Configuration Defaults (load-bearing subset)

| Variable | Default | Governs |
|---|---|---|
| `max_fuel` | 10,000,000 | instruction budget/execution |
| `max_memory_pages` | 512 (32 MiB) | guest linear memory |
| `snapshot_capacity` | 100 | ring buffer |
| `MAX_DIFF_DEPTH` | 8 | diff-chain promotion |
| `DEFAULT_MAX_CHAIN_DEPTH` | 5 | capability delegation |
| `MAX_NEGOTIATION_ROUNDS` | 2 | denial negotiation |
| `RETRIEVAL_THRESHOLD` | 0.80 | admission threshold θ |
| `MEMORY_DECAY_RATE` / `IMPORTANCE_BOOST_FACTOR` | 0.0 / 0.0 | eq. (1) — neutral |
| `IMPORTANCE_REFRESH_BOOST` | 0.05 | refresh-on-read |
| `DEDUP_THRESHOLD` | 0.05 | near-duplicate insert skip |
| AMP: a, b / target / min-age | 0.02, 0.4 / 1,000 / 24 h | pressure & eviction |
| PI: k_p, k_i, deadband, hysteresis, max Δ | 0.15, 0.02, 0.02, 0.05, 0.1 | controller |
| Co-access: w, max edge, decay, prune | 0.15, 5.0, 0.05/day, 0.01 | pheromone graph |
| RMK: ε, min episodes, cooldown | 0.1, 20, 3,600 s | exploration |
| HNSW: m, ef_construction, ef_search | 16, 64, 40 (pgvector default) | ANN index |
| `MANAGEMENT_API_KEY` / `NEXUS_AEON_HMAC_KEY` | generated, 32 B | auth / provenance |
| `MAX_BODY_BYTES` | 10 MiB | request cap |

## Appendix C: Reproduction

**AEON-IQ suite (deterministic; no API keys, no Docker required):**
```bash
# Postgres 16 + pgvector; user memoryos/memoryos_secret with CREATEDB
cargo build --release                       # in AEON-IQ/
MOCK_PORT=11435 MOCK_EMBEDDING_MODE=hash MOCK_ARCHIVAL_COMPACTION=true \
  python3 mock_openai_server.py &
# kernel env: see docker-compose.test.yml 'memoryos' service (mock upstream,
# AEON_ALLOW_INSECURE_PROVIDER_URLS=true, RETRIEVAL_THRESHOLD=0.95, AMP+RMK on)
./target/release/memoryos &
export BENCHMARK_RESULTS_DIR=benchmarks/results/repro BENCHMARK_INCLUDE_10000=true
python3 benchmarks/seed/seed_memories.py --results-dir "$BENCHMARK_RESULTS_DIR" --include-10000
python3 benchmarks/scripts/run_latency.py  --results-dir "$BENCHMARK_RESULTS_DIR" --requests 200
python3 benchmarks/scripts/run_token_savings.py --results-dir "$BENCHMARK_RESULTS_DIR"
python3 benchmarks/scripts/run_recall_quality.py --results-dir "$BENCHMARK_RESULTS_DIR"
python3 benchmarks/scripts/run_recall_extended.py --results-dir "$BENCHMARK_RESULTS_DIR"   # new
python3 benchmarks/scripts/run_temporal_correctness.py --results-dir "$BENCHMARK_RESULTS_DIR"
python3 benchmarks/scripts/run_narrative_archival.py  --results-dir "$BENCHMARK_RESULTS_DIR"
python3 benchmarks/scripts/summarize_results.py --results-dir "$BENCHMARK_RESULTS_DIR"
```

**Nexus microbenchmarks:**
```bash
cargo bench --bench nexus_validation --features \
  "bench-cold-start,bench-snapshot-create,bench-snapshot-rollback,\
bench-execute-tool,bench-execute-real-memory,bench-integrated"
```

**Full-stack kit:** `./install.sh && ./start.sh && ./doctor.sh && ./verify-live-stack.sh` (a live, no-mocks end-to-end check: memory write → semantic recall → MCP execute with Proof Capsule → timeline event).

**HNSW-bypass verification (§8.3):** run `EXPLAIN (ANALYZE)` on the two-CTE search at the 10,000-memory agent and observe `Seq Scan` + top-N heapsort; the plan and raw results for every table in §8 are committed under `benchmarks/results/academic-run/` in the AEON-IQ repository.
