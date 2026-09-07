"""Executable invariant predicates."""

from context_kernel.predicates.builtin import (
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

__all__ = [
    "ApprovalGatePredicate",
    "ChangeScopePredicate",
    "FilesystemScopePredicate",
    "ForbiddenActionPredicate",
    "GitRemoteBranchPredicate",
    "NetworkAllowlistPredicate",
    "OutputContractPredicate",
    "ResourceBudgetPredicate",
    "SecretHandlingPredicate",
    "TestBeforeProtectedActionPredicate",
]
