# AEON Context Kernel S0: Audit Baseline Manifest

**Prepared:** 2026-08-17
**Purpose:** Bind the independent S0 review to specific release assets and record the current repository state that was independently rechecked before handoff.

## 1. Canonical identities

| Field | Value |
|---|---|
| Canonical repository | `https://github.com/Adaptive-Liquidity/aeon-context-kernel` |
| Frozen S0 audit candidate | GitHub prerelease `v0.2.1` |
| v0.2.1 annotated-tag target commit | `0cb036164bd75b1b8e32ce1f9c72ace8a72cfebe` |
| Current `main` at handoff preparation | `7ec671a9c765d9ff153b65ff25f58781594db8f6` |
| Current `main` verification date | 2026-08-17 |
| Independent third-party S0 audit | Pending |
| ECC bundle status | PR #8 closed without merge; excluded from audit scope |

## 2. Verified release assets

Download the release-level [`SHA256SUMS.txt`](https://github.com/Adaptive-Liquidity/aeon-context-kernel/releases/download/v0.2.1/SHA256SUMS.txt) alongside the selected release asset, then run `sha256sum -c SHA256SUMS.txt` from the download directory before unpacking or reviewing an archive.

| Asset | SHA-256 |
|---|---|
| `AEON-S0-audit-handoff-v0.2.1.zip` | `fe8c7a96a3a00cfc5ac48c01eef60e20ad100c309487df915211bfb1031c1230` |
| `AEON_Context_Kernel_S0_v0.2.1.zip` | `a1f17093e31aad023c8f8aed7b3be0d49eddc698f2b4af6691558ac6ed33be83` |
| `aeon_context_kernel-0.2.1-py3-none-any.whl` | `23b92b2657125c61a27c13cbd289cff156385bf16ee868dd681664aa89c3321a` |
| `aeon_context_kernel-0.2.1.tar.gz` | `e1dc8a6543f79820f1337a18c0831830248204df082e223fba93cec5e71b65d6` |

The authoritative download location is the [v0.2.1 release](https://github.com/Adaptive-Liquidity/aeon-context-kernel/releases/tag/v0.2.1). The checksums above verify content integrity against the supplied release manifest; they do not by themselves establish a protected external authenticity root. The repository intentionally stores this human-readable manifest rather than duplicating binary release assets or generated evidence in Git.

## 3. Current-main scope comparison

The following command was run against the tag target and current `main`:

```bash
git diff --name-only \
  0cb036164bd75b1b8e32ce1f9c72ace8a72cfebe \
  7ec671a9c765d9ff153b65ff25f58781594db8f6 \
  -- src/context_kernel src/survival_bench tests examples
```

**Observed result:** no changed path.

The post-tag files were limited to CI/workflow configuration, repository governance/instructions, one audit-documentation link repair, `pyproject.toml`, and `uv.lock`. This establishes a bounded maintenance difference for reviewer triage. The reviewer should repeat the comparison rather than relying on this statement.

## 4. Clean-clone verification observed at current main

| Check | Observed result |
|---|---|
| Open pull requests | `0` |
| Locked environment | `uv sync --extra dev --locked` passed |
| Formatting | Ruff format check passed |
| Lint | Ruff check passed |
| Static typing | Strict Mypy passed |
| Behavior suite | 122 tests passed |
| Simulator smoke | Four simulator-only smoke runs completed with `CKERNEL_LIVE_SMOKE=0` |
| Dependency audit | No known third-party-package vulnerabilities; the local unpublished package was skipped by the advisory database |
| Repository links/metadata | Validator passed |
| Main protection | Strict current-branch project CI and resolved review conversations required; admin enforcement and linear history enabled; force pushes and branch deletion blocked |

These are internal/reproducibility observations. They do not replace external adversarial security testing or demonstrate real-model efficacy.

## 5. ECC exclusion verification

PR #8 (`feat: add aeon-context-kernel ECC bundle`) was checked as `CLOSED` with no merge commit. The following paths were checked on current `main` and observed **absent**:

```text
.claude/ecc-tools.json
.codex/config.toml
.agents/skills/aeon-context-kernel/SKILL.md
```

The bundle added external MCP endpoints, `npx -y` unpinned packages, live web search, and workspace-write agent settings. It is deliberately outside S0 and must not be counted as audited or approved by an S0 decision.

## 6. Reviewer acknowledgement

Before beginning substantive testing, the reviewer should record:

- [ ] Release asset checksum verification result.
- [ ] Archive/tag/commit identity selected for review.
- [ ] Whether current-main comparison was repeated.
- [ ] Whether the ECC exclusion was reconfirmed.
- [ ] Any divergence from the stated scope or environment.
