"""Evidence ledger — hash-chained append-only log for DCA Responsibility 6.

Inspired by aeon-context-kernel's hash-chained JSONL trace. Every state change
across the seven responsibilities emits an entry. Verifiers can replay the
chain and confirm each entry's self_hash equals hash(prev_hash || payload).
"""
import hashlib
import json
from typing import Any
from models import EvidenceEntry


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def compute_hash(prev_hash: str, kind: str, subject_id: str, payload: dict) -> str:
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    h.update(kind.encode())
    h.update(subject_id.encode())
    h.update(_canonical(payload))
    return h.hexdigest()


async def append_evidence(db, kind: str, subject_id: str, payload: dict) -> EvidenceEntry:
    last = await db.evidence.find_one(sort=[("seq", -1)])
    prev_hash = last["self_hash"] if last else "GENESIS"
    seq = (last["seq"] if last else 0) + 1
    self_hash = compute_hash(prev_hash, kind, subject_id, payload)
    entry = EvidenceEntry(
        seq=seq, prev_hash=prev_hash, self_hash=self_hash,
        kind=kind, subject_id=subject_id, payload=payload,
    )
    doc = entry.to_mongo()
    result = await db.evidence.insert_one(doc)
    entry.id = str(result.inserted_id)
    return entry


async def verify_chain(db) -> dict:
    """Walk the chain from seq=1 → tip; re-derive each self_hash."""
    cursor = db.evidence.find({}, sort=[("seq", 1)])
    prev_hash = "GENESIS"
    verified = 0
    broken_at = None
    async for doc in cursor:
        expected = compute_hash(prev_hash, doc["kind"], doc["subject_id"], doc.get("payload", {}))
        if doc["self_hash"] != expected or doc["prev_hash"] != prev_hash:
            broken_at = doc["seq"]
            break
        prev_hash = doc["self_hash"]
        verified += 1
    return {"verified_entries": verified, "broken_at": broken_at, "tip_hash": prev_hash}
