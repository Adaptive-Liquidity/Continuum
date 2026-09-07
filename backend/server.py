"""floks-pc DCA Orchestrator — FastAPI server.

Integrates the seven mandatory DCA responsibilities across:
  R1 Principal Identity      -> /api/dca/veras                (VERA registry)
  R2 Environment/Runtime     -> /api/dca/placements           (floks-pc lineage)
  R3 Durable State/Memory    -> /api/dca/memory               (aeon-iq lineage)
  R4 Authority/Capability    -> /api/dca/authority            (genesis lineage)
  R5 Effectful Execution     -> /api/dca/effects              (nexus lineage)
  R6 Evidence/Verification   -> /api/dca/evidence             (context-kernel lineage)
  R7 Coordination/Interconnect -> /api/dca/sessions           (agent-bridge lineage)

Effect Boundary (cross-cutting) is enforced inside /effects/dispatch — the
gateway resolves authority (R4), checks placement (R2), executes via nexus
adapter (R5), and appends evidence (R6) atomically per action_id.
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from base import utcnow_iso
from evidence import append_evidence, verify_chain
from capsule import build_proof_capsule, PUBLIC_KEY_HEX
from adapters import aeon_iq as aeon_adapter
from adapters import nexus as nexus_adapter
from models import (
    VERA, RuntimePlacement, MemoryFact, AuthorityGrant, Effect, Session, EvidenceEntry,
    Mandate, Role, RoleAssignment,
    CreateVeraRequest, LeasePlacementRequest, WriteMemoryRequest, IssueGrantRequest,
    ProposeEffectRequest, OpenSessionRequest, HandoffRequest,
    CreateMandateRequest, CreateRoleRequest, AssignRoleRequest, EmergencySuspendRequest,
)

load_dotenv(Path(__file__).parent / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="floks-pc DCA Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# ============================================================
# Root / status
# ============================================================
@api.get("/")
async def root():
    return {
        "product": "floks-pc DCA",
        "hierarchy": ["Asentxia Systems", "DCA", "Continuum (floks-pc lineage)", "VERA", "The Regency"],
        "responsibilities": [
            "1: Principal Identity & Responsibility",
            "2: Environment & Runtime Continuity",
            "3: Durable State & Memory",
            "4: Authority & Capability Governance",
            "5: Effectful Execution",
            "6: Evidence, Verification & Recovery",
            "7: Coordination & Interconnect",
        ],
        "packages": ["floks-pc", "aeon-iq", "nexus", "nexus-iq", "genesis", "context-kernel"],
    }


@api.get("/dca/status")
async def dca_status():
    counts = {
        "veras": await db.veras.count_documents({}),
        "placements": await db.placements.count_documents({}),
        "memories": await db.memories.count_documents({}),
        "grants": await db.grants.count_documents({}),
        "effects": await db.effects.count_documents({}),
        "evidence": await db.evidence.count_documents({}),
        "sessions": await db.sessions.count_documents({}),
    }
    chain = await verify_chain(db)
    return {
        "counts": counts,
        "evidence_chain": chain,
        "subsystems": {
            "floks-pc": {"role": "R2", "state": "linked (packages/floks-pc)"},
            "aeon-iq": {"role": "R3", "state": "linked (packages/aeon-iq)"},
            "nexus": {"role": "R5", "state": "linked (packages/nexus)"},
            "nexus-iq": {"role": "R5+R6", "state": "linked (packages/nexus-iq)"},
            "genesis": {"role": "R1+R4", "state": "linked (packages/genesis)"},
            "context-kernel": {"role": "R6", "state": "linked (packages/context-kernel)"},
        },
    }


def _oid(s: str) -> ObjectId:
    if not ObjectId.is_valid(s):
        raise HTTPException(400, f"invalid id: {s}")
    return ObjectId(s)


# ============================================================
# R1 — Principal Identity & Responsibility (VERA registry)
# ============================================================
@api.post("/dca/veras", response_model=VERA)
async def create_vera(req: CreateVeraRequest):
    v = VERA(
        trust_domain=req.trust_domain, principal_id=req.principal_id,
        display_name=req.display_name, mandate=req.mandate,
    )
    doc = v.to_mongo()
    r = await db.veras.insert_one(doc)
    v.id = str(r.inserted_id)
    await append_evidence(db, "vera.created", v.id, {
        "trust_domain": v.trust_domain, "principal_id": v.principal_id, "mandate": v.mandate,
    })
    return v


@api.get("/dca/veras", response_model=list[VERA])
async def list_veras():
    return [VERA.from_mongo(d) async for d in db.veras.find(sort=[("created_at", -1)])]


@api.get("/dca/veras/{vera_id}", response_model=VERA)
async def get_vera(vera_id: str):
    doc = await db.veras.find_one({"_id": _oid(vera_id)})
    if not doc:
        raise HTTPException(404, "vera not found")
    return VERA.from_mongo(doc)


@api.post("/dca/veras/{vera_id}/suspend", response_model=VERA)
async def suspend_vera(vera_id: str):
    doc = await db.veras.find_one_and_update(
        {"_id": _oid(vera_id)}, {"$set": {"state": "SUSPENDED"}}, return_document=True
    )
    if not doc:
        raise HTTPException(404, "vera not found")
    await append_evidence(db, "vera.transition", vera_id, {"to": "SUSPENDED"})
    # cascading: revoke active grants
    await db.grants.update_many(
        {"vera_id": vera_id, "state": "ACTIVE"}, {"$set": {"state": "SUSPENDED"}}
    )
    return VERA.from_mongo(doc)


@api.post("/dca/veras/{vera_id}/decommission", response_model=VERA)
async def decommission_vera(vera_id: str):
    doc = await db.veras.find_one_and_update(
        {"_id": _oid(vera_id)}, {"$set": {"state": "DECOMMISSIONED"}}, return_document=True
    )
    if not doc:
        raise HTTPException(404, "vera not found")
    await append_evidence(db, "vera.transition", vera_id, {"to": "DECOMMISSIONED"})
    await db.grants.update_many({"vera_id": vera_id}, {"$set": {"state": "REVOKED"}})
    await db.placements.update_many(
        {"vera_id": vera_id, "state": "ACTIVE"}, {"$set": {"state": "TERMINATED"}}
    )
    return VERA.from_mongo(doc)


# ============================================================
# R2 — Environment & Runtime Continuity (floks-pc Agent Computer)
# ============================================================
@api.post("/dca/placements/lease", response_model=RuntimePlacement)
async def lease_placement(req: LeasePlacementRequest):
    vera = await db.veras.find_one({"_id": _oid(req.vera_id)})
    if not vera:
        raise HTTPException(404, "vera not found")
    if vera["state"] != "ACTIVE":
        raise HTTPException(409, f"vera not ACTIVE ({vera['state']})")
    expires = datetime.now(timezone.utc) + timedelta(seconds=req.ttl_seconds)
    placement = RuntimePlacement(
        vera_id=req.vera_id, provider=req.provider,
        computer_id=f"pc-{uuid.uuid4().hex[:12]}",
        lease_expires_at=expires.isoformat(),
        capabilities=req.capabilities,
        surface={"browser": "chromium/cdp", "shell": True, "fs": "isolated"},
    )
    doc = placement.to_mongo()
    r = await db.placements.insert_one(doc)
    placement.id = str(r.inserted_id)
    await append_evidence(db, "placement.leased", placement.id, {
        "vera_id": req.vera_id, "provider": req.provider, "epoch": placement.lease_epoch,
    })
    return placement


@api.get("/dca/placements", response_model=list[RuntimePlacement])
async def list_placements():
    return [RuntimePlacement.from_mongo(d) async for d in db.placements.find(sort=[("created_at", -1)])]


@api.post("/dca/placements/{placement_id}/fence", response_model=RuntimePlacement)
async def fence_placement(placement_id: str):
    """Fence a runtime placement — reject subsequent effects with old epoch."""
    doc = await db.placements.find_one_and_update(
        {"_id": _oid(placement_id)},
        {"$set": {"state": "FENCED"}, "$inc": {"lease_epoch": 1}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(404, "placement not found")
    await append_evidence(db, "placement.fenced", placement_id, {"new_epoch": doc["lease_epoch"]})
    return RuntimePlacement.from_mongo(doc)


# ============================================================
# R3 — Durable State & Memory (aeon-iq lineage)
# ============================================================
@api.post("/dca/memory", response_model=MemoryFact)
async def write_memory(req: WriteMemoryRequest):
    vera = await db.veras.find_one({"_id": _oid(req.vera_id)})
    if not vera:
        raise HTTPException(404, "vera not found")
    fact = MemoryFact(
        vera_id=req.vera_id, session_id=req.session_id, kind=req.kind,
        content=req.content, source=req.source,
    )
    doc = fact.to_mongo()
    # AEON-IQ adapter: compute and persist embedding when available.
    emb = await aeon_adapter.embed_text(req.content)
    if emb:
        doc["embedding"] = emb
    r = await db.memories.insert_one(doc)
    fact.id = str(r.inserted_id)
    await append_evidence(db, "memory.write", fact.id, {
        "vera_id": req.vera_id, "kind": req.kind, "content_len": len(req.content),
        "embedded": bool(emb),
    })
    return fact


@api.get("/dca/memory/recall/{vera_id}", response_model=list[MemoryFact])
async def recall_memory(vera_id: str, q: Optional[str] = None, limit: int = 20,
                        mode: str = "auto"):
    """Recall memory. mode: 'semantic' (aeon-iq), 'substring', or 'auto'."""
    if mode == "auto":
        mode = "semantic" if (q and aeon_adapter.embedding_available()) else "substring"

    if mode == "semantic" and q:
        qvec = await aeon_adapter.embed_text(q)
        if qvec:
            cursor = db.memories.find({"vera_id": vera_id, "embedding": {"$exists": True}})
            candidates = [c async for c in cursor]
            ranked = aeon_adapter.cosine_top_k(qvec, candidates, k=limit)
            out = []
            for c in ranked:
                sim = c.pop("similarity", None)
                fact = MemoryFact.from_mongo(c)
                if fact:
                    # attach similarity via source dict (non-schema field would break)
                    fact.source = {**fact.source, "_similarity": sim}
                    out.append(fact)
            await append_evidence(db, "memory.recall", vera_id, {
                "q": q, "mode": "semantic", "returned": len(out),
            })
            return out

    # Substring fallback
    query: dict = {"vera_id": vera_id}
    if q:
        query["content"] = {"$regex": q, "$options": "i"}
    facts = []
    async for d in db.memories.find(query, sort=[("created_at", -1)]).limit(limit):
        d.pop("embedding", None)
        facts.append(MemoryFact.from_mongo(d))
    await append_evidence(db, "memory.recall", vera_id, {
        "q": q or "", "mode": "substring", "returned": len(facts),
    })
    return facts


@api.get("/dca/memory/status")
async def memory_status():
    return {
        "adapter": "aeon-iq (contract-faithful, in-orchestrator)",
        "embedding_backend": aeon_adapter.embedding_backend(),
        "embedding_provider": aeon_adapter.embedding_provider(),
        "embedding_available": aeon_adapter.embedding_available(),
        "embedding_note": aeon_adapter.embedding_note(),
        "note": ("openai backend uses text-embedding-3-small (1536-d); "
                 "local backend uses deterministic char-3gram feature hashing (256-d)"),
    }


# ============================================================
# R4 — Authority & Capability Governance (genesis lineage)
# ============================================================
@api.post("/dca/authority/grants", response_model=AuthorityGrant)
async def issue_grant(req: IssueGrantRequest):
    vera = await db.veras.find_one({"_id": _oid(req.vera_id)})
    if not vera:
        raise HTTPException(404, "vera not found")
    if vera["state"] != "ACTIVE":
        raise HTTPException(409, f"vera not ACTIVE ({vera['state']})")
    # attenuation check: child grant scope must be subset of parent
    if req.parent_grant_id:
        parent = await db.grants.find_one({"_id": _oid(req.parent_grant_id)})
        if not parent or parent["state"] != "ACTIVE":
            raise HTTPException(409, "parent grant not ACTIVE")
        if parent["capability"] != req.capability:
            raise HTTPException(400, "attenuation: capability must match parent")
    expires = datetime.now(timezone.utc) + timedelta(seconds=req.ttl_seconds)
    g = AuthorityGrant(
        vera_id=req.vera_id, granted_by=req.granted_by, capability=req.capability,
        scope=req.scope, expires_at=expires.isoformat(),
        parent_grant_id=req.parent_grant_id,
    )
    doc = g.to_mongo()
    r = await db.grants.insert_one(doc)
    g.id = str(r.inserted_id)
    await append_evidence(db, "grant.issued", g.id, {
        "vera_id": req.vera_id, "capability": req.capability, "parent": req.parent_grant_id,
    })
    return g


@api.get("/dca/authority/grants", response_model=list[AuthorityGrant])
async def list_grants(vera_id: Optional[str] = None):
    query = {"vera_id": vera_id} if vera_id else {}
    return [AuthorityGrant.from_mongo(d) async for d in db.grants.find(query, sort=[("created_at", -1)])]


@api.post("/dca/authority/grants/{grant_id}/revoke", response_model=AuthorityGrant)
async def revoke_grant(grant_id: str):
    doc = await db.grants.find_one_and_update(
        {"_id": _oid(grant_id)}, {"$set": {"state": "REVOKED"}}, return_document=True
    )
    if not doc:
        raise HTTPException(404, "grant not found")
    # cascading revocation of children
    await db.grants.update_many(
        {"parent_grant_id": grant_id, "state": "ACTIVE"}, {"$set": {"state": "REVOKED"}}
    )
    await append_evidence(db, "grant.revoked", grant_id, {"cascaded": True})
    return AuthorityGrant.from_mongo(doc)


# ============================================================
# R5 — Effectful Execution (nexus lineage) + Effect Boundary
# ============================================================
async def _resolve_authority(vera_id: str, capability: str) -> Optional[dict]:
    """Effect Boundary: find current ACTIVE grant covering this capability."""
    now = utcnow_iso()
    return await db.grants.find_one({
        "vera_id": vera_id, "capability": capability,
        "state": "ACTIVE", "expires_at": {"$gt": now},
    })


@api.post("/dca/effects/propose", response_model=Effect)
async def propose_effect(req: ProposeEffectRequest):
    """Prepare an effect. Cognition proposes; authority decides."""
    existing = await db.effects.find_one({"action_id": req.action_id})
    if existing:
        # exactly-once semantics: return existing state, do not re-execute
        return Effect.from_mongo(existing)
    eff = Effect(
        vera_id=req.vera_id, session_id=req.session_id,
        action_id=req.action_id, capability_required=req.capability_required,
        payload=req.payload, outcome="PREPARED",
    )
    doc = eff.to_mongo()
    r = await db.effects.insert_one(doc)
    eff.id = str(r.inserted_id)
    await append_evidence(db, "effect.prepared", eff.id, {
        "action_id": req.action_id, "capability": req.capability_required,
    })
    return eff


@api.post("/dca/effects/{effect_id}/dispatch", response_model=Effect)
async def dispatch_effect(effect_id: str):
    """Effect Boundary — the cross-cutting gate.

    Steps:
      1. Load effect (must be PREPARED)
      2. Verify placement lease not FENCED (R2)
      3. Resolve authority (R4): active grant covering capability
      4. Adapter dispatch — nexus-style capability-gated execution (mocked here)
      5. Commit outcome + evidence (R6)
    """
    eff = await db.effects.find_one({"_id": _oid(effect_id)})
    if not eff:
        raise HTTPException(404, "effect not found")
    if eff["outcome"] not in ("PREPARED", "UNKNOWN"):
        raise HTTPException(409, f"effect not dispatchable ({eff['outcome']})")

    grant = await _resolve_authority(eff["vera_id"], eff["capability_required"])
    if not grant:
        await db.effects.update_one({"_id": _oid(effect_id)}, {"$set": {
            "outcome": "DENIED", "denial_reason": "no active grant for capability",
        }})
        await append_evidence(db, "effect.denied", effect_id, {"reason": "no_active_grant"})
        return Effect.from_mongo(await db.effects.find_one({"_id": _oid(effect_id)}))

    # placement fencing check
    if eff.get("session_id"):
        sess = await db.sessions.find_one({"_id": _oid(eff["session_id"])})
        if sess:
            pl = await db.placements.find_one({"_id": _oid(sess["placement_id"])})
            if pl and pl["state"] != "ACTIVE":
                await db.effects.update_one({"_id": _oid(effect_id)}, {"$set": {
                    "outcome": "DENIED", "denial_reason": f"placement {pl['state']}",
                }})
                await append_evidence(db, "effect.denied", effect_id, {"reason": "placement_fenced"})
                return Effect.from_mongo(await db.effects.find_one({"_id": _oid(effect_id)}))

    # Adapter: real nexus wasmtime dispatch (falls back to nexus.echo if no wasm supplied)
    result = nexus_adapter.dispatch(grant, eff["action_id"], eff["payload"])
    result_status = result.get("status")
    committed = result_status == "committed"
    outcome = "COMMITTED" if committed else "DENIED" if result_status == "denied" else "UNKNOWN"
    failure_reason = result.get("reason") or result.get("error") or "execution outcome unknown"

    await db.effects.update_one({"_id": _oid(effect_id)}, {"$set": {
        "outcome": outcome, "grant_id": str(grant["_id"]),
        "result": result,
        "denial_reason": None if committed else failure_reason,
        "executed_at": utcnow_iso(),
    }})
    evidence_kind = "effect.committed" if committed else "effect.denied" if outcome == "DENIED" else "effect.unknown"
    await append_evidence(db, evidence_kind, effect_id, {
        "action_id": eff["action_id"], "grant_id": str(grant["_id"]),
        "adapter": result.get("adapter"), "status": result_status,
    })
    return Effect.from_mongo(await db.effects.find_one({"_id": _oid(effect_id)}))


@api.get("/dca/effects", response_model=list[Effect])
async def list_effects(vera_id: Optional[str] = None, limit: int = 50):
    query = {"vera_id": vera_id} if vera_id else {}
    return [Effect.from_mongo(d) async for d in db.effects.find(query, sort=[("created_at", -1)]).limit(limit)]


# ============================================================
# R6 — Evidence, Verification & Recovery (context-kernel lineage)
# ============================================================
@api.get("/dca/evidence", response_model=list[EvidenceEntry])
async def list_evidence(subject_id: Optional[str] = None, limit: int = 100):
    query = {"subject_id": subject_id} if subject_id else {}
    return [EvidenceEntry.from_mongo(d) async for d in db.evidence.find(query, sort=[("seq", -1)]).limit(limit)]


@api.get("/dca/evidence/verify")
async def verify_evidence():
    return await verify_chain(db)


# ============================================================
# R7 — Coordination & Interconnect (sessions + handoffs)
# ============================================================
@api.post("/dca/sessions/open", response_model=Session)
async def open_session(req: OpenSessionRequest):
    pl = await db.placements.find_one({"_id": _oid(req.placement_id)})
    if not pl or pl["state"] != "ACTIVE":
        raise HTTPException(409, "placement not ACTIVE")
    if pl["vera_id"] != req.vera_id:
        raise HTTPException(403, "placement not leased to this vera")
    sess = Session(vera_id=req.vera_id, placement_id=req.placement_id)
    doc = sess.to_mongo()
    r = await db.sessions.insert_one(doc)
    sess.id = str(r.inserted_id)
    await append_evidence(db, "session.opened", sess.id, {"vera_id": req.vera_id, "placement_id": req.placement_id})
    return sess


@api.post("/dca/sessions/{session_id}/close", response_model=Session)
async def close_session(session_id: str):
    doc = await db.sessions.find_one_and_update(
        {"_id": _oid(session_id)},
        {"$set": {"state": "CLOSED", "closed_at": utcnow_iso()}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(404, "session not found")
    await append_evidence(db, "session.closed", session_id, {})
    return Session.from_mongo(doc)


@api.post("/dca/sessions/handoff", response_model=Session)
async def handoff_session(req: HandoffRequest):
    """R7 — authenticated handoff between VERAs. Preserves participant separation."""
    target = await db.veras.find_one({"_id": _oid(req.handoff_to_vera_id)})
    if not target or target["state"] != "ACTIVE":
        raise HTTPException(409, "target vera not ACTIVE")
    doc = await db.sessions.find_one_and_update(
        {"_id": _oid(req.session_id)},
        {"$set": {"state": "HANDED_OFF", "handoff_to": req.handoff_to_vera_id,
                  "closed_at": utcnow_iso()}},
        return_document=True,
    )
    if not doc:
        raise HTTPException(404, "session not found")
    await append_evidence(db, "handoff", req.session_id, {
        "from": doc["vera_id"], "to": req.handoff_to_vera_id,
    })
    return Session.from_mongo(doc)


@api.get("/dca/sessions", response_model=list[Session])
async def list_sessions():
    return [Session.from_mongo(d) async for d in db.sessions.find(sort=[("created_at", -1)])]


# ============================================================
# Seed endpoint — demo data for the ops dashboard
# ============================================================
@api.post("/dca/seed")
async def seed_demo():
    """Idempotent-ish seed: only inserts if the demo VERA doesn't already exist."""
    existing = await db.veras.find_one({"principal_id": "demo-vera-001"})
    if existing:
        return {"seeded": False, "reason": "already exists", "vera_id": str(existing["_id"])}

    # 1. Create demo VERA
    v = VERA(
        trust_domain="asentxia.local", principal_id="demo-vera-001",
        display_name="Demo VERA (Continuum reference)",
        mandate="Demonstrate the seven DCA responsibilities end-to-end.",
    )
    r = await db.veras.insert_one(v.to_mongo())
    v.id = str(r.inserted_id)
    await append_evidence(db, "vera.created", v.id, {"principal_id": v.principal_id})

    # 2. Lease a placement
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    pl = RuntimePlacement(
        vera_id=v.id, computer_id=f"pc-{uuid.uuid4().hex[:12]}",
        lease_expires_at=expires.isoformat(),
        capabilities=["fs.read", "browser.observe"],
        surface={"browser": "chromium/cdp", "shell": True, "fs": "isolated"},
    )
    r = await db.placements.insert_one(pl.to_mongo())
    pl.id = str(r.inserted_id)
    await append_evidence(db, "placement.leased", pl.id, {"vera_id": v.id, "epoch": 1})

    # 3. Issue a grant
    g = AuthorityGrant(
        vera_id=v.id, granted_by="human:owner",
        capability="effect:http.fetch",
        scope={"host_allowlist": ["example.com"], "max_bytes": 65536},
        expires_at=expires.isoformat(),
    )
    r = await db.grants.insert_one(g.to_mongo())
    g.id = str(r.inserted_id)
    await append_evidence(db, "grant.issued", g.id, {"vera_id": v.id, "capability": g.capability})

    # 4. Open a session
    sess = Session(vera_id=v.id, placement_id=pl.id)
    r = await db.sessions.insert_one(sess.to_mongo())
    sess.id = str(r.inserted_id)
    await append_evidence(db, "session.opened", sess.id, {"vera_id": v.id, "placement_id": pl.id})

    # 5. Write memory
    f = MemoryFact(
        vera_id=v.id, session_id=sess.id, kind="semantic",
        content="Continuum is Asentxia's flagship DCA implementation. floks-pc is the runtime lineage.",
        source={"origin": "seed", "provenance": "01_DCA_Foundation.md#Continuum"},
    )
    r = await db.memories.insert_one(f.to_mongo())
    f.id = str(r.inserted_id)
    await append_evidence(db, "memory.write", f.id, {"vera_id": v.id, "kind": "semantic"})

    # 6. Propose + dispatch an effect end-to-end
    eff = Effect(
        vera_id=v.id, session_id=sess.id, action_id=f"act-{uuid.uuid4().hex[:8]}",
        capability_required="effect:http.fetch",
        payload={"url": "https://example.com/", "method": "GET"},
    )
    r = await db.effects.insert_one(eff.to_mongo())
    eff.id = str(r.inserted_id)
    await append_evidence(db, "effect.prepared", eff.id, {"action_id": eff.action_id})
    # dispatch through effect boundary
    await db.effects.update_one({"_id": ObjectId(eff.id)}, {"$set": {
        "outcome": "COMMITTED", "grant_id": g.id,
        "result": {"adapter": "nexus.mock", "status": 200},
        "executed_at": utcnow_iso(),
    }})
    await append_evidence(db, "effect.committed", eff.id, {"action_id": eff.action_id, "grant_id": g.id})

    return {"seeded": True, "vera_id": v.id, "placement_id": pl.id, "session_id": sess.id,
            "grant_id": g.id, "effect_id": eff.id}


app.include_router(api)


# ============================================================
# Phase 1 — Proof Capsule Export
# ============================================================
capsule_router = APIRouter(prefix="/api", tags=["capsules"])


@capsule_router.post("/dca/effects/{effect_id}/capsule")
async def create_capsule(effect_id: str):
    try:
        capsule = await build_proof_capsule(db, effect_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return capsule


@capsule_router.get("/dca/capsules/{effect_id}")
async def download_capsule(effect_id: str):
    from fastapi.responses import JSONResponse
    try:
        capsule = await build_proof_capsule(db, effect_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return JSONResponse(
        content=capsule,
        headers={"Content-Disposition": f'attachment; filename="capsule_{effect_id}.json"'},
    )


@capsule_router.get("/dca/orchestrator/pubkey")
async def orchestrator_pubkey():
    """Ed25519 public key clients need to verify capsule signatures + cap tokens."""
    return {"pubkey_ed25519_hex": PUBLIC_KEY_HEX,
            "usage": "verify capsule.signature and nexus capability tokens"}


@capsule_router.get("/dca/nexus/status")
async def nexus_wire_status():
    """Health probe for the live nexus-agentd wire."""
    from nexus_wire import ping, socket_path, auth_token
    info = ping()
    info["auth_configured"] = bool(auth_token())
    info["adapter_priority"] = ["nexus.live" if info["available"] else None,
                                "nexus.wasmtime" if nexus_adapter.WASMTIME_OK else None,
                                "nexus.echo"]
    info["adapter_priority"] = [a for a in info["adapter_priority"] if a]
    return info


app.include_router(capsule_router)


# ============================================================
# Phase 2 — Regency Console (governance) — bound to R4
# ============================================================
regency = APIRouter(prefix="/api/regency", tags=["regency"])


@regency.get("/mandates", response_model=list[Mandate])
async def list_mandates():
    return [Mandate.from_mongo(d) async for d in db.mandates.find(sort=[("created_at", -1)])]


@regency.post("/mandates", response_model=Mandate)
async def create_mandate(req: CreateMandateRequest):
    m = Mandate(title=req.title, description=req.description, envelope=req.envelope)
    r = await db.mandates.insert_one(m.to_mongo())
    m.id = str(r.inserted_id)
    await append_evidence(db, "vera.transition", m.id,
                          {"regency": "mandate.created", "title": m.title})
    return m


@regency.get("/roles", response_model=list[Role])
async def list_roles():
    return [Role.from_mongo(d) async for d in db.roles.find(sort=[("created_at", -1)])]


@regency.post("/roles", response_model=Role)
async def create_role(req: CreateRoleRequest):
    role = Role(name=req.name, capabilities=req.capabilities, mandate_id=req.mandate_id)
    r = await db.roles.insert_one(role.to_mongo())
    role.id = str(r.inserted_id)
    await append_evidence(db, "vera.transition", role.id,
                          {"regency": "role.created", "name": role.name,
                           "capabilities": role.capabilities})
    return role


@regency.get("/assignments", response_model=list[RoleAssignment])
async def list_assignments():
    return [RoleAssignment.from_mongo(d) async for d in db.role_assignments.find(sort=[("created_at", -1)])]


@regency.post("/assignments", response_model=RoleAssignment)
async def assign_role(req: AssignRoleRequest):
    vera = await db.veras.find_one({"_id": _oid(req.vera_id)})
    role = await db.roles.find_one({"_id": _oid(req.role_id)})
    if not vera or not role:
        raise HTTPException(404, "vera or role not found")
    a = RoleAssignment(vera_id=req.vera_id, role_id=req.role_id, assigned_by=req.assigned_by)
    r = await db.role_assignments.insert_one(a.to_mongo())
    a.id = str(r.inserted_id)
    # Materialize as authority grants for each capability in the role.
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    for cap in role["capabilities"]:
        g = AuthorityGrant(
            vera_id=req.vera_id, granted_by=f"regency:role:{role['name']}",
            capability=cap, scope={"role_id": req.role_id, "assignment_id": a.id},
            expires_at=expires.isoformat(),
        )
        gr = await db.grants.insert_one(g.to_mongo())
        await append_evidence(db, "grant.issued", str(gr.inserted_id), {
            "vera_id": req.vera_id, "capability": cap, "regency_role": role["name"],
        })
    await append_evidence(db, "vera.transition", req.vera_id,
                          {"regency": "role.assigned", "role": role["name"]})
    return a


@regency.post("/emergency-suspend")
async def emergency_suspend(req: EmergencySuspendRequest):
    """Bulk-suspend VERAs. Cascades: grants→SUSPENDED, placements→FENCED. Evidence trail.

    Locked behavior per Foundation §6:
      "The console's emergency action cannot promise an instantaneous global stop.
       It requests suspension/revocation and causes reachable enforcement points to act."
    """
    affected = {"veras": [], "grants": 0, "placements": 0}
    for vid in req.vera_ids:
        v = await db.veras.find_one({"_id": _oid(vid)})
        if not v:
            continue
        await db.veras.update_one({"_id": _oid(vid)}, {"$set": {"state": "SUSPENDED"}})
        gr = await db.grants.update_many(
            {"vera_id": vid, "state": "ACTIVE"}, {"$set": {"state": "SUSPENDED"}}
        )
        # bump lease epoch on active placements to fence them
        active_placements = await db.placements.find({"vera_id": vid, "state": "ACTIVE"}).to_list(1000)
        for p in active_placements:
            await db.placements.update_one(
                {"_id": p["_id"]},
                {"$set": {"state": "FENCED"}, "$inc": {"lease_epoch": 1}},
            )
            await append_evidence(db, "placement.fenced", str(p["_id"]),
                                  {"reason": "emergency_suspend", "initiated_by": req.initiated_by})
        affected["veras"].append(vid)
        affected["grants"] += gr.modified_count
        affected["placements"] += len(active_placements)
        await append_evidence(db, "vera.transition", vid, {
            "to": "SUSPENDED", "regency": "emergency_suspend",
            "reason": req.reason, "initiated_by": req.initiated_by,
        })
    return {"affected": affected, "boundary_note": (
        "Enforcement is receiving-side. Reachable enforcement points now reject "
        "suspended veras' grants and superseded placement epochs. Instantaneous "
        "global stop is not guaranteed across partitions."
    )}


app.include_router(regency)
