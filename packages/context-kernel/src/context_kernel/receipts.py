"""Context-delivery receipts and tamper-evident canonical JSONL traces."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from context_kernel.assembly import AssemblyRegion
from context_kernel.canonical import canonical_hash, canonical_json
from context_kernel.compaction import CompactionEvent
from context_kernel.interception import InterceptionRecord
from context_kernel.models import (
    AdmissionReason,
    AdmissionStatus,
    Semantic,
    TrustClass,
)


class SegmentDeliveryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    segment_uid: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str
    trust_class: TrustClass
    semantic: Semantic
    effective_semantic: Semantic
    admission_decision: AdmissionStatus
    admission_reason: AdmissionReason
    authoritative: bool
    eager_assembly_order: int | None = None
    assembly_region: AssemblyRegion | None = None
    omitted: bool = False
    evicted: bool = False
    retrieval_turns: tuple[int, ...] = ()


class CompactionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    planned_schedule: tuple[int, ...]
    actual_events: tuple[CompactionEvent, ...]


class ActionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    turn: int = Field(ge=0)
    interception: InterceptionRecord
    false_block: bool = False


class PerformanceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kernel_latency_ms: float = Field(ge=0)
    simulator_or_model_latency_ms: float = Field(ge=0)
    character_estimate: int = Field(ge=0)
    token_estimate: int = Field(ge=0)
    cost: float | None = Field(default=None, ge=0)


class OutcomeReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    first_violation_turn: int | None = Field(default=None, ge=0)
    completion_status: str
    right_censored: bool


class ContextDeliveryReceipt(BaseModel):
    """Structured record of context delivery and action-policy events."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario_id: str
    seed: int
    harness_version: str
    scenario_version: str
    adapter_version: str
    adapter_name: str
    model_id: str | None = None
    simulator_id: str | None = None
    predicate_set_hash: str
    scaffold_template_hash: str
    message_context_hashes: tuple[str, ...]
    segments: tuple[SegmentDeliveryRecord, ...]
    compaction: CompactionReceipt
    actions: tuple[ActionReceipt, ...]
    performance: PerformanceReceipt
    outcome: OutcomeReceipt
    trace_hash: str
    decision_trace_hash: str

    @model_validator(mode="after")
    def require_exactly_one_driver_id(self) -> Self:
        if (self.model_id is None) == (self.simulator_id is None):
            raise ValueError("exactly one of model_id or simulator_id must be set")
        logical_ids = [segment.id for segment in self.segments]
        segment_uids = [segment.segment_uid for segment in self.segments]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("receipt contains duplicate logical segment IDs")
        if len(segment_uids) != len(set(segment_uids)):
            raise ValueError("receipt contains duplicate verified segment UIDs")
        return self


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    event_type: str
    timestamp: datetime
    payload: dict[str, Any]
    previous_event_hash: str | None
    event_hash: str

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.timestamp.tzinfo is None:
            raise ValueError("trace event timestamp must be timezone-aware")
        return self


class TraceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    events: tuple[TraceEvent, ...]
    trace_hash: str
    decision_trace_hash: str


_EXCLUDED_DECISION_KEYS = frozenset(
    {
        "attempted_at",
        "created_at",
        "decision_trace_hash",
        "generated_at",
        "kernel_latency_ms",
        "simulator_or_model_latency_ms",
        "timestamp",
        "trace_hash",
    }
)


def decision_trace_projection(value: Any) -> Any:
    """Remove explicitly incidental fields while retaining ordered decisions."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, Mapping):
        return {
            str(key): decision_trace_projection(item)
            for key, item in value.items()
            if str(key) not in _EXCLUDED_DECISION_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [decision_trace_projection(item) for item in value]
    return value


def decision_trace_hash(value: Any) -> str:
    """Hash logical decisions without timestamps, latencies, or file formatting."""
    return canonical_hash(decision_trace_projection(value))


class TraceRecorder:
    """Append stable, hash-chained events in a caller-controlled order."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        event_type: str,
        payload: Mapping[str, Any] | BaseModel,
        *,
        timestamp: datetime,
    ) -> TraceEvent:
        if timestamp.tzinfo is None:
            raise ValueError("trace timestamp must be timezone-aware")
        payload_data = (
            payload.model_dump(mode="python") if isinstance(payload, BaseModel) else dict(payload)
        )
        body = {
            "sequence": len(self._events) + 1,
            "event_type": event_type,
            "timestamp": timestamp,
            "payload": payload_data,
            "previous_event_hash": (self._events[-1].event_hash if self._events else None),
        }
        event = TraceEvent(**body, event_hash=canonical_hash(body))
        self._events.append(event)
        return event

    def document(self) -> TraceDocument:
        events = tuple(self._events)
        return TraceDocument(
            run_id=self.run_id,
            events=events,
            trace_hash=canonical_hash([event.event_hash for event in events]),
            decision_trace_hash=compute_decision_trace_hash(events),
        )


def compute_decision_trace_hash(events: tuple[TraceEvent, ...]) -> str:
    """Hash the ordered logical event stream using the replay projection."""
    logical_events = [
        {
            "sequence": event.sequence,
            "event_type": event.event_type,
            "payload": event.payload,
        }
        for event in events
    ]
    return decision_trace_hash(logical_events)


def verify_trace_document(document: TraceDocument) -> tuple[bool, tuple[str, ...]]:
    """Verify event hashes, chain links, sequence numbers, and the footer hash."""
    errors: list[str] = []
    previous: str | None = None
    for expected_sequence, event in enumerate(document.events, start=1):
        if event.sequence != expected_sequence:
            errors.append(f"sequence mismatch at event {expected_sequence}")
        if event.previous_event_hash != previous:
            errors.append(f"previous hash mismatch at event {expected_sequence}")
        expected_hash = canonical_hash(event.model_dump(exclude={"event_hash"}))
        if event.event_hash != expected_hash:
            errors.append(f"event hash mismatch at event {expected_sequence}")
        previous = event.event_hash
    expected_trace_hash = canonical_hash([event.event_hash for event in document.events])
    if document.trace_hash != expected_trace_hash:
        errors.append("trace footer hash mismatch")
    expected_decision_hash = compute_decision_trace_hash(document.events)
    if document.decision_trace_hash != expected_decision_hash:
        errors.append("decision trace hash mismatch")
    return not errors, tuple(errors)


def write_trace_jsonl(path: Path, document: TraceDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        canonical_json({"record_type": "trace_event", **event.model_dump(mode="python")})
        for event in document.events
    ]
    lines.append(
        canonical_json(
            {
                "record_type": "trace_footer",
                "run_id": document.run_id,
                "trace_hash": document.trace_hash,
                "decision_trace_hash": document.decision_trace_hash,
                "event_count": len(document.events),
            }
        )
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_trace_jsonl(path: Path) -> TraceDocument:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not records or records[-1].get("record_type") != "trace_footer":
        raise ValueError("trace footer is missing")
    footer = records[-1]
    events = tuple(
        TraceEvent.model_validate(
            {key: value for key, value in record.items() if key != "record_type"}
        )
        for record in records[:-1]
    )
    if footer.get("event_count") != len(events):
        raise ValueError("trace event count does not match footer")
    return TraceDocument(
        run_id=footer["run_id"],
        events=events,
        trace_hash=footer["trace_hash"],
        decision_trace_hash=footer["decision_trace_hash"],
    )


def write_receipt_jsonl(path: Path, receipt: ContextDeliveryReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(receipt) + "\n", encoding="utf-8")


def read_receipt_jsonl(path: Path) -> ContextDeliveryReceipt:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(records) != 1:
        raise ValueError("a receipt JSONL file must contain exactly one record")
    return ContextDeliveryReceipt.model_validate(records[0])
