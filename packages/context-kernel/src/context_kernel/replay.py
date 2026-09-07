"""Deterministic trace replay verification."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from context_kernel.receipts import (
    TraceDocument,
    read_trace_jsonl,
    verify_trace_document,
)


class ReplayVerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    verified_at: datetime
    structural_integrity: bool
    reexecuted: bool
    decision_trace_match: bool
    expected_decision_trace_hash: str
    actual_decision_trace_hash: str | None
    verified: bool
    errors: tuple[str, ...]


class ReplayEngine:
    """Verify trace integrity and, when supplied, deterministic re-execution."""

    def verify(
        self,
        document: TraceDocument,
        *,
        reproduce: Callable[[TraceDocument], TraceDocument] | None = None,
        verified_at: datetime | None = None,
    ) -> ReplayVerificationReport:
        structural_integrity, integrity_errors = verify_trace_document(document)
        errors = list(integrity_errors)
        actual_hash: str | None = None
        reexecuted = reproduce is not None

        if reproduce is not None and structural_integrity:
            reproduced = reproduce(document)
            reproduced_ok, reproduced_errors = verify_trace_document(reproduced)
            if not reproduced_ok:
                errors.extend(f"reproduced trace: {error}" for error in reproduced_errors)
            actual_hash = reproduced.decision_trace_hash
        elif structural_integrity:
            actual_hash = document.decision_trace_hash

        match = bool(
            structural_integrity
            and actual_hash is not None
            and actual_hash == document.decision_trace_hash
        )
        if structural_integrity and not match:
            errors.append("replayed decision trace does not match stored hash")
        return ReplayVerificationReport(
            run_id=document.run_id,
            verified_at=verified_at or datetime.now(UTC),
            structural_integrity=structural_integrity,
            reexecuted=reexecuted,
            decision_trace_match=match,
            expected_decision_trace_hash=document.decision_trace_hash,
            actual_decision_trace_hash=actual_hash,
            verified=structural_integrity and match and not errors,
            errors=tuple(errors),
        )

    def verify_path(
        self,
        path: Path,
        *,
        reproduce: Callable[[TraceDocument], TraceDocument] | None = None,
        verified_at: datetime | None = None,
    ) -> ReplayVerificationReport:
        return self.verify(
            read_trace_jsonl(path),
            reproduce=reproduce,
            verified_at=verified_at,
        )
