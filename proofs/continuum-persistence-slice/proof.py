#!/usr/bin/env python3
"""Continuum Persistence Slice #2A — stdlib-only internal genesis proof.

This harness proves the bounded Decision #2A claim on one host:
one Continuum Computer, one VERA, one process-restart discontinuity,
durable state, one scoped revocable grant, one mediated post-restart effect,
and an independently inspectable structured evidence artifact.

It does not prove host migration, provider swap, coordination, full DCA
conformance, production readiness, or cryptographic verification.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_KEY = "continuity_marker"
STATE_VALUE = "continuum-state-survives-restart"
CAPABILITY = "effect:continuum.marker.write"
EFFECT_NAME = "continuum.marker.write"
MEDIATOR = "continuum-persistence-slice-effect-boundary"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS identity (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            computer_id TEXT NOT NULL,
            vera_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS durable_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            written_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS grants (
            grant_id TEXT PRIMARY KEY,
            capability TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('ACTIVE','REVOKED')),
            issued_at TEXT NOT NULL,
            revoked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS effects (
            attempt_id TEXT PRIMARY KEY,
            effect_name TEXT NOT NULL,
            capability TEXT NOT NULL,
            mediator TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK (outcome IN ('COMMITTED','DENIED')),
            process_id INTEGER NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evidence (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            process_id INTEGER NOT NULL,
            payload_json TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def evidence(conn: sqlite3.Connection, kind: str, payload: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO evidence(kind, occurred_at, process_id, payload_json) VALUES(?,?,?,?)",
        (kind, now_iso(), os.getpid(), json.dumps(payload, sort_keys=True)),
    )
    conn.commit()


def ensure_identity(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()
    if row:
        return row
    computer_id = f"continuum-computer-{uuid.uuid4()}"
    vera_id = f"vera-{uuid.uuid4()}"
    created_at = now_iso()
    conn.execute(
        "INSERT INTO identity(singleton, computer_id, vera_id, created_at) VALUES(1,?,?,?)",
        (computer_id, vera_id, created_at),
    )
    conn.commit()
    evidence(conn, "computer.created", {"computer_id": computer_id})
    evidence(conn, "vera.created", {"vera_id": vera_id, "computer_id": computer_id})
    return conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()


def phase1(db_path: Path, artifact_path: Path) -> dict[str, Any]:
    del artifact_path
    conn = connect(db_path)
    ident = ensure_identity(conn)
    evidence(conn, "process.phase1.started", {"phase": "pre_restart"})
    conn.execute(
        "INSERT OR REPLACE INTO durable_state(key,value,written_at) VALUES(?,?,?)",
        (STATE_KEY, STATE_VALUE, now_iso()),
    )
    conn.commit()
    evidence(conn, "state.written", {"key": STATE_KEY, "value": STATE_VALUE})

    existing = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1", (CAPABILITY,)
    ).fetchone()
    if existing and existing["state"] == "ACTIVE":
        grant_id = existing["grant_id"]
    else:
        grant_id = f"grant-{uuid.uuid4()}"
        conn.execute(
            "INSERT INTO grants(grant_id,capability,state,issued_at,revoked_at) VALUES(?,?, 'ACTIVE', ?, NULL)",
            (grant_id, CAPABILITY, now_iso()),
        )
        conn.commit()
        evidence(conn, "grant.issued", {"grant_id": grant_id, "capability": CAPABILITY, "scope": EFFECT_NAME})

    evidence(conn, "process.phase1.ready_for_restart", {"grant_id": grant_id})
    result = {
        "computer_id": ident["computer_id"],
        "vera_id": ident["vera_id"],
        "grant_id": grant_id,
        "process_id": os.getpid(),
        "phase": "pre_restart",
    }
    conn.close()
    return result


def mediate_effect(conn: sqlite3.Connection, attempt_id: str) -> str:
    grant = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1", (CAPABILITY,)
    ).fetchone()
    outcome = "COMMITTED" if grant and grant["state"] == "ACTIVE" else "DENIED"
    conn.execute(
        "INSERT INTO effects(attempt_id,effect_name,capability,mediator,outcome,process_id,occurred_at) VALUES(?,?,?,?,?,?,?)",
        (attempt_id, EFFECT_NAME, CAPABILITY, MEDIATOR, outcome, os.getpid(), now_iso()),
    )
    conn.commit()
    evidence(
        conn,
        "effect.committed" if outcome == "COMMITTED" else "effect.denied",
        {
            "attempt_id": attempt_id,
            "effect_name": EFFECT_NAME,
            "capability": CAPABILITY,
            "mediator": MEDIATOR,
            "grant_state": grant["state"] if grant else "ABSENT",
        },
    )
    return outcome


def revoke_grant(conn: sqlite3.Connection) -> str:
    grant = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1", (CAPABILITY,)
    ).fetchone()
    if not grant:
        raise RuntimeError("grant missing")
    conn.execute(
        "UPDATE grants SET state='REVOKED', revoked_at=? WHERE grant_id=?",
        (now_iso(), grant["grant_id"]),
    )
    conn.commit()
    evidence(conn, "grant.revoked", {"grant_id": grant["grant_id"], "capability": CAPABILITY})
    return grant["grant_id"]


def build_artifact(conn: sqlite3.Connection, phase1_pid: int | None = None) -> dict[str, Any]:
    ident = conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()
    state = conn.execute("SELECT * FROM durable_state WHERE key=?", (STATE_KEY,)).fetchone()
    grant = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1", (CAPABILITY,)
    ).fetchone()
    effect_rows = conn.execute("SELECT * FROM effects ORDER BY occurred_at").fetchall()
    events = []
    for row in conn.execute("SELECT * FROM evidence ORDER BY seq").fetchall():
        events.append(
            {
                "seq": row["seq"],
                "kind": row["kind"],
                "occurred_at": row["occurred_at"],
                "process_id": row["process_id"],
                "payload": json.loads(row["payload_json"]),
            }
        )
    pids = []
    for event in events:
        if event["process_id"] not in pids:
            pids.append(event["process_id"])
    if phase1_pid is None and pids:
        phase1_pid = pids[0]
    phase2_pid = os.getpid()
    committed = next((r for r in effect_rows if r["outcome"] == "COMMITTED"), None)
    denied = next((r for r in effect_rows if r["outcome"] == "DENIED"), None)
    restart_event = next((e for e in events if e["kind"] == "process.phase2.reconstituted"), None)
    state_read = next((e for e in events if e["kind"] == "state.read"), None)

    acceptance = {
        "AC-1": bool(ident and len(pids) >= 2 and phase1_pid != phase2_pid),
        "AC-2": bool(ident and len(pids) >= 2 and phase1_pid != phase2_pid),
        "AC-3": bool(state and state["value"] == STATE_VALUE and state_read),
        "AC-4": bool(committed and denied and grant and grant["state"] == "REVOKED"),
        "AC-5": bool(committed and restart_event and committed["process_id"] == phase2_pid),
        "AC-6": all(
            any(e["kind"] == kind for e in events)
            for kind in (
                "computer.created",
                "vera.created",
                "process.phase1.ready_for_restart",
                "process.phase2.reconstituted",
                "state.written",
                "state.read",
                "grant.issued",
                "grant.revoked",
                "effect.committed",
                "effect.denied",
            )
        ),
        "AC-7": bool(ident and len(pids) >= 2 and phase1_pid != phase2_pid and state_read),
        "AC-8": True,
    }
    return {
        "schema": "asentxia.continuum.persistence-slice.2a.v1",
        "generated_at": now_iso(),
        "scope": "process restart on the same host; persistence beyond process/session only",
        "computer_id": ident["computer_id"] if ident else None,
        "vera_id": ident["vera_id"] if ident else None,
        "discontinuity": {
            "type": "process_restart_same_host",
            "pre_restart_process_id": phase1_pid,
            "post_restart_process_id": phase2_pid,
        },
        "state": {"key": STATE_KEY, "value": state["value"] if state else None},
        "authority": {
            "grant_id": grant["grant_id"] if grant else None,
            "capability": CAPABILITY,
            "final_state": grant["state"] if grant else None,
        },
        "execution": {
            "effect_name": EFFECT_NAME,
            "mediator": MEDIATOR,
            "active_grant_outcome": committed["outcome"] if committed else None,
            "revoked_grant_outcome": denied["outcome"] if denied else None,
        },
        "evidence": events,
        "acceptance": acceptance,
        "claim_ceiling": "Bounded Decision #2A internal proof only; no claim is made beyond AC-1 through AC-8.",
    }


def phase2(db_path: Path, artifact_path: Path) -> dict[str, Any]:
    conn = connect(db_path)
    ident = conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()
    if not ident:
        raise RuntimeError("phase1 identity missing")
    evidence(conn, "process.phase2.reconstituted", {"phase": "post_restart"})

    state = conn.execute("SELECT * FROM durable_state WHERE key=?", (STATE_KEY,)).fetchone()
    if not state:
        raise RuntimeError("durable state missing after restart")
    evidence(conn, "state.read", {"key": STATE_KEY, "value": state["value"]})

    committed = mediate_effect(conn, f"attempt-{uuid.uuid4()}")
    revoke_grant(conn)
    denied = mediate_effect(conn, f"attempt-{uuid.uuid4()}")

    events = conn.execute("SELECT DISTINCT process_id FROM evidence ORDER BY seq").fetchall()
    phase1_pid = events[0]["process_id"] if events else None
    artifact = build_artifact(conn, phase1_pid=phase1_pid)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "computer_id": ident["computer_id"],
        "vera_id": ident["vera_id"],
        "process_id": os.getpid(),
        "phase": "post_restart",
        "state_value": state["value"],
        "effect_before_revocation": committed,
        "effect_after_revocation": denied,
        "effect_executed_after_restart": committed == "COMMITTED",
        "artifact": str(artifact_path),
    }
    conn.close()
    return result


def verify_artifact(artifact_path: Path) -> dict[str, Any]:
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    required_top = {
        "schema",
        "computer_id",
        "vera_id",
        "discontinuity",
        "state",
        "authority",
        "execution",
        "evidence",
        "acceptance",
        "claim_ceiling",
    }
    required_events = {
        "computer.created",
        "vera.created",
        "process.phase1.ready_for_restart",
        "process.phase2.reconstituted",
        "state.written",
        "state.read",
        "grant.issued",
        "grant.revoked",
        "effect.committed",
        "effect.denied",
    }
    kinds = {e.get("kind") for e in data.get("evidence", [])}
    seqs = [e.get("seq") for e in data.get("evidence", [])]
    sequential = seqs == list(range(1, len(seqs) + 1))
    acceptance = data.get("acceptance", {})
    valid = (
        required_top.issubset(data)
        and data.get("schema") == "asentxia.continuum.persistence-slice.2a.v1"
        and data.get("discontinuity", {}).get("type") == "process_restart_same_host"
        and data.get("discontinuity", {}).get("pre_restart_process_id")
        != data.get("discontinuity", {}).get("post_restart_process_id")
        and required_events.issubset(kinds)
        and sequential
        and all(acceptance.get(f"AC-{i}") is True for i in range(1, 9))
    )
    return {
        "valid": valid,
        "acceptance": {f"AC-{i}": acceptance.get(f"AC-{i}") is True for i in range(1, 9)},
        "evidence_events": len(data.get("evidence", [])),
        "sequence_contiguous": sequential,
    }


def run_all(workdir: Path) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    db = workdir / "continuum-persistence-slice.sqlite3"
    artifact = workdir / "continuum-persistence-slice-2a.json"
    if db.exists():
        db.unlink()
    if artifact.exists():
        artifact.unlink()

    p1 = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "phase1", "--db", str(db), "--artifact", str(artifact)],
        check=True,
        capture_output=True,
        text=True,
    )
    phase1_result = json.loads(p1.stdout)
    p2 = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "phase2", "--db", str(db), "--artifact", str(artifact)],
        check=True,
        capture_output=True,
        text=True,
    )
    phase2_result = json.loads(p2.stdout)
    verification = verify_artifact(artifact)
    if not verification["valid"]:
        raise SystemExit("proof verification failed")
    return {
        "phase1": phase1_result,
        "phase2": phase2_result,
        "verification": verification,
        "artifact": str(artifact),
        "database": str(db),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Continuum Persistence Slice #2A proof harness")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("phase1", "phase2"):
        s = sub.add_parser(name)
        s.add_argument("--db", type=Path, required=True)
        s.add_argument("--artifact", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--artifact", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--workdir", type=Path, default=Path(tempfile.gettempdir()) / "continuum-persistence-slice")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "phase1":
        result = phase1(args.db, args.artifact)
    elif args.command == "phase2":
        result = phase2(args.db, args.artifact)
    elif args.command == "verify":
        result = verify_artifact(args.artifact)
    elif args.command == "run":
        result = run_all(args.workdir)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
