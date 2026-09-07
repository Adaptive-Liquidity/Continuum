# Reproducibility Failure Triage

Preserve failing evidence and classify the failure before changing code or expected artifacts.

## Triage table

| Symptom | Likely class | First checks | Do not do |
|---|---|---|---|
| Dependency or interpreter error | Environment | Python version, `uv sync --extra dev`, lockfile, working directory | Modify source to accommodate an unverified environment. |
| Test failure before benchmark | Source behavior | Narrow failing test, recent diff, controlled time/randomness | Regenerate reference artifacts first. |
| Missing manifest/index/metrics directory | Incomplete artifact set | Extraction completeness, benchmark exit status, output path | Infer success from the files that remain. |
| Counts disagree across artifacts | Interrupted or inconsistent stage | Manifest count, run IDs in every collection, duplicates | Delete extras or synthesize missing files. |
| JSON parse failure | Corrupt or truncated file | File size, last line, archive integrity, original hash | Reformat or repair the only copy. |
| Sequence mismatch | Structural trace corruption | First bad event number, adjacent lines, footer count | Renumber events in place. |
| Previous-event hash mismatch | Chain corruption or reordered event | Prior event hash, line order, duplicate/missing line | Recompute links to make the trace pass. |
| Event hash mismatch | Event content changed after recording | Canonical event body, timestamp format, payload diff | Replace the stored hash. |
| Footer trace hash mismatch | Event list/footer inconsistency | Recompute list of event hashes, footer fields | Update footer without explaining origin. |
| Decision hash mismatch within stored trace | Logical projection/footer inconsistency | Excluded-key set, event payload change, canonicalization | Add meaningful fields to the exclusion set. |
| Passive validation passes, replay fails | Logical divergence | Versions, predicate set, scaffold hash, runner behavior, run spec | Call the trace “verified” based on chain integrity alone. |
| Replay run ID differs | Run-spec or stable-ID change | Scenario/adapter IDs and versions, seed, stable ID function | Ignore because payloads look similar. |
| Summary differs but metrics match | Reporting drift | Reporting code/version, sorting, serialization, environment | Alter metrics to fit the old report. |
| Metrics differ and versions differ | Possibly expected change | Change plan, release notes, version bump rationale | Label corruption before assessing intent. |
| Metrics differ without version explanation | Unexplained logical change | Source diff, predicate/scenario/adapter/harness changes | Bless new artifacts automatically. |
| PNG bytes differ but source tables match | Renderer/environment variance | JSON/CSV points, SVG content, visual chart | Fail the entire audit on PNG bytes alone. |
| Reference outcomes look “too good” | Interpretation risk | Scenario ground truth, safe/violating pair, false blocks, deterministic driver | Claim production superiority. |

## Diagnostic order

Follow this order to avoid masking the root cause:

1. Preserve originals and record file hashes.
2. Verify extraction and expected paths.
3. Validate JSON/JSONL parsing.
4. Reconcile counts and run IDs.
5. Validate event sequence and hash chain.
6. Validate stored decision-trace hash.
7. Compare version identities and configuration hashes.
8. Perform full re-execution replay.
9. Compare metrics and reports.
10. Inspect source changes only after locating the failing layer.

## Structural versus logical failure

A structural failure means the stored trace cannot prove its own chain integrity. Stop before re-execution unless diagnosis explicitly requires a safe copy.

A logical failure means the stored trace is structurally self-consistent, but current project code reproduces a different decision-trace hash. Investigate version identities and source behavior. This can be a legitimate versioned change, an environment/configuration mismatch, or a regression.

Do not merge the two failure classes into a generic “hash mismatch.”

## Version comparison checklist

Compare, in order:

1. Project/package version.
2. `scenario_id` and `scenario_version`.
3. Adapter name and version.
4. Harness version.
5. Simulator or model ID.
6. Predicate-set hash.
7. Scenario scaffold-template hash.
8. Seed and pressure level.
9. Compaction budget and schedule.
10. Decision-projection rules.

Record both old and new values. If logic changed without a stable identity change, report a versioning defect even when the new behavior is intentional.

## Canonicalization checks

The project canonical format uses sorted keys, compact separators, UTF-8, deterministic UTC timestamps with microseconds and `Z`, enum values, POSIX paths, and sorted set representations. Trace event hashes include the event timestamp and previous-event link. The decision projection removes only explicitly incidental fields.

A pretty-printed or differently spaced JSON file may still carry the same logical data, but changing any event value requires a new event hash. Do not conflate file whitespace with event-body changes.

## Reporting drift

When reports differ:

1. Confirm both were generated from the same `metrics.json` logical content.
2. Compare `summary.json` and `survival_points.json` canonically.
3. Compare CSV values after line-ending normalization.
4. Inspect Markdown and SVG differences.
5. Visually inspect PNG output and compare source data.
6. Check plotting-library and font environment only after logical data matches.

## Escalation report

For every unresolved issue, report:

- exact failing path or command;
- first failing event or run ID;
- expected and actual values;
- structural integrity status;
- replay status;
- relevant version identities;
- whether originals were preserved;
- next safe diagnostic step.
