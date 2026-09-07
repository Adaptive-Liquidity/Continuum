"""Canonical serialization and hashing helpers.

The project hashes logical records rather than incidental file formatting. All
hashes are SHA-256 over UTF-8 encoded RFC-8259-compatible JSON with sorted keys
and compact separators.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _canonical_datetime(value: datetime) -> str:
    """Return an unambiguous UTC timestamp with microsecond precision."""
    if value.tzinfo is None:
        raise ValueError("canonical timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def to_canonical_data(value: Any) -> Any:
    """Convert supported Python values to a deterministic JSON-compatible tree."""
    if isinstance(value, BaseModel):
        return to_canonical_data(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return to_canonical_data(value.value)
    if isinstance(value, datetime):
        return _canonical_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Mapping):
        return {
            str(key): to_canonical_data(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (set, frozenset)):
        converted = [to_canonical_data(item) for item in value]
        return sorted(converted, key=canonical_json)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_canonical_data(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a value with stable key ordering and no insignificant whitespace."""
    return json.dumps(
        to_canonical_data(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_text(value: str) -> str:
    """Hash an exact text value using SHA-256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash the canonical JSON representation of a logical value."""
    return sha256_text(canonical_json(value))
