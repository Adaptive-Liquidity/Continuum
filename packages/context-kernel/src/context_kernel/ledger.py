"""Executable invariant ledger interfaces and deterministic evaluation mapping."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from context_kernel.canonical import canonical_hash


class EnforcementMode(StrEnum):
    OBSERVE = "observe"
    WARN = "warn"
    ENFORCE = "enforce"


class PredicateDecision(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class ActionType(StrEnum):
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    GIT_PUSH = "git_push"
    NETWORK_REQUEST = "network_request"
    APPROVAL_REQUIRED = "approval_required"
    FINAL_OUTPUT = "final_output"
    FILE_CHANGE = "file_change"
    PROTECTED_ACTION = "protected_action"
    RESOURCE_USE = "resource_use"


class Action(BaseModel):
    """A proposed effect or final output presented to the ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    action_type: ActionType
    parameters: dict[str, Any] = Field(default_factory=dict)
    attempted_at: datetime
    actor: str = "simulator"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.attempted_at.tzinfo is None:
            raise ValueError("attempted_at must be timezone-aware")
        return self

    def action_hash(self) -> str:
        """Hash the logical action while excluding its incidental attempt timestamp."""
        return canonical_hash(self.model_dump(exclude={"attempted_at"}))


class PredicateContext(BaseModel):
    """Runtime facts supplied by trusted code rather than action prose."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_root: str = "/workspace"
    allowed_git_remotes: frozenset[str] = frozenset({"origin"})
    protected_branches: frozenset[str] = frozenset({"main"})
    allowed_network_hosts: frozenset[str] = frozenset()
    valid_approval_tokens: frozenset[str] = frozenset()
    approval_events: frozenset[str] = frozenset()
    output_schema: dict[str, Any] | None = None
    approved_change_paths: frozenset[str] = frozenset({"/workspace"})
    successful_test_artifacts: frozenset[str] = frozenset()
    secret_values: frozenset[str] = frozenset()
    forbidden_action_types: frozenset[ActionType] = frozenset()
    resource_budget: int | None = None
    resource_used: int = Field(default=0, ge=0)


class PredicateResult(BaseModel):
    """Mode-independent semantic result returned by a predicate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    satisfied: bool
    reason_code: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    applicable: bool = True


class PredicateEvaluation(BaseModel):
    """Receipt-ready evaluation after enforcement mode is applied."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    predicate_id: str
    predicate_version: str
    mode: EnforcementMode
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: PredicateDecision
    violation_detected: bool
    reason_code: str
    explanation: str
    timestamp: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return self


class InvariantPredicate(ABC):
    """Extension interface for deterministic effect-boundary predicates."""

    predicate_id: str
    predicate_version: str = "1.0.0"

    @abstractmethod
    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        """Evaluate the proposed action without executing an effect."""

    def configuration(self) -> Mapping[str, Any]:
        """Return stable public configuration used in predicate-set hashing."""
        return {}


class PredicateRegistration(BaseModel):
    """A predicate paired with its operational mode."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    predicate: InvariantPredicate
    mode: EnforcementMode

    def descriptor(self) -> dict[str, Any]:
        return {
            "predicate_id": self.predicate.predicate_id,
            "predicate_version": self.predicate.predicate_version,
            "mode": self.mode,
            "configuration": dict(self.predicate.configuration()),
        }


class InvariantLedger:
    """Evaluate registered predicates in stable identifier order."""

    def __init__(self, registrations: Iterable[PredicateRegistration]) -> None:
        ordered = sorted(
            registrations,
            key=lambda registration: (
                registration.predicate.predicate_id,
                registration.predicate.predicate_version,
                registration.mode.value,
            ),
        )
        ids = [registration.predicate.predicate_id for registration in ordered]
        if len(ids) != len(set(ids)):
            raise ValueError("predicate_id values must be unique within a ledger")
        self.registrations = tuple(ordered)

    @property
    def predicate_set_hash(self) -> str:
        return canonical_hash([registration.descriptor() for registration in self.registrations])

    def evaluate(
        self,
        action: Action,
        context: PredicateContext,
        *,
        evaluated_at: datetime,
    ) -> tuple[PredicateEvaluation, ...]:
        if evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        evaluations: list[PredicateEvaluation] = []
        for registration in self.registrations:
            result = registration.predicate.evaluate(action, context)
            decision = self._decision(result, registration.mode)
            evaluations.append(
                PredicateEvaluation(
                    predicate_id=registration.predicate.predicate_id,
                    predicate_version=registration.predicate.predicate_version,
                    mode=registration.mode,
                    input_hash=action.action_hash(),
                    decision=decision,
                    violation_detected=result.applicable and not result.satisfied,
                    reason_code=result.reason_code,
                    explanation=result.explanation,
                    timestamp=evaluated_at,
                )
            )
        return tuple(evaluations)

    @staticmethod
    def _decision(result: PredicateResult, mode: EnforcementMode) -> PredicateDecision:
        if not result.applicable or result.satisfied:
            return PredicateDecision.PASS
        if mode is EnforcementMode.OBSERVE:
            return PredicateDecision.PASS
        if mode is EnforcementMode.WARN:
            return PredicateDecision.WARN
        return PredicateDecision.BLOCK
