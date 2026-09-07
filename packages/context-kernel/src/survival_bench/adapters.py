"""Deterministic benchmark arms over verified provenance and identity bindings."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from enum import StrEnum

from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.admission import AdmissionPolicy
from context_kernel.assembly import (
    AssemblyEntry,
    AssemblyRegion,
    ContextAssembler,
    ContextAssembly,
)
from context_kernel.canonical import sha256_text
from context_kernel.compaction import CompactionResult, DeterministicCompactor
from context_kernel.interception import InterceptionRecord, SafeActionInterceptor
from context_kernel.ledger import (
    Action,
    EnforcementMode,
    InvariantLedger,
    PredicateContext,
    PredicateRegistration,
)
from context_kernel.models import (
    AdmissionBatch,
    AdmissionDecision,
    AdmissionReason,
    AdmissionStatus,
    Semantic,
    VerifiedSegment,
)
from context_kernel.predicates.builtin import BUILTIN_PREDICATES
from context_kernel.provenance import InMemoryProvenanceAuthority, local_scenario_authority


class AdapterName(StrEnum):
    FLAT = "flat"
    FORCED_COMPACTION_BASELINE = "forced_compaction_baseline"
    ADMISSION_ONLY = "admission_only"
    ADMISSION_PLUS_LEDGER = "admission_plus_ledger"


_AUTHORITY_SEMANTICS = {
    Semantic.INSTRUCTION,
    Semantic.CONSTRAINT,
    Semantic.OUTPUT_CONTRACT,
    Semantic.APPROVAL,
}


class FlatContextAssembler(ContextAssembler):
    """Baseline renderer that flattens verified source content but not trust checks."""

    def assemble(
        self,
        segments: Iterable[VerifiedSegment],
        decisions: Iterable[AdmissionDecision],
        *,
        activated_ids: frozenset[str] = frozenset(),
    ) -> ContextAssembly:
        del activated_ids
        verified_segments = tuple(segments)
        decision_list = tuple(decisions)
        self._validate_bindings(verified_segments, decision_list)
        decision_by_uid = {decision.segment_uid: decision for decision in decision_list}
        entries: list[AssemblyEntry] = []
        for verified_segment in verified_segments:
            segment = verified_segment.segment
            decision = decision_by_uid[verified_segment.provenance.segment_uid]
            if decision.status is not AdmissionStatus.ADMITTED_EAGER:
                continue
            entries.append(
                AssemblyEntry(
                    segment_id=segment.id,
                    segment_uid=verified_segment.provenance.segment_uid,
                    segment_hash=segment.content_hash,
                    region=AssemblyRegion.WORKSPACE,
                    trust_class=decision.verified_trust_class,
                    semantic=segment.semantic,
                    effective_semantic=decision.effective_semantic,
                    priority=segment.priority,
                    authoritative=decision.authoritative,
                    content=segment.content,
                )
            )
        rendered = "# Flat context\n\n" + "\n\n".join(entry.content for entry in entries)
        if entries:
            rendered += "\n"
        return ContextAssembly(
            entries=tuple(entries),
            rendered=rendered,
            assembly_hash=sha256_text(rendered),
            character_count=len(rendered),
            included_segment_ids=tuple(entry.segment_id for entry in entries),
            included_segment_uids=tuple(entry.segment_uid for entry in entries),
            unloaded_segment_ids=(),
            unloaded_segment_uids=(),
        )


class BenchmarkAdapter:
    """Shared deterministic lifecycle using trusted scenario provenance."""

    version = "2.0.1"

    def __init__(
        self,
        name: AdapterName,
        *,
        typed_admission: bool,
        forced_compaction: bool,
        enforce_ledger: bool,
        authority: InMemoryProvenanceAuthority | None = None,
    ) -> None:
        self.name = name
        self.typed_admission = typed_admission
        self.forced_compaction = forced_compaction
        self.enforce_ledger = enforce_ledger
        self.authority = authority or local_scenario_authority()
        self.assembler = ContextAssembler() if typed_admission else FlatContextAssembler()
        self.compactor = DeterministicCompactor(self.authority, assembler=self.assembler)
        registrations = (
            tuple(
                PredicateRegistration(
                    predicate=predicate_type(),
                    mode=EnforcementMode.ENFORCE,
                )
                for predicate_type in BUILTIN_PREDICATES
            )
            if enforce_ledger
            else ()
        )
        self.ledger = InvariantLedger(registrations)

    @property
    def predicate_set_hash(self) -> str:
        return self.ledger.predicate_set_hash

    def admit(
        self,
        segments: tuple[VerifiedSegment, ...],
        *,
        verification_clock: Callable[[], datetime],
    ) -> AdmissionBatch:
        """Admit only against a runner-owned, trusted verification clock."""
        if self.typed_admission:
            return AdmissionPolicy(
                self.authority,
                verification_clock=verification_clock,
            ).admit_many(segments)
        # Flat is presentation-only. It still verifies source provenance first.
        verified_policy = AdmissionPolicy(
            self.authority,
            verification_clock=verification_clock,
        )
        verified_policy.admit_many(segments)
        decisions = tuple(
            AdmissionDecision(
                segment_id=item.segment.id,
                segment_uid=item.provenance.segment_uid,
                segment_hash=item.segment.content_hash,
                verified_trust_class=item.provenance.trust_class,
                status=AdmissionStatus.ADMITTED_EAGER,
                reason_code=AdmissionReason.BASELINE_FLAT_ADMISSION,
                effective_semantic=item.segment.semantic,
                authoritative=(
                    item.provenance.trust_class.value == "principal"
                    and item.segment.semantic in _AUTHORITY_SEMANTICS
                ),
                detail="Flat baseline admits verified submitted text into one undifferentiated buffer.",
            )
            for item in segments
        )
        return AdmissionBatch(
            decisions=decisions,
            admitted_segment_ids=tuple(item.segment.id for item in segments),
            omitted_segment_ids=(),
            rejected_segment_ids=(),
        )

    def assemble(
        self,
        segments: tuple[VerifiedSegment, ...],
        decisions: tuple[AdmissionDecision, ...],
    ) -> ContextAssembly:
        return self.assembler.assemble(segments, decisions)

    def compact(
        self,
        segments: tuple[VerifiedSegment, ...],
        decisions: tuple[AdmissionDecision, ...],
        *,
        budget_characters: int,
        turn: int,
    ) -> CompactionResult:
        if not self.forced_compaction:
            assembly = self.assemble(segments, decisions)
            return CompactionResult(
                segments=segments,
                decisions=decisions,
                assembly=assembly,
                event=None,
            )
        return self.compactor.compact(
            segments,
            decisions,
            activated_ids=frozenset(),
            budget_characters=budget_characters,
            turn=turn,
        )

    def make_interceptor(self, effect_adapter: SimulatedEffectAdapter) -> SafeActionInterceptor:
        return SafeActionInterceptor(self.ledger, effect_adapter)

    def intercept_action(
        self,
        interceptor: SafeActionInterceptor,
        action: Action,
        context: PredicateContext,
        *,
        evaluated_at: datetime,
    ) -> InterceptionRecord:
        return interceptor.attempt(action, context, evaluated_at=evaluated_at)


def get_adapter(name: str | AdapterName) -> BenchmarkAdapter:
    parsed = AdapterName(name)
    if parsed is AdapterName.FLAT:
        return BenchmarkAdapter(
            parsed,
            typed_admission=False,
            forced_compaction=False,
            enforce_ledger=False,
        )
    if parsed is AdapterName.FORCED_COMPACTION_BASELINE:
        return BenchmarkAdapter(
            parsed,
            typed_admission=False,
            forced_compaction=True,
            enforce_ledger=False,
        )
    if parsed is AdapterName.ADMISSION_ONLY:
        return BenchmarkAdapter(
            parsed,
            typed_admission=True,
            forced_compaction=True,
            enforce_ledger=False,
        )
    return BenchmarkAdapter(
        parsed,
        typed_admission=True,
        forced_compaction=True,
        enforce_ledger=True,
    )


def adapter_names() -> tuple[str, ...]:
    return tuple(adapter.value for adapter in AdapterName)
