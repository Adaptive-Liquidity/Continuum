"""Template tests for a new AEON predicate.

Update the import path, class name, action type, parameters, and reason codes to
match the concrete predicate.
"""

from datetime import UTC, datetime

import pytest
from context_kernel.predicates.example import ExamplePolicyPredicate

from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.interception import ActionOutcome, SafeActionInterceptor
from context_kernel.ledger import (
    Action,
    ActionType,
    EnforcementMode,
    InvariantLedger,
    PredicateContext,
    PredicateDecision,
    PredicateRegistration,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def make_action(
    *, target: str, action_type: ActionType = ActionType.PROTECTED_ACTION
) -> Action:
    return Action(
        id=f"example-{target}",
        action_type=action_type,
        parameters={"target": target},
        attempted_at=FIXED_TIME,
    )


@pytest.mark.parametrize(
    ("mode", "decision", "outcome", "effect_count"),
    [
        (EnforcementMode.OBSERVE, PredicateDecision.PASS, ActionOutcome.ALLOWED, 1),
        (EnforcementMode.WARN, PredicateDecision.WARN, ActionOutcome.WARNED, 1),
        (EnforcementMode.ENFORCE, PredicateDecision.BLOCK, ActionOutcome.BLOCKED, 0),
    ],
)
def test_violation_maps_each_mode_before_effect(
    mode: EnforcementMode,
    decision: PredicateDecision,
    outcome: ActionOutcome,
    effect_count: int,
) -> None:
    predicate = ExamplePolicyPredicate(allowed_targets=frozenset({"approved"}))
    adapter = SimulatedEffectAdapter()
    interceptor = SafeActionInterceptor(
        InvariantLedger([PredicateRegistration(predicate=predicate, mode=mode)]),
        adapter,
    )

    record = interceptor.attempt(
        make_action(target="forbidden"),
        PredicateContext(),
        evaluated_at=FIXED_TIME,
    )

    assert record.evaluations[0].violation_detected is True
    assert record.evaluations[0].decision is decision
    assert record.outcome is outcome
    assert record.effect_executed is (effect_count == 1)
    assert len(adapter.state.effect_log) == effect_count


def test_valid_action_passes_and_executes_in_enforce_mode() -> None:
    predicate = ExamplePolicyPredicate(allowed_targets=frozenset({"approved"}))
    adapter = SimulatedEffectAdapter()
    interceptor = SafeActionInterceptor(
        InvariantLedger(
            [PredicateRegistration(predicate=predicate, mode=EnforcementMode.ENFORCE)]
        ),
        adapter,
    )

    record = interceptor.attempt(
        make_action(target="approved"),
        PredicateContext(),
        evaluated_at=FIXED_TIME,
    )

    assert record.outcome is ActionOutcome.ALLOWED
    assert record.evaluations[0].violation_detected is False
    assert len(adapter.state.effect_log) == 1


def test_unrelated_action_is_not_applicable() -> None:
    predicate = ExamplePolicyPredicate(allowed_targets=frozenset({"approved"}))
    result = predicate.evaluate(
        make_action(target="forbidden", action_type=ActionType.FILESYSTEM_WRITE),
        PredicateContext(),
    )

    assert result.applicable is False
    assert result.satisfied is True
    assert result.reason_code == "not_applicable"


def test_configuration_changes_predicate_set_hash() -> None:
    first = InvariantLedger(
        [
            PredicateRegistration(
                predicate=ExamplePolicyPredicate(allowed_targets=frozenset({"a"})),
                mode=EnforcementMode.ENFORCE,
            )
        ]
    )
    second = InvariantLedger(
        [
            PredicateRegistration(
                predicate=ExamplePolicyPredicate(allowed_targets=frozenset({"b"})),
                mode=EnforcementMode.ENFORCE,
            )
        ]
    )

    assert first.predicate_set_hash != second.predicate_set_hash
