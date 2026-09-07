# AEON Verification Gate Matrix

Select the smallest gate set that answers the user's question, then escalate sequentially.

## Gate levels

| Level | Purpose | Required checks | Typical use |
|---|---|---|---|
| Focused | Prove one changed behavior | Narrow pytest node or file; deterministic repeat if relevant | During implementation |
| Core | Validate source quality | Full pytest, Ruff, mypy | Pull request or handoff |
| Smoke | Validate end-to-end artifact path | Four-arm smoke, passive audit, four replays, report regeneration | Any cross-cutting change |
| Pilot | Validate every scenario once | 48-run pilot, passive audit, 48 replays, report regeneration | Predicate/scenario/adapter changes |
| Full | Validate complete reference matrix | 240-run full, passive audit, 240 replays, report regeneration | Release or reference evidence |

Run levels in order. Do not continue after an unexplained failure.

## Environment and source gates

From the repository root:

```bash
uv sync --extra dev
uv run ruff format --check src tests examples
uv run pytest --cov=context_kernel --cov=survival_bench --cov-report=term
uv run ruff check .
uv run mypy src
uv run python examples/basic_usage.py
uv run ckernel demo
```

If the project intentionally does not enforce formatting, record the formatting check as not applicable rather than silently omitting it. Treat coverage as diagnostic unless a threshold is configured.

## Staged benchmark commands

```bash
uv run ckernel bench smoke --results-root results
uv run ckernel bench pilot --results-root results
uv run ckernel bench full --results-root results
```

Current reference sizes are:

| Stage | Scenarios | Arms | Seeds | Expected runs |
|---|---:|---:|---:|---:|
| Smoke | 1 | 4 | 1 | 4 |
| Pilot | 12 | 4 | 1 | 48 |
| Full | 12 | 4 | 5 | 240 |

If the catalog, arm set, or seed set intentionally changes, derive expected counts from the new documented matrix and record the difference. Do not force old counts onto a versioned new design.

## Passive artifact audit

Run after every benchmark stage:

```bash
python3 /home/ubuntu/skills/aeon-context-reproducibility-audit/scripts/audit_artifacts.py \
  --results-directory results/context-survival-smoke-v1 \
  --expected-runs 4 \
  --output audit/smoke-artifact-audit.json \
  --pretty
```

Repeat with expected counts 48 and 240 for the current pilot and full stages. A successful script exit proves passive structural checks only.

## Full replay sweep

Replay sorted trace paths using the project CLI:

```bash
for trace in results/context-survival-smoke-v1/traces/*.jsonl; do
  uv run ckernel replay "$trace" >/dev/null || exit 1
done
```

Run equivalent sweeps for pilot and full. Capture a machine-readable failure list when preparing formal evidence. Do not suppress stderr in diagnostic runs.

## Report regeneration

Copy the result directory before regeneration when auditing supplied evidence:

```bash
cp -a results/context-survival-full-v1 audit/context-survival-full-v1-regenerated
uv run ckernel bench report audit/context-survival-full-v1-regenerated
```

Compare these logical artifacts first:

1. `summary.json`
2. `survival_points.json`
3. `summary.csv`
4. `survival_points.csv`
5. `report.md`
6. `survival_curves.svg`
7. `survival_curves.png` by visual/data consistency rather than bytes alone

## Expected top-level stage artifacts

A complete stage directory normally contains:

| Artifact | Purpose |
|---|---|
| `manifest.json` | Stage identity, matrix, versions, and run count |
| `run_index.jsonl` | One index record per run |
| `metrics.json` | Aggregate list of per-run metrics |
| `metrics.jsonl` | One metric record per line |
| `metrics.csv` | Tabular metric export |
| `receipts/` | One context-delivery receipt per run |
| `traces/` | One event-chain trace per run |
| `run_metrics/` | One canonical per-run metric file per run |
| `summary.json`, `summary.csv` | Arm-level summary |
| `survival_points.json`, `.csv` | Auditable survival-curve source data |
| `survival_curves.png`, `.svg` | Rendered figures |
| `report.md` | Human-readable generated report |

Treat project-specific optional files as optional, but record them.

## Pass criteria

A stage passes only when:

- the benchmark command exits zero;
- expected run counts reconcile across manifest, index, metrics, receipts, traces, and per-run metrics;
- every trace passes passive structural validation;
- every trace passes full logical replay;
- generated summaries derive from saved metrics and regenerate consistently;
- no unexplained version or hash difference remains;
- claims remain within deterministic simulator boundaries.
