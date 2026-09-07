"""Verifier-issued provenance for AEON's local deterministic runtime.

The in-memory HMAC authority is a test/simulator trust root. Production hosts must
provide an equivalent protected issuer and verifier rather than reuse this key.
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Final

from context_kernel.canonical import canonical_hash, canonical_json
from context_kernel.models import ContextSegment, TrustClass, VerifiedProvenance, VerifiedSegment

_DEFAULT_TTL: Final[timedelta] = timedelta(hours=1)


class ProvenanceVerificationError(ValueError):
    """Raised when an attestation is not valid for a submitted segment."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _payload(provenance: VerifiedProvenance) -> dict[str, object]:
    return provenance.model_dump(exclude={"attestation_id", "signature"}, mode="python")


def _signature(signing_key: bytes, provenance: VerifiedProvenance) -> str:
    return hmac.new(
        signing_key,
        canonical_json(_payload(provenance)).encode("utf-8"),
        sha256,
    ).hexdigest()


class InMemoryProvenanceAuthority:
    """Injectable deterministic provenance issuer and verifier for local fixtures."""

    def __init__(
        self,
        *,
        keys: dict[str, bytes],
        active_key_id: str,
        audience: str,
        policy_scope: str,
        revoked_attestation_ids: frozenset[str] = frozenset(),
    ) -> None:
        if not keys:
            raise ValueError("at least one verifier key is required")
        if active_key_id not in keys:
            raise ValueError("active_key_id must identify a configured verifier key")
        if not audience:
            raise ValueError("audience must be non-empty")
        if not policy_scope:
            raise ValueError("policy_scope must be non-empty")
        self._keys = dict(keys)
        self.active_key_id = active_key_id
        self.audience = audience
        self.policy_scope = policy_scope
        self.revoked_attestation_ids = revoked_attestation_ids

    def issue(
        self,
        segment: ContextSegment,
        *,
        trust_class: TrustClass,
        issued_at: datetime,
        expires_at: datetime | None = None,
        nonce: str | None = None,
    ) -> VerifiedSegment:
        """Issue an immutable attestation for exact current segment bytes."""
        if issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")
        expires = expires_at or (issued_at + _DEFAULT_TTL)
        if expires.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if expires <= issued_at:
            raise ValueError("expires_at must be after issued_at")
        selected_nonce = nonce or canonical_hash(
            {
                "logical_id": segment.id,
                "content_hash": segment.content_hash,
                "issued_at": issued_at,
                "issuer_key_id": self.active_key_id,
            }
        )
        segment_uid = canonical_hash(
            {
                "source_id": segment.source_id,
                "content_hash": segment.content_hash,
                "issuer_key_id": self.active_key_id,
                "audience": self.audience,
                "policy_scope": self.policy_scope,
                "nonce": selected_nonce,
            }
        )
        unsigned = VerifiedProvenance(
            segment_uid=segment_uid,
            logical_id=segment.id,
            source_id=segment.source_id,
            content_hash=segment.content_hash,
            trust_class=trust_class,
            issuer_key_id=self.active_key_id,
            audience=self.audience,
            policy_scope=self.policy_scope,
            issued_at=issued_at,
            expires_at=expires,
            nonce=selected_nonce,
            attestation_id="0" * 64,
            signature="0" * 64,
        )
        attestation_id = canonical_hash(_payload(unsigned))
        provisional = unsigned.model_copy(update={"attestation_id": attestation_id})
        signature = _signature(self._keys[self.active_key_id], provisional)
        provenance = provisional.model_copy(update={"signature": signature})
        return VerifiedSegment(segment=segment, provenance=provenance)

    def verify(
        self,
        verified_segment: VerifiedSegment,
        *,
        now: datetime,
        expected_audience: str | None = None,
        expected_policy_scope: str | None = None,
    ) -> None:
        """Verify issuer identity, signed claims, lifecycle, and exact binding."""
        if now.tzinfo is None:
            raise ValueError("verification time must be timezone-aware")
        provenance = verified_segment.provenance
        segment = verified_segment.segment
        if provenance.issuer_key_id not in self._keys:
            raise ProvenanceVerificationError("unknown_issuer_key", "Issuer key is not trusted.")
        if provenance.audience != (expected_audience or self.audience):
            raise ProvenanceVerificationError(
                "audience_mismatch", "Attestation audience does not match."
            )
        if provenance.policy_scope != (expected_policy_scope or self.policy_scope):
            raise ProvenanceVerificationError(
                "policy_scope_mismatch", "Attestation policy scope does not match."
            )
        if provenance.attestation_id in self.revoked_attestation_ids:
            raise ProvenanceVerificationError(
                "attestation_revoked", "Attestation has been revoked."
            )
        if now < provenance.issued_at:
            raise ProvenanceVerificationError(
                "attestation_not_yet_valid", "Attestation is not valid yet."
            )
        if now >= provenance.expires_at:
            raise ProvenanceVerificationError("attestation_expired", "Attestation has expired.")
        expected_attestation_id = canonical_hash(_payload(provenance))
        if not hmac.compare_digest(provenance.attestation_id, expected_attestation_id):
            raise ProvenanceVerificationError(
                "attestation_id_mismatch", "Attestation ID does not match claims."
            )
        expected_signature = _signature(self._keys[provenance.issuer_key_id], provenance)
        if not hmac.compare_digest(provenance.signature, expected_signature):
            raise ProvenanceVerificationError(
                "invalid_signature", "Attestation signature is invalid."
            )
        if provenance.logical_id != segment.id:
            raise ProvenanceVerificationError(
                "logical_id_mismatch", "Attestation logical ID does not match segment."
            )
        if provenance.source_id != segment.source_id:
            raise ProvenanceVerificationError(
                "source_id_mismatch", "Attestation source ID does not match segment."
            )
        if provenance.content_hash != segment.content_hash:
            raise ProvenanceVerificationError(
                "content_hash_mismatch", "Attestation hash does not match exact segment content."
            )


def local_scenario_authority() -> InMemoryProvenanceAuthority:
    """Return the deterministic local issuer used only by simulator fixtures."""
    return InMemoryProvenanceAuthority(
        keys={"scenario-fixture-key-v1": b"aeon-simulator-fixture-key-v1"},
        active_key_id="scenario-fixture-key-v1",
        audience="aeon-context-kernel",
        policy_scope="simulator-fixtures/v1",
    )


def fixed_verification_time() -> datetime:
    """Use a controlled default only for local deterministic fixture issuance."""
    return datetime(2026, 1, 1, tzinfo=UTC)
