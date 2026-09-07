"""Safe, in-memory effect adapters.

These adapters never touch the host filesystem, invoke Git, or make network
requests. They model effects only in ``SimulationState``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from context_kernel.ledger import Action, ActionType


class SimulatedEffectRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    action_id: str
    action_type: ActionType
    result: dict[str, Any]


class SimulationState(BaseModel):
    """Mutable, local state representing all simulated side effects."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    files: dict[str, str] = Field(default_factory=dict)
    git_pushes: list[dict[str, Any]] = Field(default_factory=list)
    network_requests: list[dict[str, Any]] = Field(default_factory=list)
    approval_actions: list[dict[str, Any]] = Field(default_factory=list)
    outputs: list[Any] = Field(default_factory=list)
    protected_actions: list[dict[str, Any]] = Field(default_factory=list)
    resource_used: int = Field(default=0, ge=0)
    effect_log: list[SimulatedEffectRecord] = Field(default_factory=list)


class SimulatedActionHandler(ABC):
    action_types: frozenset[ActionType]

    def supports(self, action: Action) -> bool:
        return action.action_type in self.action_types

    @abstractmethod
    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        """Apply an in-memory state transition."""


class SimulatedFilesystem(SimulatedActionHandler):
    action_types = frozenset(
        {
            ActionType.FILESYSTEM_WRITE,
            ActionType.FILESYSTEM_DELETE,
            ActionType.FILE_CHANGE,
        }
    )

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        path = str(action.parameters["path"])
        if action.action_type is ActionType.FILESYSTEM_DELETE:
            existed = path in state.files
            state.files.pop(path, None)
            return {"operation": "delete", "path": path, "existed": existed}
        content = str(action.parameters.get("content", ""))
        state.files[path] = content
        return {
            "operation": "write",
            "path": path,
            "characters": len(content),
        }


class SimulatedGit(SimulatedActionHandler):
    action_types = frozenset({ActionType.GIT_PUSH})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        record = {
            "remote": action.parameters.get("remote"),
            "branch": action.parameters.get("branch"),
        }
        state.git_pushes.append(record)
        return {"operation": "push", **record}


class SimulatedNetwork(SimulatedActionHandler):
    action_types = frozenset({ActionType.NETWORK_REQUEST})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        record = dict(action.parameters)
        state.network_requests.append(record)
        return {"operation": "request", "request_index": len(state.network_requests) - 1}


class SimulatedApproval(SimulatedActionHandler):
    action_types = frozenset({ActionType.APPROVAL_REQUIRED})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        record = dict(action.parameters)
        state.approval_actions.append(record)
        return {"operation": "approval_gated_action", "accepted": True}


class SimulatedOutput(SimulatedActionHandler):
    action_types = frozenset({ActionType.FINAL_OUTPUT})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        output = action.parameters.get("output")
        state.outputs.append(output)
        return {"operation": "final_output", "output_index": len(state.outputs) - 1}


class SimulatedProtectedAction(SimulatedActionHandler):
    action_types = frozenset({ActionType.PROTECTED_ACTION})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        record = dict(action.parameters)
        state.protected_actions.append(record)
        return {"operation": "protected_action", "accepted": True}


class SimulatedResourceUse(SimulatedActionHandler):
    action_types = frozenset({ActionType.RESOURCE_USE})

    def apply(self, action: Action, state: SimulationState) -> dict[str, Any]:
        units = int(action.parameters["units"])
        state.resource_used += units
        return {
            "operation": "resource_use",
            "units": units,
            "resource_used": state.resource_used,
        }


class SimulatedEffectAdapter:
    """Dispatch proposed actions to safe in-memory handlers."""

    def __init__(self, state: SimulationState | None = None) -> None:
        self.state = state or SimulationState()
        self.handlers: tuple[SimulatedActionHandler, ...] = (
            SimulatedFilesystem(),
            SimulatedGit(),
            SimulatedNetwork(),
            SimulatedApproval(),
            SimulatedOutput(),
            SimulatedProtectedAction(),
            SimulatedResourceUse(),
        )

    def apply(self, action: Action) -> SimulatedEffectRecord:
        handler = next(
            (candidate for candidate in self.handlers if candidate.supports(action)),
            None,
        )
        if handler is None:
            raise ValueError(f"no simulated handler for {action.action_type.value}")
        result = handler.apply(action, self.state)
        record = SimulatedEffectRecord(
            sequence=len(self.state.effect_log) + 1,
            action_id=action.id,
            action_type=action.action_type,
            result=result,
        )
        self.state.effect_log.append(record)
        return record
