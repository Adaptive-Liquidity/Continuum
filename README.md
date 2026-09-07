# Continuum

### The operating layer for persistent autonomous intelligence.
Continuum is Asentxia Systems’ working **Distributed Cognitive Architecture (DCA)**: an umbrella operating layer that connects identity, authority, memory, execution, runtime environments, governance, coordination, and evidence into one persistent system.

It is designed for autonomous intelligence that must operate beyond a single prompt, process, model, session, or provider.

> **Cognition proposes → Genesis authorizes → FLOKS provides the environment → Nexus executes → AEON remembers → Context Kernel verifies → Continuum coordinates everything.**

---

## What Continuum provides

Continuum separates the responsibilities required for dependable autonomous operation while connecting them through explicit interfaces, policy, state, and evidence.

- Persistent principal identity
- Signed authority and capability delegation
- Isolated agent computers and runtime environments
- Persistent memory and context retrieval
- Sandboxed tool execution
- Resource limits, snapshots, rollback, replay, and recovery
- Provenance-aware context admission
- Hash-chained execution traces
- Proof Capsules and operational evidence
- Multi-agent coordination
- Governance, mandates, assignments, and emergency suspension
- An operational dashboard for inspecting the entire system

---

## Core components

### Genesis — Identity and Authority

Genesis creates signed agent identities and manages the authority they receive.

It supports:

- Capability delegation
- Expiry and renewal
- Pause and suspension
- Revocation
- Authority-aware execution
- Persistent responsibility across runtime changes

Genesis answers:

> **Who is acting, and what are they authorized to do?**

---

### CONTINUUM — Agent Computers

Continuum provides isolated logical computers and runtime environments for autonomous principals.

It connects agents to dedicated or shared Runloop Devboxes with:

- Persistent computer identity
- Pairing and attachment
- MCP access
- Capability tokens
- Environment placement
- Recovery and takeover flows
- Runtime isolation

Continuum answers:

> **Where is the agent operating?**

---

### AEON-IQ — Persistent Memory

AEON-IQ is a multi-provider-compatible memory proxy for persistent autonomous systems.

It:

1. Retrieves relevant memories before model calls.
2. Sends the enriched request to the configured model.
3. Extracts new facts and durable state afterward.
4. Preserves memory across sessions and runtime changes.

AEON-IQ answers:

> **What does the principal remember, and why is that memory relevant?**

---

### Nexus — Secure Execution Kernel

Nexus provides bounded and recoverable execution for agent tools.

It runs tools inside WASM/WASI sandboxes with:

- Capability gates
- Resource limits
- Snapshots
- Rollback
- Replay
- Recovery
- Controlled side effects
- Execution records

Nexus answers:

> **What was executed, under which permissions, and within what limits?**

---

### Nexus-IQ — Self-Hosted Operating Kit

Nexus-IQ packages the core execution and evidence stack for local or self-hosted deployment.

It combines:

- Nexus
- MCP support
- Proof Capsules
- Optional AEON-IQ memory
- PostgreSQL
- Background workers
- Local operational services

Nexus-IQ answers:

> **How can the execution substrate be deployed and operated as a complete system?**

---

### Context Kernel — Context Safety and Evidence

The Context Kernel controls what information is admitted into an autonomous operation and records how that operation changes state.

It provides:

- Provenance verification
- Context admission control
- Deterministic invariants
- Hash-chained traces
- Evidence recording
- Replay support
- State-transition inspection

The Context Kernel answers:

> **What information was trusted, what changed, and can the operation be reconstructed?**

---

### Backend Orchestrator

The backend orchestrator connects the DCA responsibilities through explicit routes and effect boundaries.

It coordinates:

- FastAPI routes
- Sessions
- Authority
- Memory
- Runtime placements
- Effects
- Evidence
- Packages
- Recovery
- System state

The orchestrator answers:

> **How do the individual responsibilities operate together as one system?**

---

### Frontend Dashboard

The Continuum dashboard is the operational console for inspecting and controlling the system.

It provides visibility into:

- VERA identities
- Runtime placements
- Agent computers
- Memory
- Authority
- Effects
- Evidence
- Packages
- Sessions
- Regency governance

The dashboard answers:

> **What is happening across the system right now?**

---

### VERA — Persistent Principal Identity

A **VERA** is a Verifiable Execution and Recovery Assurance

Its identity and responsibility persist across changes to:

- Models
- Credentials
- Agents
- Processes
- Sessions
- Environments
- Computers
- Hosts

VERA answers:

> **Which persistent entity owns responsibility for this activity?**

---

### The Regency — Governance

The Regency is the governance layer for autonomous principals and organizations.

It provides structures for:

- Mandates
- Roles
- Assignments
- Organizational responsibility
- Policy boundaries
- Emergency suspension
- Governance review

The Regency answers:

> **Who may direct, constrain, suspend, or review autonomous activity?**

---

## Current architecture

```text
			 CONTINUUM
		 Umbrella DCA operating layer
			      │
 ┌──────────────┬─────────────┼──────────────┬──────────────┐
 │              │             │              │              │
Genesis      FLOKS-PC      AEON-IQ        Nexus       Context Kernel
Identity     Environment    Memory       Execution     Safety/Evidence
Authority
			      │
		    Backend Orchestrator
			      │
		     Frontend Dashboard
			      │
			 The Regency
			 Governance
```

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).
