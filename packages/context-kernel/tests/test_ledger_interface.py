from __future__ import annotations

from conftest import FIXED_TIME, make_action
from context_kernel.ledger import (
    EnforcementMode,
    InvariantLedger,
    InvariantPredicate,
    PredicateContext,
    PredicateDecision,
    PredicateRegistration,
    PredicateResult,
)


class ConfigurablePredicate(InvariantPredicate):
    def __init__(self, predicate_id: str, *, satisfied: bool, value: int = 1) -> None:
        self.predicate_id = predicate_id
        self.satisfied = satisfied
        self.value = value

    def evaluate(self, action: object, context: object) -> PredicateResult:
        del action, context
        return PredicateResult(
            satisfied=self.satisfied,
            reason_code="test_result",
            explanation="Deterministic test predicate result.",
        )

    def configuration(self) -> dict[str, int]:
        return {"value": self.value}


def test_modes_map_one_violation_to_observe_warn_and_block() -> None:
    expected = {
        EnforcementMode.OBSERVE: PredicateDecision.PASS,
        EnforcementMode.WARN: PredicateDecision.WARN,
        EnforcementMode.ENFORCE: PredicateDecision.BLOCK,
    }
    action = make_action()

    for mode, decision in expected.items():
        ledger = InvariantLedger(
            [
                PredicateRegistration(
                    predicate=ConfigurablePredicate("failure", satisfied=False),
                    mode=mode,
                )
            ]
        )
        evaluation = ledger.evaluate(action, PredicateContext(), evaluated_at=FIXED_TIME)[0]
        assert evaluation.decision is decision
        assert evaluation.violation_detected is True
        assert evaluation.input_hash == action.action_hash()


def test_satisfied_predicate_passes_in_all_modes() -> None:
    for mode in EnforcementMode:
        ledger = InvariantLedger(
            [
                PredicateRegistration(
                    predicate=ConfigurablePredicate("success", satisfied=True),
                    mode=mode,
                )
            ]
        )
        evaluation = ledger.evaluate(make_action(), PredicateContext(), evaluated_at=FIXED_TIME)[0]
        assert evaluation.decision is PredicateDecision.PASS
        assert evaluation.violation_detected is False


def test_predicate_set_hash_and_evaluation_order_are_registration_order_independent() -> None:
    alpha = PredicateRegistration(
        predicate=ConfigurablePredicate("alpha", satisfied=True, value=10),
        mode=EnforcementMode.ENFORCE,
    )
    beta = PredicateRegistration(
        predicate=ConfigurablePredicate("beta", satisfied=True, value=20),
        mode=EnforcementMode.WARN,
    )

    forward = InvariantLedger([alpha, beta])
    reverse = InvariantLedger([beta, alpha])

    assert forward.predicate_set_hash == reverse.predicate_set_hash
    assert [
        item.predicate_id
        for item in forward.evaluate(make_action(), PredicateContext(), evaluated_at=FIXED_TIME)
    ] == ["alpha", "beta"]
