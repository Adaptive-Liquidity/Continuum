# Predicate Authoring Contract

Use this reference when adding or changing an `InvariantPredicate` or a trusted fact it consumes.

## Interface contract

Implement a deterministic class with:

```python
class ExamplePredicate(InvariantPredicate):
    predicate_id = "stable_snake_case_id"
    predicate_version = "1.0.0"

    def evaluate(self, action: Action, context: PredicateContext) -> PredicateResult:
        ...

    def configuration(self) -> Mapping[str, Any]:
        ...
```

Keep evaluation side-effect-free. Read only the proposed `Action`, trusted `PredicateContext`, and immutable public configuration. Do not read files, environment secrets, clocks, network state, global random state, or mutable singleton state.

## Applicability and results

Return `applicable=False`, `satisfied=True`, and a stable `not_applicable` reason for unrelated action types. For applicable actions, distinguish malformed input from policy denial.

| Path | `applicable` | `satisfied` | Reason-code pattern |
|---|---:|---:|---|
| Unrelated action | false | true | `not_applicable` |
| Missing or malformed required parameter | true | false | `<subject>_missing` or `<subject>_invalid` |
| Valid and allowed | true | true | `<subject>_allowed`, `_verified`, `_valid`, or `_within_*` |
| Valid but forbidden | true | false | `<subject>_forbidden`, `_not_allowlisted`, `_exceeded`, or `_outside_*` |
| Policy not configured and predicate is optional | false | true | `<subject>_not_configured` |

Use stable machine-readable reason codes and concise human-readable explanations. Do not embed secrets in explanations. Avoid including unordered structures unless sorted.

## Trusted-fact design

Add a `PredicateContext` field only for a fact supplied by trusted runtime code. Prefer immutable types such as `frozenset`, primitive values, or frozen nested models. Give safe defaults that do not accidentally grant authority.

Examples of trusted facts include allowlisted hosts, runtime approval tokens, successful test artifact IDs, approved paths, configured schema, protected branches, resource budget, and current resource use.

Never derive the following from prose:

- approval validity;
- test success;
- trust class or authentication;
- secret status;
- whether an action is protected;
- policy allowlists.

## Public configuration and hashing

Override `configuration()` when constructor options change evaluation behavior. Return a deterministic mapping containing non-secret public configuration. The ledger hashes the predicate ID, version, mode, and configuration.

Do not include volatile values such as timestamps, object identities, temporary paths, or unordered raw sets. Canonicalize or sort where necessary.

Bump `predicate_version` when the same inputs may now produce a different semantic result, reason code, applicability classification, or configuration interpretation. A documentation-only change does not require a bump.

## Built-in registration

When the predicate belongs in every enforcing benchmark arm:

1. Export the class through the predicate package.
2. Add its class to `BUILTIN_PREDICATES`.
3. Keep the collection deterministic.
4. Confirm the enforcing adapter instantiates it in enforce mode.
5. Expect the predicate-set hash to change.
6. Assess whether reference benchmark artifacts require intentional regeneration.

Do not add a built-in predicate merely for a single scenario if its behavior is not generally applicable. Consider an adapter-specific registration or a narrower experimental arm.

## Required test matrix

Create a minimal violating case factory and an allowed case factory. For each applicable violation, test all modes through `SafeActionInterceptor`:

| Mode | Evaluation decision | Final outcome | Effect executed | Simulator log change |
|---|---|---|---:|---:|
| Observe | pass with `violation_detected=true` | allowed | true | one effect |
| Warn | warn | warned | true | one effect |
| Enforce | block | blocked | false | no effect |

Also test:

- the valid case passes in enforce mode and executes one simulated effect;
- an unrelated action is not applicable and does not create a false violation;
- malformed applicable input returns a deterministic result rather than raising unexpectedly;
- `configuration()` changes alter the predicate-set hash;
- registration input order does not alter evaluation order or predicate-set hash;
- duplicate predicate IDs are rejected;
- explanations and receipts do not expose configured secret values.

## Action-type additions

If no existing `ActionType` expresses the effect, add one through the kernel-engineering workflow. Define the parameter schema informally in code and tests, add an in-memory simulator handler, and verify state mutation. Then add predicate applicability and scenario fixtures.

Do not overload an unrelated action type to avoid updating dispatch. Distinct effect semantics deserve distinct stable action identities.

## Example review checklist

Before completion, answer all questions affirmatively:

1. Is authority based only on runtime provenance and controlled facts?
2. Is evaluation deterministic and effect-free?
3. Are not-applicable, malformed, allowed, and violating paths explicit?
4. Are the ID, version, and reason codes stable?
5. Does public behavior-affecting configuration participate in hashing?
6. Does enforce mode prove zero effect?
7. Are positive and negative cases present in both unit and scenario coverage where appropriate?
8. Are benchmark/reference hash changes explained rather than normalized away?
