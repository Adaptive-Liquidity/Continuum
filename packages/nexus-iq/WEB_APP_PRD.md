# Nexus-IQ Web App — Product Requirements & Build Plan (PRD)

> Status: Draft for review · Date: 2026-06-24 · Owner: Adaptive Liquidity
> Source: grounded codebase audit of Nexus, AEON-IQ, and the Nexus-IQ kit (not a clean-slate vision).

## 1. Summary

Nexus-IQ is the **consumer-facing app** for the Nexus + AEON-IQ stack: one local control plane where a user connects providers, runs governed AI/tool executions, controls memory, and — uniquely — gets **signed, exportable proof of what happened** plus **state rollback**. The `install.sh` + Docker stack already starts the system; this web app is what lets users *understand, configure, and use* it.

The product wedge (one line): **Nexus-IQ turns AI runs into governed, inspectable, recoverable, exportable events.**

## 2. Honest positioning (read this first)

A codebase audit corrected one load-bearing assumption in early vision drafts:

- **Nexus governs the sandboxed execution boundary** — i.e. it allows/blocks/logs a **WASM module's WASI host-calls** (file, network, etc.) at the guest↔host boundary, and produces a signed proof capsule. Evidence: `src/sandbox/wasi.rs`, `src/hypervisor/mod.rs` (`execute_tool_wasi`, capability authorize), `src/security/capability.rs`.
- **Nexus does NOT today sit between an LLM and its tool choices.** It does not intercept "the model decided to call tool X" and block it, and it does **not route models** (`src/hypervisor/llm_policy.rs` is a *failure-recovery advisor*, feature-gated `ai-recovery`, off by default).
- Therefore "control plane that governs an agent's tool calls and routes the model" is the **destination**, not today's reality. That layer is net-new (an agent/MCP-governance wrapper + a provider router).

This honesty is itself a selling point to the accountability/security-minded buyer (NIST AI RMF trustworthiness characteristics; OWASP LLM Top 10).

## 3. Audit: what exists (reuse) vs net-new

### Reusable today
| Capability | Where | Notes |
|---|---|---|
| AEON-IQ REST API (`:8080`, `X-Management-Key`) | AEON `src/main.rs`, `src/api.rs` | memory CRUD/search/list, timeline, stats, export, retrievals |
| Memory store (pgvector) + fields | AEON `src/models.rs`, migrations | incl. `status` (active/candidate/quarantined/suppressed) and `sensitivity` (unknown/normal/private/sensitive/secret) — migration 0019 |
| Memory-usage log | AEON migration 0021 `memory_retrieval_logs`; `GET /agents/:id/retrievals` | records candidate + **injected** memory ids + scores + latency per request |
| Nexus daemon (`nexus-agentd`) | `src/bin/nexus_agentd.rs`, `src/daemon/mod.rs` | length-prefixed JSON over **Unix socket** (not HTTP); `Execute`/`Ping`/`Shutdown`; optional auth token |
| Nexus MCP tools (STDIO) | `src/bin/nexus_mcp.rs` | execute, execute_proof, snapshot create/rollback, issue/attenuate token, fork_and_race, instinct, `nexus_iq_execute` |
| Proof Capsule v1 (signed) | `src/proof/schema.rs` | run/tool/input digests, capability evidence, snapshot, failure/rollback, **redaction manifest**, **limitations[]**, memory evidence, Ed25519 signature, `duration_ms` (latency) |
| Snapshots / rollback | `src/hypervisor/mod.rs`, `nexus_snapshot_*` | create, rollback, digest TOCTOU-guard, capability-gated memory preview |
| Capability tokens | `src/security/capability.rs` | issue/attenuate/validate Ed25519 chains; denial events; negotiation (denied→narrowed subset) |
| Provider proxy (AEON) | AEON `src/proxy.rs` | OpenAI-compatible **single-upstream** passthrough; injects recalled memory as system message |
| Kit Docker stack | `nexusiq/docker-compose.yml` | postgres + aeon (`:8080`) + nexus-agentd (socket) + nexus-mcp (STDIO) |

### Net-new (must build)
| Gap | Severity | Notes |
|---|---|---|
| **HTTP front door to Nexus** | required | agentd = socket-only, MCP = STDIO-only; browser can't reach Nexus. Need a gateway/BFF. |
| **Multi-provider router** | big | AEON proxy is single-upstream. No routing rules / fallback / cost-cap / per-request reason. The differentiator + moat. |
| **Cost tracking** | big | No cost recorded anywhere; telemetry (`src/telemetry`) is in-memory (duration, fuel) only. Need a persisted cost ledger. |
| **Proof capsule persistence/index** | small | Capsules are write-once, embedded in responses; not stored/queryable by id. Need a store. |
| **Sensitivity enforcement** | small | `sensitivity` field exists but **gates nothing** — all memory text is sent to the provider for embedding/extraction/injection. Wire it into retrieval/embedding filters to make "private = local-only" true. AEON `src/api.rs` (`embed_text` always called), `src/memory/extraction.rs`, `src/memory/store.rs` (filters on `status` only). |
| **Agent/MCP-governance wrapper** | big | To actually "block the model's tool call" Nexus must be fronted by a layer that maps a model's tool-use request → capability check → wrapped sandboxed execution. |
| **Web UI (8 screens)** | required | The existing `/dashboard` is a **benchmark/marketing** site (Next.js, GitHub Pages), not a control plane — not reusable as-is; reuse its tooling only. |

## 4. Hero moments × reality (what to demo)

Lead with what's real and uniquely ours.

| Hero moment | Real today | Net-new |
|---|---|---|
| **2 — "Proves what happened" (Proof Packs)** 🟢 strongest | signed capsule: digests, capability evidence, snapshot, failure/rollback, redaction manifest, limitations (=unsupported claims), memory evidence, latency | persist/index (small); **cost** line; **provider/route** line (waits on router); "supported claims" presentation |
| **3 — "Recovers from bad state" (Rollback)** 🟢 real | snapshot/rollback, before/after, digest guard, capability-gated preview, audit trail | preview/confirm **UI** only |
| **1 — "Controls access" (Governance)** 🟡 half-real | allow/block/log a sandboxed module's WASI calls; denial events; negotiation; memory-usage transparency (retrieval logs) | "block the *model's* tool call" + "route the model" (wrapper+router, big); "private memory not sent to provider" (wire `sensitivity`, small) |

## 5. Architecture (reuse-maximizing)

Add **two services** to the existing kit compose:

```
browser ─▶ nexus-iq-web (Next.js, 127.0.0.1:3000)
                 │ HTTP
                 ▼
          nexus-iq-gateway (BFF / control-plane API)
                 ├─ socket ─▶ nexus-agentd      (execute, proof, snapshot, tokens)
                 ├─ REST   ─▶ aeon (:8080)       (memory, timeline, retrieval logs)
                 ├─ Postgres (reuse AEON's)      (cost ledger, proof index, runs)
                 └─ Provider Router  [NET-NEW]   (multi-provider, fallback, cost-cap, reason log)
```

**Key decision — build the gateway in Rust (axum):** it can link the Nexus crate directly (daemon client, proof verify, capability tokens) instead of re-implementing the socket protocol + proof schema in another language. Reuse AEON's Postgres for new tables; reuse AEON REST for memory/timeline. Frontend = Next.js (reuse dashboard tooling). UI talks only to the gateway.

## 6. Phased MVP plan

- **Phase 0 — the real hero demo.** Gateway skeleton + auth + one scripted end-to-end flow: run task → execute sandboxed with **one capability allowed, one blocked** → **signed Proof Pack** (Evidence Drawer: capabilities, memories-used via retrieval logs, snapshot, latency, limitations) → **export** → **preview+confirm rollback** → **linkage graph** (run→capability→memory→proof→snapshot, already linked by ids in the capsule). ~90% wiring over real surfaces + a small capsule store. Delivers Hero 2 + 3 + the real half of 1.
- **Phase 1 — make two beats true cheaply.** Wire `sensitivity` → retrieval/embedding filter ("**private = never leaves the box**"); add a **cost** field to runs/capsule (estimated ok). Makes the memory hero beat and the Proof Pack cost line honest.
- **Phase 2 — the differentiator (moat).** Multi-provider **router** + **cost ledger** + **agent/MCP-governance wrapper** → makes "route the model" and "block the agent's tool call" real.

**Delivery:** two new containers in the existing `nexusiq` compose; UI on `127.0.0.1:3000`, gateway internal — consistent with how the kit ships.

## 7. Decisions to lock
1. Gateway language: **Rust/axum** (recommended, reuse Nexus crates) vs Node/TS.
2. Cost/proof data home: **reuse AEON Postgres** (new schema) vs a dedicated gateway DB.
3. Router scope for Phase 2: rules engine surface (cost/latency/privacy/fallback) and where it intercepts.
4. Auth model for the web app (single-user local vs multi-user).

## 8. Risks / honesty guardrails
- Do **not** demo "block the model's tool call" or "route the model" until Phase 2 ships — the engine doesn't do it yet.
- Do **not** claim "private memory not sent to OpenAI" until Phase 1 wires `sensitivity` enforcement — today it is sent.
- Proof Pack "cost" and "provider/route" lines are blank until Phase 1/2.

## 9. Evidence index
- Governance boundary: `nexus/src/sandbox/wasi.rs`, `nexus/src/hypervisor/mod.rs`, `nexus/src/security/capability.rs`, `nexus/src/bin/nexus_mcp.rs`.
- Proof capsule: `nexus/src/proof/schema.rs`; daemon evidence in `nexus/src/daemon/mod.rs`.
- Memory model + enforcement gap: `AEON-IQ/src/models.rs`, migrations `0019_memory_status_sensitivity.sql`, `0021_memory_retrieval_logs.sql`; `AEON-IQ/src/api.rs`, `src/memory/extraction.rs`, `src/memory/store.rs`, `src/embeddings.rs`, `src/proxy.rs`.
- Kit stack: `nexusiq/docker-compose.yml`, `nexusiq/install.sh`.
