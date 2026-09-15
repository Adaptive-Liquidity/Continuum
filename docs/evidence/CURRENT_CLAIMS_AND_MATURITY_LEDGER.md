# Current Claims & Maturity Ledger — Continuum Persistence Slice

**Date:** 2026-09-15  
**Authority basis:** Category Doctrine v1 (2026-09-12) + Decision #2A (2026-09-12)  
**Scope:** Current bounded claims supported by the Decision #2A reproducible artifact and current repository evidence.

Allowed maturity labels follow Category Doctrine v1: **Verified**, **Tested implementation**, **Integration-stage / integration-ready**, **Active R&D**.

## Verified — Decision #2A observables

### CPS-ENV-001 — Verified

**Claim:** One named Continuum Computer ID remains the same across a process restart on the same host.  
**DCA responsibility:** Environment  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-1 = true. Pre-restart and post-restart process IDs differ while the Computer ID remains constant.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** Persistence beyond the tested process/session discontinuity only; no machine/host migration claim.

### CPS-VERA-001 — Verified

**Claim:** One named VERA remains the same principal across the tested process restart and remains bound to the same Continuum Computer.  
**DCA responsibility:** Cognition Boundary / Authority  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-2 and AC-7 = true; VERA ID remains constant across distinct process IDs.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** Does not prove every VERA property across every substrate, model, credential or machine.

### CPS-STATE-001 — Verified

**Claim:** A durable operational state value written before process restart is readable after reconstitution without model-context replay.  
**DCA responsibility:** State  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-3 = true; `state.written` occurs before the discontinuity and `state.read` after it with the same value.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** This proves the bounded state value in this slice, not the complete AEON-IQ memory system or arbitrary-state migration.

### CPS-AUTH-001 — Verified

**Claim:** The tested mediated effect is permitted while an explicit scoped grant is active and refused after the grant is revoked.  
**DCA responsibility:** Authority  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-4 = true; the artifact records `effect.committed`, `grant.revoked`, then `effect.denied` for the same capability.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** Bounded to the tested capability and local persistence slice.

### CPS-EXEC-001 — Verified

**Claim:** One mediated effect occurs after process reconstitution under the active grant through an execution boundary distinct from cognition.  
**DCA responsibility:** Execution  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-5 = true; the committed effect runs in the post-restart process via the persistence-slice effect mediator.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** This proof uses the slice's local mediator; it is not evidence that every Continuum effect has been executed through the full NEXUS production path.

### CPS-EVID-001 — Verified

**Claim:** The persistence slice emits an independently inspectable structured record containing the Computer ID, VERA ID, discontinuity, state write/read, grant, committed effect, revocation and denied retry.  
**DCA responsibility:** Evidence  
**Artifact:** `docs/evidence/continuum-persistence-slice-2a.json`  
**Verification:** AC-6 = true and verifier reports a contiguous evidence sequence.  
**Last verified:** 2026-09-15  
**Owner:** Continuum  
**Claim ceiling:** Structured evidence only; this row does not claim cryptographic verification.

## Tested implementation — supporting lineage

The following supporting systems have repository-native test and/or validation evidence and are used as technical lineage, not as proof that Continuum completely implements all seven responsibilities:

- **AEON-IQ:** Postgres-backed validation, memory retrieval and benchmark proof artifacts.
- **NEXUS:** WASM/WASI execution, capability gates, snapshots/rollback, replay and Proof Capsule implementation/tests.
- **Genesis Runtime / AEON Program:** signed identity, attenuation, revocation, expiry and authority lifecycle tests; AEON Program devnet/smoke evidence.
- **FLOKS / Agent Computer lineage:** authenticated remote Agent Computer path, durable records, CDP accessibility, checkpoint/recovery evidence.
- **Agent-Bridge:** narrow scoped cross-system control with authenticated/confirm-gated actions.

These supporting claims remain subject to their repository-specific limitations and should be cited individually in research papers.

## Not cleared by this ledger

This ledger does **not** clear claims that:

- Continuum completely implements all seven DCA responsibilities;
- DCA is an externally established industry standard;
- Continuum persistence has been verified across host/machine migration;
- model-provider swap has been verified as a persistence discontinuity;
- multi-VERA coordination is production-complete;
- Context Kernel has passed its pending independent S0 re-audit;
- universal recovery, absolute isolation, production readiness or arbitrary-scale coordination are established.

## Reproduction

Run:

```bash
python proofs/continuum-persistence-slice/proof.py run --workdir proofs/continuum-persistence-slice/.run
python proofs/continuum-persistence-slice/proof.py verify --artifact proofs/continuum-persistence-slice/.run/continuum-persistence-slice-2a.json
python -m unittest -v proofs/continuum-persistence-slice/test_proof.py
```

A valid run must report AC-1 through AC-8 as true.
