# V32.55 — Application QA Decoupling and Data Recovery

Release verdict: **PARTIAL_PASS_BLOCKED**.

The deterministic fixture contract is isolated from market evidence and the protected-file guard self-test passed. V2 is unchanged and remains `ACQUIRED_WITH_REVIEW_REQUIRED`: 42237 rows, 3 gaps, and 13 absent candles. V3 is a separate immutable target; its current status is `ACQUISITION_IN_PROGRESS_OR_BLOCKED`.

## QA evidence

- Fixture: `deterministic_hourly_v1`, UTC hourly OHLCV schema, normal/gap/duplicate/invalid/stale and unavailable/malformed/timeout response cases. It is QA-only and not empirical evidence or a forecast source.
- V32.54 retests document 11 resolved IDs and 47 unresolved IDs. The full current inventory, categories, root-cause hypotheses, and per-ID fixture-mode retest command are in `failure_inventory.csv`.
- Network policy remains deny-by-default outside QA-owned loopback ports; authorization remains fail-closed.

## Track B

V2 missing timestamps are explicit in `integrity_and_data_status.json`. No candle is synthesized and no canonical parquet is overwritten. V3 must retain archived official responses, hashes, coverage, UTC/OHLCV validation, reproducible rebuild, and comparisons before it can be reviewed.

## Governed decisions

- Research Experiment: INCONCLUSIVE
- Prospective Evidence: COLLECTING
- Model Authorization: OFFLINE_RESEARCH_ONLY
- Live Trading: DISABLED
