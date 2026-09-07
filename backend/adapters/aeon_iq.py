"""AEON-IQ semantic retrieval adapter.

Contract-faithful in-orchestrator replacement for the upstream
packages/aeon-iq Rust MemoryOS proxy. Two embedding backends:

  1. OpenAI-compatible via `text-embedding-3-small` (1536-d) through the
     configured Emergent gateway or direct provider path when available.
  2. Deterministic local hash-embedder (256-d, char-n-gram feature hashing)
     as fallback — real cosine similarity, no external dep.

Vectors are stored on each MemoryFact document under `embedding: list[float]`.
Recall computes cosine similarity in numpy and returns top-K. Both backends
match aeon-iq's HNSW retrieval contract shape.
"""
from __future__ import annotations
import os
import asyncio
import hashlib
from typing import Optional
import numpy as np

LOCAL_DIM = 256
_backend = None  # "openai" | "local"
_client = None
_provider = None
_backend_note = None


def _init():
    global _backend, _client, _provider, _backend_note
    if _backend is not None:
        return
    gateway_key = os.environ.get("EMERGENT_LLM_KEY")
    gateway_base = os.environ.get("EMERGENT_LLM_BASE_URL")
    direct_key = os.environ.get("OPENAI_API_KEY")
    if gateway_key and gateway_base:
        try:
            from openai import OpenAI
            _client = OpenAI(api_key=gateway_key, base_url=gateway_base)
            _client.embeddings.create(model="text-embedding-3-small", input="ping")
            _backend = "openai"
            _provider = "emergent-gateway"
            return
        except Exception as error:
            _backend_note = f"gateway embedding unavailable ({type(error).__name__})"
    elif direct_key:
        try:
            from openai import OpenAI
            _client = OpenAI(api_key=direct_key)
            _client.embeddings.create(model="text-embedding-3-small", input="ping")
            _backend = "openai"
            _provider = "openai"
            return
        except Exception as error:
            _backend_note = f"provider embedding unavailable ({type(error).__name__})"
    else:
        _backend_note = "no embedding provider configured"
    _backend = "local"
    _provider = "local"


def embedding_available() -> bool:
    _init()
    return _backend in ("openai", "local")


def embedding_backend() -> str:
    _init()
    return _backend or "local"


def embedding_provider() -> str:
    _init()
    return _provider or "local"


def embedding_note() -> str:
    _init()
    return _backend_note or "text-embedding-3-small active"


def _local_embed(text: str, dim: int = LOCAL_DIM) -> list[float]:
    """Deterministic char-3gram feature hashing → L2-normalized vector."""
    vec = np.zeros(dim, dtype=np.float32)
    t = ("  " + (text or "").lower() + "  ").encode("utf-8", "ignore")
    for i in range(len(t) - 2):
        gram = t[i:i + 3]
        h = int.from_bytes(hashlib.md5(gram).digest()[:4], "big")
        idx = h % dim
        sign = 1.0 if (h >> 31) & 1 else -1.0
        vec[idx] += sign
    n = np.linalg.norm(vec)
    if n > 0:
        vec /= n
    return vec.tolist()


async def embed_text(text: str) -> Optional[list[float]]:
    _init()
    if _backend == "openai":
        def _do():
            r = _client.embeddings.create(model="text-embedding-3-small", input=text[:8000])
            return r.data[0].embedding
        try:
            return await asyncio.to_thread(_do)
        except Exception:
            pass  # fall through to local
    return _local_embed(text)


def cosine_top_k(query_vec: list[float], candidates: list[dict], k: int = 20) -> list[dict]:
    if not candidates:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    q_norm = q / (np.linalg.norm(q) + 1e-9)
    scored = []
    for c in candidates:
        emb = c.get("embedding")
        if not emb:
            continue
        v = np.asarray(emb, dtype=np.float32)
        if v.shape != q_norm.shape:
            continue  # dim mismatch — skip (e.g., mixed backends over time)
        v_norm = v / (np.linalg.norm(v) + 1e-9)
        score = float(np.dot(q_norm, v_norm))
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, c in scored[:k]:
        c2 = {kk: vv for kk, vv in c.items() if kk != "embedding"}
        c2["similarity"] = round(score, 4)
        out.append(c2)
    return out
