# Capability Policy

Execution policy is MCP-first and AEON-scoped.

- MCP transport: `nexus-mcp` (STDIO)
- No REST/OpenAPI execution gateway
- AEON remains a management-key protected REST API (`127.0.0.1:8080`)

## Capability profiles

Two memory capabilities are required in the policy model:

- `ReadMemory`
- `WriteMemory`

These are tied to:

- `NEXUS_AEON_AGENT_ID`
- `NEXUS_AEON_SESSION_ID`

A token scoped to one agent/session must not authorize another.

## Attenuation

Use explicit attenuation before delegating:

- Start from a broad authority token.
- Derive constrained child tokens with `nexus_attenuate_token`.
- Child tokens must never expand scope; they only remove or narrow grants.
- `WriteMemory` should be granted only to trusted system components.
- `ReadMemory` should be granted only to principals that need retrieval context.

## Unauthorized access and denials

- AEON memory read/write/timeline routes require `X-Management-Key`.
- `scripts/doctor.sh` fails when `ALLOW_UNAUTH_MANAGEMENT` is set to a truthy value.
- Mismatched agent/session scope must be denied.
- Cross-agent memory reads/writes are denied by policy.

## Mapping to AEON identifiers

For every run, bind:

- `agent_id` (`NEXUS_AEON_AGENT_ID`)
- `session_id` (`NEXUS_AEON_SESSION_ID`)
- HMAC provenance (`NEXUS_AEON_HMAC_KEY`)

These labels are enforced at runtime boundary points (Nexus daemon ↔ AEON) and reflected in timeline linkage (`capsule_digest`) and proof evidence.

## Operational default posture

- Untrusted tooling: deny `WriteMemory`, allow narrow `ReadMemory` only when justified.
- Operator-only MCP visibility: management functions should remain restricted to local/admin workflows.
- Keep scope checks strict; unknown/missing claims fail closed.
