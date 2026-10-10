# Agent C — Targets, Models, and Baselines Audit

**Mode:** Read-only code audit. No model was trained and no parameter search was run.

## Findings

### High — B0 and B0b do not implement registered side counterfactuals
- **Evidence:** `baselines.py:26-33` makes B0 an acceptance mask only. Outcomes are resolved using setup-owned side (`run_full_research_pipeline.py:132-162`), and B0b masks detector side (`:234-236, 320-321`) instead of resolving always-long and always-short outcomes. Preregistration defines random direction and abstention (`PREREGISTRATION_v1.md:140-145`).
- **Impact:** The directional baselines reuse setup-side outcomes and do not measure their declared comparator.
- **Correction:** Resolve both directional outcomes per eligible timestamp; implement deterministic seeded random side/abstention and true all-long/all-short counterfactuals. Add a one-opportunity fixture where long and short outcomes differ.

### High — only pair 01 supplies the model target and all barrier pairs reuse its mask
- **Evidence:** Training labels use `barrier_pair_01` BASE `net_r > 0` at `run_full_research_pipeline.py:216-218`; classifiers are fitted once (`:245-272`); the same LightGBM mask is applied to every pair (`:329-335`). Preregistration treats the barrier pairs as a confirmatory family (`PREREGISTRATION_v1.md:184-185`).
- **Correction:** Either implement independently registered pair-specific models/thresholds, or limit confirmatory claims to P01 and label other rows as fixed-mask secondary analyses. Do not search configurations.

### High — model target does not encode registered target/auxiliary states
- **Evidence:** Runner converts positive BASE net R into a binary label and converts null to `-1R` (`run_full_research_pipeline.py:216-218`); evaluation arrays also replace null with `-1R` (`:226-227`). This collapses unavailable, gap, unresolved, timeout and actual losing outcomes into binary losses. Compare preregistered outcome categories and primary endpoint in `PREREGISTRATION_v1.md:78-108, 140-169`.
- **Correction:** Preserve categorical outcomes and nulls; exclude unresolved/unavailable observations under a documented eligibility rule rather than imputing a loss. Validate target definition before fitting.

### High — train-only threshold selection is still in-sample outcome optimization
- **Evidence:** Threshold candidates are selected by maximizing mean realized training R at `run_full_research_pipeline.py:275-288`; the test segment is then scored on that selected threshold. Preregistration requires threshold fitted in-sample and locked, but describes calibration/selection protocols and purge in `PREREGISTRATION_v1.md:191-205, 218-227`.
- **Correction:** Implement the registered disjoint chronological train/calibration/threshold-selection blocks, with purges/embargoes before each outer test.

### High — listed LightGBM configurations are not evaluated
- **Evidence:** `lgb_configs` lists candidates but `best_lgb_cfg = lgb_configs[1]` at `run_full_research_pipeline.py:254-263`; no comparison is performed. Ledger later records only a hard-coded threshold and omits actual selected config (`:350-361`).
- **Correction:** Describe model config as fixed if that is preregistered; write actual model parameters and threshold to each unique run/trial event.

### Medium — B4-lite is not calibrated
- **Evidence:** `baselines.py:59-75` fits scaler + plain `LogisticRegression`; `predict_proba` forwards its raw probabilities. Preregistration names a calibrated logistic comparator (`PREREGISTRATION_v1.md:140-145`).
- **Correction:** Use time-respecting calibration data or accurately mark the comparator as uncalibrated and treat protocol mismatch as non-confirmatory.

## Side ownership
Setup events own LONG/SHORT; the meta-model currently only gates acceptance. No side-flip behavior was found.
