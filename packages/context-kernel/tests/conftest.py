"""Shared deterministic fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from context_kernel.admission import AdmissionPolicy
from context_kernel.ledger import Action, ActionType
from context_kernel.models import (
    ContextSegment,
    LoadMode,
    Priority,
    Semantic,
    TrustClass,
    VerifiedSegment,
)
from context_kernel.provenance import InMemoryProvenanceAuthority

FIXED_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
TEST_AUTHORITY = InMemoryProvenanceAuthority(
    keys={"test-key-v1": b"aeon-test-provenance-key-v1"},
    active_key_id="test-key-v1",
    audience="aeon-context-kernel",
    policy_scope="test-fixtures/v1",
)


@pytest.fixture
def fixed_time() -> datetime:
    return FIXED_TIME


@pytest.fixture
def provenance_authority() -> InMemoryProvenanceAuthority:
    return TEST_AUTHORITY


def make_policy(
    authority: InMemoryProvenanceAuthority = TEST_AUTHORITY,
    **kwargs: Any,
) -> AdmissionPolicy:
    """Build an admission policy with a fixture-owned runtime clock."""
    return AdmissionPolicy(
        authority,
        verification_clock=lambda: FIXED_TIME,
        **kwargs,
    )


def make_raw_segment(
    segment_id: str,
    content: str,
    *,
    semantic: Semantic = Semantic.CONTEXT,
    priority: Priority = Priority.SUPPORTING,
    load_mode: LoadMode = LoadMode.EAGER,
    trust_class: TrustClass = TrustClass.TRUSTED_WORKSPACE,
    metadata: dict[str, Any] | None = None,
) -> ContextSegment:
    return ContextSegment(
        id=segment_id,
        content=content,
        source_id=f"source:{segment_id}",
        created_at=FIXED_TIME,
        semantic=semantic,
        priority=priority,
        load_mode=load_mode,
        trust_class=trust_class,
        metadata=metadata or {},
    )


def make_segment(
    segment_id: str,
    content: str,
    *,
    semantic: Semantic = Semantic.CONTEXT,
    priority: Priority = Priority.SUPPORTING,
    load_mode: LoadMode = LoadMode.EAGER,
    trust_class: TrustClass = TrustClass.TRUSTED_WORKSPACE,
    metadata: dict[str, Any] | None = None,
) -> VerifiedSegment:
    raw = make_raw_segment(
        segment_id,
        content,
        semantic=semantic,
        priority=priority,
        load_mode=load_mode,
        trust_class=trust_class,
        metadata=metadata,
    )
    return TEST_AUTHORITY.issue(raw, trust_class=trust_class, issued_at=FIXED_TIME)


def make_action(
    action_type: ActionType = ActionType.FILESYSTEM_WRITE,
    *,
    parameters: dict[str, Any] | None = None,
) -> Action:
    return Action(
        id="action-1",
        action_type=action_type,
        parameters=parameters or {},
        attempted_at=FIXED_TIME,
    )
