"""Determinism primitives used by receipts, replay, and the simulator."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from context_kernel.canonical import canonical_hash

T = TypeVar("T")


@dataclass
class ControlledClock:
    """A monotonic clock that advances by a fixed step after every read."""

    current: datetime = datetime(2026, 1, 1, tzinfo=UTC)
    step: timedelta = timedelta(milliseconds=1)

    def __post_init__(self) -> None:
        if self.current.tzinfo is None:
            raise ValueError("controlled clock start must be timezone-aware")
        if self.step <= timedelta(0):
            raise ValueError("controlled clock step must be positive")

    def now(self) -> datetime:
        value = self.current
        self.current = self.current + self.step
        return value

    def peek(self) -> datetime:
        return self.current


class SeededRandom:
    """Small explicit wrapper around Python's deterministic seeded PRNG."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def choice(self, values: tuple[T, ...]) -> T:
        if not values:
            raise ValueError("cannot choose from an empty tuple")
        return self._random.choice(values)

    def randint(self, lower: int, upper: int) -> int:
        return self._random.randint(lower, upper)

    def random(self) -> float:
        return self._random.random()


def stable_run_id(
    *,
    scenario_id: str,
    scenario_version: str,
    adapter_name: str,
    adapter_version: str,
    seed: int,
) -> str:
    digest = canonical_hash(
        {
            "adapter_name": adapter_name,
            "adapter_version": adapter_version,
            "scenario_id": scenario_id,
            "scenario_version": scenario_version,
            "seed": seed,
        }
    )
    return f"run-{digest[:20]}"
