# Kernel Change-Impact Matrix

Use this matrix before implementation and again before declaring a change complete.

| Change | Inspect and usually edit | Prove with tests | Version/hash impact to assess | Common mistake |
|---|---|---|---|---|
| Add or rename a semantic, trust class, priority, load mode, status, or reason | `models.py`, admission/assembly/receipt consumers, serializers | Model validation, every mapping branch, round-trip receipts | Stored schemas, admission decisions, assembly and decision hashes | Updating the enum without exhaustively updating mappings. |
| Change authentication or authority rules | `admission.py`, `assembly.py` | Failed provenance, external authority claim, workspace policy off/on | Admission/assembly hashes and benchmark traces | Inferring authority from prose or making tool output authoritative. |
| Change region placement or rendering | `assembly.py` | Exact region, stable ordering, unloaded activation, external isolation | Assembly hashes and every trace containing assembly events | Treating output formatting as incidental when it is hashed. |
| Change compaction selection or summary | `compaction.py` | Deterministic repeat, protected residency, unsatisfied budget, reason records | Segment/assembly hashes, compaction events, scenario scaffold outcome | Evicting protected material to force the budget to pass. |
| Add predicate context fact | `ledger.py`, predicate implementation, scenario contexts | Frozen-model validation, allowed/violating predicate cases | Predicate behavior; set hash only if descriptor/config changes | Reading the fact from action prose instead of trusted context. |
| Add or modify a predicate | Predicate module and exports; benchmark registration if built in | Not-applicable, valid, invalid, all modes, no effect on enforce | Predicate version and predicate-set hash; benchmark reference results | Omitting behavior-affecting configuration from `configuration()`. |
| Change mode mapping or ledger ordering | `ledger.py` | Registration-order independence, unique IDs, all modes | Predicate-set and decision-trace hashes | Letting input registration order control evaluation. |
| Change interception | `interception.py` | Full-ledger evaluation, block-before-effect, warn execution, effect count | Action events and decision traces | Applying an effect before checking whether any predicate blocks. |
| Add action type | `ActionType`, simulator handler/dispatch/state, predicates, scenarios | Supported dispatch, state mutation, allowed and blocked paths | Stored action schema and traces; adapter version if behavior changes | Adding enum value without a simulator handler or policy coverage. |
| Change simulator state/effect record | `adapters/simulated.py`, receipts if serialized | Sequential effect log, expected state, unsupported-action rejection | Trace and receipt payloads; simulator ID/version | Accidentally using host filesystem, network, or Git. |
| Add receipt field | `receipts.py`, runner construction, read/write tests | Required/optional behavior, exactly one driver, canonical round trip | Receipt schema and stored artifacts | Adding nondeterministic or secret-bearing data to evidence. |
| Change event payload or order | Recorder call sites, `receipts.py`, runner | Chain integrity, sequence, footer, logical replay | Trace and decision hashes; harness/adapter/scenario version | Reordering for convenience without a version or migration decision. |
| Change decision projection | `receipts.py` | Timestamp tolerance plus logically different replay rejection | Decision-trace compatibility | Excluding a meaningful field merely to suppress mismatch. |
| Change replay reconstruction | `replay.py`, runner `run_spec`/reproduce path | Structural failure, successful re-execution, logical mismatch | Harness/scenario/adapter versions | Re-executing before validating the stored chain. |
| Change CLI command or output | `cli.py` and invoked workflow | Typer invocation, exit code, artifact paths | Operator compatibility, not usually a logical hash | Printing success while returning zero on failed replay. |

## Version decision

Apply a version bump when a stable public identity now represents different logical behavior. Prefer the narrowest applicable version:

| Changed behavior | Candidate identity |
|---|---|
| Predicate evaluation or public configuration | `predicate_version` |
| Scenario fixture, schedule, invariant, or ground truth | `scenario_version` |
| Adapter composition or arm semantics | adapter `version` |
| Runner lifecycle or trace contract | `HARNESS_VERSION` |
| Simulator action semantics | `SIMULATOR_ID` version |
| Package API or release behavior | project version |

Do not bump versions mechanically. Explain which replay or comparison boundary the bump communicates.

## Focused-test selection

Run the smallest test node that proves the change, then the complete file, then shared gates. Examples:

```bash
uv run pytest tests/test_models_admission.py -q
uv run pytest tests/test_assembly_compaction.py -q
uv run pytest tests/test_ledger_interface.py tests/test_predicates_interception.py -q
uv run pytest tests/test_receipts_replay.py -q
uv run pytest tests/test_benchmark.py -q
```

Use `ckernel bench smoke` after cross-cutting changes. Use pilot when scenario or adapter coverage changed. Reserve full for reference evidence or release validation.
