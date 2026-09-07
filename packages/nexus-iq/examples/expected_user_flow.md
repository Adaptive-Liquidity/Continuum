# Expected Memory-Mode User Flow: run-live-example.sh

This document narrates the explicit memory-mode flow in
`./run-live-example.sh`. Core mode does not run the memory write, recall, or
timeline legs; use `./verify-live-stack.sh` to verify Nexus execution and a
real Proof Capsule without making a memory claim.

---

## Prerequisites

- `.env` contains `NEXUS_AEON_ENABLED=true`
- a real provider is configured
- `./start.sh` has been run and `./doctor.sh` passes the memory checks
- `OPENAI_API_KEY` is set in `.env` (required for steps a and b)
- `data/modules/sample_tool.wasm` exists (created by `./install.sh`)

Steps (c) and (d) — WASM execution and proof capture — do not require a
provider key and will run even if steps (a) and (b) fail.

---

## Step (a): Write a memory

```
▸ (a) Write a memory → POST /api/v1/agents/nexusiq/memories
```

The script POSTs an episodic memory to AEON-IQ's management API:

```json
{
  "content": "NexusIQ live validation marker <timestamp>: the self-host kit executed a WASM module and recorded a proof capsule.",
  "memory_type": "episodic",
  "importance": 0.7
}
```

**Expected output (success):**

```
✓ memory written (HTTP 201); marker=live-20260622T120000Z-12345
  {"id":"...","agent_id":"nexusiq","memory_type":"episodic",...}
```

**If the key is missing or invalid:**

```
✗ memory write FAILED (HTTP 401)
⚠  This is an embedding/provider failure — set a valid OPENAI_API_KEY ...
```

The script continues to step (c) regardless.

---

## Step (b): Recall

```
▸ (b) Recall → POST /api/v1/memories/search
```

Runs a semantic similarity search against stored memories:

```json
{
  "agent_id": "nexusiq",
  "query": "What did NexusIQ execute and prove?",
  "limit": 3
}
```

**Expected output (success):**

```
✓ recall returned HTTP 200
  • NexusIQ live validation marker ...: the self-host kit executed a WASM module ...
```

If no memories match the retrieval threshold (default 0.80) yet — for example
on a first run before the embedding index is populated — you may see:

```
✓ recall returned HTTP 200
  (no hits yet)
```

This is normal. The memory written in step (a) may not be immediately
retrievable if the embedding job is still in flight.

---

## Step (c): Nexus execution and proof

```
▸ (c) Nexus execution + proof → MCP tools/call nexus_execute_proof
```

The script sends three JSON-RPC 2.0 messages to `connect-mcp.sh` over stdin:

1. `initialize` — MCP handshake
2. `notifications/initialized` — client ready notification
3. `tools/call nexus_execute_proof` — execute `sample_tool.wasm`

`connect-mcp.sh` starts `nexus-mcp` with `--no-deps` after verifying the already-running `nexus-agentd`
and pipes the messages through. `nexus-mcp` forwards the execution request to
`nexus-agentd` over the Unix socket.

**Expected output (success):**

```
✓ nexus_execute_proof invoked over connect-mcp.sh (module=sample_tool.wasm)
```

The raw MCP response contains a `proof_capsule` field in the tool result. The
module (`sample_tool.wasm`) is a minimal no-op WASM module that exports
`_start` — it returns immediately with a successful exit. The Nexus hypervisor
wraps the execution in a capability-gated WASI sandbox, records the result,
and returns a Proof Capsule.

**If the stack is not running:**

```
✗ no response from MCP server (is the stack up? ./start.sh)
```

---

## Step (d): Extract proof capsule

```
▸ (d) Extract proof_capsule → data/proofs/<capsule_id>.json
```

The script parses the MCP response to extract the `proof_capsule` object and
writes it to disk.

**Expected output (success):**

```
✓ proof captured
ProofCapsule written: data/proofs/cap-<uuid>.json
```

The file at `data/proofs/cap-<uuid>.json` contains the full Proof Capsule:
module path, execution result, capability grants, timestamp, and the
cryptographic binding. Example structure:

```json
{
  "capsule_id": "cap-...",
  "module": "/modules/sample_tool.wasm",
  "result": "success",
  "timestamp": "2026-06-22T12:00:00Z",
  "capability_grants": [],
  "hmac_binding": "..."
}
```

The exact fields depend on the Nexus version. To inspect:

```bash
cat data/proofs/cap-<uuid>.json
ls -la data/proofs/
```

---

## Step (e): Timeline delivery

```
▸ (e) Timeline → POST events to /api/v1/agents/nexusiq/timeline
```

POSTs an execution event to AEON-IQ's timeline endpoint. If the proof capsule
contained timeline events from step (c), those are included in the body.
Otherwise a synthetic event describing the execution is posted.

**Expected output (success):**

```
✓ timeline event recorded (HTTP 201)
Timeline event status: delivered
```

**If AEON is unreachable:**

```
✗ AEON unreachable — timeline event not delivered
Timeline event status: unavailable
```

Timeline delivery is fail-open — a failure here does not block the rest of
the flow.

---

## Step (f): Where to inspect

```
▸ (f) Where to inspect
```

Prints the commands to inspect the results:

```
Proof capsules (host):   /home/you/nexusiq/data/proofs/
  Latest:                /home/you/nexusiq/data/proofs/cap-<uuid>.json
List proofs:             ls -la data/proofs/
Stats:                   curl -fsS -H "X-Management-Key: $MANAGEMENT_API_KEY" http://127.0.0.1:8080/api/v1/stats
Search memories:         curl -fsS -X POST http://127.0.0.1:8080/api/v1/memories/search ...
Query timeline at time:  curl -fsS -H "X-Management-Key: $MANAGEMENT_API_KEY" "http://127.0.0.1:8080/api/v1/agents/nexusiq/timeline/at?timestamp=..."
```

---

## Final verdict

**All steps passed:**

```
✓ run-live-example: end-to-end flow completed.
```

**One or more steps failed:**

```
✗ run-live-example: one or more legs FAILED (see ✗ above). This is a real failure, not a mock.
```

Exit code is 0 on full success, 1 if any step failed. Each failure prints
what went wrong with enough context to diagnose — check the `✗` lines above
the verdict.
