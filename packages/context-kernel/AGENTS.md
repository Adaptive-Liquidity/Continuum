# AEON Context Kernel Agent Instructions

## Canonical state

The canonical repository is `https://github.com/Adaptive-Liquidity/aeon-context-kernel`. The v0.2.1 external S0 review returned a **Fail** summary with S0-001 (High: caller-influenced provenance lifecycle time) and S0-002 (Low: caller metadata could affect compaction residency). The v0.2.2 remediation was superseded after S0-003 showed its runner clock rejected valid fixture attestations. The current **v0.2.3 correction candidate** is not audit-cleared; independent focused re-audit is still pending. Do not describe S0 as passed or cleared.

Do **not** begin S1, provider integration, real effects, AEON-IQ integration, or real-model efficacy work until the independent S0 review has no unresolved Critical or High finding and required fixes are independently retested.

## Required change workflow

Never push directly to protected `main`. Create a focused branch and pull request. Keep changes narrow, document trust/version/evidence impact, and add behavior-focused positive and negative tests.

Repository-native **squash auto-merge** may be queued only after feedback is addressed. It completes only when all of the following gates pass:

| Gate | Requirement |
|---|---|
| Project CI | `Python 3.12 quality and deterministic smoke` succeeds on the current head. |
| Review conversations | Every actionable inline thread—human or automated—is fixed or given a documented disposition and resolved. |
| Branch state | The branch is current with protected `main`. |

CodeRabbit and Cursor Bugbot may add review feedback, but their service availability and reporting mode are not reliable status contexts; actionable findings must instead be handled as review conversations. Never dismiss a comment, resolve a thread without addressing it, weaken a required check, or bypass branch protection to force a merge. New commits restart the gates. Eligible Dependabot updates may be automatically queued for this same native path, but they do not receive a bypass or an automatic approval.

## Environment and quality gates

Install only from the committed lock:

```bash
uv sync --extra dev --locked
uv run ruff format --check src tests examples
uv run ruff check .
uv run mypy src
uv run pytest
uv run ckernel bench smoke --results-root .ci-results
```

The v0.2.3 lock requires pytest `>=9.0.3` to avoid `PYSEC-2026-1845`; do not reintroduce an affected version.

## Trust and implementation invariants

Authority comes from verifier-issued runtime provenance and policy, never from segment prose, metadata, logical IDs, submitted timestamps, or caller-selected lifecycle time. Admission must receive a trusted runtime clock; no method may fall back to `segment.created_at`. Simulator runners must initialize that clock from trusted harness state that is after the catalog fixture issuance window, never from an admitted segment. Preserve exact content/UID/trust bindings through admission, assembly, compaction, receipts, and replay. Missing, duplicate, surplus, or mismatched bindings must fail closed. S0 compaction protection is limited to verified-principal required instruction, constraint, and output-contract segments; metadata cannot add protection, and a trusted invariant registry remains S1 work. Enforcement must complete before any simulated state mutation. Required tests, demos, and benchmark stages remain simulator-only unless a later approved architecture gate explicitly says otherwise.

## Claim boundaries

Describe benchmark outputs as **deterministic conformance/regression evidence**, not real-model efficacy. Replay proves deterministic reconstruction of the simulator decision path; it does not prove model understanding, semantic compliance, artifact authenticity, production security, or prompt-injection immunity. Context-delivery receipts are runtime delivery and policy records, not compliance receipts.

## Evidence and release handling

Preserve historical artifacts and release targets; never rewrite them in place. Generated result trees belong in release assets or explicit audit directories, not ordinary source commits. Every release must bind its source commit, package version, CI state, limitations, and asset checksums. Security fixes must record the advisory, affected/fixed versions, focused tests, full gates, dependency-audit result, and whether runtime behavior changed.

Use the repository’s workflow snapshots under `docs/workflows/` for detailed kernel engineering, benchmark authoring, and reproducibility-audit procedures.
