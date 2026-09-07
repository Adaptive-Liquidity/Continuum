# AEON Context Kernel S0: Independent Audit Return Template

**Reviewer / organization:**

**Review date:**

**Review scope:** Confirm that this review covers S0 verifier-issued provenance and identity binding only. List anything excluded from the review.

## 1. Package integrity and environment

| Item | Reviewer entry |
|---|---|
| Archive name | `AEON_Context_Kernel_S0_v0.2.1.zip` |
| Archive SHA-256 observed | |
| Expected SHA-256 | Copy the archive entry from the attached `SHA256SUMS.txt` |
| Checksum matched | Yes / No |
| Operating system | |
| Python version | |
| `uv` version | |
| Lockfile/environment status | |
| Review commit or unpacked source identity | |

## 2. Commands and baseline results

List every command run, including exit status. Attach unedited console logs or provide a stable location for them.

| Command | Exit status | Result / log reference |
|---|---:|---|
| `uv sync --extra dev --locked` | | |
| `uv run pytest` | | |
| `uv run ruff format --check .` | | |
| `uv run ruff check .` | | |
| `uv run mypy src` | | |
| `python examples/basic_usage.py` | | |
| `cker demo` | | |
| Reviewer-created tests / proof of concept | | |

## 3. Required adversarial checks

For each check, record the exact test/proof-of-concept location or include the full command and output. “Not tested” requires a reason.

| ID | Result: Pass / Fail / Not tested | Evidence location | Notes |
|---|---|---|---|
| A1: raw caller asserts trusted/principal authority | | | |
| A2: forged or changed provenance | | | |
| A3: expired, wrong-scope, or revoked provenance | | | |
| A4: attestation replay in one admission session | | | |
| A5: post-verification content substitution | | | |
| A6: duplicate caller logical ID | | | |
| A7: duplicate/swapped verified UID or mismatched decision | | | |
| A8: missing, surplus, or duplicate decision during assembly | | | |
| A9: duplicate logical ID or verified UID in receipts | | | |
| A10: empty allowlist denies admission | | | |
| A11: supplied conformance/replay evidence | | | |

## 4. Findings

Create one subsection per finding. Include a finding even if it is fixed during the review; mark it as fixed and explain how it was verified.

### Finding ID: S0-XXX

| Field | Reviewer entry |
|---|---|
| Title | |
| Severity: Critical / High / Medium / Low / Informational | |
| Affected package/version/files | |
| Preconditions | |
| Exact reproduction steps | |
| Observed result | |
| Expected secure result | |
| Security impact | |
| Proof-of-concept/log/test attachment | |
| Recommended remediation | |
| Retest result, if remediated | |

## 5. Limitations and non-claims

State clearly whether the review did **not** assess each item below.

| Item | Assessed? | Statement |
|---|---|---|
| S1 trusted invariant registry and compaction residency | | |
| Real filesystem, network, Git, approval, or output effects | | |
| Provider/API integration | | |
| Real-model instruction following or prompt-injection resistance | | |
| Real-world tool protection | | |
| Long-context task effectiveness or efficiency | | |

## 6. Final decision

Select one result and give a short reason.

| Decision | Select | Reason |
|---|---|---|
| **Pass**: no unresolved Critical/High S0 issue and required evidence is reproducible | Yes / No | |
| **Conditional pass**: no unresolved Critical/High issue, but tracked remediation/evidence is required | Yes / No | |
| **Fail**: unresolved Critical/High issue, a required acceptance check fails, or evidence cannot be reproduced | Yes / No | |

## 7. What must happen next

State one of the following, or a more specific equivalent.

> **Pass:** S0 is acceptable for planning S1. This is not approval for provider integration, real effects, or claims of real-model effectiveness.

> **Conditional pass:** Complete the listed remediation and obtain focused independent verification before S1.

> **Fail:** Freeze development beyond S0. Fix only the listed S0 issues, then request a new independent review.
