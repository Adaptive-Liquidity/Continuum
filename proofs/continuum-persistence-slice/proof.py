#!/usr/bin/env python3
"""Continuum Persistence Slice #2A — stdlib-only bounded proof harness.

Two sequential OS processes share one SQLite store on the same host. Phase 1
writes identity, durable state, and an active grant, then exits normally.
Phase 2 reconstitutes the same Computer and VERA, reads the marker, commits
one mediated local write, revokes the grant, and records a denied retry.

The verifier recomputes AC-1 through AC-8 from raw artifact fields. Stored
acceptance booleans are ignored. This is an internal script by the same
author, not third-party verification.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
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
EFFECT_CLASS = "in_process_sqlite_status_write"
MEDIATOR = "continuum-persistence-slice-effect-boundary"
SCHEMA = "asentxia.continuum.persistence-slice.2a.v1"
SCOPE = "process restart on the same host; persistence beyond process/session only"
CLAIM_CEILING = (
    "Bounded Decision #2A internal proof only; no claim is made beyond AC-1 through AC-8."
)
REQUIRED_EVENTS = (
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
REQUIRED_EVENTS_SET = set(REQUIRED_EVENTS)
REQUIRED_TOP = (
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
    "identity_continuity",
    "excluded_scope",
    "scope",
)
REQUIRED_TOP_SET = set(REQUIRED_TOP)
# Claims this slice must mark unproven. AC-8 fails if any flag is True.
EXCLUDED_SCOPE_KEYS = (
    "host_migration",
    "crash_recovery",
    "model_provider_replacement",
    "external_side_effect",
    "third_party_verification",
    "cryptographic_notarization",
    "production_readiness",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def host_id() -> str:
    return socket.gethostname()


def excluded_scope_template() -> dict[str, bool]:
    return {key: False for key in EXCLUDED_SCOPE_KEYS}


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
    evidence(conn, "computer.created", {"computer_id": computer_id, "host": host_id()})
    evidence(conn, "vera.created", {"vera_id": vera_id, "computer_id": computer_id})
    return conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()


def phase1(db_path: Path, artifact_path: Path) -> dict[str, Any]:
    del artifact_path
    conn = connect(db_path)
    ident = ensure_identity(conn)
    evidence(conn, "process.phase1.started", {"phase": "pre_restart", "host": host_id()})
    conn.execute(
        "INSERT OR REPLACE INTO durable_state(key,value,written_at) VALUES(?,?,?)",
        (STATE_KEY, STATE_VALUE, now_iso()),
    )
    conn.commit()
    evidence(conn, "state.written", {"key": STATE_KEY, "value": STATE_VALUE})

    existing = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1",
        (CAPABILITY,),
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
        evidence(
            conn,
            "grant.issued",
            {"grant_id": grant_id, "capability": CAPABILITY, "scope": EFFECT_NAME},
        )

    evidence(
        conn,
        "process.phase1.ready_for_restart",
        {"grant_id": grant_id, "host": host_id()},
    )
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
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1",
        (CAPABILITY,),
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
            "effect_class": EFFECT_CLASS,
            "capability": CAPABILITY,
            "mediator": MEDIATOR,
            "grant_state": grant["state"] if grant else "ABSENT",
        },
    )
    return outcome


def revoke_grant(conn: sqlite3.Connection) -> str:
    grant = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1",
        (CAPABILITY,),
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


def _events_from_db(conn: sqlite3.Connection) -> list[dict[str, Any]]:
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
    return events


def _first_event(events: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    for event in events:
        if event.get("kind") == kind:
            return event
    return {}


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def compute_acceptance(data: dict[str, Any]) -> dict[str, bool]:
    """Recompute AC-1..AC-8 from raw artifact fields. Ignores stored acceptance."""
    events = data.get("evidence")
    if not isinstance(events, list):
        events = []
    kinds = [event.get("kind") for event in events]
    seqs = [event.get("seq") for event in events]
    sequential = seqs == list(range(1, len(seqs) + 1)) and bool(seqs)

    disc = data.get("discontinuity") if isinstance(data.get("discontinuity"), dict) else {}
    ident = data.get("identity_continuity") if isinstance(data.get("identity_continuity"), dict) else {}
    state = data.get("state") if isinstance(data.get("state"), dict) else {}
    authority = data.get("authority") if isinstance(data.get("authority"), dict) else {}
    execution = data.get("execution") if isinstance(data.get("execution"), dict) else {}
    excluded = data.get("excluded_scope") if isinstance(data.get("excluded_scope"), dict) else {}

    pre_pid = disc.get("pre_restart_process_id")
    post_pid = disc.get("post_restart_process_id")
    pids_differ = pre_pid is not None and post_pid is not None and pre_pid != post_pid

    created_computer_event = _first_event(events, "computer.created")
    created_vera_event = _first_event(events, "vera.created")
    written_event = _first_event(events, "state.written")
    read_event = _first_event(events, "state.read")
    ready_event = _first_event(events, "process.phase1.ready_for_restart")
    restart_event = _first_event(events, "process.phase2.reconstituted")
    committed = _first_event(events, "effect.committed")
    revoked = _first_event(events, "grant.revoked")
    denied = _first_event(events, "effect.denied")
    restart_observed = bool(
        ready_event.get("process_id") == pre_pid
        and restart_event.get("process_id") == post_pid
        and pids_differ
    )

    created_computer = _payload(created_computer_event).get("computer_id")
    created_vera = _payload(created_vera_event).get("vera_id")
    vera_bound_computer = _payload(created_vera_event).get("computer_id")
    written_value = _payload(written_event).get("value")
    read_value = _payload(read_event).get("value")

    computer_id = data.get("computer_id")
    vera_id = data.get("vera_id")
    pre_computer = ident.get("pre_computer_id")
    post_computer = ident.get("post_computer_id")
    pre_vera = ident.get("pre_vera_id")
    post_vera = ident.get("post_vera_id")
    bound_computer = ident.get("bound_computer_id")

    ac1 = bool(
        computer_id
        and created_computer
        and computer_id == created_computer
        and computer_id == pre_computer
        and computer_id == post_computer
        and pre_computer == post_computer
        and restart_observed
    )
    ac2 = bool(
        vera_id
        and created_vera
        and vera_id == created_vera
        and vera_id == pre_vera
        and vera_id == post_vera
        and pre_vera == post_vera
        and restart_observed
    )
    ac3 = bool(
        written_value == STATE_VALUE
        and read_value == STATE_VALUE
        and state.get("value") == STATE_VALUE
        and state.get("key") == STATE_KEY
        and written_event.get("seq")
        and restart_event.get("seq")
        and read_event.get("seq")
        and written_event["seq"] < restart_event["seq"] < read_event["seq"]
    )
    ac4 = bool(
        committed
        and revoked
        and denied
        and committed.get("seq")
        and revoked.get("seq")
        and denied.get("seq")
        and committed["seq"] < revoked["seq"] < denied["seq"]
        and authority.get("final_state") == "REVOKED"
        and authority.get("capability") == CAPABILITY
        and _payload(committed).get("capability") == CAPABILITY
        and _payload(revoked).get("capability") == CAPABILITY
        and _payload(denied).get("capability") == CAPABILITY
        and execution.get("active_grant_outcome") == "COMMITTED"
        and execution.get("revoked_grant_outcome") == "DENIED"
    )
    ac5 = bool(
        committed
        and committed.get("process_id") == post_pid
        and execution.get("mediator") == MEDIATOR
        and execution.get("effect_class") == EFFECT_CLASS
        and execution.get("effect_name") == EFFECT_NAME
    )
    ac6 = REQUIRED_EVENTS_SET.issubset(set(kinds)) and sequential
    ac7 = bool(
        created_computer
        and vera_bound_computer
        and bound_computer
        and created_computer == vera_bound_computer
        and bound_computer == vera_bound_computer
        and bound_computer == created_computer
    )
    flags_present = all(key in excluded for key in EXCLUDED_SCOPE_KEYS)
    flags_unproven = flags_present and all(excluded.get(key) is False for key in EXCLUDED_SCOPE_KEYS)
    same_host = bool(
        disc.get("pre_restart_host")
        and disc.get("post_restart_host")
        and disc.get("pre_restart_host") == disc.get("post_restart_host")
        and disc.get("type") == "process_restart_same_host"
    )
    scope_bounded = data.get("scope") == SCOPE and data.get("claim_ceiling") == CLAIM_CEILING
    ac8 = bool(flags_unproven and same_host and scope_bounded)

    return {
        "AC-1": ac1,
        "AC-2": ac2,
        "AC-3": ac3,
        "AC-4": ac4,
        "AC-5": ac5,
        "AC-6": ac6,
        "AC-7": ac7,
        "AC-8": ac8,
    }


def build_artifact(conn: sqlite3.Connection, phase1_pid: int | None = None) -> dict[str, Any]:
    ident = conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()
    state = conn.execute("SELECT * FROM durable_state WHERE key=?", (STATE_KEY,)).fetchone()
    grant = conn.execute(
        "SELECT * FROM grants WHERE capability=? ORDER BY issued_at DESC LIMIT 1",
        (CAPABILITY,),
    ).fetchone()
    effect_rows = conn.execute("SELECT * FROM effects ORDER BY occurred_at").fetchall()
    events = _events_from_db(conn)
    pids: list[int] = []
    for event in events:
        if event["process_id"] not in pids:
            pids.append(event["process_id"])
    if phase1_pid is None and pids:
        phase1_pid = pids[0]
    phase2_pid = os.getpid()
    committed = next((row for row in effect_rows if row["outcome"] == "COMMITTED"), None)
    denied = next((row for row in effect_rows if row["outcome"] == "DENIED"), None)

    created_computer = _payload(_first_event(events, "computer.created")).get("computer_id")
    created_vera = _payload(_first_event(events, "vera.created")).get("vera_id")
    vera_bound_computer = _payload(_first_event(events, "vera.created")).get("computer_id")
    phase1_host = _payload(_first_event(events, "process.phase1.ready_for_restart")).get("host")
    phase2_host = _payload(_first_event(events, "process.phase2.reconstituted")).get("host")

    artifact: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": now_iso(),
        "scope": SCOPE,
        "computer_id": ident["computer_id"] if ident else None,
        "vera_id": ident["vera_id"] if ident else None,
        "identity_continuity": {
            "pre_computer_id": created_computer,
            "post_computer_id": ident["computer_id"] if ident else None,
            "pre_vera_id": created_vera,
            "post_vera_id": ident["vera_id"] if ident else None,
            "bound_computer_id": vera_bound_computer,
        },
        "discontinuity": {
            "type": "process_restart_same_host",
            "pre_restart_process_id": phase1_pid,
            "post_restart_process_id": phase2_pid,
            "pre_restart_host": phase1_host,
            "post_restart_host": phase2_host,
        },
        "state": {"key": STATE_KEY, "value": state["value"] if state else None},
        "authority": {
            "grant_id": grant["grant_id"] if grant else None,
            "capability": CAPABILITY,
            "final_state": grant["state"] if grant else None,
        },
        "execution": {
            "effect_name": EFFECT_NAME,
            "effect_class": EFFECT_CLASS,
            "mediator": MEDIATOR,
            "active_grant_outcome": committed["outcome"] if committed else None,
            "revoked_grant_outcome": denied["outcome"] if denied else None,
        },
        "excluded_scope": excluded_scope_template(),
        "evidence": events,
        "claim_ceiling": CLAIM_CEILING,
    }
    artifact["acceptance"] = compute_acceptance(artifact)
    return artifact


def phase2(db_path: Path, artifact_path: Path) -> dict[str, Any]:
    conn = connect(db_path)
    ident = conn.execute("SELECT * FROM identity WHERE singleton=1").fetchone()
    if not ident:
        raise RuntimeError("phase1 identity missing")
    evidence(conn, "process.phase2.reconstituted", {"phase": "post_restart", "host": host_id()})

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
    events = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    seqs = [event.get("seq") for event in events]
    sequential = seqs == list(range(1, len(seqs) + 1)) and bool(seqs)
    acceptance = compute_acceptance(data)
    disc = data.get("discontinuity") if isinstance(data.get("discontinuity"), dict) else {}
    structural = (
        REQUIRED_TOP_SET.issubset(data)
        and data.get("schema") == SCHEMA
        and disc.get("type") == "process_restart_same_host"
    )
    valid = bool(structural and all(acceptance.values()))
    return {
        "valid": valid,
        "acceptance": acceptance,
        "evidence_events": len(events),
        "sequence_contiguous": sequential,
        "producer_acceptance_ignored": True,
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
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
