"""Built-in deterministic effect-boundary predicates."""

from __future__ import annotations

import json
import posixpath
from collections.abc import Mapping
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from context_kernel.canonical import canonical_json
from context_kernel.ledger import (
    Action,
    ActionType,
    InvariantPredicate,
    PredicateContext,
    PredicateResult,
)


def _not_applicable(predicate_id: str) -> PredicateResult:
    return PredicateResult(
        satisfied=True,
        applicable=False,
        reason_code="not_applicable",
        explanation=f"{predicate_id} does not apply to this action type.",
    )


def _normalized_path(path: str, workspace_root: str) -> str:
    root = posixpath.normpath("/" + workspace_root.lstrip("/"))
    if path.startswith("/"):
        return posixpath.normpath(path)
    return posixpath.normpath(posixpath.join(root, path))


def _within(path: str, root: str) -> bool:
    normalized_path = posixpath.normpath("/" + path.lstrip("/"))
    normalized_root = posixpath.normpath("/" + root.lstrip("/"))
    return normalized_path == normalized_root or normalized_path.startswith(
        normalized_root.rstrip("/") + "/"
    )


class FilesystemScopePredicate(InvariantPredicate):
    predicate_id = "filesystem_scope"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type not in {
            ActionType.FILESYSTEM_WRITE,
            ActionType.FILESYSTEM_DELETE,
        }:
            return _not_applicable(self.predicate_id)
        path = action.parameters.get("path")
        if not isinstance(path, str) or not path:
            return PredicateResult(
                satisfied=False,
                reason_code="filesystem_path_missing",
                explanation="Filesystem actions require a non-empty path.",
            )
        normalized = _normalized_path(path, context.workspace_root)
        allowed = _within(normalized, context.workspace_root)
        return PredicateResult(
            satisfied=allowed,
            reason_code=(
                "filesystem_within_workspace" if allowed else "filesystem_outside_workspace"
            ),
            explanation=(
                f"Normalized path {normalized!r} is inside workspace root."
                if allowed
                else f"Normalized path {normalized!r} escapes workspace root {context.workspace_root!r}."
            ),
        )


class GitRemoteBranchPredicate(InvariantPredicate):
    predicate_id = "git_remote_branch_policy"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type is not ActionType.GIT_PUSH:
            return _not_applicable(self.predicate_id)
        remote = action.parameters.get("remote")
        branch = action.parameters.get("branch")
        if not isinstance(remote, str) or remote not in context.allowed_git_remotes:
            return PredicateResult(
                satisfied=False,
                reason_code="git_remote_not_allowlisted",
                explanation=f"Git remote {remote!r} is not in the runtime allowlist.",
            )
        if not isinstance(branch, str) or branch in context.protected_branches:
            return PredicateResult(
                satisfied=False,
                reason_code="git_protected_branch",
                explanation=f"Git branch {branch!r} is protected from push actions.",
            )
        return PredicateResult(
            satisfied=True,
            reason_code="git_push_allowed",
            explanation="The Git remote is allowlisted and the branch is not protected.",
        )


class NetworkAllowlistPredicate(InvariantPredicate):
    predicate_id = "network_allowlist"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type is not ActionType.NETWORK_REQUEST:
            return _not_applicable(self.predicate_id)
        host = action.parameters.get("host")
        if not isinstance(host, str):
            url = action.parameters.get("url")
            host = urlsplit(url).hostname if isinstance(url, str) else None
        normalized = host.rstrip(".").lower() if isinstance(host, str) else None
        allowed_hosts = {item.rstrip(".").lower() for item in context.allowed_network_hosts}
        allowed = normalized is not None and normalized in allowed_hosts
        return PredicateResult(
            satisfied=allowed,
            reason_code=("network_host_allowlisted" if allowed else "network_host_not_allowlisted"),
            explanation=(
                f"Network host {normalized!r} is allowlisted."
                if allowed
                else f"Network host {normalized!r} is not allowlisted."
            ),
        )


class ApprovalGatePredicate(InvariantPredicate):
    predicate_id = "explicit_approval_gate"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        requires_approval = bool(
            action.action_type is ActionType.APPROVAL_REQUIRED
            or action.metadata.get("requires_approval") is True
        )
        if not requires_approval:
            return _not_applicable(self.predicate_id)
        token = action.parameters.get("approval_token")
        event_id = action.parameters.get("approval_event_id")
        valid = bool(
            (isinstance(token, str) and token in context.valid_approval_tokens)
            or (isinstance(event_id, str) and event_id in context.approval_events)
        )
        return PredicateResult(
            satisfied=valid,
            reason_code=("approval_verified" if valid else "approval_missing_or_invalid"),
            explanation=(
                "A runtime-issued approval token or event was verified."
                if valid
                else "No valid runtime approval token or approval event was supplied; textual claims do not count."
            ),
        )


class OutputContractPredicate(InvariantPredicate):
    predicate_id = "output_contract"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type is not ActionType.FINAL_OUTPUT:
            return _not_applicable(self.predicate_id)
        if context.output_schema is None:
            return PredicateResult(
                satisfied=True,
                applicable=False,
                reason_code="output_schema_not_configured",
                explanation="No output schema is configured for this run.",
            )
        output = action.parameters.get("output")
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                return PredicateResult(
                    satisfied=False,
                    reason_code="output_not_valid_json",
                    explanation="The final output is prose or invalid JSON.",
                )
        try:
            Draft202012Validator.check_schema(context.output_schema)
            Draft202012Validator(context.output_schema).validate(output)
        except SchemaError as exc:
            return PredicateResult(
                satisfied=False,
                reason_code="output_schema_invalid",
                explanation=f"The configured output schema is invalid: {exc.message}",
            )
        except ValidationError as exc:
            return PredicateResult(
                satisfied=False,
                reason_code="output_schema_validation_failed",
                explanation=f"The final output failed schema validation: {exc.message}",
            )
        return PredicateResult(
            satisfied=True,
            reason_code="output_schema_valid",
            explanation="The final output validates against the configured JSON schema.",
        )


class ChangeScopePredicate(InvariantPredicate):
    predicate_id = "change_scope"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type not in {
            ActionType.FILE_CHANGE,
            ActionType.FILESYSTEM_WRITE,
            ActionType.FILESYSTEM_DELETE,
        }:
            return _not_applicable(self.predicate_id)
        path = action.parameters.get("path")
        if not isinstance(path, str) or not path:
            return PredicateResult(
                satisfied=False,
                reason_code="change_path_missing",
                explanation="A file-modification action requires a path.",
            )
        normalized = _normalized_path(path, context.workspace_root)
        allowed = any(_within(normalized, root) for root in context.approved_change_paths)
        return PredicateResult(
            satisfied=allowed,
            reason_code=(
                "change_within_approved_scope" if allowed else "change_outside_approved_scope"
            ),
            explanation=(
                f"Change path {normalized!r} is inside an approved path set."
                if allowed
                else f"Change path {normalized!r} is outside all approved path sets."
            ),
        )


class TestBeforeProtectedActionPredicate(InvariantPredicate):
    predicate_id = "test_before_protected_action"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        protected = bool(
            action.action_type is ActionType.PROTECTED_ACTION
            or action.metadata.get("requires_tests") is True
        )
        if not protected:
            return _not_applicable(self.predicate_id)
        artifact = action.parameters.get("test_artifact_id")
        valid = isinstance(artifact, str) and artifact in context.successful_test_artifacts
        return PredicateResult(
            satisfied=valid,
            reason_code=("test_artifact_verified" if valid else "test_artifact_missing_or_invalid"),
            explanation=(
                "A successful runtime test artifact was verified."
                if valid
                else "No valid successful test artifact was supplied; textual claims do not count."
            ),
        )


class ForbiddenActionPredicate(InvariantPredicate):
    predicate_id = "forbidden_action"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        forbidden = action.action_type in context.forbidden_action_types
        return PredicateResult(
            satisfied=not forbidden,
            reason_code=("action_type_allowed" if not forbidden else "action_type_forbidden"),
            explanation=(
                f"Action type {action.action_type.value!r} is allowed."
                if not forbidden
                else f"Action type {action.action_type.value!r} is forbidden by runtime policy."
            ),
            applicable=True,
        )


class SecretHandlingPredicate(InvariantPredicate):
    predicate_id = "secret_handling"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if not context.secret_values:
            return PredicateResult(
                satisfied=True,
                applicable=False,
                reason_code="no_secret_values_configured",
                explanation="No simulator secret values are configured.",
            )
        serialized = canonical_json(action.parameters)
        exposed = sorted(secret for secret in context.secret_values if secret in serialized)
        safe = not exposed
        return PredicateResult(
            satisfied=safe,
            reason_code=("no_secret_exposure" if safe else "secret_value_exposed"),
            explanation=(
                "No configured secret value appears in action arguments."
                if safe
                else "A configured secret value appears in proposed action arguments."
            ),
        )


class ResourceBudgetPredicate(InvariantPredicate):
    predicate_id = "resource_budget"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        if action.action_type is not ActionType.RESOURCE_USE:
            return _not_applicable(self.predicate_id)
        if context.resource_budget is None:
            return PredicateResult(
                satisfied=True,
                applicable=False,
                reason_code="resource_budget_not_configured",
                explanation="No fixed resource budget is configured.",
            )
        units = action.parameters.get("units")
        if not isinstance(units, int) or isinstance(units, bool) or units < 0:
            return PredicateResult(
                satisfied=False,
                reason_code="resource_units_invalid",
                explanation="Resource-use actions require a non-negative integer unit count.",
            )
        projected = context.resource_used + units
        allowed = projected <= context.resource_budget
        return PredicateResult(
            satisfied=allowed,
            reason_code=("resource_budget_available" if allowed else "resource_budget_exceeded"),
            explanation=(
                f"Projected use {projected} is within budget {context.resource_budget}."
                if allowed
                else f"Projected use {projected} exceeds budget {context.resource_budget}."
            ),
        )


BUILTIN_PREDICATES: tuple[type[InvariantPredicate], ...] = (
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


def builtin_predicate_versions() -> Mapping[str, str]:
    return {predicate.predicate_id: predicate.predicate_version for predicate in BUILTIN_PREDICATES}
