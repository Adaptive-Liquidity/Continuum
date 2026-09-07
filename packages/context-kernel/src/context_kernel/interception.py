"""Safe effect-boundary interception."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from context_kernel.adapters import SimulatedEffectAdapter, SimulatedEffectRecord
from context_kernel.ledger import (
    Action,
    InvariantLedger,
    PredicateContext,
    PredicateDecision,
    PredicateEvaluation,
)


class ActionOutcome(StrEnum):
    ALLOWED = "allowed"
    WARNED = "warned"
    BLOCKED = "blocked"


class InterceptionRecord(BaseModel):
    """Complete decision and effect result for one proposed action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Action
    action_hash: str
    evaluations: tuple[PredicateEvaluation, ...]
    outcome: ActionOutcome
    effect_executed: bool
    effect: SimulatedEffectRecord | None


class SafeActionInterceptor:
    """Evaluate all invariants before dispatching a simulated effect."""

    def __init__(
        self,
        ledger: InvariantLedger,
        effect_adapter: SimulatedEffectAdapter | None = None,
    ) -> None:
        self.ledger = ledger
        self.effect_adapter = effect_adapter or SimulatedEffectAdapter()

    def attempt(
        self,
        action: Action,
        context: PredicateContext,
        *,
        evaluated_at: datetime,
    ) -> InterceptionRecord:
        evaluations = self.ledger.evaluate(
            action,
            context,
            evaluated_at=evaluated_at,
        )
        blocked = any(evaluation.decision is PredicateDecision.BLOCK for evaluation in evaluations)
        if blocked:
            return InterceptionRecord(
                action=action,
                action_hash=action.action_hash(),
                evaluations=evaluations,
                outcome=ActionOutcome.BLOCKED,
                effect_executed=False,
                effect=None,
            )

        warned = any(evaluation.decision is PredicateDecision.WARN for evaluation in evaluations)
        effect = self.effect_adapter.apply(action)
        return InterceptionRecord(
            action=action,
            action_hash=action.action_hash(),
            evaluations=evaluations,
            outcome=ActionOutcome.WARNED if warned else ActionOutcome.ALLOWED,
            effect_executed=True,
            effect=effect,
        )
