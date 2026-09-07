# Concept-Evidence Suite Design

The concept-evidence suite is a deterministic integration layer. It does not replace project unit tests or the benchmark; it composes focused claim tests, the existing project suite, a fresh smoke run, passive artifact validation, and complete replay into one claim-indexed evidence package.

## Test architecture

The runner copies `templates/test_aeon_concept_claims.py` into a temporary test file under the repository's `tests/` directory. This permits normal project imports and pytest fixtures while leaving the repository source and permanent tests unchanged. The file is removed in a `finally` path, including after a failing claim test.

The template must use only existing local APIs and in-memory simulators. It must not issue host filesystem writes through AEON action adapters, network requests, real Git operations, deployments, provider calls, or access to real secrets.

| Claim | Test name | Direct assertion |
|---|---|---|
| `C1` | `test_c1_provenance_controls_authority_and_region` | Principal constraint is authoritative; external instruction-like content is demoted to `reference`, non-authoritative, and placed in region D. |
| `C2` | `test_c2_admission_and_assembly_repeat_exactly` | Two identical runs produce equal admission decisions, rendered assemblies, and assembly hashes. |
| `C3` | `test_c3_compaction_keeps_protected_segments` | Required principal and active-invariant segments remain; budget failure is recorded rather than evicting protected material. |
| `C4` | `test_c4_enforce_blocks_before_simulated_effect` | An out-of-workspace write produces block, `effect_executed=False`, and zero simulator effects. |
| `C5` | `test_c5_runtime_evidence_beats_text_claims` | Textual approval/test claims fail while an allowed runtime token/artifact passes. |
| `C6` | `test_c6_trace_tamper_and_timestamp_semantics` | Event payload modification fails chain verification; timestamp-only event reconstruction preserves decision hash; a logical change differs. |
| `C8` | `test_c8_scoring_separates_violation_and_false_block` | Enforcing benchmark run records no observed violation for a violating challenge that is blocked and maintains a zero false-block count. |

`C7` is tested by the runner rather than a pytest function because it requires a fresh smoke matrix, output inspection, and full CLI replay.

## Runner behavior

`run_concept_validation.py` accepts a project root and output directory. It writes only under the explicit output directory and temporarily under `tests/` for the injected test module.

The runner stages are sequential and stop after failures that would make later evidence misleading:

1. Validate expected project layout and verify that `uv` is available.
2. Synchronize development dependencies with `uv sync --extra dev` unless `--skip-sync` is specified.
3. Run all project tests with `uv run pytest` unless `--skip-full-tests` is specified.
4. Copy and run claim-specific tests, collect JUnit XML, and remove the temporary test file.
5. Run `uv run ckernel bench smoke --results-root <output>/results`.
6. Invoke the bundled `audit_artifacts.py` using the current interpreter against the fresh smoke directory with `--expected-runs 4`.
7. Replay every generated smoke trace in lexical path order using `uv run ckernel replay`.
8. Write `concept_evidence.json` and `concept_evidence.md` under the output directory.

The runner records every command, working directory, elapsed time, exit code, and captured output location. It records an incomplete/failed stage rather than treating a skipped stage as success.

## Claim status algorithm

| Claim | Status condition |
|---|---|
| `C1`–`C6`, `C8` | **Demonstrated** only if the claim-specific test passed. |
| `C7` | **Demonstrated** only if full project tests, fresh smoke, passive audit, and all four replays passed. |
| Any skipped/failed required stage | **Not demonstrated**, with the exact stage named. |
| `N1`–`N6` | **Out of scope** unconditionally; the report explains the boundary. |

The runner must report the current assessment as **Demonstrated for the tested deterministic implementation and stated fixtures**. It must never label a claim as absolute proof.

## Report structure

The JSON report contains schema version, timestamps, project/output paths, command records, claim records, non-claim records, environment versions, smoke result paths, audit summary, replay counts, and overall status.

The Markdown report begins with a bounded conclusion, then presents a claim table, command evidence table, fresh smoke evidence table, explicit non-claims, and limitations. It must include the phrase: “These results demonstrate deterministic implementation mechanics, not model understanding or production-provider behavior.”

## Failure behavior

The runner returns nonzero for an execution failure, failed claim test, failed fresh-smoke audit, or failed replay. It retains output logs and partial report evidence. It removes only its temporary injected test module; it never modifies source, checked-in tests, supplied receipts, supplied traces, or checked-in results.
