# P00 source index

Inspected public revisions for P00 implementation-realization claims.

| System | Repository | Pinned revision | Role |
|---|---|---|---|
| Continuum / DCA doctrine | Adaptive-Liquidity/Continuum | a47421e58de73def7e6aae6ee3e90ac5a6be8caf | Artifact package + Makefile. Harness rewrite rides this tree. |
| FLOKS / Agent Computer | Adaptive-Liquidity/floks-pc | 35b5e7149e96a8360ec0dc6411b438392fa91ca4 | Component evidence only. L0–L3 private-beta. Not integrated in #2A. |
| AEON-IQ | Adaptive-Liquidity/AEON-IQ-temp | d5866e85edb3a7f7ea7186854655981ca73760f4 | Recovery mirror of adaptiveliquidity/AEON-IQ. Component evidence only. Not Continuum state. |
| Genesis Runtime | Adaptive-Liquidity/genesis-runtime | dfd9c69a45302034a41e997f03655c0452e93010 | Component evidence only. R0–R2 in-memory authority. Not integrated in #2A. |
| NEXUS | Adaptive-Liquidity/Nexus-temp | 2e863998665d5b9a0369dc5cf3f2307b27835e46 | Recovery mirror of adaptiveliquidity/Nexus. Table 6 inspected revision: last human merge after RUSTSEC-2026-0188/0190 wasmtime 45.0.3 bump (f7a1564, 2026-06-29). |
| Agent-Bridge | Adaptive-Liquidity/Agent-Bridge | 5925ab0443487581e5698c570d9c8dd6c826af8b | Component evidence only. Narrow confirm-gated control plane. Not integrated in #2A. |

## NEXUS pin rationale

Do not pin e720495540f5. That commit is `docs: auto-update benchmark chart [skip ci]` (2026-08-30).
Do not pin f801071de4b0 as the inspected tree. It is a real H2 capability-grant test (2026-06-17) but predates the wasmtime advisory fix.

Recorded capability-test evidence commits, not Table 6 pins:

- 944f16977a502792117b6e706e24c03c96796c18 — WASI capability-enforcement merge (2026-06-12)
- f801071de4b01a1c04368c5bdfc5fdd0da9288dc — H2 execute_wasi allowlist / parent-token tests (2026-06-17)
- f7a1564b44deec6aace15c2acee362ea5f78f77d — advisory floor; wasmtime 45.0.3 (2026-06-29)

Advisory floor: do not inspect Nexus-temp below f7a1564 for execution claims.
