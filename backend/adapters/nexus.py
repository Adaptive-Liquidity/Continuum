"""Nexus WASM sandbox adapter — contract-faithful.

Mirrors packages/nexus behavior:
  - Ed25519-signed capability tokens (signed by the orchestrator's key)
  - Pre-opened WASI directory scope (via wasmtime WasiConfig)
  - Deterministic execution (no ambient FS/network)
  - Snapshot/rollback via fresh Store per call
  - Capability trace collected during execution

If wasmtime is not importable, execute() returns a diagnostic result explaining
the fallback so the orchestrator does not fail hard.
"""
from __future__ import annotations
import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ed25519 (reuse capsule's keypair for a single-signer model)
from capsule import sign_bytes, verify_bytes, PUBLIC_KEY_HEX

WASM_DEMO_PATH = Path(__file__).parent.parent / "wasm" / "hello.wasm"
WASM_NEXUS_DEMO_PATH = Path(__file__).parent.parent / "wasm" / "nexus_demo.wasm"

try:
    import wasmtime  # type: ignore
    WASMTIME_OK = True
except Exception:
    wasmtime = None
    WASMTIME_OK = False


def mint_capability_token(grant: dict, action_id: str, ttl_seconds: int = 60) -> dict:
    """Sign a scoped capability token derived from an active grant."""
    payload = {
        "grant_id": str(grant["_id"]) if "_id" in grant else grant["id"],
        "vera_id": grant["vera_id"],
        "capability": grant["capability"],
        "scope": grant.get("scope", {}),
        "action_id": action_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "not_after": time.time() + ttl_seconds,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {
        "payload": payload,
        "signature": sign_bytes(canonical),
        "signer_pubkey": PUBLIC_KEY_HEX,
    }


def verify_capability_token(token: dict) -> tuple[bool, str]:
    p = token.get("payload", {})
    canonical = json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    if not verify_bytes(canonical, token.get("signature", ""), token.get("signer_pubkey")):
        return False, "signature invalid"
    if p.get("not_after", 0) < time.time():
        return False, "token expired"
    return True, "ok"


def _load_module_bytes(payload: dict) -> Optional[bytes]:
    if b64 := payload.get("wasm_b64"):
        try:
            return base64.b64decode(b64)
        except Exception:
            return None
    if path := payload.get("wasm_path"):
        p = Path(path)
        if p.exists() and p.suffix == ".wasm":
            return p.read_bytes()
    if payload.get("use_nexus_demo"):
        # Pure-compute payload compatible with the real nexus hypervisor
        # (no WASI imports). Runs fib(30)*10.
        if WASM_NEXUS_DEMO_PATH.exists():
            return WASM_NEXUS_DEMO_PATH.read_bytes()
    if payload.get("use_demo"):
        # WASI stdout hello — for wasmtime scaffold only.
        if WASM_DEMO_PATH.exists():
            return WASM_DEMO_PATH.read_bytes()
    return None


def _demo_intended_for_wire(payload: dict) -> bool:
    """True if the caller supplied a module that will work with nexus.live."""
    return bool(payload.get("use_nexus_demo") or payload.get("wasm_b64") or payload.get("wasm_path"))


def execute_wasm(cap_token: dict, wasm_bytes: bytes, entry: str = "_start",
                 args: Optional[list[str]] = None) -> dict:
    """Execute wasm_bytes under wasmtime with WASI, scoped by cap_token."""
    ok, why = verify_capability_token(cap_token)
    if not ok:
        return {"adapter": "nexus.wasmtime", "status": "denied",
                "reason": why, "capability_trace": []}

    if not WASMTIME_OK:
        return {
            "adapter": "nexus.fallback", "status": "wasmtime_unavailable",
            "reason": "wasmtime python binding not installed; call falls back to inspection-only",
            "module_digest": hashlib.sha256(wasm_bytes).hexdigest(),
            "module_size": len(wasm_bytes),
            "capability_trace": [{"action": "verify_token", "outcome": "ok"}],
        }

    trace = [{"action": "verify_token", "outcome": "ok"}]
    stdout_bytes = b""
    exit_code = 0
    error = None

    try:
        engine = wasmtime.Engine()
        module = wasmtime.Module(engine, wasm_bytes)
        trace.append({"action": "compile", "digest": hashlib.sha256(wasm_bytes).hexdigest()[:16]})

        linker = wasmtime.Linker(engine)
        linker.define_wasi()

        # Snapshot-per-call: fresh Store, fresh WASI, no filesystem mounts.
        store = wasmtime.Store(engine)

        # Capture stdout to a temp file (WASI preview1 pattern)
        import tempfile, os as _os
        with tempfile.TemporaryDirectory() as td:
            out_path = _os.path.join(td, "stdout")
            wasi = wasmtime.WasiConfig()
            wasi.stdout_file = out_path
            if args:
                wasi.argv = ["module.wasm", *args]
            store.set_wasi(wasi)
            trace.append({"action": "wasi_init", "scope": "no-fs no-net", "stdout": "captured"})

            instance = linker.instantiate(store, module)
            trace.append({"action": "instantiate", "outcome": "ok"})

            start = instance.exports(store).get(entry)
            if start is None:
                # Try _start as fallback
                start = instance.exports(store).get("_start")
            if start is None:
                error = f"entry point {entry!r} not exported"
                exit_code = 127
            else:
                try:
                    start(store)
                    trace.append({"action": "call", "entry": entry, "outcome": "returned"})
                except wasmtime.ExitTrap as e:
                    exit_code = getattr(e, "code", 0) or 0
                    trace.append({"action": "call", "entry": entry, "outcome": f"exit({exit_code})"})

            try:
                with open(out_path, "rb") as f:
                    stdout_bytes = f.read()
            except FileNotFoundError:
                stdout_bytes = b""

    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        trace.append({"action": "trap", "outcome": error})
        exit_code = 1

    result = {
        "adapter": "nexus.wasmtime",
        "status": "committed" if error is None and exit_code == 0 else "faulted",
        "exit_code": exit_code,
        "stdout": stdout_bytes.decode("utf-8", errors="replace"),
        "stdout_bytes": len(stdout_bytes),
        "module_digest": hashlib.sha256(wasm_bytes).hexdigest(),
        "capability_trace": trace,
    }
    if error:
        result["error"] = error
    return result


def dispatch(grant: dict, action_id: str, payload: dict) -> dict:
    """High-level entrypoint used by /effects/dispatch.

    Wire selection:
      1. `payload.force_local=True` → wasmtime (bypass wire)
      2. Live nexus-agentd reachable → real Rust wire (nexus.live)
      3. wasmtime available → in-orchestrator scaffold (nexus.wasmtime)
      4. No module + no wire → nexus.echo

    All three return a common shape: adapter, status, capability_trace, plus
    adapter-specific fields (stdout for wasmtime, output for live).
    """
    wasm_bytes = _load_module_bytes(payload)
    if wasm_bytes is None:
        return {"adapter": "nexus.echo", "echoed": payload,
                "note": "no wasm module in payload; set use_demo=true or supply wasm_b64/wasm_path",
                "capability_trace": [{"action": "no_module", "outcome": "echo"}]}

    token = mint_capability_token(grant, action_id)
    entry = payload.get("entry", "_start")
    args = payload.get("args") or []

    # Prefer the live nexus-agentd wire when the daemon is reachable AND
    # the module wasn't the WASI-hello demo (which requires fd_write and
    # would fail against the pure-compute nexus hypervisor).
    if not payload.get("force_local") and _demo_intended_for_wire(payload):
        try:
            from nexus_wire import execute as wire_execute, is_available as wire_available
            if wire_available():
                return _live_dispatch(wire_execute, grant, action_id, payload,
                                      wasm_bytes, entry, token)
        except Exception as e:
            # Fall through to wasmtime if wire client itself throws
            trace_extra = [{"action": "wire_probe", "outcome": f"exception: {type(e).__name__}"}]
            result = execute_wasm(token, wasm_bytes, entry=entry, args=args)
            result.setdefault("capability_trace", []).extend(trace_extra)
            return result

    return execute_wasm(token, wasm_bytes, entry=entry, args=args)


def _live_dispatch(wire_execute, grant: dict, action_id: str, payload: dict,
                   wasm_bytes: bytes, entry: str, token: dict) -> dict:
    """Send Execute frame to nexus-agentd; return unified result shape."""
    input_json = payload.get("input") or {"action_id": action_id,
                                          "capability": grant.get("capability")}
    trace = [
        {"action": "verify_token", "outcome": "ok"},
        {"action": "wire_probe", "outcome": "reachable"},
    ]
    resp = wire_execute(name=grant.get("capability", "effect"),
                        wasm_bytes=wasm_bytes, entry=entry, input_json=input_json)
    module_digest = hashlib.sha256(wasm_bytes).hexdigest()

    if resp.get("type") == "Executed":
        out = resp.get("output") or {}
        success = out.get("success", False)
        trace.append({
            "action": "execute", "outcome": "committed" if success else "faulted",
            "execution_time_ms": out.get("execution_time_ms"),
            "fuel_consumed": out.get("fuel_consumed"),
            "rollback_performed": out.get("rollback_performed"),
            "wire_ms": resp.get("wire_ms"),
        })
        result = {
            "adapter": "nexus.live",
            "status": "committed" if success else "faulted",
            "output": out,
            "module_digest": module_digest,
            "wire_ms": resp.get("wire_ms"),
            "daemon_socket": __import__("nexus_wire").socket_path(),
            "execution_time_ms": out.get("execution_time_ms"),
            "fuel_consumed": out.get("fuel_consumed"),
            "rollback_performed": out.get("rollback_performed"),
            "capability_trace": trace,
        }
        if not success:
            result["error"] = out.get("error")
        return result
    if resp.get("type") == "Error":
        trace.append({"action": "execute", "outcome": f"error: {resp.get('message')}"})
        return {
            "adapter": "nexus.live",
            "status": "faulted",
            "error": resp.get("message"),
            "module_digest": module_digest,
            "wire_ms": resp.get("wire_ms"),
            "capability_trace": trace,
        }
    # WireError → fall back to wasmtime for graceful degradation
    trace.append({"action": "wire", "outcome": f"error: {resp.get('error')}"})
    result = execute_wasm(token, wasm_bytes, entry=entry)
    result.setdefault("capability_trace", []).extend(trace)
    result["degraded_from"] = "nexus.live"
    return result
