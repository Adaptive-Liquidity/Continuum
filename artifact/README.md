# P00 artifact package

This directory is the artifact root referenced by Distributed Cognitive Architecture (P00).

From the Continuum repository root (also valid if this directory is the cwd and `make -C ..` is used):

```bash
make reproduce-p00
make verify-evidence
```

`make reproduce-p00` is the Decision #2A harness path (`make reproduce-p00-harness`): unit tests, a fresh two-process proof, and an independent recompute of AC-1 through AC-8. P00 LaTeX is not in this repository and is not part of that target.

## Contents

- `manifest.json` — machine-readable claim-to-evidence ledger
- `CLAIMS.md` — human-readable mirror
- `SOURCE_INDEX.md` — repository URLs, pins, and claim ceilings
- `MANUSCRIPT_PATCHES.md` — exact P00 text replacements (no LaTeX source is in this repo)
- `docs/evidence/continuum-persistence-slice-2a.json` — archived #2A artifact (repo path), regenerated from `proof.py run` on 2026-09-27 (not hand-edited)
- `proofs/continuum-persistence-slice/` — harness, verifier, tests

## Claim ceiling / limits

Same-host clean process restart only: two sequential OS processes share one SQLite store; phase 1 exits normally (no kill or crash). The verifier is a separate, internal script by the same author, not third-party verification. The effect is a local, mediated SQLite write, not an external side effect. This does not demonstrate crash recovery, host migration, model/provider replacement, external effects, third-party verification, cryptographic notarization, or production readiness.
