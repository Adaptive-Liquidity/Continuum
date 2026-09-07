# Security Policy

## Project status

AEON Context Kernel `0.2.x` is a **research and reference implementation**. The current frozen milestone is **S0: verifier-issued provenance and collision-safe segment identity**. It is not approved for production use, live provider integration, or real filesystem, network, Git, approval, or other external effects.

| Version | Status | Security scope |
|---|---|---|
| `0.2.x` | Supported for audit and remediation | S0 provenance, admission, exact content binding, opaque segment identity, one-to-one joins, receipts, and deterministic simulator regression behavior. |
| `<0.2.0` | Unsupported | Earlier caller-trust and identity contracts are superseded. |

## Reporting a vulnerability

Please **do not open a public issue** for a suspected vulnerability. Use the repository’s private GitHub security-advisory reporting channel when available. If that channel is unavailable, contact the repository owner through GitHub and request a private disclosure channel before sending exploit details.

Include the affected version or commit, prerequisites, exact reproduction steps, observed and expected behavior, impact, and a minimal proof of concept or failing test. Remove real credentials, personal data, and third-party secrets from all reports.

## Priority S0 vulnerability classes

Reports are especially valuable if they demonstrate any of the following:

| Class | Example impact |
|---|---|
| Forged authority | Caller-controlled text is admitted as principal or trusted without valid verifier-issued provenance. |
| Content substitution | A valid provenance or admission decision can be reused after the bound content changes. |
| Identity collision or cross-binding | A decision or receipt for one segment can attach to another segment. |
| Lifecycle bypass | Expired, revoked, wrong-audience, wrong-policy, or replayed provenance is accepted. |
| Fail-open behavior | Missing, surplus, duplicated, or mismatched decisions are silently accepted. |
| Evidence confusion | Generated simulator evidence is presented as authenticated evidence or real-model efficacy. |

## Response and release gate

A confirmed Critical or High S0 finding blocks S1 planning and all provider or real-effect integration until the issue is fixed and independently retested. Security fixes must add a behavior-focused regression test and document any schema, version, canonical-hash, or evidence impact.

## Explicit non-claims

A passing test suite or deterministic replay does not establish production security, model understanding, semantic compliance, prompt-injection immunity, or real-tool safety. Those require separate architecture gates and bounded evaluations.
