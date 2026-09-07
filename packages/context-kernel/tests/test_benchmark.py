from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from context_kernel.cli import app
from context_kernel.provenance import fixed_verification_time
from context_kernel.receipts import read_trace_jsonl
from context_kernel.replay import ReplayEngine
from survival_bench.adapters import AdapterName, adapter_names, get_adapter
from survival_bench.harness import BenchmarkHarness, BenchmarkStage
from survival_bench.reporting import generate_report
from survival_bench.runner import ScenarioRunner
from survival_bench.scenarios import SCENARIOS, get_scenario, scenario_ids

EXPECTED_SCENARIOS = {
    "workspace_boundary",
    "protected_remote",
    "protected_branch",
    "destructive_operation",
    "network_egress",
    "approval_gate",
    "environment_isolation",
    "output_contract",
    "secret_handling",
    "change_scope",
    "test_before_action",
    "resource_budget",
}


def test_catalog_has_exact_required_scenarios_and_five_reproducible_seeds() -> None:
    assert len(SCENARIOS) == 12
    assert set(scenario_ids()) == EXPECTED_SCENARIOS

    for scenario in SCENARIOS:
        for seed in range(5):
            assert scenario.materialize(seed) == scenario.materialize(seed)


def test_all_four_adapters_expose_the_common_runtime_interface() -> None:
    assert adapter_names() == (
        "flat",
        "forced_compaction_baseline",
        "admission_only",
        "admission_plus_ledger",
    )
    variant = get_scenario("workspace_boundary").materialize(0)

    for adapter_name in adapter_names():
        adapter = get_adapter(adapter_name)
        admission = adapter.admit(
            variant.initial_segments,
            verification_clock=fixed_verification_time,
        )
        assembly = adapter.assemble(variant.initial_segments, admission.decisions)
        assert assembly.included_segment_ids
        assert adapter.predicate_set_hash


def test_typed_arms_keep_external_instruction_out_of_authoritative_region() -> None:
    variant = get_scenario("workspace_boundary").materialize(0)
    segments = (*variant.initial_segments, *variant.delayed_segments)

    verification_time = variant.runtime_start
    for adapter_name in (
        AdapterName.ADMISSION_ONLY,
        AdapterName.ADMISSION_PLUS_LEDGER,
    ):
        adapter = get_adapter(adapter_name)
        admission = adapter.admit(
            segments,
            verification_clock=lambda: verification_time,
        )
        assembly = adapter.assemble(segments, admission.decisions)
        external = next(
            entry for entry in assembly.entries if entry.segment_id.endswith(":adversarial")
        )
        assert external.authoritative is False
        assert external.region.value.startswith("D_external_untrusted")


@pytest.mark.parametrize("scenario_id", scenario_ids())
@pytest.mark.parametrize("adapter_name", adapter_names())
def test_every_scenario_runs_end_to_end_on_every_adapter(
    scenario_id: str, adapter_name: str
) -> None:
    artifact = ScenarioRunner().run(scenario_id, adapter_name, 0)

    assert artifact.metrics.scenario_id == scenario_id
    assert artifact.metrics.adapter_name == adapter_name
    assert artifact.receipt.run_id == artifact.trace.run_id == artifact.metrics.run_id
    assert artifact.receipt.trace_hash == artifact.trace.trace_hash
    assert artifact.receipt.decision_trace_hash == artifact.trace.decision_trace_hash
    assert artifact.receipt.actions
    assert artifact.receipt.compaction.planned_schedule
    assert artifact.metrics.false_block_count == 0
    if adapter_name == AdapterName.ADMISSION_PLUS_LEDGER:
        assert artifact.metrics.survived_without_violation is True


def test_runner_admits_initial_and_delayed_fixture_segments_at_trusted_runtime_start() -> None:
    scenario_id = "protected_remote"
    variant = get_scenario(scenario_id).materialize(0)
    assert variant.runtime_start > max(
        item.provenance.issued_at for item in (*variant.initial_segments, *variant.delayed_segments)
    )

    artifact = ScenarioRunner().run(scenario_id, AdapterName.ADMISSION_ONLY, 0)
    initial = next(event for event in artifact.trace.events if event.event_type == "admission")
    delayed = next(
        event for event in artifact.trace.events if event.event_type == "delayed_admission"
    )

    assert set(initial.payload["admitted_segment_ids"]) == {
        item.segment.id for item in variant.initial_segments
    }
    assert delayed.payload["admission"].admitted_segment_ids == (
        variant.delayed_segments[0].segment.id,
    )


def test_runner_reproduces_same_logical_trace_and_metrics() -> None:
    runner = ScenarioRunner()
    first = runner.run("protected_branch", AdapterName.ADMISSION_PLUS_LEDGER, 4)
    second = runner.run("protected_branch", AdapterName.ADMISSION_PLUS_LEDGER, 4)

    assert first.metrics == second.metrics
    assert first.trace.decision_trace_hash == second.trace.decision_trace_hash
    assert first.trace.trace_hash == second.trace.trace_hash


def test_full_reexecution_replay_matches_decision_trace(tmp_path: Path) -> None:
    runner = ScenarioRunner()
    artifact = runner.run(
        "approval_gate",
        AdapterName.ADMISSION_PLUS_LEDGER,
        3,
        output_directory=tmp_path,
    )
    path = tmp_path / "traces" / f"{artifact.metrics.run_id}.jsonl"
    document = read_trace_jsonl(path)

    report = ReplayEngine().verify(
        document,
        reproduce=runner.reproduce_trace,
        verified_at=artifact.trace.events[-1].timestamp,
    )

    assert report.verified is True
    assert report.reexecuted is True
    assert report.decision_trace_match is True


def test_smoke_harness_writes_four_runs_and_regenerates_report(tmp_path: Path) -> None:
    summary = BenchmarkHarness().run_stage(
        BenchmarkStage.SMOKE,
        results_root=tmp_path,
        experiment_id="smoke-test",
    )
    directory = Path(summary.output_directory)

    assert summary.manifest.planned_run_count == 4
    assert summary.manifest.completed_run_count == 4
    assert len(tuple((directory / "traces").glob("*.jsonl"))) == 4
    assert len(tuple((directory / "receipts").glob("*.jsonl"))) == 4
    report = generate_report(directory)
    for path in (
        report.summary_csv,
        report.summary_json,
        report.survival_points_csv,
        report.survival_points_json,
        report.chart_png,
        report.chart_svg,
        report.report_markdown,
    ):
        assert Path(path).is_file()
        assert Path(path).stat().st_size > 0


def test_demo_cli_shows_observe_warn_and_pre_effect_enforce() -> None:
    result = CliRunner().invoke(app, ["demo"])

    assert result.exit_code == 0
    records = json.loads(result.stdout)
    assert [record["mode"] for record in records] == ["observe", "warn", "enforce"]
    assert [record["effect_executed"] for record in records] == [True, True, False]


def test_benchmark_adapter_requires_runner_owned_verification_clock() -> None:
    variant = get_scenario("workspace_boundary").materialize(0)

    with pytest.raises(TypeError, match="verification_clock"):
        get_adapter(AdapterName.ADMISSION_ONLY).admit(  # type: ignore[call-arg]
            variant.initial_segments
        )
