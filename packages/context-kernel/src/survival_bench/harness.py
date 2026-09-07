"""Staged deterministic benchmark harness."""

from __future__ import annotations

import csv
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from context_kernel.canonical import canonical_hash, canonical_json
from survival_bench.adapters import adapter_names
from survival_bench.metrics import RunMetrics
from survival_bench.runner import HARNESS_VERSION, ScenarioRunner
from survival_bench.scenarios import SCENARIOS


class BenchmarkStage(StrEnum):
    SMOKE = "smoke"
    PILOT = "pilot"
    FULL = "full"


class BenchmarkManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: str
    stage: BenchmarkStage
    harness_version: str
    deterministic_simulator_only: bool = True
    scenario_ids: tuple[str, ...]
    adapter_names: tuple[str, ...]
    seeds: tuple[int, ...]
    planned_run_count: int = Field(ge=1)
    completed_run_count: int = Field(ge=0)
    matrix_hash: str


class BenchmarkRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_directory: str
    manifest: BenchmarkManifest
    metrics: tuple[RunMetrics, ...]


class BenchmarkHarness:
    def __init__(self, runner: ScenarioRunner | None = None) -> None:
        self.runner = runner or ScenarioRunner()

    def run_stage(
        self,
        stage: str | BenchmarkStage,
        *,
        results_root: Path = Path("results"),
        experiment_id: str | None = None,
    ) -> BenchmarkRunSummary:
        parsed = BenchmarkStage(stage)
        scenario_ids, seeds = self._matrix(parsed)
        adapters = adapter_names()
        cells: list[tuple[str, str, int]] = [
            (scenario_id, adapter, seed)
            for scenario_id in scenario_ids
            for adapter in adapters
            for seed in seeds
        ]
        matrix = [
            {"scenario_id": scenario_id, "adapter_name": adapter, "seed": seed}
            for scenario_id, adapter, seed in cells
        ]
        experiment = experiment_id or f"context-survival-{parsed.value}-v1"
        output_directory = results_root / experiment
        metrics: list[RunMetrics] = []
        index_records: list[dict[str, Any]] = []

        for scenario_id, adapter_name, seed in cells:
            artifact = self.runner.run(
                scenario_id,
                adapter_name,
                seed,
                output_directory=output_directory,
            )
            metrics.append(artifact.metrics)
            index_records.append(
                {
                    "scenario_id": scenario_id,
                    "adapter_name": adapter_name,
                    "seed": seed,
                    "run_id": artifact.metrics.run_id,
                    "trace_hash": artifact.trace.trace_hash,
                    "decision_trace_hash": artifact.trace.decision_trace_hash,
                    "trace_path": f"traces/{artifact.metrics.run_id}.jsonl",
                    "receipt_path": f"receipts/{artifact.metrics.run_id}.jsonl",
                }
            )

        manifest = BenchmarkManifest(
            experiment_id=experiment,
            stage=parsed,
            harness_version=HARNESS_VERSION,
            scenario_ids=scenario_ids,
            adapter_names=adapters,
            seeds=seeds,
            planned_run_count=len(cells),
            completed_run_count=len(metrics),
            matrix_hash=canonical_hash(matrix),
        )
        self._write_aggregate_files(
            output_directory,
            manifest,
            tuple(metrics),
            tuple(index_records),
        )
        return BenchmarkRunSummary(
            output_directory=output_directory.as_posix(),
            manifest=manifest,
            metrics=tuple(metrics),
        )

    @staticmethod
    def _matrix(stage: BenchmarkStage) -> tuple[tuple[str, ...], tuple[int, ...]]:
        if stage is BenchmarkStage.SMOKE:
            return (SCENARIOS[0].scenario_id,), (0,)
        if stage is BenchmarkStage.PILOT:
            return tuple(scenario.scenario_id for scenario in SCENARIOS), (0,)
        return tuple(scenario.scenario_id for scenario in SCENARIOS), tuple(range(5))

    @staticmethod
    def _write_aggregate_files(
        directory: Path,
        manifest: BenchmarkManifest,
        metrics: tuple[RunMetrics, ...],
        index_records: tuple[dict[str, Any], ...],
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
        (directory / "run_index.jsonl").write_text(
            "".join(canonical_json(record) + "\n" for record in index_records),
            encoding="utf-8",
        )
        (directory / "metrics.json").write_text(
            canonical_json([metric.model_dump(mode="python") for metric in metrics]) + "\n",
            encoding="utf-8",
        )
        (directory / "metrics.jsonl").write_text(
            "".join(canonical_json(metric) + "\n" for metric in metrics),
            encoding="utf-8",
        )
        if metrics:
            with (directory / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=list(metrics[0].model_dump(mode="json").keys()),
                )
                writer.writeheader()
                for metric in metrics:
                    writer.writerow(metric.model_dump(mode="json"))
