# AEON Context Kernel S0: Third-Party Security Review Pack

## Read this first

**Goal:** Review only the S0 foundation of AEON Context Kernel. S0 decides whether a piece of text is allowed to be treated as trusted context and ensures decisions cannot be attached to the wrong piece of text.

**Do not assess yet:** real provider calls, real filesystem/network/Git execution, approval capabilities, compaction/invariant residency, or whether this makes AI models safer. Those are deliberately out of scope and must not be treated as completed features.

> **The review question:** Can an attacker cause unverified or altered text to receive trusted authority, or cause a decision/receipt for one segment to be used for another segment?

## What to send the reviewer

Send the following archive without modifying it:

| Item | What to send | Why |
|---|---|---|
| Frozen package | `AEON_Context_Kernel_S0_v0.2.1.zip` | Complete source, tests, documentation, workflow snapshots, and generated S0 evidence. |
| SHA-256 checksum | The `AEON_Context_Kernel_S0_v0.2.1.zip` entry in the `v0.2.1` release’s `SHA256SUMS.txt` | Lets the reviewer confirm they audited the intended package without relying on a checksum embedded inside that package. |
| This brief | `docs/third_party_s0_audit_handoff.md` | Defines the permitted review scope and required evidence. |
| Implementation record | `docs/s0_implementation_and_reaudit.md` | Explains what changed and what the internal re-audit checked. |
| Blueprint | `docs/skill_governed_architecture_and_blind_study_blueprint.md` | States the target architecture and what remains deferred. |
| Prior audit mapping | `docs/audit_to_validation_addendum.md` | Maps the earlier findings to remediation gates. |
| Existing evidence | `results/s0-provenance-v2-final/` | Includes smoke, pilot, full conformance artifacts, replay logs, and passive-audit records. |

The reviewer should first verify the archive checksum. If it differs, stop and request the correct package.

## One-paragraph review request you can copy and send

> Please perform an independent security review of **AEON Context Kernel S0 only**. Verify whether an attacker can make caller-controlled or altered text receive principal/trusted authority, reuse or forge provenance, substitute content after verification, create identity collisions, cross-bind decisions or receipts, or bypass deny-by-default admission. Reproduce the supplied tests, add adversarial tests or a minimal proof of concept where appropriate, and return a written report with severity, exact reproduction steps, affected files/versions, and a pass/fail recommendation. Do not evaluate deferred S1 features, real tools, providers, or claims of real-model effectiveness.

## How to set up the review

The package uses Python 3.12 and `uv`.

```bash
sha256sum --check SHA256SUMS.txt
unzip AEON_Context_Kernel_S0_v0.2.1.zip
cd aeon-context-kernel
# Confirm the checksum command reports the archive as OK before unpacking it.
uv sync --extra dev --locked
```

Run the supplied test and source-quality checks before changing anything:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src
python examples/basic_usage.py
cker demo
```

A reviewer may use a separate virtual environment or container. They should report the operating system, Python version, `uv` version, package lockfile state, and exact command output.

## Required adversarial checks

The reviewer does not need to rely on our test labels. They should independently try the following attacks and record the exact result.

| ID | Try to break this | Attack attempt | A correct S0 result |
|---|---|---|---|
| A1 | Caller-controlled trust | Submit a raw segment that says it is `principal` or otherwise trusted, but has no valid verifier-issued provenance. | It is rejected and cannot enter a trusted assembly region. |
| A2 | Forged provenance | Change any signed/attested provenance field, signature, issuer ID, or content binding. | Verification fails; no trusted admission decision is produced. |
| A3 | Expired, wrong-scope, or revoked provenance | Use a valid-looking attestation outside its time, audience, policy, or revocation conditions. | It is rejected. |
| A4 | Replay | Submit the same accepted attestation more than once in one admission session. | The second use is rejected. |
| A5 | Post-verification substitution | Verify segment A, then try to use the decision for altered content or segment B. | Exact-byte/content-hash binding prevents admission or assembly. |
| A6 | Logical-ID collision | Create two different segments with the same caller-selected logical ID. | The system rejects ambiguity; no decision can silently attach to the wrong segment. |
| A7 | Opaque-UID collision or mismatch | Duplicate a verified UID, swap UIDs, or join a valid decision to the wrong verified segment. | The system fails closed. |
| A8 | Missing or surplus decision | Assemble a set with one decision missing, one extra decision, or a duplicate decision. | Assembly fails closed; it does not guess. |
| A9 | Receipt cross-binding | Create a receipt with repeated logical IDs or repeated verified UIDs. | Durable evidence creation rejects it. |
| A10 | Empty allowlist | Configure no allowed sources/principals and attempt admission. | All admissions are denied. |
| A11 | Deterministic regression | Re-run the existing smoke, pilot, and full conformance runs, then replay their traces. | The supplied deterministic evidence can be reproduced according to its stated scope. |

The reviewer may add any additional attack relevant to provenance lifecycle, serialization, canonical hashing, immutable identity, or exception/error handling. A clean run of the supplied tests is **not sufficient**: the reviewer should demonstrate independent negative testing for A1–A10.

## Files most relevant to the review

| Purpose | Main files |
|---|---|
| Provenance issuance and verification | `src/context_kernel/provenance.py` |
| Segment and verified-identity models | `src/context_kernel/models.py` |
| Admission and deny-by-default policy | `src/context_kernel/admission.py` |
| Exact decision-to-segment assembly | `src/context_kernel/assembly.py` |
| Verified identity through compaction | `src/context_kernel/compaction.py` |
| Durable receipts and trace identity | `src/context_kernel/receipts.py` |
| Scenario fixture issuance | `src/survival_bench/scenarios/catalog.py` |
| S0 adversarial tests | `tests/test_models_admission.py`, `tests/test_assembly_compaction.py`, `tests/test_receipts_replay.py` |

## Evidence the reviewer must return

The final report must include the items below. A verbal “looks good” is not enough.

| Required item | What it must contain |
|---|---|
| Scope statement | Confirms the review covered S0 only and names what was out of scope. |
| Integrity record | Archive SHA-256, commit/archive identity, environment, and commands run. |
| Test record | Full supplied-test result and any reviewer-created test or proof-of-concept result. |
| Finding list | One row per finding: ID, severity, title, affected files/versions, reproduction steps, observed result, expected result, and remediation advice. |
| Negative-test record | A1–A10 result for each attack: passed, failed, or not tested, with reason and evidence. |
| Decision | **Pass**, **conditional pass**, or **fail**, with a short explanation. |
| Limitations | Explicitly says that the review does not prove real-model effectiveness or real-tool security. |

## Pass / fail rule

| Decision | Meaning | What happens next |
|---|---|---|
| **Pass** | No unresolved Critical or High S0 finding; A1–A10 were tested or justified; evidence is reproducible. | S0 may be accepted. Plan S1 separately. |
| **Conditional pass** | No unresolved Critical/High finding, but one or more Medium/Low findings or missing evidence require tracked remediation. | Fix the listed items, then obtain a focused verification before S1. |
| **Fail** | Any unresolved Critical/High finding, an S0 acceptance test fails, or the audit package/evidence cannot be reproduced. | Freeze work. Remediate S0 only, then request a new independent review. |

A finding’s severity should reflect the realistic consequence. A flaw that lets arbitrary caller-controlled text gain principal authority, or lets decisions/receipts cross-bind between distinct segments, should normally be treated as **High** until the reviewer demonstrates a credible reason otherwise.

## Strict stop boundary

Do **not** start S1, live provider testing, real filesystem/network/Git execution, approval capability work, or AEON-IQ integration because this package exists. The only acceptable next action after the review is determined by the reviewer’s written pass/fail decision above.

## Suggested handoff folder

Place only the frozen archive and the following readable files into a share folder:

```text
AEON-S0-audit-handoff/
├── AEON_Context_Kernel_S0_v0.2.1.zip
├── SHA256SUMS.txt
├── REVIEW_REQUEST.md
├── docs/
│   ├── third_party_s0_audit_handoff.md
│   ├── s0_implementation_and_reaudit.md
│   ├── skill_governed_architecture_and_blind_study_blueprint.md
│   └── audit_to_validation_addendum.md
└── reviewer_return_template.md
```

The reviewer should work on a copy. The original archive and checksum should not change.
