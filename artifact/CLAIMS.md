# P00 claims ledger

Human-readable mirror of `artifact/manifest.json`.

| ID | Class | Responsibility | Claim | Evidence | Ceiling |
|---|---|---|---|---|---|
| DEF-DCA-7 | DEFINITION | all | Seven separable systems responsibilities around a persistent principal | manuscript §4 | Architecture statement only |
| DEF-VERA | DEFINITION | Authority / Cognition Boundary | VERA is a persistent principal independent of one model/process/host | manuscript Def. 1 | Not legal personhood or formal verification |
| EXP-2A-AC1 | EXPERIMENTALLY VERIFIED | Environment | Same Continuum Computer ID across same-host process restart | #2A artifact AC-1 | Process/session only |
| EXP-2A-AC2 | EXPERIMENTALLY VERIFIED | Cognition Boundary | Same VERA ID across same-host process restart | #2A artifact AC-2 | Process/session only |
| EXP-2A-AC3 | EXPERIMENTALLY VERIFIED | State | Durable marker written before restart is read after | #2A artifact AC-3 | One key/value |
| EXP-2A-AC4 | EXPERIMENTALLY VERIFIED | Authority | Active grant commits; revocation denies the same capability | #2A artifact AC-4 | Local grant table |
| EXP-2A-AC5 | EXPERIMENTALLY VERIFIED | Execution | Post-restart effect goes through a non-model mediator | #2A artifact AC-5 | In-process SQLite status write; not NEXUS |
| EXP-2A-AC6 | EXPERIMENTALLY VERIFIED | Evidence | Structured event sequence is independently recomputable | #2A artifact AC-6 | Not notarized / not tamper-evident |
| EXP-2A-AC8 | EXPERIMENTALLY VERIFIED | Evidence | Excluded scope is not represented as proven | #2A artifact AC-8 | Computed excluded_scope flags |
| COMP-FLOKS | COMPONENT EVIDENCE | Environment | FLOKS L0–L3 private-beta Agent Computer lineage | floks-pc@35b5e714 | Not integrated in #2A |
| COMP-AEON | COMPONENT EVIDENCE | State | AEON-IQ memory proxy lineage | AEON-IQ-temp@d5866e85 | Recovery mirror; not integrated in #2A |
| COMP-GENESIS | COMPONENT EVIDENCE | Authority | Genesis R0–R2 authority lifecycle tests | genesis-runtime@dfd9c69a | In-memory; not integrated in #2A |
| COMP-NEXUS | COMPONENT EVIDENCE | Execution | NEXUS WASI/capability tests | Nexus-temp@2e863998 | Recovery mirror; not integrated in #2A |
| COMP-BRIDGE | COMPONENT EVIDENCE | Coordination | Agent-Bridge narrow confirm-gated control plane | Agent-Bridge@5925ab04 | Not production multi-VERA |
| INT-COG | INTEGRATION-STAGE | Cognition Boundary | Model-neutral interface exists | Continuum interface | No model/provider replacement experiment |
