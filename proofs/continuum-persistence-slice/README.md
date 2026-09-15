# Continuum Persistence Slice — Decision #2A

Internal, reproducible proof for the bounded Continuum Genesis Proof defined by Decision #2A.

## What it demonstrates

One named Continuum Computer and one named VERA survive a process restart on the same host. Durable state written before restart is read afterward. A mediated effect commits while an explicit scoped grant is active, the grant is revoked, and the same capability is refused afterward. A structured evidence artifact records the discontinuity and all acceptance observables without relying on the principal's narration.

This proof is intentionally narrow. It supports AC-1 through AC-8 only. It does not establish claims outside the Decision #2A acceptance scope.

## Run

```bash
python proofs/continuum-persistence-slice/proof.py run \
  --workdir proofs/continuum-persistence-slice/.run
```

The command launches two separate Python processes against the same SQLite database and writes:

- `.run/continuum-persistence-slice.sqlite3`
- `.run/continuum-persistence-slice-2a.json`

## Verify

```bash
python proofs/continuum-persistence-slice/proof.py verify \
  --artifact proofs/continuum-persistence-slice/.run/continuum-persistence-slice-2a.json
```

A passing verifier returns `"valid": true` with AC-1 through AC-8 all `true`.

## Test

```bash
python -m unittest -v proofs/continuum-persistence-slice/test_proof.py
```

The integration test launches phase 1 and phase 2 as distinct operating-system processes and independently checks the persisted artifact.
