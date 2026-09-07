# AEON Context Kernel Coding Instructions

Read and follow [`../AGENTS.md`](../AGENTS.md) before proposing or editing code.

The prior v0.2.1 S0 review failed on S0-001 (High: caller-influenced provenance lifecycle time) and S0-002 (Low: caller metadata affecting compaction residency). The v0.2.2 remediation was superseded by S0-003, where a runner clock rejected valid fixture attestations. The current boundary is the **v0.2.3 S0 correction candidate**, pending independent focused re-audit; do not implement S1, provider integrations, real effects, AEON-IQ integration, or real-model efficacy work.

Preserve verifier-issued authority, trusted runtime-clock lifecycle checks, runner-owned runtime starts after fixture issuance, exact content and opaque-UID bindings, fail-closed joins, metadata-free S0 compaction protection, pre-effect enforcement, canonical replay, and simulator-only required paths. Never infer trust, approval, test success, or provenance from prose, metadata, or submitted timestamps.

All changes use a focused pull request. Do not push directly to `main`. Address actionable review comments, keep every review conversation resolved honestly, and use repository-native squash auto-merge only after project CI succeeds on the current head. CodeRabbit and Cursor Bugbot feedback must be addressed when actionable, but their availability is not itself a required status context.
