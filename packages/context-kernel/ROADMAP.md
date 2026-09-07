# AEON Context Kernel Roadmap

The roadmap is gate-driven rather than date-driven. A later stage does not begin until the preceding architecture, test, and independent-review requirements pass.

| Stage | Objective | Current status | Exit gate |
|---|---|---|---|
| **S0** | Verifier-issued provenance, exact content binding, opaque segment identity, and exact joins | **Implemented; independent review pending** | No unresolved Critical/High S0 finding; required adversarial checks independently reproduced. |
| **S1** | Structurally unambiguous model-facing envelope, trusted invariant registry, and compaction integrity | Blocked | Fresh adversarial tests, deterministic evidence, and independent S1 review. |
| **S2** | Immutable resolved-effect capabilities, single-use approvals, redacted/authenticated evidence, and race-safe resource control | Blocked | Simulator-first adversarial review covering rebinding, redirects, symlinks, Git refs, approval replay, and concurrent budgets. |
| **Offline model harness** | Compare full context, retrieval, compression, and hybrid context delivery using simulated tools | Blocked | Frozen architecture bundle, deterministic source/constraint oracles, and label-blinded scoring. |
| **Blinded model study** | Measure task usefulness, constraint retention, source fidelity, proposal safety, token cost, and latency | Blocked | Preregistered analysis and non-inferiority margin; held-out tasks/attacks; signed study manifest. |
| **Controlled integration** | Optional provider adapters and carefully scoped effects | Blocked | Prior gates pass; separate threat model and operational approval. |

## Immediate next action

Send the frozen S0 audit package to an independent reviewer using [`docs/third_party_s0_audit_handoff.md`](docs/third_party_s0_audit_handoff.md). Remediate and independently retest any finding before opening S1 implementation work.

## Non-goals of the current release

Version `0.2.1` is not a production agent runtime, provider integration, prompt-injection solution, compliance system, or proof that long-context model behavior improves. Its generated benchmark results are deterministic conformance/regression outputs only.
