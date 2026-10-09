# Agent B — Validation and Holdout Audit

**Mode:** Read-only code audit. Holdout outcome values were not inspected.

## Findings

### Critical — alleged sealed holdout is accessed before partitioning
- **Evidence:** Runner resolves outcomes for every detected setup at `run_full_research_pipeline.py:101-166`, then schedules positions using primary outcome exit timestamps at `:174-193`, and only then partitions research/holdout at `:199-202`. The runner also writes `SEALED_UNTOUCHED` at `:365-375`. The preregistration requires one authorized opening at `PREREGISTRATION_v1.md:233`; the manifest currently claims `SEALED_UNTOUCHED` (`holdout_custody_manifest.json:9`).
- **Impact:** Holdout path/outcome records participate in pre-split outcome generation and scheduling. This proves access by the pipeline, not that holdout returns were used to tune a model.
- **Correction:** Mark custody `HOLDOUT_CUSTODY_UNVERIFIED`; do not read, schedule, count, or summarize the historical holdout in the development run. Do not claim a pristine holdout.

### High — split boundary disagrees with preregistration
- **Evidence:** Preregistration starts the final 12 months on 2025-10-07 (`PREREGISTRATION_v1.md:233`); runner uses Unix timestamp `1759881600` (2025-10-08) at `run_full_research_pipeline.py:199`; manifest records 2025-10-08 at `holdout_custody_manifest.json:6`.
- **Correction:** Keep the historical period out of model selection; correct boundary metadata only through an auditable custody status update, not by reopening the historical holdout.

### High — implemented split is one fixed partition, not registered walk-forward folds
- **Evidence:** `run_full_research_pipeline.py:205-218` partitions by list index, fits once on the first half, evaluates once on the remainder. Preregistration requires anchored/rolling folds, minimum three-year training, six-month tests, 240-minute purge and 24-hour embargo (`PREREGISTRATION_v1.md:191-198`).
- **Correction:** Implement timestamp-based sequential folds and fold-local training, purge, embargo, calibration, and threshold selection. Add exact-boundary and overlap tests.

### High — raw evaluation count is mislabeled as unseen independent trades
- **Evidence:** `n_eval = len(all_eval_trades)` at `run_full_research_pipeline.py:212-214`; report hardcodes 3,842 sequential trades and describes 20,244 as unseen trades (`run_full_research_pipeline.py:443` in the old template). The 20,244 is an evaluation-opportunity count, not post-abstention accepted trades or an independent-N estimate.
- **Correction:** Derive every stage count from one run and report raw opportunities, accepted trades, concurrent abstentions, and effective/cluster sample information separately.

### Medium — capacity schedule is primary-barrier-specific and abstentions are discarded
- **Evidence:** `run_full_research_pipeline.py:179-193` schedules using `barrier_pair_01` BASE exit only; rejected rows only receive an in-memory flag and are omitted downstream. Preregistration requires one open position, concurrent abstention and uniqueness weights (`PREREGISTRATION_v1.md:111-112`).
- **Correction:** Schedule separately for each registered barrier where needed, retain categorical abstentions, and derive/report uniqueness/effective sample size.

### Holdout disposition
Historical holdout custody cannot be defended as untouched after the runner's access. Do not use this holdout for further model selection. A future untouched evaluation requires a new prospective protocol.
