"""DCA domain models — one per mandatory responsibility."""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from base import BaseDocument, utcnow_iso

# ---------- Responsibility 1: Principal Identity & Responsibility ----------
VeraState = Literal["ACTIVE", "SUSPENDED", "DECOMMISSIONED"]


class VERA(BaseDocument):
    """Verifiable Entity with Revocable Authority — the persistent principal."""
    trust_domain: str
    principal_id: str  # stable across models, sessions, hosts
    display_name: str
    mandate: str  # what the VERA is responsible for
    state: VeraState = "ACTIVE"
    representation: dict[str, Any] = Field(default_factory=dict)  # credential bindings


# ---------- Responsibility 2: Environment & Runtime Continuity ----------
PlacementState = Literal["ACTIVE", "FENCED", "TERMINATED"]


class RuntimePlacement(BaseDocument):
    """floks-pc Agent Computer: 1 VERA ↔ 1 isolated computer (provider-backed)."""
    vera_id: str
    provider: str = "runloop-devbox"  # v1 provider per floks-pc AUTHORITY.md
    computer_id: str
    lease_epoch: int = 1
    lease_expires_at: str
    state: PlacementState = "ACTIVE"
    capabilities: list[str] = Field(default_factory=list)  # scoped, not authority
    surface: dict[str, Any] = Field(default_factory=dict)  # browser, fs, shell


# ---------- Responsibility 3: Durable State & Memory ----------
class MemoryFact(BaseDocument):
    """AEON-IQ memory: extracted fact bound to VERA, with provenance."""
    vera_id: str
    session_id: Optional[str] = None
    kind: Literal["semantic", "episodic", "operational", "derived"] = "semantic"
    content: str
    source: dict[str, Any] = Field(default_factory=dict)  # provenance
    retention_policy: Literal["retain", "ttl", "purge_on_revoke"] = "retain"


# ---------- Responsibility 4: Authority & Capability Governance ----------
GrantState = Literal["ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED"]


class AuthorityGrant(BaseDocument):
    """Genesis-style delegated authority: scope + ceiling + expiry."""
    vera_id: str
    granted_by: str  # VERA or human principal
    capability: str  # e.g. "effect:http.fetch", "effect:solana.sign"
    scope: dict[str, Any] = Field(default_factory=dict)  # ceiling constraints
    expires_at: str
    state: GrantState = "ACTIVE"
    parent_grant_id: Optional[str] = None  # attenuation chain


# ---------- Responsibility 5: Effectful Execution ----------
EffectOutcome = Literal["PREPARED", "DISPATCHED", "COMMITTED", "DENIED", "UNKNOWN", "COMPENSATED"]


class Effect(BaseDocument):
    """Nexus-mediated effect execution with fail-closed capability gate."""
    vera_id: str
    session_id: Optional[str] = None
    action_id: str  # unique action identity (deduplication)
    capability_required: str
    grant_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    outcome: EffectOutcome = "PREPARED"
    denial_reason: Optional[str] = None
    result: dict[str, Any] = Field(default_factory=dict)
    executed_at: Optional[str] = None


# ---------- Responsibility 6: Evidence, Verification & Recovery ----------
class EvidenceEntry(BaseDocument):
    """Hash-chained JSONL-style evidence, context-kernel-inspired."""
    seq: int
    prev_hash: str
    self_hash: str
    kind: Literal[
        "vera.created", "vera.transition",
        "placement.leased", "placement.fenced",
        "memory.write", "memory.recall",
        "grant.issued", "grant.revoked",
        "effect.prepared", "effect.dispatched", "effect.committed", "effect.denied", "effect.unknown",
        "session.opened", "session.closed", "handoff",
    ]
    subject_id: str  # id of the affected object
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------- Responsibility 7: Coordination & Interconnect ----------
SessionState = Literal["OPEN", "CLOSED", "HANDED_OFF"]


class Session(BaseDocument):
    """Authenticated logical session for a VERA on a placement."""
    vera_id: str
    placement_id: str
    state: SessionState = "OPEN"
    opened_at: str = Field(default_factory=utcnow_iso)
    closed_at: Optional[str] = None
    handoff_to: Optional[str] = None  # another vera_id


# ---------- Request/Response DTOs ----------
class CreateVeraRequest(BaseModel):
    trust_domain: str
    principal_id: str
    display_name: str
    mandate: str


class LeasePlacementRequest(BaseModel):
    vera_id: str
    provider: str = "runloop-devbox"
    ttl_seconds: int = 3600
    capabilities: list[str] = Field(default_factory=list)


class WriteMemoryRequest(BaseModel):
    vera_id: str
    session_id: Optional[str] = None
    kind: Literal["semantic", "episodic", "operational", "derived"] = "semantic"
    content: str
    source: dict[str, Any] = Field(default_factory=dict)


class IssueGrantRequest(BaseModel):
    vera_id: str
    granted_by: str
    capability: str
    scope: dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = 3600
    parent_grant_id: Optional[str] = None


class ProposeEffectRequest(BaseModel):
    vera_id: str
    session_id: Optional[str] = None
    action_id: str
    capability_required: str
    payload: dict[str, Any] = Field(default_factory=dict)


class OpenSessionRequest(BaseModel):
    vera_id: str
    placement_id: str


class HandoffRequest(BaseModel):
    session_id: str
    handoff_to_vera_id: str


# ---------- Regency (governance) ----------
class Mandate(BaseDocument):
    """A governing instrument scoping what a VERA / role may do."""
    title: str
    description: str
    envelope: dict[str, Any] = Field(default_factory=dict)  # ceiling constraints
    state: Literal["ACTIVE", "SUSPENDED", "DISSOLVED"] = "ACTIVE"


class Role(BaseDocument):
    """A named bundle of capabilities that can be assigned to VERAs."""
    name: str
    capabilities: list[str] = Field(default_factory=list)
    mandate_id: Optional[str] = None


class RoleAssignment(BaseDocument):
    vera_id: str
    role_id: str
    assigned_by: str
    state: Literal["ACTIVE", "WITHDRAWN", "SUSPENDED", "EXPELLED"] = "ACTIVE"


class CreateMandateRequest(BaseModel):
    title: str
    description: str
    envelope: dict[str, Any] = Field(default_factory=dict)


class CreateRoleRequest(BaseModel):
    name: str
    capabilities: list[str] = Field(default_factory=list)
    mandate_id: Optional[str] = None


class AssignRoleRequest(BaseModel):
    vera_id: str
    role_id: str
    assigned_by: str = "regency-console"


class EmergencySuspendRequest(BaseModel):
    vera_ids: list[str]
    reason: str
    initiated_by: str = "regency-console"
