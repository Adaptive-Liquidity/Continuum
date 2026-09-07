"""Proof Capsule builder — per packages/nexus-iq/PROOF_CAPSULES.md spec.

Ed25519 keypair is generated at first import and persisted to disk so capsule
signatures remain verifiable across restarts.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

_KEY_PATH = Path(__file__).parent / ".orchestrator_key.pem"


def _load_or_create_key() -> Ed25519PrivateKey:
    if _KEY_PATH.exists():
        return serialization.load_pem_private_key(_KEY_PATH.read_bytes(), password=None)
    k = Ed25519PrivateKey.generate()
    _KEY_PATH.write_bytes(k.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    _KEY_PATH.chmod(0o600)
    return k


_priv = _load_or_create_key()
_pub: Ed25519PublicKey = _priv.public_key()

PUBLIC_KEY_HEX = _pub.public_bytes(
    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
).hex()


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sign_bytes(data: bytes) -> str:
    return _priv.sign(data).hex()


def verify_bytes(data: bytes, sig_hex: str, pub_hex: str = None) -> bool:
    pub_hex = pub_hex or PUBLIC_KEY_HEX
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
    try:
        pub.verify(bytes.fromhex(sig_hex), data)
        return True
    except Exception:
        return False


async def build_proof_capsule(db, effect_id: str) -> dict:
    """Assemble a signed Proof Capsule for a committed effect.

    Contract fields (per nexus-iq/PROOF_CAPSULES.md):
      capsule_id, module, result, timestamp, capability_records,
      hmac_binding | signature, memory_evidence, limitations,
      redaction_manifest, duration_ms, profile_digest, failure(optional)
    """
    from bson import ObjectId
    eff = await db.effects.find_one({"_id": ObjectId(effect_id)})
    if not eff:
        raise ValueError(f"effect {effect_id} not found")

    # Gather evidence subchain for this effect (all entries where subject_id == effect_id)
    evidence = []
    async for e in db.evidence.find({"subject_id": effect_id}, sort=[("seq", 1)]):
        evidence.append({
            "seq": e["seq"], "kind": e["kind"],
            "prev_hash": e["prev_hash"], "self_hash": e["self_hash"],
            "payload": e.get("payload", {}),
        })
    if not evidence:
        raise ValueError(f"effect {effect_id} has no evidence")

    # Subchain root: SHA256 over the concatenation of entries' self_hash values
    root = hashlib.sha256()
    for e in evidence:
        root.update(bytes.fromhex(e["self_hash"]))
    subchain_root = root.hexdigest()

    # Grant record (capability provenance)
    grant_record = None
    if eff.get("grant_id"):
        g = await db.grants.find_one({"_id": ObjectId(eff["grant_id"])})
        if g:
            grant_record = {
                "grant_id": str(g["_id"]), "capability": g["capability"],
                "scope": g.get("scope", {}), "granted_by": g["granted_by"],
                "expires_at": g["expires_at"], "state": g["state"],
                "parent_grant_id": g.get("parent_grant_id"),
            }

    # Memory evidence: memories written during the effect's session
    memory_evidence = []
    if eff.get("session_id"):
        async for m in db.memories.find({"session_id": eff["session_id"]}, sort=[("created_at", 1)]):
            memory_evidence.append({
                "memory_id": str(m["_id"]), "kind": m["kind"],
                "content_hash": hashlib.sha256(m["content"].encode()).hexdigest(),
                "source": m.get("source", {}), "created_at": m["created_at"],
            })

    # Base capsule
    exec_at = eff.get("executed_at") or datetime.now(timezone.utc).isoformat()
    created_at = eff.get("created_at")
    duration_ms = None
    if exec_at and created_at:
        try:
            duration_ms = int((
                datetime.fromisoformat(exec_at) - datetime.fromisoformat(created_at)
            ).total_seconds() * 1000)
        except Exception:
            pass

    capsule = {
        "capsule_id": f"cap_{effect_id}",
        "capsule_version": "1.0",
        "profile_digest": hashlib.sha256(b"floks-pc-orchestrator/0.1.0").hexdigest()[:16],
        "module": f"orchestrator/effect/{eff['capability_required']}",
        "action_id": eff["action_id"],
        "vera_id": eff["vera_id"],
        "session_id": eff.get("session_id"),
        "timestamp": exec_at,
        "duration_ms": duration_ms,
        "result": eff.get("result", {}),
        "capability_records": [grant_record] if grant_record else [],
        "memory_evidence": memory_evidence,
        "evidence_subchain": {
            "root": subchain_root, "count": len(evidence),
            "first_seq": evidence[0]["seq"], "last_seq": evidence[-1]["seq"],
            "entries": evidence,
        },
        "limitations": [
            ("execution used the authenticated upstream nexus-agentd over its Unix socket"
             if eff.get("result", {}).get("adapter") == "nexus.live"
             else "orchestrator adapter is contract-faithful; not the upstream Rust nexus binary"),
            "signature attests to capsule integrity only, not to WASM execution correctness",
            "memory_evidence excludes memories written outside the bound session_id",
        ],
        "redaction_manifest": {"redacted_fields": []},
    }

    # Failure surface (per nexus-iq spec)
    if eff.get("outcome") in ("DENIED", "UNKNOWN"):
        capsule["failure"] = {
            "failure_category": eff["outcome"].lower(),
            "error_summary": eff.get("denial_reason") or "outcome unresolved",
        }

    # Sign the canonical capsule (excluding the signature block itself)
    signed_bytes = _canonical(capsule)
    capsule["signature_type"] = "ed25519"
    capsule["signature"] = sign_bytes(signed_bytes)
    capsule["signer_pubkey"] = PUBLIC_KEY_HEX

    return capsule
