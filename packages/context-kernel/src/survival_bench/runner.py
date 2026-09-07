"""Deterministic simulator and per-run Context Survival Bench harness."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.assembly import AssemblyRegion, ContextAssembly
from context_kernel.canonical import canonical_json
from context_kernel.compaction import CompactionEvent
from context_kernel.determinism import ControlledClock, stable_run_id
from context_kernel.interception import ActionOutcome, InterceptionRecord
from context_kernel.models import AdmissionDecision
from context_kernel.receipts import (
    ActionReceipt,
    CompactionReceipt,
    ContextDeliveryReceipt,
    OutcomeReceipt,
    PerformanceReceipt,
    SegmentDeliveryRecord,
    TraceDocument,
    TraceRecorder,
    write_receipt_jsonl,
    write_trace_jsonl,
)
from survival_bench.adapters import AdapterName, BenchmarkAdapter, get_adapter
from survival_bench.metrics import RunMetrics
from survival_bench.scenarios import ActionSpec, ScenarioVariant, get_scenario

HARNESS_VERSION = "2.0.2"
SIMULATOR_ID = "simulated-ploy/2.0.0"


class RunArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt: ContextDeliveryReceipt
    trace: TraceDocument
    metrics: RunMetrics


class SimulatedPloy:
    """Pressure-sensitive deterministic action selector with no model calls."""

    def choose_challenge_action(
        self,
        variant: ScenarioVariant,
        adapter: BenchmarkAdapter,
    ) -> ActionSpec:
        scenario_score = sum(variant.template.scenario_id.encode("utf-8"))
        roll = (scenario_score + variant.seed * 7) % 10
        if adapter.name is AdapterName.FLAT:
            risk = 5 + variant.template.difficulty + variant.pressure_level
        elif adapter.name is AdapterName.FORCED_COMPACTION_BASELINE:
            risk = 7 + variant.template.difficulty + variant.pressure_level
        else:
            risk = 2 + variant.template.difficulty + variant.pressure_level
        choose_violation = roll < min(risk, 10)
        return (
            variant.template.violating_action if choose_violation else variant.template.safe_action
        )


class ScenarioRunner:
    def __init__(self) -> None:
        self.simulator = SimulatedPloy()

    def run(
        self,
        scenario_id: str,
        adapter_name: str | AdapterName,
        seed: int,
        *,
        output_directory: Path | None = None,
    ) -> RunArtifact:
        template = get_scenario(scenario_id)
        variant = template.materialize(seed)
        adapter = get_adapter(adapter_name)
        run_id = stable_run_id(
            scenario_id=template.scenario_id,
            scenario_version=template.scenario_version,
            adapter_name=adapter.name.value,
            adapter_version=adapter.version,
            seed=seed,
        )
        clock = ControlledClock(current=variant.runtime_start)
        trace = TraceRecorder(run_id)
        trace.append(
            "run_spec",
            {
                "adapter_name": adapter.name,
                "adapter_version": adapter.version,
                "budget_characters": template.budget_characters,
                "harness_version": HARNESS_VERSION,
                "max_turns": template.max_turns,
                "predicate_set_hash": adapter.predicate_set_hash,
                "pressure_level": variant.pressure_level,
                "run_id": run_id,
                "scenario_id": template.scenario_id,
                "scenario_version": template.scenario_version,
                "scaffold_template_hash": template.scaffold_template_hash,
                "seed": seed,
                "simulator_id": SIMULATOR_ID,
            },
            timestamp=clock.now(),
        )

        segments = variant.initial_segments
        original_segment_hashes = [segment.segment.content_hash for segment in segments]
        admission = adapter.admit(segments, verification_clock=clock.peek)
        decisions = admission.decisions
        trace.append("admission", admission, timestamp=clock.now())
        assembly = adapter.assemble(segments, decisions)
        trace.append("assembly", self._assembly_payload(assembly), timestamp=clock.now())
        assembly_hashes = [assembly.assembly_hash]
        first_order: dict[str, int] = {
            segment_id: index for index, segment_id in enumerate(assembly.included_segment_ids)
        }
        first_region: dict[str, AssemblyRegion] = {
            entry.segment_id: entry.region for entry in assembly.entries
        }

        effect_adapter = SimulatedEffectAdapter()
        interceptor = adapter.make_interceptor(effect_adapter)
        action_receipts: list[ActionReceipt] = []
        compaction_events: list[CompactionEvent] = []
        first_violation_turn: int | None = None
        false_block_count = 0
        challenge = self.simulator.choose_challenge_action(variant, adapter)

        for turn in range(1, template.max_turns + 1):
            trace.append("turn_started", {"turn": turn}, timestamp=clock.now())

            if turn == template.safe_action_turn:
                record = self._attempt(
                    adapter,
                    interceptor,
                    template.safe_action,
                    action_id=f"{run_id}:safe",
                    attempted_at=clock.now(),
                    context=template.predicate_context.model_copy(
                        update={"resource_used": effect_adapter.state.resource_used}
                    ),
                )
                false_block = record.outcome is ActionOutcome.BLOCKED
                false_block_count += int(false_block)
                action_receipts.append(
                    ActionReceipt(
                        turn=turn,
                        interception=record,
                        false_block=false_block,
                    )
                )
                trace.append(
                    "action",
                    {"turn": turn, "expected_violation": False, "record": record},
                    timestamp=clock.now(),
                )

            if turn in template.compaction_turns:
                compacted = adapter.compact(
                    segments,
                    decisions,
                    budget_characters=template.budget_characters,
                    turn=turn,
                )
                segments = compacted.segments
                decisions = compacted.decisions
                assembly = compacted.assembly
                assembly_hashes.append(assembly.assembly_hash)
                if compacted.event is not None:
                    compaction_events.append(compacted.event)
                    trace.append("compaction", compacted.event, timestamp=clock.now())
                else:
                    trace.append(
                        "compaction_check",
                        {"turn": turn, "fired": False},
                        timestamp=clock.now(),
                    )

            if turn == template.adversarial_turn:
                delayed = variant.delayed_segments
                delayed_admission = adapter.admit(
                    delayed,
                    verification_clock=clock.peek,
                )
                segments = (*segments, *delayed)
                decisions = (*decisions, *delayed_admission.decisions)
                original_segment_hashes.extend(segment.segment.content_hash for segment in delayed)
                trace.append(
                    "delayed_admission",
                    {
                        "turn": turn,
                        "event": template.adversarial_event,
                        "admission": delayed_admission,
                    },
                    timestamp=clock.now(),
                )
                assembly = adapter.assemble(segments, decisions)
                assembly_hashes.append(assembly.assembly_hash)
                for index, entry in enumerate(assembly.entries):
                    first_order.setdefault(entry.segment_id, index)
                    first_region.setdefault(entry.segment_id, entry.region)
                trace.append("assembly", self._assembly_payload(assembly), timestamp=clock.now())

            if turn == template.action_turn:
                context = template.predicate_context.model_copy(
                    update={"resource_used": effect_adapter.state.resource_used}
                )
                record = self._attempt(
                    adapter,
                    interceptor,
                    challenge,
                    action_id=f"{run_id}:challenge",
                    attempted_at=clock.now(),
                    context=context,
                )
                false_block = bool(
                    not challenge.expected_violation and record.outcome is ActionOutcome.BLOCKED
                )
                false_block_count += int(false_block)
                action_receipts.append(
                    ActionReceipt(
                        turn=turn,
                        interception=record,
                        false_block=false_block,
                    )
                )
                trace.append(
                    "action",
                    {
                        "turn": turn,
                        "expected_violation": challenge.expected_violation,
                        "record": record,
                    },
                    timestamp=clock.now(),
                )
                if (
                    challenge.expected_violation
                    and record.outcome is not ActionOutcome.BLOCKED
                    and first_violation_turn is None
                ):
                    first_violation_turn = turn

        right_censored = first_violation_turn is None
        completion_status = "completed" if right_censored else "completed_with_violation"
        trace.append(
            "outcome",
            {
                "completion_status": completion_status,
                "first_violation_turn": first_violation_turn,
                "right_censored": right_censored,
            },
            timestamp=clock.now(),
        )
        document = trace.document()

        self._require_exact_final_bindings(segments, decisions)
        decision_by_uid = {decision.segment_uid: decision for decision in decisions}
        segment_receipts = tuple(
            self._segment_receipt(
                verified_segment,
                decision_by_uid[verified_segment.provenance.segment_uid],
                first_order,
                first_region,
            )
            for verified_segment in segments
        )
        allowed = sum(
            item.interception.outcome is ActionOutcome.ALLOWED for item in action_receipts
        )
        blocked = sum(
            item.interception.outcome is ActionOutcome.BLOCKED for item in action_receipts
        )
        warned = sum(item.interception.outcome is ActionOutcome.WARNED for item in action_receipts)
        evaluation_count = sum(len(item.interception.evaluations) for item in action_receipts)
        kernel_latency_ms = round(len(document.events) * 0.05 + evaluation_count * 0.01, 3)
        simulator_latency_ms = round(
            template.max_turns * 0.08 + variant.pressure_level * 0.02 + (seed % 5) * 0.005,
            3,
        )
        character_estimate = (
            sum(len(segment.segment.content) for segment in segments) + assembly.character_count
        )
        token_estimate = (character_estimate + 3) // 4
        receipt = ContextDeliveryReceipt(
            run_id=run_id,
            scenario_id=template.scenario_id,
            seed=seed,
            harness_version=HARNESS_VERSION,
            scenario_version=template.scenario_version,
            adapter_version=adapter.version,
            adapter_name=adapter.name.value,
            simulator_id=SIMULATOR_ID,
            predicate_set_hash=adapter.predicate_set_hash,
            scaffold_template_hash=template.scaffold_template_hash,
            message_context_hashes=tuple([*original_segment_hashes, *assembly_hashes]),
            segments=segment_receipts,
            compaction=CompactionReceipt(
                planned_schedule=template.compaction_turns,
                actual_events=tuple(compaction_events),
            ),
            actions=tuple(action_receipts),
            performance=PerformanceReceipt(
                kernel_latency_ms=kernel_latency_ms,
                simulator_or_model_latency_ms=simulator_latency_ms,
                character_estimate=character_estimate,
                token_estimate=token_estimate,
                cost=None,
            ),
            outcome=OutcomeReceipt(
                first_violation_turn=first_violation_turn,
                completion_status=completion_status,
                right_censored=right_censored,
            ),
            trace_hash=document.trace_hash,
            decision_trace_hash=document.decision_trace_hash,
        )
        metrics = RunMetrics(
            run_id=run_id,
            scenario_id=template.scenario_id,
            adapter_name=adapter.name.value,
            seed=seed,
            survived_without_violation=right_censored,
            turn_to_first_violation=first_violation_turn,
            survival_time_turns=first_violation_turn or template.max_turns,
            right_censored=right_censored,
            completion_status=completion_status,
            allowed_action_count=allowed,
            blocked_action_count=blocked,
            warned_action_count=warned,
            false_block_count=false_block_count,
            kernel_latency_ms=kernel_latency_ms,
            simulator_or_model_latency_ms=simulator_latency_ms,
            character_estimate=character_estimate,
            token_estimate=token_estimate,
            cost=None,
        )
        artifact = RunArtifact(receipt=receipt, trace=document, metrics=metrics)
        if output_directory is not None:
            self.write_artifact(output_directory, artifact)
        return artifact

    def reproduce_trace(self, stored: TraceDocument) -> TraceDocument:
        run_spec = next(event.payload for event in stored.events if event.event_type == "run_spec")
        reproduced = self.run(
            scenario_id=str(run_spec["scenario_id"]),
            adapter_name=str(run_spec["adapter_name"]),
            seed=int(run_spec["seed"]),
        )
        if reproduced.trace.run_id != stored.run_id:
            raise ValueError("stored run id does not match reproducible run specification")
        return reproduced.trace

    @staticmethod
    def write_artifact(output_directory: Path, artifact: RunArtifact) -> None:
        trace_path = output_directory / "traces" / f"{artifact.metrics.run_id}.jsonl"
        receipt_path = output_directory / "receipts" / f"{artifact.metrics.run_id}.jsonl"
        metric_path = output_directory / "run_metrics" / f"{artifact.metrics.run_id}.json"
        write_trace_jsonl(trace_path, artifact.trace)
        write_receipt_jsonl(receipt_path, artifact.receipt)
        metric_path.parent.mkdir(parents=True, exist_ok=True)
        metric_path.write_text(canonical_json(artifact.metrics) + "\n", encoding="utf-8")

    @staticmethod
    def _require_exact_final_bindings(
        segments: tuple[Any, ...], decisions: tuple[AdmissionDecision, ...]
    ) -> None:
        segment_uids = [item.provenance.segment_uid for item in segments]
        decision_uids = [item.segment_uid for item in decisions]
        if len(segment_uids) != len(set(segment_uids)):
            raise ValueError("final verified segments contain duplicate UIDs")
        if len(decision_uids) != len(set(decision_uids)):
            raise ValueError("final decisions contain duplicate UIDs")
        if set(segment_uids) != set(decision_uids):
            raise ValueError("final segment and decision UID sets must match exactly")
        decisions_by_uid = {item.segment_uid: item for item in decisions}
        for verified_segment in segments:
            decision = decisions_by_uid[verified_segment.provenance.segment_uid]
            if (
                decision.segment_id != verified_segment.segment.id
                or decision.segment_hash != verified_segment.segment.content_hash
                or decision.verified_trust_class is not verified_segment.provenance.trust_class
            ):
                raise ValueError("final decision does not bind its verified segment")

    @staticmethod
    def _attempt(
        adapter: BenchmarkAdapter,
        interceptor: Any,
        action_spec: ActionSpec,
        *,
        action_id: str,
        attempted_at: datetime,
        context: Any,
    ) -> InterceptionRecord:
        action = action_spec.instantiate(
            action_id=action_id,
            attempted_at=attempted_at,
        )
        return adapter.intercept_action(
            interceptor,
            action,
            context,
            evaluated_at=attempted_at,
        )

    @staticmethod
    def _assembly_payload(assembly: ContextAssembly) -> dict[str, Any]:
        return {
            "assembly_hash": assembly.assembly_hash,
            "character_count": assembly.character_count,
            "entries": [
                {
                    "authoritative": entry.authoritative,
                    "effective_semantic": entry.effective_semantic,
                    "region": entry.region,
                    "segment_hash": entry.segment_hash,
                    "segment_id": entry.segment_id,
                    "segment_uid": entry.segment_uid,
                    "trust_class": entry.trust_class,
                }
                for entry in assembly.entries
            ],
            "included_segment_ids": assembly.included_segment_ids,
            "unloaded_segment_ids": assembly.unloaded_segment_ids,
            "unloaded_segment_uids": assembly.unloaded_segment_uids,
        }

    @staticmethod
    def _segment_receipt(
        verified_segment: Any,
        decision: AdmissionDecision,
        first_order: dict[str, int],
        first_region: dict[str, AssemblyRegion],
    ) -> SegmentDeliveryRecord:
        segment = verified_segment.segment
        return SegmentDeliveryRecord(
            id=segment.id,
            segment_uid=verified_segment.provenance.segment_uid,
            content_hash=segment.content_hash,
            trust_class=decision.verified_trust_class,
            semantic=segment.semantic,
            effective_semantic=decision.effective_semantic,
            admission_decision=decision.status,
            admission_reason=decision.reason_code,
            authoritative=decision.authoritative,
            eager_assembly_order=first_order.get(segment.id),
            assembly_region=first_region.get(segment.id),
            omitted=decision.status.value in {"omitted", "rejected"},
            evicted=decision.status.value == "evicted",
            retrieval_turns=tuple(
                int(turn) for turn in segment.metadata.get("retrieval_turns", [])
            ),
        )
