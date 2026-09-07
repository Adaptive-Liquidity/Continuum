from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from conftest import FIXED_TIME, make_action, make_policy, make_segment
from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.assembly import ContextAssembler
from context_kernel.canonical import canonical_hash
from context_kernel.determinism import ControlledClock, stable_run_id
from context_kernel.interception import SafeActionInterceptor
from context_kernel.ledger import (
    EnforcementMode,
    InvariantLedger,
    PredicateContext,
    PredicateRegistration,
)
from context_kernel.predicates import FilesystemScopePredicate
from context_kernel.receipts import (
    ActionReceipt,
    CompactionReceipt,
    ContextDeliveryReceipt,
    OutcomeReceipt,
    PerformanceReceipt,
    SegmentDeliveryRecord,
    TraceRecorder,
    read_receipt_jsonl,
    read_trace_jsonl,
    write_receipt_jsonl,
    write_trace_jsonl,
)
from context_kernel.replay import ReplayEngine


def make_trace(*, start: datetime = FIXED_TIME, changed: bool = False):
    clock = ControlledClock(current=start)
    recorder = TraceRecorder("run-test")
    recorder.append(
        "run_started",
        {"scenario_id": "workspace_boundary", "seed": 7},
        timestamp=clock.now(),
    )
    recorder.append(
        "admission",
        {
            "segment_id": "principal",
            "decision": "rejected" if changed else "admitted_eager",
            "timestamp": clock.now(),
        },
        timestamp=clock.now(),
    )
    recorder.append(
        "outcome",
        {"completion_status": "completed", "right_censored": True},
        timestamp=clock.now(),
    )
    return recorder.document()


def test_controlled_clock_and_run_id_are_reproducible() -> None:
    left = ControlledClock()
    right = ControlledClock()

    assert [left.now(), left.now(), left.now()] == [
        right.now(),
        right.now(),
        right.now(),
    ]
    arguments = {
        "scenario_id": "workspace_boundary",
        "scenario_version": "1.0.0",
        "adapter_name": "admission_plus_ledger",
        "adapter_version": "1.0.0",
        "seed": 3,
    }
    assert stable_run_id(**arguments) == stable_run_id(**arguments)


def test_decision_trace_hash_ignores_incidental_timestamps() -> None:
    earlier = make_trace(start=FIXED_TIME)
    later = make_trace(start=FIXED_TIME + timedelta(days=30))

    assert earlier.trace_hash != later.trace_hash
    assert earlier.decision_trace_hash == later.decision_trace_hash


def test_successful_replay_accepts_same_logical_decisions_with_new_timestamps(
    tmp_path,
) -> None:
    stored = make_trace(start=FIXED_TIME)
    path = tmp_path / "trace.jsonl"
    write_trace_jsonl(path, stored)
    loaded = read_trace_jsonl(path)

    report = ReplayEngine().verify(
        loaded,
        reproduce=lambda _: make_trace(start=FIXED_TIME + timedelta(days=1)),
        verified_at=FIXED_TIME,
    )

    assert report.verified is True
    assert report.structural_integrity is True
    assert report.reexecuted is True
    assert report.decision_trace_match is True


def test_replay_detects_tampered_event_without_updated_hash(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    write_trace_jsonl(path, make_trace())
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[1]["payload"]["decision"] = "tampered"
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n")

    report = ReplayEngine().verify_path(path, verified_at=FIXED_TIME)

    assert report.verified is False
    assert report.structural_integrity is False
    assert any("event hash mismatch" in error for error in report.errors)


def test_replay_detects_valid_but_different_reexecuted_decision_trace() -> None:
    report = ReplayEngine().verify(
        make_trace(),
        reproduce=lambda _: make_trace(changed=True),
        verified_at=FIXED_TIME,
    )

    assert report.structural_integrity is True
    assert report.reexecuted is True
    assert report.decision_trace_match is False
    assert report.verified is False


def test_receipt_contains_required_fields_and_round_trips_as_canonical_jsonl(
    tmp_path,
) -> None:
    segment = make_segment("principal", "Remain inside the workspace.")
    decision = make_policy().admit(segment)
    assembly = ContextAssembler().assemble((segment,), (decision,))
    ledger = InvariantLedger(
        [
            PredicateRegistration(
                predicate=FilesystemScopePredicate(),
                mode=EnforcementMode.ENFORCE,
            )
        ]
    )
    action = make_action(parameters={"path": "/workspace/result.txt", "content": "ok"})
    interception = SafeActionInterceptor(ledger, SimulatedEffectAdapter()).attempt(
        action, PredicateContext(), evaluated_at=FIXED_TIME
    )
    recorder = TraceRecorder("run-receipt")
    recorder.append("admission", decision, timestamp=FIXED_TIME)
    recorder.append("assembly", assembly, timestamp=FIXED_TIME + timedelta(milliseconds=1))
    recorder.append("action", interception, timestamp=FIXED_TIME + timedelta(milliseconds=2))
    document = recorder.document()
    receipt = ContextDeliveryReceipt(
        run_id="run-receipt",
        scenario_id="workspace_boundary",
        seed=1,
        harness_version="1.0.0",
        scenario_version="1.0.0",
        adapter_version="1.0.0",
        adapter_name="admission_plus_ledger",
        simulator_id="simulated-ploy/1.0.0",
        predicate_set_hash=ledger.predicate_set_hash,
        scaffold_template_hash=canonical_hash({"template": "v1"}),
        message_context_hashes=(segment.segment.content_hash, assembly.assembly_hash),
        segments=(
            SegmentDeliveryRecord(
                id=segment.segment.id,
                segment_uid=segment.provenance.segment_uid,
                content_hash=segment.segment.content_hash,
                trust_class=decision.verified_trust_class,
                semantic=segment.segment.semantic,
                effective_semantic=decision.effective_semantic,
                admission_decision=decision.status,
                admission_reason=decision.reason_code,
                authoritative=decision.authoritative,
                eager_assembly_order=0,
                assembly_region=assembly.entries[0].region,
            ),
        ),
        compaction=CompactionReceipt(planned_schedule=(4,), actual_events=()),
        actions=(ActionReceipt(turn=5, interception=interception),),
        performance=PerformanceReceipt(
            kernel_latency_ms=0.4,
            simulator_or_model_latency_ms=0.2,
            character_estimate=assembly.character_count,
            token_estimate=(assembly.character_count + 3) // 4,
            cost=None,
        ),
        outcome=OutcomeReceipt(
            first_violation_turn=None,
            completion_status="completed",
            right_censored=True,
        ),
        trace_hash=document.trace_hash,
        decision_trace_hash=document.decision_trace_hash,
    )
    path = tmp_path / "receipt.jsonl"

    write_receipt_jsonl(path, receipt)
    loaded = read_receipt_jsonl(path)

    assert loaded == receipt
    assert loaded.actions[0].interception.effect_executed is True
    assert loaded.compaction.planned_schedule == (4,)
    assert loaded.performance.cost is None
    assert path.read_text().endswith("\n")


def test_receipt_rejects_duplicate_verified_segment_uid() -> None:
    segment = make_segment("principal", "Remain inside the workspace.")
    decision = make_policy().admit(segment)
    entry = SegmentDeliveryRecord(
        id=segment.segment.id,
        segment_uid=segment.provenance.segment_uid,
        content_hash=segment.segment.content_hash,
        trust_class=decision.verified_trust_class,
        semantic=segment.segment.semantic,
        effective_semantic=decision.effective_semantic,
        admission_decision=decision.status,
        admission_reason=decision.reason_code,
        authoritative=decision.authoritative,
    )
    common = {
        "run_id": "duplicate-uid",
        "scenario_id": "workspace_boundary",
        "seed": 1,
        "harness_version": "2.0.0",
        "scenario_version": "2.0.0",
        "adapter_version": "2.0.0",
        "adapter_name": "admission_only",
        "simulator_id": "simulated-ploy/2.0.0",
        "predicate_set_hash": canonical_hash([]),
        "scaffold_template_hash": canonical_hash({"template": "v2"}),
        "message_context_hashes": (segment.segment.content_hash,),
        "compaction": CompactionReceipt(planned_schedule=(), actual_events=()),
        "actions": (),
        "performance": PerformanceReceipt(
            kernel_latency_ms=0.0,
            simulator_or_model_latency_ms=0.0,
            character_estimate=0,
            token_estimate=0,
            cost=None,
        ),
        "outcome": OutcomeReceipt(
            first_violation_turn=None,
            completion_status="completed",
            right_censored=True,
        ),
        "trace_hash": "0" * 64,
        "decision_trace_hash": "1" * 64,
    }

    with pytest.raises(ValueError, match="duplicate"):
        ContextDeliveryReceipt(segments=(entry, entry), **common)
