"""Template for a deterministic AEON invariant predicate.

Copy into the project, then rename the class, ID, parameter, reason codes, and
configuration for the concrete invariant. Prefer trusted PredicateContext facts
when the policy is runtime-specific.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from context_kernel.ledger import (
    Action,
    ActionType,
    InvariantPredicate,
    PredicateContext,
    PredicateResult,
)


class ExamplePolicyPredicate(InvariantPredicate):
    predicate_id = "example_policy"
    predicate_version = "1.0.0"

    def __init__(self, *, allowed_targets: frozenset[str]) -> None:
        self.allowed_targets = allowed_targets

    def configuration(self) -> Mapping[str, Any]:
        """Expose stable, public, behavior-affecting configuration."""
        return {"allowed_targets": sorted(self.allowed_targets)}

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        del context  # Replace with trusted runtime facts when the invariant needs them.
        if action.action_type is not ActionType.PROTECTED_ACTION:
            return PredicateResult(
                satisfied=True,
                applicable=False,
                reason_code="not_applicable",
                explanation="example_policy does not apply to this action type.",
            )

        target = action.parameters.get("target")
        if not isinstance(target, str) or not target:
            return PredicateResult(
                satisfied=False,
                reason_code="example_target_missing",
                explanation="Protected actions require a non-empty target.",
            )

        allowed = target in self.allowed_targets
        return PredicateResult(
            satisfied=allowed,
            reason_code=(
                "example_target_allowed" if allowed else "example_target_forbidden"
            ),
            explanation=(
                f"Target {target!r} is allowed."
                if allowed
                else f"Target {target!r} is not allowed by runtime policy."
            ),
        )
