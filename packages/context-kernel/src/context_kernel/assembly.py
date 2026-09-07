"""Deterministic assembly over verified segment and decision identities."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from context_kernel.canonical import canonical_json, sha256_text
from context_kernel.models import (
    AdmissionDecision,
    AdmissionStatus,
    Priority,
    Semantic,
    TrustClass,
    VerifiedSegment,
)


class AssemblyRegion(StrEnum):
    PRINCIPAL = "A_principal_instructions_and_required_constraints"
    WORKSPACE = "B_trusted_workspace_context"
    TOOL_OUTPUT = "C_tool_outputs"
    EXTERNAL = "D_external_untrusted_reference_material"
    OUTPUT_CONTRACT = "E_output_contract"


_REGION_ORDER: dict[AssemblyRegion, int] = {
    region: index for index, region in enumerate(AssemblyRegion)
}
_PRIORITY_ORDER: dict[Priority, int] = {
    Priority.REQUIRED: 0,
    Priority.IMPORTANT: 1,
    Priority.SUPPORTING: 2,
}
_REGION_TITLES: dict[AssemblyRegion, str] = {
    AssemblyRegion.PRINCIPAL: "A. Principal instructions and required constraints",
    AssemblyRegion.WORKSPACE: "B. Trusted workspace context",
    AssemblyRegion.TOOL_OUTPUT: "C. Tool outputs (non-authoritative unless policy says otherwise)",
    AssemblyRegion.EXTERNAL: "D. External-untrusted reference material (reference only)",
    AssemblyRegion.OUTPUT_CONTRACT: "E. Output contract",
}


class AssemblyEntry(BaseModel):
    """One verified admitted segment at its deterministic assembly location."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str
    segment_uid: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_hash: str
    region: AssemblyRegion
    trust_class: TrustClass
    semantic: Semantic
    effective_semantic: Semantic
    priority: Priority
    authoritative: bool
    content: str


class ContextAssembly(BaseModel):
    """Rendered active context plus its verified logical ordering metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: tuple[AssemblyEntry, ...]
    rendered: str
    assembly_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    character_count: int = Field(ge=0)
    included_segment_ids: tuple[str, ...]
    included_segment_uids: tuple[str, ...]
    unloaded_segment_ids: tuple[str, ...]
    unloaded_segment_uids: tuple[str, ...]


class ContextAssembler:
    """Build active context only from exact verified decision bindings."""

    def assemble(
        self,
        segments: Iterable[VerifiedSegment],
        decisions: Iterable[AdmissionDecision],
        *,
        activated_ids: frozenset[str] = frozenset(),
    ) -> ContextAssembly:
        verified_segments = tuple(segments)
        decision_list = tuple(decisions)
        self._validate_bindings(verified_segments, decision_list)
        decision_by_uid = {decision.segment_uid: decision for decision in decision_list}

        entries: list[AssemblyEntry] = []
        unloaded: list[VerifiedSegment] = []
        for verified_segment in verified_segments:
            segment = verified_segment.segment
            decision = decision_by_uid[verified_segment.provenance.segment_uid]
            if self._is_resident(decision, segment.id, activated_ids):
                entries.append(self._entry(verified_segment, decision))
            elif decision.status in {
                AdmissionStatus.ADMITTED_ON_DEMAND,
                AdmissionStatus.AVAILABLE_RETRIEVAL,
            }:
                unloaded.append(verified_segment)

        ordered = tuple(sorted(entries, key=self._entry_sort_key))
        rendered = self._render(ordered)
        return ContextAssembly(
            entries=ordered,
            rendered=rendered,
            assembly_hash=sha256_text(rendered),
            character_count=len(rendered),
            included_segment_ids=tuple(entry.segment_id for entry in ordered),
            included_segment_uids=tuple(entry.segment_uid for entry in ordered),
            unloaded_segment_ids=tuple(item.segment.id for item in unloaded),
            unloaded_segment_uids=tuple(item.provenance.segment_uid for item in unloaded),
        )

    @staticmethod
    def _validate_bindings(
        segments: tuple[VerifiedSegment, ...], decisions: tuple[AdmissionDecision, ...]
    ) -> None:
        logical_ids = [item.segment.id for item in segments]
        uids = [item.provenance.segment_uid for item in segments]
        decision_uids = [decision.segment_uid for decision in decisions]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("duplicate segment_id values are not assemblable")
        if len(uids) != len(set(uids)):
            raise ValueError("duplicate segment_uid values are not assemblable")
        if len(decision_uids) != len(set(decision_uids)):
            raise ValueError("duplicate decision segment_uid values are not assemblable")
        if set(uids) != set(decision_uids):
            raise ValueError("segment and decision UID sets must match exactly")
        decision_by_uid = {decision.segment_uid: decision for decision in decisions}
        for verified_segment in segments:
            segment = verified_segment.segment
            provenance = verified_segment.provenance
            decision = decision_by_uid[provenance.segment_uid]
            if (
                decision.segment_id != segment.id
                or decision.segment_hash != segment.content_hash
                or decision.verified_trust_class is not provenance.trust_class
            ):
                raise ValueError("decision does not exactly bind its verified segment")

    @staticmethod
    def _is_resident(
        decision: AdmissionDecision,
        segment_id: str,
        activated_ids: frozenset[str],
    ) -> bool:
        if decision.status is AdmissionStatus.ADMITTED_EAGER:
            return True
        return bool(
            segment_id in activated_ids
            and decision.status
            in {
                AdmissionStatus.ADMITTED_ON_DEMAND,
                AdmissionStatus.AVAILABLE_RETRIEVAL,
            }
        )

    @staticmethod
    def _entry(verified_segment: VerifiedSegment, decision: AdmissionDecision) -> AssemblyEntry:
        segment = verified_segment.segment
        trust_class = decision.verified_trust_class
        if trust_class is TrustClass.EXTERNAL_UNTRUSTED:
            region = AssemblyRegion.EXTERNAL
        elif decision.effective_semantic is Semantic.OUTPUT_CONTRACT and decision.authoritative:
            region = AssemblyRegion.OUTPUT_CONTRACT
        elif decision.authoritative:
            region = AssemblyRegion.PRINCIPAL
        elif trust_class is TrustClass.TOOL_OUTPUT:
            region = AssemblyRegion.TOOL_OUTPUT
        else:
            region = AssemblyRegion.WORKSPACE
        return AssemblyEntry(
            segment_id=segment.id,
            segment_uid=verified_segment.provenance.segment_uid,
            segment_hash=segment.content_hash,
            region=region,
            trust_class=trust_class,
            semantic=segment.semantic,
            effective_semantic=decision.effective_semantic,
            priority=segment.priority,
            authoritative=decision.authoritative,
            content=segment.content,
        )

    @staticmethod
    def _entry_sort_key(entry: AssemblyEntry) -> tuple[int, int, str, str]:
        return (
            _REGION_ORDER[entry.region],
            _PRIORITY_ORDER[entry.priority],
            entry.segment_id,
            entry.segment_uid,
        )

    @staticmethod
    def _render(entries: tuple[AssemblyEntry, ...]) -> str:
        sections: list[str] = []
        for region in AssemblyRegion:
            region_entries = tuple(entry for entry in entries if entry.region is region)
            if not region_entries:
                continue
            lines = [f"## {_REGION_TITLES[region]}"]
            for entry in region_entries:
                descriptor = canonical_json(
                    {
                        "authoritative": entry.authoritative,
                        "effective_semantic": entry.effective_semantic,
                        "id": entry.segment_id,
                        "segment_uid": entry.segment_uid,
                        "semantic": entry.semantic,
                        "trust_class": entry.trust_class,
                    }
                )
                lines.extend(
                    [
                        f"SEGMENT {descriptor}",
                        "CONTENT_BEGIN",
                        entry.content,
                        "CONTENT_END",
                    ]
                )
            sections.append("\n".join(lines))
        return "\n\n".join(sections) + ("\n" if sections else "")
