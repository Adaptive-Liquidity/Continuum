# AEON-to-Nexus MemoryEvidence contract

The AEON plane persists execution-linked memory metadata and execution traces, while Nexus provides proofs for each execution. This is not a free-form text field flow; evidence is a reference artifact.

## MemoryEvidenceRef shape and constraints

`MemoryEvidenceRef` is the cross-system reference used for evidence linking:

- It does **not** include raw memory text.
- It links to a proof capsule (`capsule_id` or equivalent digest).
- It carries agent/session context under the AEON identifiers:
  - `NEXUS_AEON_AGENT_ID` (defaults to `nexusiq`)
  - `NEXUS_AEON_SESSION_ID`
- Agent/session labels must be identity-bound/HMAC-consistent when stored with `NEXUS_AEON_HMAC_KEY`.
- Memory retrieval failures must not leak raw memory content.

## Memory modes

The memory-result contract uses one of:

- `advisory` — available memory was returned as advisory context.
- `attested` — retrieval + evidence was successfully recorded.
- `degraded` — retrieval succeeded partially or with reduced quality.
- `absent` — no memory evidence was produced or available.

Use these modes as policy input for execution trust decisions.

## Linking rules

- A proof capsule’s `memory_evidence` entry must align to `NEXUS_AEON_AGENT_ID` / `NEXUS_AEON_SESSION_ID`.
- Cross-agent and cross-session memory evidence is denied.
- AEON timeline linkage uses `capsule_digest` and can carry:
  - `event_type` (e.g., `proof_capsule_emitted`)
  - `session_id`
  - `capsule_digest`
  - optional run/snapshot fields
- `run-live-example.sh` posts to `POST /api/v1/agents/<agent>/timeline` and includes the capsule digest.

## API scope

All AEON memory/timeline calls are management-key protected:

- endpoint: `AEON` REST API at `http://127.0.0.1:8080`
- header: `X-Management-Key: ${MANAGEMENT_API_KEY}`
- scripts rely on `./doctor.sh` to confirm auth and readiness.

## Storage and denial behavior

- No raw memory text is used in `MemoryEvidenceRef`.
- Unauthorized access is rejected before write/read acceptance.
- If `MANAGEMENT_API_KEY` is missing/invalid, memory/timeline routes fail but MCP execution can still be observed independently.
