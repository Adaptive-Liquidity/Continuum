---
name: aeon-context-survival-bench
description: Authoring and extension workflow for the AEON Context Survival Bench. Use when adding or changing invariant predicates, action types, scenario templates, benchmark adapters, scoring, metrics, or reports while preserving deterministic ground truth, safe-versus-violating action pairs, enforcement-mode coverage, and the fixed staged benchmark lifecycle.
---

# AEON Context Survival Bench Authoring

## Purpose

Extend the benchmark as a deterministic regression oracle rather than a model-quality claim. Keep scenario ground truth explicit, all required effects in memory, and all required scoring free of provider calls or LLM judges.

## Official repository and merge gate

Use `https://github.com/Adaptive-Liquidity/aeon-context-kernel` as canonical. The v0.2.1 external S0 review returned a Fail summary with S0-001 (High: caller-influenced provenance lifecycle time) and S0-002 (Low: caller metadata could affect compaction residency). The current v0.2.2 remediation candidate remains blocked pending independent focused re-audit. Deterministic simulator stages remain conformance/regression evidence; do not start S1, provider, real-effect, AEON-IQ, or real-model study implementation before that gate passes.

Make changes on a focused branch and pull request, never directly on protected `main`. Repository-native squash auto-merge may complete only after stable project CI passes and all actionable review conversations are fixed or given a documented disposition and resolved. CodeRabbit and Cursor Bugbot feedback must be handled when actionable, but their availability is not a required status context.

## Boundary with blinded real-model studies

Do not add provider calls, real effects, model-selected scenario outcomes, or LLM-judge scoring to the required smoke, pilot, full, or concept-evidence path. If a request asks whether typed context changes real-model behavior, create a separately versioned, explicitly opt-in study layer that consumes the same hardened scenario fixtures but never changes their deterministic ground truth. Keep treatment assignment hidden from the model, score model proposals from independent task state, separate proposal behavior from enforce-mode execution outcomes, record provider/version/decoding provenance, and label the result as bounded experimental evidence rather than a benchmark regression result. Read the companion kernel-engineering contract for trusted provenance and the reproducibility-audit claim boundary before authoring that layer.

## Select the authoring route

| Request | Route | Read first |
|---|---|---|
| Add or modify an invariant predicate | Predicate route | [`references/predicate-authoring.md`](references/predicate-authoring.md) |
| Add an action type used by predicates or scenarios | Action-type route | Predicate reference, then the companion kernel-engineering skill |
| Add or modify a scenario | Scenario route | [`references/scenario-authoring.md`](references/scenario-authoring.md) |
| Add or modify an adapter or arm | Adapter route | Scenario reference and existing `survival_bench/adapters.py` |
| Change scoring, metrics, survival points, or reports | Measurement route | Benchmark methodology, `metrics.py`, `reporting.py`, and tests |

Before editing, run the passive surface inspector:

```bash
python3 /home/ubuntu/skills/aeon-context-survival-bench/scripts/inspect_extension_surface.py \
  --project-root /path/to/aeon-context-kernel
```

Use its JSON inventory to avoid duplicate predicate IDs, scenario IDs, action types, or adapters. The script parses source only; it does not import or execute the project.

## Shared authoring workflow

### 1. Define the invariant and ground truth

Write one principal invariant as a deterministic statement over a proposed action and trusted runtime facts. Define what counts as a safe action and what counts as a violation before writing implementation code.

Reject requirements that can only be judged semantically by an LLM unless the user explicitly wants a separate, non-normative experiment. The required benchmark path must remain deterministic and locally scoreable.

### 2. Identify the controlled runtime fact

Place approvals, allowed paths, remotes, branches, hosts, schemas, test artifacts, secrets, forbidden action types, and resource budgets in `PredicateContext` or an equally controlled runtime model. Never count textual claims inside tool output or external material as evidence.

### 3. Preserve versioned identity

Use stable snake-case IDs and semantic versions. A behavior change to an existing predicate, scenario, adapter, harness, or simulator requires an explicit version assessment. Do not silently reuse an old identity for new logical behavior.

### 4. Author paired behavior

Create both an allowed case and an applicable violating case. For scenarios, label `expected_violation` in the action specification before runtime selection. For predicates, use stable reason codes for not-applicable, allowed, malformed, and violating inputs.

### 5. Add focused tests before matrix runs

Test the narrow extension first. Assert logical outcomes and simulator state, not just printed output. Prove deterministic repetition with the same inputs. Then run the relevant integration matrix.

### 6. Execute stages in order

Install the committed environment with `uv sync --extra dev --locked`, then run stages sequentially into an explicit results root:

```bash
uv run ckernel bench smoke --results-root results
uv run ckernel bench pilot --results-root results
uv run ckernel bench full --results-root results
```

Smoke must pass before pilot. Pilot must pass before full. Do not run full merely because it exists; use it for a reference result, release evidence, or a user-requested complete matrix.

Use the companion `aeon-context-reproducibility-audit` skill to reconcile artifacts and replay traces after any stage.

## Predicate route

Copy [`templates/predicate.py`](templates/predicate.py) and [`templates/predicate_tests.py`](templates/predicate_tests.py) as starting points, then adapt names, applicability, context facts, reason codes, and tests.

Implement `evaluate()` without effects. Return `applicable=False` for unrelated actions. Validate malformed applicable inputs explicitly rather than allowing an exception to define policy. Expose public options through `configuration()` so the predicate-set hash reflects behavior.

If the predicate should be built in, export it, add it to `BUILTIN_PREDICATES`, and verify that the enforcing benchmark arm registers it. Test:

1. Unrelated action is not applicable.
2. Valid applicable action is satisfied.
3. Invalid applicable action is unsatisfied.
4. Observe records a violation and executes the simulator effect.
5. Warn records a warning and executes the simulator effect.
6. Enforce blocks and leaves the simulator effect log unchanged.
7. Predicate-set hash is stable across registration input order.

## Action-type route

Add the enum member and a simulator handler and state update before using the action in scenarios. Define its parameter contract and malformed-input behavior. Decide which predicates apply. Confirm that unsupported actions remain explicit errors and that no required path reaches the host filesystem, real Git, network, deployment, or secrets.

Use the companion `aeon-context-kernel-engineering` skill for changes to `ActionType`, interception, or the simulator.

## Scenario route

Copy [`templates/scenario_entry.py`](templates/scenario_entry.py), then follow the complete contract in [`references/scenario-authoring.md`](references/scenario-authoring.md).

Keep the principal invariant, adversarial material, safe action, violating action, predicate context, schedule, budget, and difficulty explicit. Make the adversarial material realistic but label it with controlled trust and semantics. Ensure its prose cannot promote itself.

Add the scenario to the versioned catalog and update exact-catalog tests only when the new scenario is intentional. Test all adapters for at least one seed and deterministic materialization for the same seed. Verify that typed arms keep external-untrusted instructions out of authoritative regions.

## Adapter route

Implement the same thin lifecycle used by existing arms: admit, assemble, compact, make an interceptor, intercept an action, and report. Keep scenario fixtures and scoring identical across arms so the comparison changes one runtime treatment rather than the ground truth.

Name the arm according to what it actually does. Do not describe a harness-forced compactor as provider-native behavior. Give the adapter a stable version and expose it through `adapter_names()` and CLI validation.

## Measurement route

Keep `expected_violation` as scenario ground truth. Count an observed violation only when an expected-violation effect reaches the simulator. Count a false block when a safe action is blocked. Keep these metrics independent.

Preserve right-censoring and the documented survival-time semantics. Keep modeled latency labeled as modeled, token counts labeled as estimates, and cost null when no paid provider runs. Generate reports from saved metrics rather than recomputing hidden judgments from traces.

When adding a metric or report field, update the Pydantic model, CSV and JSON emitters, report regeneration, integration tests, and artifact audit expectations together.

## Completion report

Report the new or changed invariant, stable IDs and versions, paired safe and violating behavior, focused tests, stage results, replay or audit results, and any intentional reference-result changes. State clearly that deterministic simulator outcomes are regression evidence for this implementation, not cross-provider production evidence.
