"""Typed logical context, verified provenance, and admission records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from context_kernel.canonical import sha256_text


class Semantic(StrEnum):
    INSTRUCTION = "instruction"
    CONSTRAINT = "constraint"
    CONTEXT = "context"
    REFERENCE = "reference"
    TOOL_OUTPUT = "tool_output"
    OUTPUT_CONTRACT = "output_contract"
    APPROVAL = "approval"
    HANDOFF_SUMMARY = "handoff_summary"


class Priority(StrEnum):
    REQUIRED = "required"
    IMPORTANT = "important"
    SUPPORTING = "supporting"


class LoadMode(StrEnum):
    EAGER = "eager"
    ON_DEMAND = "on_demand"
    RETRIEVAL = "retrieval"


class TrustClass(StrEnum):
    PRINCIPAL = "principal"
    TRUSTED_WORKSPACE = "trusted_workspace"
    TOOL_OUTPUT = "tool_output"
    EXTERNAL_UNTRUSTED = "external_untrusted"


class AdmissionStatus(StrEnum):
    ADMITTED_EAGER = "admitted_eager"
    ADMITTED_ON_DEMAND = "admitted_on_demand"
    AVAILABLE_RETRIEVAL = "available_retrieval"
    OMITTED = "omitted"
    EVICTED = "evicted"
    REJECTED = "rejected"


class AdmissionReason(StrEnum):
    LOAD_MODE_EAGER = "load_mode_eager"
    LOAD_MODE_ON_DEMAND = "load_mode_on_demand"
    LOAD_MODE_RETRIEVAL = "load_mode_retrieval"
    EXTERNAL_REFERENCE_EAGER = "external_reference_eager"
    EXTERNAL_REFERENCE_ON_DEMAND = "external_reference_on_demand"
    EXTERNAL_REFERENCE_RETRIEVAL = "external_reference_retrieval"
    EXTERNAL_AUTHORITY_CLAIM_DEMOTED = "external_authority_claim_demoted"
    DISABLED_BY_POLICY = "disabled_by_policy"
    AUTHENTICATION_REQUIRED = "authentication_required"
    TRUST_CLASS_DISALLOWED = "trust_class_disallowed"
    PROVENANCE_REQUIRED = "provenance_required"
    PROVENANCE_INVALID = "provenance_invalid"
    DUPLICATE_SEGMENT_ID = "duplicate_segment_id"
    DUPLICATE_SEGMENT_UID = "duplicate_segment_uid"
    DECISION_BINDING_MISMATCH = "decision_binding_mismatch"
    COMPACTION_EVICTION = "compaction_eviction"
    BASELINE_FLAT_ADMISSION = "baseline_flat_admission"


class ContextSegment(BaseModel):
    """Untrusted logical content claims with an exact UTF-8 content hash.

    A segment's claimed trust class and metadata are input data only. They never
    become authoritative unless a separate ``VerifiedProvenance`` attestation
    is accepted by the admission policy.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    content: str
    content_hash: str = Field(default="", pattern=r"^[0-9a-f]{64}$")
    source_id: str = Field(min_length=1)
    created_at: datetime
    semantic: Semantic
    priority: Priority
    load_mode: LoadMode
    trust_class: TrustClass
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_and_verify_hash(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        content = normalized.get("content")
        if not isinstance(content, str):
            return normalized
        expected = sha256_text(content)
        supplied = normalized.get("content_hash")
        if supplied is None or supplied == "":
            normalized["content_hash"] = expected
        elif supplied != expected:
            raise ValueError("content_hash does not match content")
        return normalized

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self


# Public alias used by host adapters that want to distinguish raw input from
# verifier-bound content without breaking existing logical-context imports.
SubmittedSegment = ContextSegment


class VerifiedProvenance(BaseModel):
    """An immutable issuer-signed binding of identity, exact bytes, and trust."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_uid: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    trust_class: TrustClass
    issuer_key_id: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    policy_scope: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=1)
    attestation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("provenance timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("provenance expiry must follow issuance")
        return self


class VerifiedSegment(BaseModel):
    """A submitted segment bound one-to-one to immutable verified provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment: ContextSegment
    provenance: VerifiedProvenance

    @model_validator(mode="after")
    def require_exact_binding(self) -> Self:
        if self.provenance.logical_id != self.segment.id:
            raise ValueError("provenance logical_id does not match segment")
        if self.provenance.source_id != self.segment.source_id:
            raise ValueError("provenance source_id does not match segment")
        if self.provenance.content_hash != self.segment.content_hash:
            raise ValueError("provenance content_hash does not match segment")
        return self

    @property
    def identity_key(self) -> tuple[str, str]:
        return (self.provenance.segment_uid, self.segment.content_hash)


class AdmissionDecision(BaseModel):
    """A deterministic decision bound to one verified segment identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    segment_id: str
    segment_uid: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    verified_trust_class: TrustClass
    status: AdmissionStatus
    reason_code: AdmissionReason
    effective_semantic: Semantic
    authoritative: bool
    detail: str


class AdmissionBatch(BaseModel):
    """Stable admission output preserving controlled submitted-segment order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decisions: tuple[AdmissionDecision, ...]
    admitted_segment_ids: tuple[str, ...]
    omitted_segment_ids: tuple[str, ...]
    rejected_segment_ids: tuple[str, ...]
