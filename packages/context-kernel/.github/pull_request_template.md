## Summary

Describe the observable behavior changed and why the change is needed.

## Milestone and scope

- [ ] S0 security/remediation
- [ ] Documentation, CI, or reproducibility only
- [ ] S1 or later work explicitly approved after the prior gate
- [ ] No provider integration or real-effect execution added

## Trust and security impact

Explain whether this affects provenance, authority, segment identity, assembly, compaction, actions, approvals, receipts, traces, replay, or evidence authenticity.

## Determinism and compatibility

State any package-version, schema, canonical-hash, trace, receipt, scenario, adapter, metric, or report-contract impact.

## Tests and evidence

List focused negative and positive tests. Check the gates that passed:

- [ ] `uv run ruff format --check src tests examples`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`
- [ ] `uv run ckernel bench smoke --results-root .ci-results`

## Auto-merge readiness

- [ ] Required repository checks have completed successfully.
- [ ] Every actionable review conversation has been fixed or given a documented disposition and resolved.
- [ ] I understand that new commits restart the merge gates.

## Claim boundary

- [ ] Documentation does not describe simulator outputs as real-model efficacy evidence.
- [ ] Context-delivery receipts are not described as proof of model understanding or compliance.
- [ ] Any unrun gate or remaining uncertainty is stated explicitly.
