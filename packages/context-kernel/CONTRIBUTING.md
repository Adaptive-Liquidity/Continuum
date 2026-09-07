# Contributing to AEON Context Kernel

Thank you for helping improve the project. Contributions must preserve the project’s trust, pre-effect enforcement, and deterministic replay boundaries.

## Current development gate

The repository is currently frozen at **S0 (`0.2.x`)** while an independent security review is pending. Until that review passes, contributions should be limited to S0 security fixes, tests, documentation corrections, CI/reproducibility improvements, and audit support. Do not begin S1, provider integration, AEON-IQ integration, or real-effect adapters on `main`.

## Development setup

```bash
git clone https://github.com/Adaptive-Liquidity/aeon-context-kernel.git
cd aeon-context-kernel
uv sync --extra dev --locked
uv run pytest
```

Create a focused branch, keep changes narrow, and include tests for observable behavior. Never infer authority, approval, test success, or provenance from prose.

## Required local checks

Run the following before opening a pull request:

```bash
uv run ruff format --check src tests examples
uv run ruff check .
uv run mypy src
uv run pytest
uv run ckernel bench smoke --results-root .ci-results
```

Generated benchmark artifacts belong in local result directories or a versioned release-evidence package, not in ordinary source commits.

## Pull-request expectations

A pull request must explain the intended behavior, trust/security impact, files changed, negative and positive tests, version or canonical-hash impact, and any gate not run. Changes affecting receipts, traces, scenarios, metrics, or reports must state how reproducibility was checked.

Pull requests may be queued for repository-native squash auto-merge. They merge only after the required project CI, CodeRabbit, and Cursor Bugbot checks succeed and all actionable review conversations are fixed and resolved. New commits dismiss stale results and restart the gates. Contributors must not resolve a thread merely to make the merge button available; the fix or reasoned disposition must be visible in the pull request.

| Change type | Minimum evidence |
|---|---|
| Provenance, schema, or admission | Adversarial authority-claim tests and valid-admission tests. |
| Assembly or compaction | Exact-binding, region-placement, protected-residency, and unsatisfied-budget tests. |
| Interception or predicates | Observe/warn/enforce tests and proof that enforce blocks before simulator mutation. |
| Receipt, trace, or replay | Structural tamper and logical-divergence tests. |
| Scenario, adapter, metric, or report | Focused benchmark tests and a fresh smoke run. |

## Security reports

Do not disclose vulnerabilities in a public issue. Follow [`SECURITY.md`](SECURITY.md).

## Claims and documentation

Describe simulator outputs as **deterministic conformance/regression evidence**, never real-model efficacy. Context-delivery receipts show what the runtime delivered and decided; they do not prove model understanding or compliance.

## License

By contributing, you agree that your contribution is licensed under the repository’s [MIT License](LICENSE).
