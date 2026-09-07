"""Deterministic admission over verifier-bound segment provenance."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime

from context_kernel.canonical import canonical_hash
from context_kernel.models import (
    AdmissionBatch,
    AdmissionDecision,
    AdmissionReason,
    AdmissionStatus,
    ContextSegment,
    LoadMode,
    Semantic,
    TrustClass,
    VerifiedSegment,
)
from context_kernel.provenance import InMemoryProvenanceAuthority, ProvenanceVerificationError

_STATUS_BY_LOAD_MODE: dict[LoadMode, AdmissionStatus] = {
    LoadMode.EAGER: AdmissionStatus.ADMITTED_EAGER,
    LoadMode.ON_DEMAND: AdmissionStatus.ADMITTED_ON_DEMAND,
    LoadMode.RETRIEVAL: AdmissionStatus.AVAILABLE_RETRIEVAL,
}

_REASON_BY_LOAD_MODE: dict[LoadMode, AdmissionReason] = {
    LoadMode.EAGER: AdmissionReason.LOAD_MODE_EAGER,
    LoadMode.ON_DEMAND: AdmissionReason.LOAD_MODE_ON_DEMAND,
    LoadMode.RETRIEVAL: AdmissionReason.LOAD_MODE_RETRIEVAL,
}

_EXTERNAL_REASON_BY_LOAD_MODE: dict[LoadMode, AdmissionReason] = {
    LoadMode.EAGER: AdmissionReason.EXTERNAL_REFERENCE_EAGER,
    LoadMode.ON_DEMAND: AdmissionReason.EXTERNAL_REFERENCE_ON_DEMAND,
    LoadMode.RETRIEVAL: AdmissionReason.EXTERNAL_REFERENCE_RETRIEVAL,
}

_AUTHORITY_SEMANTICS = {
    Semantic.INSTRUCTION,
    Semantic.CONSTRAINT,
    Semantic.OUTPUT_CONTRACT,
    Semantic.APPROVAL,
}


class AdmissionPolicy:
    """Classify segments using verified provenance, never caller trust claims."""

    def __init__(
        self,
        authority: InMemoryProvenanceAuthority,
        *,
        verification_clock: Callable[[], datetime],
        allowed_trust_classes: frozenset[TrustClass] | None = None,
        trusted_workspace_instruction_authority: bool = False,
    ) -> None:
        self.authority = authority
        self._verification_clock = verification_clock
        self.allowed_trust_classes = (
            frozenset(TrustClass) if allowed_trust_classes is None else allowed_trust_classes
        )
        self.trusted_workspace_instruction_authority = trusted_workspace_instruction_authority
        self._consumed_attestation_ids: set[str] = set()

    def admit(self, verified_segment: VerifiedSegment) -> AdmissionDecision:
        """Return a decision using only the policy's trusted runtime clock."""
        return self._admit_at(verified_segment, verification_time=self._verification_time())

    def _admit_at(
        self,
        verified_segment: VerifiedSegment,
        *,
        verification_time: datetime,
    ) -> AdmissionDecision:
        """Return a deterministic decision at one trusted runtime instant."""
        segment = verified_segment.segment
        provenance = verified_segment.provenance
        try:
            self.authority.verify(verified_segment, now=verification_time)
        except ProvenanceVerificationError as error:
            return self._terminal(
                verified_segment,
                AdmissionStatus.REJECTED,
                AdmissionReason.PROVENANCE_INVALID,
                f"Verified provenance was rejected: {error.code}.",
            )

        if provenance.attestation_id in self._consumed_attestation_ids:
            return self._terminal(
                verified_segment,
                AdmissionStatus.REJECTED,
                AdmissionReason.PROVENANCE_INVALID,
                "Verified provenance was rejected: attestation_replayed.",
            )
        self._consumed_attestation_ids.add(provenance.attestation_id)

        trust_class = provenance.trust_class
        if trust_class not in self.allowed_trust_classes:
            return self._terminal(
                verified_segment,
                AdmissionStatus.REJECTED,
                AdmissionReason.TRUST_CLASS_DISALLOWED,
                "The runtime policy does not allow this verified trust class.",
            )

        status = _STATUS_BY_LOAD_MODE[segment.load_mode]
        effective_semantic = segment.semantic
        authoritative = self._is_authoritative(segment.semantic, trust_class)

        if trust_class is TrustClass.EXTERNAL_UNTRUSTED:
            effective_semantic = Semantic.REFERENCE
            authoritative = False
            if segment.semantic in _AUTHORITY_SEMANTICS:
                reason = AdmissionReason.EXTERNAL_AUTHORITY_CLAIM_DEMOTED
                detail = (
                    "External-untrusted material remains available as labeled "
                    "reference and cannot enter an authoritative instruction region."
                )
            else:
                reason = _EXTERNAL_REASON_BY_LOAD_MODE[segment.load_mode]
                detail = "External-untrusted material is admitted only as labeled reference."
        else:
            reason = _REASON_BY_LOAD_MODE[segment.load_mode]
            detail = "The segment was admitted according to verified provenance and load mode."

        return AdmissionDecision(
            segment_id=segment.id,
            segment_uid=provenance.segment_uid,
            segment_hash=segment.content_hash,
            verified_trust_class=trust_class,
            status=status,
            reason_code=reason,
            effective_semantic=effective_semantic,
            authoritative=authoritative,
            detail=detail,
        )

    def admit_unverified(self, segment: ContextSegment) -> AdmissionDecision:
        """Return an explicit non-authoritative rejection for raw caller input."""
        return AdmissionDecision(
            segment_id=segment.id,
            segment_uid=canonical_hash(
                {"unverified_logical_id": segment.id, "content_hash": segment.content_hash}
            ),
            segment_hash=segment.content_hash,
            verified_trust_class=TrustClass.EXTERNAL_UNTRUSTED,
            status=AdmissionStatus.REJECTED,
            reason_code=AdmissionReason.PROVENANCE_REQUIRED,
            effective_semantic=segment.semantic,
            authoritative=False,
            detail="Caller-submitted content requires verifier-issued provenance before admission.",
        )

    def admit_many(self, segments: Iterable[VerifiedSegment]) -> AdmissionBatch:
        """Admit a one-to-one verified batch while rejecting identity collisions."""
        segment_list = tuple(segments)
        logical_ids = [item.segment.id for item in segment_list]
        uids = [item.provenance.segment_uid for item in segment_list]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("duplicate segment_id values are not admissible")
        if len(uids) != len(set(uids)):
            raise ValueError("duplicate segment_uid values are not admissible")
        verification_time = self._verification_time()
        decisions = tuple(
            self._admit_at(segment, verification_time=verification_time) for segment in segment_list
        )
        admitted = tuple(
            decision.segment_id
            for decision in decisions
            if decision.status
            in {
                AdmissionStatus.ADMITTED_EAGER,
                AdmissionStatus.ADMITTED_ON_DEMAND,
                AdmissionStatus.AVAILABLE_RETRIEVAL,
            }
        )
        omitted = tuple(
            decision.segment_id
            for decision in decisions
            if decision.status in {AdmissionStatus.OMITTED, AdmissionStatus.EVICTED}
        )
        rejected = tuple(
            decision.segment_id
            for decision in decisions
            if decision.status is AdmissionStatus.REJECTED
        )
        return AdmissionBatch(
            decisions=decisions,
            admitted_segment_ids=admitted,
            omitted_segment_ids=omitted,
            rejected_segment_ids=rejected,
        )

    def _verification_time(self) -> datetime:
        """Read the verifier time from trusted runtime policy, never segment data."""
        verification_time = self._verification_clock()
        if verification_time.tzinfo is None:
            raise ValueError("verification clock must return a timezone-aware datetime")
        return verification_time

    def _is_authoritative(self, semantic: Semantic, trust_class: TrustClass) -> bool:
        if semantic not in _AUTHORITY_SEMANTICS:
            return False
        if trust_class is TrustClass.PRINCIPAL:
            return True
        return bool(
            self.trusted_workspace_instruction_authority
            and trust_class is TrustClass.TRUSTED_WORKSPACE
        )

    @staticmethod
    def _terminal(
        verified_segment: VerifiedSegment,
        status: AdmissionStatus,
        reason: AdmissionReason,
        detail: str,
    ) -> AdmissionDecision:
        return AdmissionDecision(
            segment_id=verified_segment.segment.id,
            segment_uid=verified_segment.provenance.segment_uid,
            segment_hash=verified_segment.segment.content_hash,
            verified_trust_class=verified_segment.provenance.trust_class,
            status=status,
            reason_code=reason,
            effective_semantic=verified_segment.segment.semantic,
            authoritative=False,
            detail=detail,
        )
