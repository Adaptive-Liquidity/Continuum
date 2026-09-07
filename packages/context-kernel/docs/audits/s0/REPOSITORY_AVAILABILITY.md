# AEON S0 Audit Handoff: Repository Availability Report

**Question:** Is the comprehensive S0 audit handoff entirely in the GitHub repository?

**Answer:** **Not entirely.** The repository contains the source, tests, governance, core audit documentation, and the comprehensive phase-by-phase audit plan. The frozen archives, release checksum file, and generated evidence remain release assets rather than committed repository files.

## Availability by material

| Material | Current location | Committed in repository? | Notes |
|---|---|---:|---|
| S0 source code, tests, `pyproject.toml`, and `uv.lock` | Current `main` | **Yes** | The canonical review source is current `main` commit `7ec671a9c765d9ff153b65ff25f58781594db8f6`. |
| Original third-party audit brief | `docs/third_party_s0_audit_handoff.md` | **Yes** | The concise reviewer request and A1–A10 checks are committed. |
| Original return template | `docs/third_party_s0_audit_return_template.md` | **Yes** | The original independent-review template is committed. |
| S0 implementation/re-audit record | `docs/s0_implementation_and_reaudit.md` | **Yes** | Includes the internal deterministic/replay claims and stop boundary. |
| S0 change plan | `docs/change-plans/s0_identity_and_provenance.md` | **Yes** | States intended invariants, non-goals, and test matrix. |
| Blueprint and audit crosswalk | `docs/skill_governed_architecture_and_blind_study_blueprint.md`, `docs/audit_to_validation_addendum.md` | **Yes** | These distinguish S0 from deferred S1/S2 and real-model work. |
| Governance and persistent agent guidance | `AGENTS.md`, `GOVERNANCE.md`, `SECURITY.md`, `ROADMAP.md` | **Yes** | Includes protected-PR and audit-gate policy. |
| Frozen S0 source/evidence archive | `AEON_Context_Kernel_S0_v0.2.1.zip` on the v0.2.1 release | **No** | Published as a release asset, not committed as a repository file. |
| Original reviewer handoff archive | `AEON-S0-audit-handoff-v0.2.1.zip` on the v0.2.1 release | **No** | Published as a release asset, not committed as a repository file. |
| SHA-256 release manifest | `SHA256SUMS.txt` on the v0.2.1 release | **No** | Published as a release asset; used to verify release downloads. |
| Python wheel and source distribution | v0.2.1 release assets | **No** | Published assets, not source-controlled binaries. |
| Generated smoke/pilot/full result directories, receipt/traces, charts, replay logs | Included in the frozen release evidence archive | **No** | Deliberately excluded from Git source control to keep the repository lean. They are evidence artifacts, not source inputs. |
| Comprehensive phase-by-phase plan | `docs/audits/s0/README.md` | **Yes** | Repository-native entry point for the independent S0 review. |
| Enhanced reviewer return template | `docs/audits/s0/REVIEWER_RETURN_TEMPLATE.md` | **Yes** | Required structure for the external reviewer’s evidence-return report. |
| Audit baseline manifest | `docs/audits/s0/AUDIT_BASELINE_MANIFEST.md` | **Yes** | Records current-main commit, post-tag scope comparison, ECC exclusion, and final clean-clone verification. |
| Availability report | `docs/audits/s0/REPOSITORY_AVAILABILITY.md` | **Yes** | Explains why release assets and generated evidence remain outside Git source control. |
| Outer comprehensive ZIP and its checksum | Local comprehensive handoff package | **No** | Optional convenience bundle; the repository and v0.2.1 release provide the canonical materials. |

## Practical consequence

An external reviewer can obtain the **core audit source and documentation** by cloning the repository and obtain the **frozen evidence and checksums** from the [v0.2.1 release](https://github.com/Adaptive-Liquidity/aeon-context-kernel/releases/tag/v0.2.1).

The repository now provides the permanent, canonical non-binary audit entry point under `docs/audits/s0/`. The v0.2.1 release provides the checksummed frozen archive and generated evidence. This intentional split lets an auditor start from the repository while avoiding duplicated binary artifacts and generated result trees in Git.

> This report describes availability only. It does not change the S0 stop gate: independent review remains required before S1, provider work, real effects, AEON-IQ, or real-model testing.
