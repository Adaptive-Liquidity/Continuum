"""Static reporting for versioned deterministic benchmark results."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pydantic import BaseModel, ConfigDict

from context_kernel.canonical import canonical_json
from survival_bench.adapters import AdapterName
from survival_bench.metrics import RunMetrics


class ReportArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    results_directory: str
    summary_csv: str
    summary_json: str
    survival_points_csv: str
    survival_points_json: str
    chart_png: str
    chart_svg: str
    report_markdown: str


_COLORS = {
    AdapterName.FLAT.value: "#7A7A7A",
    AdapterName.FORCED_COMPACTION_BASELINE.value: "#C44E52",
    AdapterName.ADMISSION_ONLY.value: "#4C72B0",
    AdapterName.ADMISSION_PLUS_LEDGER.value: "#2A7F62",
}

_LABELS = {
    AdapterName.FLAT.value: "Flat",
    AdapterName.FORCED_COMPACTION_BASELINE.value: "Forced compaction baseline",
    AdapterName.ADMISSION_ONLY.value: "Admission only",
    AdapterName.ADMISSION_PLUS_LEDGER.value: "Admission + ledger",
}


def load_metrics(directory: Path) -> tuple[RunMetrics, ...]:
    data = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    return tuple(RunMetrics.model_validate(item) for item in data)


def kaplan_meier_points(metrics: tuple[RunMetrics, ...]) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[RunMetrics]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.adapter_name].append(metric)
    points: list[dict[str, Any]] = []
    for adapter_name in sorted(grouped):
        group = grouped[adapter_name]
        survival = 1.0
        points.append(
            {
                "adapter_name": adapter_name,
                "turn": 0,
                "at_risk": len(group),
                "violations": 0,
                "censored": 0,
                "survival_probability": 1.0,
            }
        )
        for turn in sorted({item.survival_time_turns for item in group}):
            at_risk = sum(item.survival_time_turns >= turn for item in group)
            violations = sum(
                item.survival_time_turns == turn and not item.right_censored for item in group
            )
            censored = sum(
                item.survival_time_turns == turn and item.right_censored for item in group
            )
            if at_risk and violations:
                survival *= 1.0 - violations / at_risk
            points.append(
                {
                    "adapter_name": adapter_name,
                    "turn": turn,
                    "at_risk": at_risk,
                    "violations": violations,
                    "censored": censored,
                    "survival_probability": round(survival, 8),
                }
            )
    return tuple(points)


def summarize(metrics: tuple[RunMetrics, ...]) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, list[RunMetrics]] = defaultdict(list)
    for metric in metrics:
        grouped[metric.adapter_name].append(metric)
    rows: list[dict[str, Any]] = []
    for adapter_name in sorted(grouped):
        group = grouped[adapter_name]
        survived = sum(item.survived_without_violation for item in group)
        violations = len(group) - survived
        violation_turns = [
            item.turn_to_first_violation
            for item in group
            if item.turn_to_first_violation is not None
        ]
        rows.append(
            {
                "adapter_name": adapter_name,
                "runs": len(group),
                "survived_without_violation": survived,
                "violations": violations,
                "survival_rate": round(survived / len(group), 6),
                "mean_violation_turn_if_observed": (
                    round(mean(violation_turns), 3) if violation_turns else None
                ),
                "right_censored": sum(item.right_censored for item in group),
                "allowed_actions": sum(item.allowed_action_count for item in group),
                "warned_actions": sum(item.warned_action_count for item in group),
                "blocked_actions": sum(item.blocked_action_count for item in group),
                "false_blocks": sum(item.false_block_count for item in group),
                "mean_kernel_latency_ms": round(mean(item.kernel_latency_ms for item in group), 3),
                "mean_simulator_latency_ms": round(
                    mean(item.simulator_or_model_latency_ms for item in group), 3
                ),
            }
        )
    return tuple(rows)


def generate_report(directory: Path) -> ReportArtifacts:
    metrics = load_metrics(directory)
    if not metrics:
        raise ValueError("results directory contains no metrics")
    points = kaplan_meier_points(metrics)
    summary = summarize(metrics)

    summary_json_path = directory / "summary.json"
    summary_csv_path = directory / "summary.csv"
    points_json_path = directory / "survival_points.json"
    points_csv_path = directory / "survival_points.csv"
    png_path = directory / "survival_curves.png"
    svg_path = directory / "survival_curves.svg"
    markdown_path = directory / "report.md"

    summary_json_path.write_text(canonical_json(summary) + "\n", encoding="utf-8")
    points_json_path.write_text(canonical_json(points) + "\n", encoding="utf-8")
    _write_csv(summary_csv_path, summary)
    _write_csv(points_csv_path, points)
    _plot_survival(points, png_path, svg_path)
    markdown_path.write_text(_markdown_report(summary), encoding="utf-8")

    return ReportArtifacts(
        results_directory=directory.as_posix(),
        summary_csv=summary_csv_path.as_posix(),
        summary_json=summary_json_path.as_posix(),
        survival_points_csv=points_csv_path.as_posix(),
        survival_points_json=points_json_path.as_posix(),
        chart_png=png_path.as_posix(),
        chart_svg=svg_path.as_posix(),
        report_markdown=markdown_path.as_posix(),
    )


def _write_csv(path: Path, rows: tuple[dict[str, Any], ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _plot_survival(points: tuple[dict[str, Any], ...], png_path: Path, svg_path: Path) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        grouped[str(point["adapter_name"])].append(point)

    plt.style.use("seaborn-v0_8-whitegrid")
    figure, axis = plt.subplots(figsize=(10.5, 6.5))
    figure.subplots_adjust(left=0.11, right=0.98, bottom=0.12, top=0.82)
    for adapter_name in AdapterName:
        rows = sorted(grouped.get(adapter_name.value, []), key=lambda row: row["turn"])
        if not rows:
            continue
        x_values = [int(row["turn"]) for row in rows]
        y_values = [float(row["survival_probability"]) for row in rows]
        color = _COLORS[adapter_name.value]
        axis.step(
            x_values,
            y_values,
            where="post",
            linewidth=2.4,
            color=color,
            label=_LABELS[adapter_name.value],
        )
        for row in rows:
            if int(row["censored"]) > 0:
                axis.scatter(
                    [int(row["turn"])],
                    [float(row["survival_probability"])],
                    marker="|",
                    s=130,
                    linewidths=2,
                    color=color,
                    zorder=4,
                )

    figure.suptitle(
        "Deterministic Context-Kernel Conformance",
        x=0.11,
        y=0.95,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    figure.text(
        0.11,
        0.90,
        "Local simulator conformance/regression outputs; ticks mark right-censored fixtures",
        ha="left",
        fontsize=9.5,
        color="#555555",
    )
    axis.set_xlabel("Turn")
    axis.set_ylabel("Probability of no scheduled fixture violation")
    axis.set_ylim(-0.02, 1.04)
    axis.set_xlim(left=0)
    axis.legend(frameon=True, loc="lower left")
    axis.spines[["top", "right"]].set_visible(False)
    figure.savefig(png_path, dpi=220, facecolor="white")
    figure.savefig(svg_path, facecolor="white")
    plt.close(figure)


def _markdown_report(summary: tuple[dict[str, Any], ...]) -> str:
    header = (
        "# Context-Kernel Deterministic Conformance Report\n\n"
        "> These are deterministic local simulator conformance/regression outputs. They do not "
        "measure real-model safety, usefulness, or provider superiority.\n\n"
        "| Adapter | Runs | Survived | Violations | Survival rate | False blocks |\n"
        "|---|---:|---:|---:|---:|---:|\n"
    )
    rows = "".join(
        "| {adapter_name} | {runs} | {survived_without_violation} | {violations} | "
        "{survival_rate:.1%} | {false_blocks} |\n".format(**row)
        for row in summary
    )
    return (
        header
        + rows
        + "\nThe conformance chart uses deterministic predicate outcomes only; no LLM-as-judge "
        "scoring or model behavior is measured. Right-censored fixtures completed without an "
        "observed scheduled violation through their final turn.\n"
    )
