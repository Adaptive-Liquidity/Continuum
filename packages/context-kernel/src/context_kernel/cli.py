"""Command-line interface for the context kernel and survival bench."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer

from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.canonical import canonical_json
from context_kernel.interception import SafeActionInterceptor
from context_kernel.ledger import (
    Action,
    ActionType,
    EnforcementMode,
    InvariantLedger,
    PredicateContext,
    PredicateRegistration,
)
from context_kernel.predicates import FilesystemScopePredicate
from context_kernel.receipts import read_trace_jsonl
from context_kernel.replay import ReplayEngine
from survival_bench.adapters import adapter_names
from survival_bench.harness import BenchmarkHarness, BenchmarkStage
from survival_bench.reporting import generate_report
from survival_bench.runner import ScenarioRunner
from survival_bench.scenarios import scenario_ids

app = typer.Typer(
    name="ckernel",
    no_args_is_help=True,
    help="AEON Context Kernel and deterministic Context Survival Bench.",
)
bench_app = typer.Typer(no_args_is_help=True, help="Run staged deterministic benchmarks.")
app.add_typer(bench_app, name="bench")


@app.command()
def demo() -> None:
    """Demonstrate observe, warn, and enforce using a simulated filesystem effect."""
    records = []
    for index, mode in enumerate(EnforcementMode, start=1):
        adapter = SimulatedEffectAdapter()
        ledger = InvariantLedger(
            [
                PredicateRegistration(
                    predicate=FilesystemScopePredicate(),
                    mode=mode,
                )
            ]
        )
        action = Action(
            id=f"demo-{mode.value}",
            action_type=ActionType.FILESYSTEM_WRITE,
            parameters={"path": "/outside/demo.txt", "content": "simulated"},
            attempted_at=datetime(2026, 1, 1, 0, 0, index, tzinfo=UTC),
        )
        record = SafeActionInterceptor(ledger, adapter).attempt(
            action,
            PredicateContext(workspace_root="/workspace"),
            evaluated_at=action.attempted_at,
        )
        records.append(
            {
                "mode": mode,
                "outcome": record.outcome,
                "effect_executed": record.effect_executed,
                "simulated_effect_count": len(adapter.state.effect_log),
                "violation_detected": record.evaluations[0].violation_detected,
            }
        )
    typer.echo(canonical_json(records))


@app.command("run-scenario")
def run_scenario(
    scenario_id: str = typer.Argument(help="Scenario identifier."),
    adapter: str = typer.Option(
        "admission_plus_ledger",
        "--adapter",
        help="Benchmark adapter name.",
    ),
    seed: int = typer.Option(0, "--seed", help="Deterministic integer seed."),
    output_directory: Path = typer.Option(
        Path("results/single"),
        "--output-directory",
        help="Directory for receipt, trace, and metric artifacts.",
    ),
) -> None:
    """Run one deterministic scenario and persist its complete artifacts."""
    if scenario_id not in scenario_ids():
        raise typer.BadParameter(f"unknown scenario; choose one of: {', '.join(scenario_ids())}")
    if adapter not in adapter_names():
        raise typer.BadParameter(f"unknown adapter; choose one of: {', '.join(adapter_names())}")
    artifact = ScenarioRunner().run(
        scenario_id,
        adapter,
        seed,
        output_directory=output_directory,
    )
    typer.echo(
        canonical_json(
            {
                "metrics": artifact.metrics,
                "receipt": (output_directory / "receipts" / f"{artifact.metrics.run_id}.jsonl"),
                "trace": (output_directory / "traces" / f"{artifact.metrics.run_id}.jsonl"),
            }
        )
    )


@app.command()
def replay(trace: Path = typer.Argument(help="Path to a stored trace JSONL file.")) -> None:
    """Re-execute a deterministic simulator run and verify its decision-trace hash."""
    document = read_trace_jsonl(trace)
    report = ReplayEngine().verify(
        document,
        reproduce=ScenarioRunner().reproduce_trace,
        verified_at=datetime.now(UTC),
    )
    typer.echo(canonical_json(report))
    if not report.verified:
        raise typer.Exit(code=1)


def _run_benchmark(stage: BenchmarkStage, results_root: Path) -> None:
    summary = BenchmarkHarness().run_stage(stage, results_root=results_root)
    report = generate_report(Path(summary.output_directory))
    typer.echo(
        canonical_json(
            {
                "manifest": summary.manifest,
                "output_directory": summary.output_directory,
                "report": report,
            }
        )
    )


@bench_app.command("smoke")
def bench_smoke(results_root: Path = typer.Option(Path("results"), "--results-root")) -> None:
    """Run one scenario across four adapters using one seed."""
    _run_benchmark(BenchmarkStage.SMOKE, results_root)


@bench_app.command("pilot")
def bench_pilot(results_root: Path = typer.Option(Path("results"), "--results-root")) -> None:
    """Run all twelve scenarios across four adapters using one seed."""
    _run_benchmark(BenchmarkStage.PILOT, results_root)


@bench_app.command("full")
def bench_full(results_root: Path = typer.Option(Path("results"), "--results-root")) -> None:
    """Run all twelve scenarios across four adapters using five seeds."""
    _run_benchmark(BenchmarkStage.FULL, results_root)


@bench_app.command("report")
def bench_report(
    results_directory: Path = typer.Argument(help="Versioned benchmark results directory."),
) -> None:
    """Regenerate all benchmark figures and summary tables from saved metrics."""
    typer.echo(canonical_json(generate_report(results_directory)))
