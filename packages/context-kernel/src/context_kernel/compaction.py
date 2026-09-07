"""Deterministic compaction over verified segment identities."""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from context_kernel.assembly import ContextAssembler, ContextAssembly
from context_kernel.canonical import sha256_text
from context_kernel.models import (
    AdmissionDecision,
    AdmissionReason,
    AdmissionStatus,
    Priority,
    Semantic,
    TrustClass,
    VerifiedSegment,
)
from context_kernel.provenance import InMemoryProvenanceAuthority


class CompactionAction(StrEnum):
    SUMMARIZED = "summarized"
    EVICTED = "evicted"


class CompactionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str
    segment_uid: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: CompactionAction
    reason_code: str
    before_content_hash: str
    after_content_hash: str | None = None
    before_characters: int = Field(ge=0)
    after_characters: int = Field(ge=0)


class CompactionEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    turn: int = Field(ge=0)
    budget_characters: int = Field(gt=0)
    before_assembly_hash: str
    after_assembly_hash: str
    before_characters: int = Field(ge=0)
    after_characters: int = Field(ge=0)
    records: tuple[CompactionRecord, ...]
    protected_segment_ids: tuple[str, ...]
    protected_segment_uids: tuple[str, ...]
    budget_satisfied: bool


class CompactionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    segments: tuple[VerifiedSegment, ...]
    decisions: tuple[AdmissionDecision, ...]
    assembly: ContextAssembly
    event: CompactionEvent | None


class DeterministicCompactor:
    """Apply reproducible summarize-then-evict policy to verified segments."""

    def __init__(
        self,
        authority: InMemoryProvenanceAuthority,
        *,
        summary_characters: int = 160,
        assembler: ContextAssembler | None = None,
    ) -> None:
        if summary_characters < 32:
            raise ValueError("summary_characters must be at least 32")
        self.authority = authority
        self.summary_characters = summary_characters
        self.assembler = assembler or ContextAssembler()

    def compact(
        self,
        segments: tuple[VerifiedSegment, ...],
        decisions: tuple[AdmissionDecision, ...],
        *,
        activated_ids: frozenset[str],
        budget_characters: int,
        turn: int,
    ) -> CompactionResult:
        if budget_characters <= 0:
            raise ValueError("budget_characters must be positive")

        before = self.assembler.assemble(segments, decisions, activated_ids=activated_ids)
        if before.character_count <= budget_characters:
            return CompactionResult(
                segments=segments,
                decisions=decisions,
                assembly=before,
                event=None,
            )

        segment_by_id = {item.segment.id: item for item in segments}
        decision_by_uid = {decision.segment_uid: decision for decision in decisions}
        protected_uids = frozenset(
            item.provenance.segment_uid for item in segments if self._is_protected(item)
        )
        records: list[CompactionRecord] = []

        summarize_order = self._candidate_ids(
            before,
            segment_by_id,
            protected_uids,
            priorities=(Priority.SUPPORTING, Priority.IMPORTANT),
        )
        current = before
        for segment_id in summarize_order:
            if current.character_count <= budget_characters:
                break
            verified_segment = segment_by_id[segment_id]
            segment = verified_segment.segment
            summary = self._summary(segment.content)
            if summary == segment.content:
                continue
            updated_raw = segment.model_copy(
                update={
                    "content": summary,
                    "content_hash": sha256_text(summary),
                    "metadata": {**segment.metadata, "deterministically_summarized": True},
                }
            )
            updated_verified = self.authority.issue(
                updated_raw,
                trust_class=verified_segment.provenance.trust_class,
                issued_at=verified_segment.provenance.issued_at,
                expires_at=verified_segment.provenance.expires_at,
                nonce=(f"{verified_segment.provenance.nonce}:summary:{updated_raw.content_hash}"),
            )
            old_decision = decision_by_uid.pop(verified_segment.provenance.segment_uid)
            updated_decision = old_decision.model_copy(
                update={
                    "segment_uid": updated_verified.provenance.segment_uid,
                    "segment_hash": updated_raw.content_hash,
                }
            )
            segment_by_id[segment_id] = updated_verified
            decision_by_uid[updated_decision.segment_uid] = updated_decision
            records.append(
                CompactionRecord(
                    segment_id=segment_id,
                    segment_uid=updated_verified.provenance.segment_uid,
                    action=CompactionAction.SUMMARIZED,
                    reason_code="budget_pressure_deterministic_summary",
                    before_content_hash=segment.content_hash,
                    after_content_hash=updated_raw.content_hash,
                    before_characters=len(segment.content),
                    after_characters=len(summary),
                )
            )
            current = self._assemble_maps(
                segments,
                segment_by_id,
                decision_by_uid,
                activated_ids,
            )

        eviction_order = self._candidate_ids(
            current,
            segment_by_id,
            protected_uids,
            priorities=(Priority.SUPPORTING, Priority.IMPORTANT, Priority.REQUIRED),
        )
        for segment_id in eviction_order:
            if current.character_count <= budget_characters:
                break
            verified_segment = segment_by_id[segment_id]
            decision = decision_by_uid[verified_segment.provenance.segment_uid]
            if decision.status is AdmissionStatus.EVICTED:
                continue
            decision_by_uid[verified_segment.provenance.segment_uid] = decision.model_copy(
                update={
                    "status": AdmissionStatus.EVICTED,
                    "reason_code": AdmissionReason.COMPACTION_EVICTION,
                    "authoritative": False,
                    "detail": "Evicted by deterministic character-budget compaction.",
                }
            )
            records.append(
                CompactionRecord(
                    segment_id=segment_id,
                    segment_uid=verified_segment.provenance.segment_uid,
                    action=CompactionAction.EVICTED,
                    reason_code="budget_pressure_deterministic_eviction",
                    before_content_hash=verified_segment.segment.content_hash,
                    after_content_hash=None,
                    before_characters=len(verified_segment.segment.content),
                    after_characters=0,
                )
            )
            current = self._assemble_maps(
                segments,
                segment_by_id,
                decision_by_uid,
                activated_ids,
            )

        final_segments = tuple(segment_by_id[item.segment.id] for item in segments)
        final_decisions = tuple(
            decision_by_uid[item.provenance.segment_uid] for item in final_segments
        )
        protected_ids = tuple(
            item.segment.id
            for item in final_segments
            if item.provenance.segment_uid in protected_uids
        )
        event = CompactionEvent(
            turn=turn,
            budget_characters=budget_characters,
            before_assembly_hash=before.assembly_hash,
            after_assembly_hash=current.assembly_hash,
            before_characters=before.character_count,
            after_characters=current.character_count,
            records=tuple(records),
            protected_segment_ids=tuple(sorted(protected_ids)),
            protected_segment_uids=tuple(sorted(protected_uids)),
            budget_satisfied=current.character_count <= budget_characters,
        )
        return CompactionResult(
            segments=final_segments,
            decisions=final_decisions,
            assembly=current,
            event=event,
        )

    def _assemble_maps(
        self,
        original_segments: tuple[VerifiedSegment, ...],
        segment_by_id: dict[str, VerifiedSegment],
        decision_by_uid: dict[str, AdmissionDecision],
        activated_ids: frozenset[str],
    ) -> ContextAssembly:
        current_segments = tuple(segment_by_id[item.segment.id] for item in original_segments)
        current_decisions = tuple(
            decision_by_uid[item.provenance.segment_uid] for item in current_segments
        )
        return self.assembler.assemble(
            current_segments,
            current_decisions,
            activated_ids=activated_ids,
        )

    @staticmethod
    def _is_protected(verified_segment: VerifiedSegment) -> bool:
        segment = verified_segment.segment
        principal_required = bool(
            verified_segment.provenance.trust_class is TrustClass.PRINCIPAL
            and segment.priority is Priority.REQUIRED
            and segment.semantic
            in {
                Semantic.INSTRUCTION,
                Semantic.CONSTRAINT,
                Semantic.OUTPUT_CONTRACT,
            }
        )
        # Trusted invariant-registry residency is deferred to S1. Caller metadata
        # must never create S0 compaction protection.
        return principal_required

    @staticmethod
    def _candidate_ids(
        assembly: ContextAssembly,
        segment_by_id: dict[str, VerifiedSegment],
        protected_uids: frozenset[str],
        *,
        priorities: tuple[Priority, ...],
    ) -> tuple[str, ...]:
        ordered: list[str] = []
        for priority in priorities:
            matching = [
                entry.segment_id
                for entry in reversed(assembly.entries)
                if segment_by_id[entry.segment_id].segment.priority is priority
                and entry.segment_uid not in protected_uids
            ]
            ordered.extend(matching)
        return tuple(ordered)

    def _summary(self, content: str) -> str:
        normalized = re.sub(r"\s+", " ", content).strip()
        if len(normalized) <= self.summary_characters:
            return content
        clipped = normalized[: self.summary_characters].rstrip()
        return f"[DETERMINISTIC SUMMARY] {clipped}…"
