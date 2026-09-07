# AEON Reproducibility Audit

**Author:** Manus AI
**Audit date:** YYYY-MM-DD
**Repository or artifact source:**
**Source revision:**
**Project version:**
**Python version:**
**Results directory:**

## Executive summary

State in one paragraph whether source gates, artifact completeness, structural trace integrity, logical replay, and report regeneration were verified. Name the highest-severity failure and the principal limitation. Do not claim model understanding, compliance, or production-provider performance.

## Scope and preservation

Describe what was supplied, what was copied or hashed before inspection, and which operations were passive versus write-capable. Confirm whether report regeneration used a duplicate directory.

| Evidence item | Original path | Preserved hash or copy | Notes |
|---|---|---|---|
| Repository | | | |
| Result directory | | | |
| Audit output | | | |
| Regenerated report copy | | | |

## Environment and identities

| Field | Observed value |
|---|---|
| Project/package version | |
| Scenario version(s) | |
| Adapter version(s) | |
| Harness version | |
| Simulator or model ID | |
| Predicate-set hash(es) | |
| Scaffold-template hash(es) | |
| Stage and expected matrix | |

## Verification results

Use only **Verified**, **Failed**, **Not run**, or **Not applicable**.

| Check | Status | Evidence |
|---|---|---|
| Environment synchronization | | |
| Focused tests | | |
| Full pytest | | |
| Ruff format check | | |
| Ruff lint | | |
| Mypy | | |
| Example and demo | | |
| Benchmark stage command | | |
| Artifact count reconciliation | | |
| Receipt parsing and reconciliation | | |
| Trace structural integrity | | |
| Full logical replay | | |
| Summary regeneration | | |
| Survival-point regeneration | | |
| Figure/data consistency | | |

## Artifact reconciliation

| Collection | Expected | Observed | Unique run IDs | Missing or extra IDs |
|---|---:|---:|---:|---|
| Manifest | | | | |
| Run index | | | | |
| Aggregate metrics | | | | |
| Metrics JSONL | | | | |
| Receipts | | | | |
| Traces | | | | |
| Per-run metrics | | | | |

## Trace and replay findings

Report the number structurally valid, structurally invalid, replay verified, and replay failed. List each failed run ID and the first concrete error.

| Run ID | Structural integrity | Replay | Expected hash | Actual hash | Error |
|---|---|---|---|---|---|
| | | | | | |

## Report-regeneration findings

| Artifact | Logical comparison | Notes |
|---|---|---|
| `summary.json` | | |
| `survival_points.json` | | |
| `summary.csv` | | |
| `survival_points.csv` | | |
| `report.md` | | |
| `survival_curves.svg` | | |
| `survival_curves.png` | | |

## Findings and severity

Describe each finding as an observed condition, its evidence, impact, and safe next action. Separate structural corruption, logical divergence, environment problems, reporting drift, and versioning defects.

| Severity | Finding | Evidence | Impact | Next action |
|---|---|---|---|---|
| | | | | |

## Limitations

State unrun checks, unavailable source or environment data, optional files, renderer variability, and simulator interpretation boundaries.

## Conclusion

Give a concise disposition: verified for the stated scope, failed, or partially verified. Name any condition required before stronger claims can be made.

## Command log

```text
Command:
Exit status:
Key output:
```
