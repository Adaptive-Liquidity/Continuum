"""Machine-readable Context Survival Bench metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RunMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario_id: str
    adapter_name: str
    seed: int
    survived_without_violation: bool
    turn_to_first_violation: int | None = Field(default=None, ge=0)
    survival_time_turns: int = Field(ge=0)
    right_censored: bool
    completion_status: str
    allowed_action_count: int = Field(ge=0)
    blocked_action_count: int = Field(ge=0)
    warned_action_count: int = Field(ge=0)
    false_block_count: int = Field(ge=0)
    kernel_latency_ms: float = Field(ge=0)
    simulator_or_model_latency_ms: float = Field(ge=0)
    character_estimate: int = Field(ge=0)
    token_estimate: int = Field(ge=0)
    cost: float | None = Field(default=None, ge=0)
