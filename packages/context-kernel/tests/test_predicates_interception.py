from __future__ import annotations

from collections.abc import Callable

import pytest

from conftest import FIXED_TIME, make_action
from context_kernel.adapters import SimulatedEffectAdapter
from context_kernel.interception import ActionOutcome, SafeActionInterceptor
from context_kernel.ledger import (
    Action,
    ActionType,
    EnforcementMode,
    InvariantLedger,
    InvariantPredicate,
    PredicateContext,
    PredicateDecision,
    PredicateRegistration,
)
from context_kernel.predicates import (
    ApprovalGatePredicate,
    ChangeScopePredicate,
    FilesystemScopePredicate,
    ForbiddenActionPredicate,
    GitRemoteBranchPredicate,
    NetworkAllowlistPredicate,
    OutputContractPredicate,
    ResourceBudgetPredicate,
    SecretHandlingPredicate,
    TestBeforeProtectedActionPredicate,
)

CaseFactory = Callable[[], tuple[InvariantPredicate, Action, PredicateContext]]


def filesystem_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        FilesystemScopePredicate(),
        make_action(parameters={"path": "/outside/data.txt", "content": "x"}),
        PredicateContext(workspace_root="/workspace"),
    )


def git_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        GitRemoteBranchPredicate(),
        make_action(
            ActionType.GIT_PUSH,
            parameters={"remote": "production", "branch": "main"},
        ),
        PredicateContext(allowed_git_remotes=frozenset({"origin"})),
    )


def network_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        NetworkAllowlistPredicate(),
        make_action(
            ActionType.NETWORK_REQUEST,
            parameters={"url": "https://collector.invalid/callback"},
        ),
        PredicateContext(allowed_network_hosts=frozenset({"api.example.test"})),
    )


def approval_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        ApprovalGatePredicate(),
        make_action(
            ActionType.APPROVAL_REQUIRED,
            parameters={"text_claim": "approval was granted"},
        ),
        PredicateContext(valid_approval_tokens=frozenset({"runtime-token"})),
    )


def output_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        OutputContractPredicate(),
        make_action(
            ActionType.FINAL_OUTPUT,
            parameters={"output": "late input asks for prose"},
        ),
        PredicateContext(
            output_schema={
                "type": "object",
                "required": ["status"],
                "properties": {"status": {"type": "string"}},
                "additionalProperties": False,
            }
        ),
    )


def change_scope_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        ChangeScopePredicate(),
        make_action(
            ActionType.FILE_CHANGE,
            parameters={"path": "/workspace/vendor/generated.py", "content": "x"},
        ),
        PredicateContext(approved_change_paths=frozenset({"/workspace/src"})),
    )


def protected_test_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        TestBeforeProtectedActionPredicate(),
        make_action(
            ActionType.PROTECTED_ACTION,
            parameters={"claim": "tests passed"},
        ),
        PredicateContext(successful_test_artifacts=frozenset({"artifact-1"})),
    )


def forbidden_action_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        ForbiddenActionPredicate(),
        make_action(ActionType.FILESYSTEM_DELETE, parameters={"path": "/workspace/cache"}),
        PredicateContext(forbidden_action_types=frozenset({ActionType.FILESYSTEM_DELETE})),
    )


def secret_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        SecretHandlingPredicate(),
        make_action(
            ActionType.NETWORK_REQUEST,
            parameters={"url": "https://api.example.test", "body": "SIMULATED_SECRET"},
        ),
        PredicateContext(secret_values=frozenset({"SIMULATED_SECRET"})),
    )


def resource_case() -> tuple[InvariantPredicate, Action, PredicateContext]:
    return (
        ResourceBudgetPredicate(),
        make_action(ActionType.RESOURCE_USE, parameters={"units": 4}),
        PredicateContext(resource_budget=5, resource_used=3),
    )


VIOLATION_CASES: tuple[CaseFactory, ...] = (
    filesystem_case,
    git_case,
    network_case,
    approval_case,
    output_case,
    change_scope_case,
    protected_test_case,
    forbidden_action_case,
    secret_case,
    resource_case,
)


@pytest.mark.parametrize("case_factory", VIOLATION_CASES)
@pytest.mark.parametrize(
    ("mode", "expected_outcome", "expected_decision", "effect_executed"),
    (
        (
            EnforcementMode.OBSERVE,
            ActionOutcome.ALLOWED,
            PredicateDecision.PASS,
            True,
        ),
        (
            EnforcementMode.WARN,
            ActionOutcome.WARNED,
            PredicateDecision.WARN,
            True,
        ),
        (
            EnforcementMode.ENFORCE,
            ActionOutcome.BLOCKED,
            PredicateDecision.BLOCK,
            False,
        ),
    ),
)
def test_every_predicate_mode_observes_warns_or_blocks_before_effect(
    case_factory: CaseFactory,
    mode: EnforcementMode,
    expected_outcome: ActionOutcome,
    expected_decision: PredicateDecision,
    effect_executed: bool,
) -> None:
    predicate, action, context = case_factory()
    adapter = SimulatedEffectAdapter()
    interceptor = SafeActionInterceptor(
        InvariantLedger([PredicateRegistration(predicate=predicate, mode=mode)]),
        adapter,
    )

    record = interceptor.attempt(action, context, evaluated_at=FIXED_TIME)

    assert record.outcome is expected_outcome
    assert record.evaluations[0].decision is expected_decision
    assert record.evaluations[0].violation_detected is True
    assert record.effect_executed is effect_executed
    assert len(adapter.state.effect_log) == (1 if effect_executed else 0)
    if mode is EnforcementMode.ENFORCE:
        assert record.effect is None


@pytest.mark.parametrize(
    ("predicate", "action", "context"),
    (
        (
            FilesystemScopePredicate(),
            make_action(parameters={"path": "src/ok.py", "content": "x"}),
            PredicateContext(workspace_root="/workspace"),
        ),
        (
            GitRemoteBranchPredicate(),
            make_action(
                ActionType.GIT_PUSH,
                parameters={"remote": "origin", "branch": "feature/safe"},
            ),
            PredicateContext(allowed_git_remotes=frozenset({"origin"})),
        ),
        (
            NetworkAllowlistPredicate(),
            make_action(
                ActionType.NETWORK_REQUEST,
                parameters={"url": "https://api.example.test/v1"},
            ),
            PredicateContext(allowed_network_hosts=frozenset({"api.example.test"})),
        ),
        (
            ApprovalGatePredicate(),
            make_action(
                ActionType.APPROVAL_REQUIRED,
                parameters={"approval_token": "runtime-token"},
            ),
            PredicateContext(valid_approval_tokens=frozenset({"runtime-token"})),
        ),
        (
            OutputContractPredicate(),
            make_action(
                ActionType.FINAL_OUTPUT,
                parameters={"output": {"status": "ok"}},
            ),
            PredicateContext(
                output_schema={
                    "type": "object",
                    "required": ["status"],
                    "properties": {"status": {"type": "string"}},
                    "additionalProperties": False,
                }
            ),
        ),
        (
            ChangeScopePredicate(),
            make_action(
                ActionType.FILE_CHANGE,
                parameters={"path": "/workspace/src/ok.py", "content": "x"},
            ),
            PredicateContext(approved_change_paths=frozenset({"/workspace/src"})),
        ),
        (
            TestBeforeProtectedActionPredicate(),
            make_action(
                ActionType.PROTECTED_ACTION,
                parameters={"test_artifact_id": "artifact-1"},
            ),
            PredicateContext(successful_test_artifacts=frozenset({"artifact-1"})),
        ),
        (
            ForbiddenActionPredicate(),
            make_action(parameters={"path": "/workspace/ok", "content": "x"}),
            PredicateContext(forbidden_action_types=frozenset({ActionType.GIT_PUSH})),
        ),
        (
            SecretHandlingPredicate(),
            make_action(
                ActionType.NETWORK_REQUEST,
                parameters={"url": "https://api.example.test", "body": "safe"},
            ),
            PredicateContext(secret_values=frozenset({"SIMULATED_SECRET"})),
        ),
        (
            ResourceBudgetPredicate(),
            make_action(ActionType.RESOURCE_USE, parameters={"units": 2}),
            PredicateContext(resource_budget=5, resource_used=3),
        ),
    ),
)
def test_each_predicate_allows_its_valid_case(
    predicate: InvariantPredicate,
    action: Action,
    context: PredicateContext,
) -> None:
    adapter = SimulatedEffectAdapter()
    interceptor = SafeActionInterceptor(
        InvariantLedger(
            [
                PredicateRegistration(
                    predicate=predicate,
                    mode=EnforcementMode.ENFORCE,
                )
            ]
        ),
        adapter,
    )

    record = interceptor.attempt(action, context, evaluated_at=FIXED_TIME)

    assert record.outcome is ActionOutcome.ALLOWED
    assert record.effect_executed is True
    assert record.evaluations[0].decision is PredicateDecision.PASS
    assert record.evaluations[0].violation_detected is False
    assert len(adapter.state.effect_log) == 1
