# P00 manuscript patches

Apply these replacements to P00_DCA_Preprint before resubmission. Continuum does not contain the LaTeX source.

## §6.2 Method — insert after the Phase 1 / Phase 2 paragraph

The mediated effect is an in-process SQLite status write performed by a local effect-boundary function; it is not an external side effect and is not routed through NEXUS.

## Table 3 status column

| Responsibility | Status |
|---|---|
| Environment | Component evidence (not integrated in #2A) |
| State | Component evidence (not integrated in #2A) |
| Authority | Component evidence (not integrated in #2A) |
| Execution | Component evidence (not integrated in #2A) |
| Evidence | Verified (bounded #2A) + component evidence (NEXUS, not integrated in #2A) |
| Coordination | Component evidence (not integrated in #2A); integration-stage / tested narrow surface |
| Cognition Boundary | Integration-stage |

Keep every existing limitation sentence. Do not upgrade any lineage to integrated DCA conformance.

## Table 6 — mark recovery mirrors and replace the Nexus pin

| System | Repository | Pinned revision | Note |
|---|---|---|---|
| Continuum / DCA doctrine | Adaptive-Liquidity/Continuum | current publish commit | |
| FLOKS / floks-pc | Adaptive-Liquidity/floks-pc | 35b5e7149e96 | |
| AEON-IQ | Adaptive-Liquidity/AEON-IQ-temp | d5866e85edb3 | Recovery mirror of adaptiveliquidity/AEON-IQ |
| Genesis Runtime | Adaptive-Liquidity/genesis-runtime | dfd9c69a4530 | |
| NEXUS | Adaptive-Liquidity/Nexus-temp | f801071de4b0 | Recovery mirror of adaptiveliquidity/Nexus. Pin is the H2 execute_wasi capability-grant test commit, not a benchmark-chart bot commit. |
| Agent-Bridge | Adaptive-Liquidity/Agent-Bridge | 5925ab044348 | |

## Appendix A reproduction command

Keep:

```
make reproduce-p00
```

Add one sentence: the artifact root is the Continuum repository root (or `artifact/` with `make -C .. reproduce-p00`). The command runs `python -m unittest` on the slice tests, `proof.py run`, and `proof.py verify`.

## Reference [9]

Replace Koepe arXiv:1907.07154 with:

[9] M. S. Miller. “Robust Composition: Towards a Unified Approach to Access Control and Concurrency Control.” PhD thesis, Johns Hopkins University, May 2006. http://www.erights.org/talks/thesis

Optional secondary (not a substitute): Miller, Yee, and Shapiro, “Capability Myths Demolished,” Technical Report SRL2003-02, Johns Hopkins University, 2003.

## Table 4 — leave wording; implementation now matches

AC-1 same Continuum Computer ID across the restart
AC-2 same VERA ID across the restart
AC-5 post-restart effect passes through a non-model mediator
AC-8 excluded scope is not silently represented as proven

These are now separate computed predicates. AC-8 is never a literal true.
