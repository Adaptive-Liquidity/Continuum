"""Live Nexus wire client — speaks the packages/nexus daemon protocol.

Protocol (from packages/nexus/src/daemon/protocol.rs + mod.rs):
  Transport: Unix stream socket (POSIX). Framing: `[u32 BE payload_len][json]`.
  Request:  {"type":"Ping"} | {"type":"Execute", name, wasm_bytes|wasm_path, entry, input, auth_token?}
  Response: {"type":"Pong", "version": "..."}
          | {"type":"Executed", "output": ToolOutput}
          | {"type":"Error", "message": "..."}

wasm_bytes uses serde_bytes serialization → JSON array of u8 (byte-per-int).

Env vars honored (compatible with nexus-agentd):
  NEXUS_AGENTD_SOCKET      — socket path (default /run/nexus-agentd.sock or platform default)
  NEXUS_AGENTD_AUTH_TOKEN  — bearer token if configured on the daemon

Falls back cleanly if socket unreachable — the higher-level nexus adapter
selects the wasmtime path when this wire returns UNREACHABLE.
"""
from __future__ import annotations
import base64
import json
import os
import socket
import struct
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_SOCKET = "/run/nexus-agentd.sock"
CONNECT_TIMEOUT_S = 1.5
RECV_TIMEOUT_S = 30.0


def socket_path() -> str:
    return os.environ.get("NEXUS_AGENTD_SOCKET", DEFAULT_SOCKET)


def auth_token() -> Optional[str]:
    t = os.environ.get("NEXUS_AGENTD_AUTH_TOKEN", "").strip()
    return t or None


def _connect() -> socket.socket:
    p = socket_path()
    if not Path(p).exists():
        raise FileNotFoundError(f"nexus-agentd socket not present at {p}")
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(CONNECT_TIMEOUT_S)
    s.connect(p)
    s.settimeout(RECV_TIMEOUT_S)
    return s


def _write_frame(s: socket.socket, payload: dict) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode()
    s.sendall(struct.pack(">I", len(body)) + body)


def _read_exact(s: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("nexus-agentd closed the stream")
        buf += chunk
    return buf


def _read_frame(s: socket.socket) -> dict:
    (length,) = struct.unpack(">I", _read_exact(s, 4))
    if length > 64 * 1024 * 1024:
        raise ValueError(f"frame too large: {length}")
    body = _read_exact(s, length)
    return json.loads(body)


def is_available() -> bool:
    """Fast reachability probe — attempts a Ping."""
    try:
        s = _connect()
    except Exception:
        return False
    try:
        _write_frame(s, {"type": "Ping"})
        resp = _read_frame(s)
        return resp.get("type") == "Pong"
    except Exception:
        return False
    finally:
        try: s.close()
        except Exception: pass


def ping() -> dict:
    """Returns {"available": bool, "version": str|None, "socket": str, "error": str|None}."""
    p = socket_path()
    try:
        s = _connect()
    except Exception as e:
        return {"available": False, "version": None, "socket": p, "error": f"{type(e).__name__}: {e}"}
    try:
        _write_frame(s, {"type": "Ping"})
        resp = _read_frame(s)
        if resp.get("type") == "Pong":
            return {"available": True, "version": resp.get("version"), "socket": p, "error": None}
        return {"available": False, "version": None, "socket": p, "error": f"unexpected {resp}"}
    except Exception as e:
        return {"available": False, "version": None, "socket": p, "error": f"{type(e).__name__}: {e}"}
    finally:
        try: s.close()
        except Exception: pass


def execute(name: str, wasm_bytes: bytes, entry: str = "_start",
            input_json: Optional[dict] = None) -> dict:
    """Send Execute request, return the daemon response as a dict.

    Return shapes:
      success: {"type":"Executed", "output": {...}, "wire_ms": int}
      denied/err: {"type":"Error", "message": "..."}
      wire error: {"type":"WireError", "error": "..."} (adapter-only)
    """
    payload: dict[str, Any] = {
        "type": "Execute",
        "name": name,
        # nexus daemon expects wasm_bytes as base64-encoded string (STANDARD alphabet)
        "wasm_bytes": base64.b64encode(wasm_bytes).decode("ascii"),
        "entry": entry,
        "input": input_json or {},
    }
    if tok := auth_token():
        payload["auth_token"] = tok

    t0 = time.time()
    try:
        s = _connect()
    except Exception as e:
        return {"type": "WireError", "error": f"connect: {type(e).__name__}: {e}"}
    try:
        _write_frame(s, payload)
        resp = _read_frame(s)
        resp["wire_ms"] = int((time.time() - t0) * 1000)
        return resp
    except Exception as e:
        return {"type": "WireError", "error": f"io: {type(e).__name__}: {e}"}
    finally:
        try: s.close()
        except Exception: pass
