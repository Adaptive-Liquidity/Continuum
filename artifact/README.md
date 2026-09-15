# P00 artifact package

This directory is the artifact root referenced by Distributed Cognitive Architecture (P00).

From the Continuum repository root (also valid if this directory is the cwd and `make -C ..` is used):

```bash
make reproduce-p00
make verify-evidence
```

`make reproduce-p00` runs the Decision #2A unit tests, executes a fresh two-process proof, and independently recomputes AC-1 through AC-8.

## Contents

- `manifest.json` — machine-readable claim-to-evidence ledger
- `CLAIMS.md` — human-readable mirror
- `SOURCE_INDEX.md` — repository URLs, pins, and claim ceilings
- `MANUSCRIPT_PATCHES.md` — exact P00 text replacements (no LaTeX source is in this repo)
- `docs/evidence/continuum-persistence-slice-2a.json` — archived #2A artifact (repo path)
- `proofs/continuum-persistence-slice/` — harness, verifier, tests

## Claim ceiling

This package supports the bounded same-host process-restart slice only. It does not prove host migration, model/provider replacement, credential rotation, multi-VERA coordination, complete DCA conformance, or production readiness.
