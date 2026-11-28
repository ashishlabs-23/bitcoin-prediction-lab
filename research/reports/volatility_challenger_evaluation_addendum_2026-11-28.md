# Addendum (2026-11-28) — Volatility Challenger Harness Integrity, Corrected Scores and Re-Ranking

**Parent report (unchanged):** `research/reports/volatility_challenger_evaluation_report.md` (Experiment EXP-VOL-CHALLENGER-2026-01, executed 2026-10-17T04:27:45Z).
**Addendum date:** 2026-11-28
**Pre-registered experiment:** E1 — harness integrity (defect repair, not a model search).
**Code changed:** `research/experiments/evaluate_volatility_challengers.py` (+345 / −63 lines), new regression suite `tests/test_volatility_harness_guards_2026_11_28.py`.
**Status of this document:** a dated, additive amendment. The 2026-10-17 report is *not* rewritten, edited or deleted; its numbers stand as the output of the defective harness and are superseded here only for the purpose of decision-making. Every number below is reproducible from the command in §9.

---

## 1. Why this addendum exists

A research audit on 2026-11-28 found that the challenger evaluation harness contained four defects that invalidated its 24-hour scorecard. The most serious one produced a mean QLIKE of **9436.8193** for the `Rolling-720h HAR-24H` challenger — a number that is not a forecast loss at all but an artefact of scoring negative "variance" predictions through a clamp. The second one admitted look-ahead information into every rolling training window. The third one *fabricated* a Model Confidence Set status in the emitted markdown. The fourth one indexed a fallback by position instead of by timestamp.

Because the harness output feeds governance decisions, the defects are repaired first and the corrected numbers are recorded here. No model was tuned, re-specified or re-selected after the fix; the challengers are the same objects with the same hyper-parameters, scored by the same QLIKE/DM-HLN/MCS machinery on the same non-overlapping blocks.

---

## 2. The four defects (pre-fix line numbers)

| # | Location (pre-fix) | Defect | Consequence |
| :--- | :--- | :--- | :--- |
| D1 | `:218-230` (fit `:221`, prediction `:227`, fallback `:229`) | Ridge was fitted on the **raw variance level** (`y_w = train_window["rv24h_var_ann"].values`) and the linear prediction `m.predict(...)` was appended **directly as a variance** — no `exp` link, no floor, no positivity constraint. The same pattern existed for the 168H challenger at `:169-179`. | 35 of 331 predictions were negative (min **−0.29611**). The QLIKE clamp at `:47-49` (`np.maximum(y_pred, 1e-6)`) turned each into a loss of ≈**369,061.66**, inflating mean QLIKE to **9436.8193**. |
| D2 | `:221` | Training window `df.index < idx_ts` admitted rows whose 24H target is computed from returns up to `idx_ts + 23h` — a **target-maturity (look-ahead) leak** of up to 23 hours. The same defect existed at `:170` for the 168H challenger (leak of up to 167 hours). | The challenger was trained on rows whose targets overlap the evaluation target, flattering its score (§6). |
| D3 | `:280`, `:299` (and the fixed rows at `:279`, `:297`, `:298`) | The emitted report hard-coded the string `**SURVIVES (In MCS)**` for `Rolling-720h HAR-24H` although the stored MCS computation (`:245`) had **eliminated** that model. The executive summary (`:268`) likewise hard-coded "Survives in the 95% Model Confidence Set". | A fabricated statistical status in a governed research artefact. |
| D4 | `:275`, `:293` | The evaluation date range was hard-coded as `(2026-01-01 to 2026-10-16)` while the data extended to 2026-11-28. | Misstated sample span; stale provenance. |
| D5 | `:229` | The persistence fallback used positional indexing `pred_persist_24[len(pred_rolling_24)]`, which is only correct if the evaluation index starts at row 0 of the persistence vector. | Silent misalignment in any re-sliced or filtered evaluation. |

---

## 3. Reproduction of the defect (pre-fix code, data through 2026-11-28)

The pre-fix harness was re-executed on the current dataset before any edit:

```
cd /home/ubuntu/bt && python3 research/experiments/evaluate_volatility_challengers.py
```

| Quantity | Value |
| :--- | :--- |
| Non-overlapping 24H blocks (2026-01-01 → 2026-11-28) | 331 |
| Negative variance forecasts emitted by `Rolling-720h HAR-24H` | **35 / 331** |
| Minimum forecast | **−0.29611** |
| Maximum single QLIKE loss | **369,061.66** |
| Mean QLIKE of `Rolling-720h HAR-24H` | **9436.81930** |
| Share of that mean contributed by the 35 negative rows | 9436.05 / 9436.82 = **99.99 %** |

The harness also emitted, for the same run, the claim `| Rolling-720h HAR-24H | ... | 9436.81930 | ... | **SURVIVES (In MCS)** |` although its own MCS log line read `MCS eliminated model 'Rolling-720h HAR-24H (Challenger)'`. The 2026-10-17 report contains the same class of error at N = 258 blocks (mean QLIKE 9292.44248 with the fabricated "SURVIVES" cell).

---

## 4. What was changed (line level)

All edits are confined to `research/experiments/evaluate_volatility_challengers.py`.

**D1 — positive, scale-aware variance forecasts.** New `ensure_positive_variance()` (l. 84) floors every forecast at `max(pred, 0.05 * rv30d_var_ann)` using the trailing 30-day realized variance *at that forecast origin*, and raises `NonPositiveForecastError(ValueError)` if any value is non-finite before the guard or still non-positive/non-finite after it. New `log_space_variance_fit()` (l. 150) fits Ridge on `log(max(y, 1e-12))`, clips the linear predictor to `[-700, +700]` before `exp` (overflow guard), and passes the result through the floor. New `rolling_predictions()` (l. 197) replaces the two hand-written loops (`:169-179`, `:219-230`) and separates `target_col` (the fitted quantity) from `fallback_col` (persistence). New `validate_positive_variance()` (l. 132) is an assertion-only variant used for the persistence and rolling-30D benchmarks, which are positive by construction and must not be moved by a guard — the baseline is therefore bit-identical to the pre-fix run (0.81175).

**D2 — causal windows.** New `causal_window_mask()` (l. 177) selects the half-open interval `(idx_ts − 720h, idx_ts − embargo_hours)`. The 24H challenger uses `embargo_hours=24` (l. 456) and the 168H challenger uses `embargo_hours=168` (l. 401): a row stamped `t` carries a target computed from returns over `(t, t + horizon]`, so it is only fully observed at `t + horizon`. No training row may now mature after the forecast origin.

**D3 — computed MCS status.** `mcs_status()` (l. 333) and `render_table()` (l. 338) render every "95% MCS Status" cell from the stored `mcs_24` / `mcs_168` lists returned by `model_confidence_set()`. The executive-summary sentence is likewise computed. The literal `SURVIVES (In MCS)` now exists in exactly one place in the code — inside `mcs_status()` — and a test enforces that.

**D4 — computed date range.** `evaluation_span()` (l. 353) derives the span from `df_*_eval.index.min()` / `.max()` plus the horizon; the literal `2026-10-16` no longer appears anywhere in the file.

**D5 — timestamp fallback.** The fallback is now `df.at[idx_ts, "rv1d_var_ann"]` (24H) / `df.at[idx_ts, "rv7d_var_ann_lag"]` (168H) inside `rolling_predictions()`.

**Operational guardrail added.** The committed report path can be redirected with `VOL_CHALLENGER_REPORT_PATH` (l. 67) so a re-run can be reproduced without overwriting the frozen 2026-10-17 artefact; the default path is unchanged.

**Correctness note.** The two stored 24H artefacts (`ConventionalHAR24H`, `HARQLIKE24HChallenger`) already apply their own inverse link and emit variances directly; they must **not** be exponentiated by the harness. This is now documented at l. 442-445.

---

## 5. Corrected scorecard (post-fix harness, same data, same models, same blocks)

### 5.1 24-Hour horizon (`rv24h_var_ann`), N = 331 non-overlapping blocks, issue timestamps 2026-01-01 → 2026-11-28 (last target matures 2026-11-29)

| Model Candidate | Role | Mean QLIKE (pre-fix) | **Mean QLIKE (corrected)** | RMSE | MAE | 95% MCS (computed) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| HAR-QLIKE-24H-v1.0 | Research Challenger | 0.33920 | **0.33920** | 0.19673 | 0.12324 | In MCS |
| HAR-OLS-24H | Conventional Baseline | 0.41537 | 0.41537 | 0.20565 | 0.10278 | In MCS |
| Rolling 30D (24h) | Naive Benchmark | 0.49696 | 0.49696 | 0.22534 | 0.12980 | Eliminated |
| Persistence (24h) | Naive Baseline | 0.81175 | 0.81175 | 0.23881 | 0.14264 | Eliminated |
| Rolling-720h HAR-24H | Research Challenger | **9436.81930** | **0.95567** | 0.29530 | 0.14939 | In MCS (see §8) |

Pairwise HLN (Student's $t_{T-1}$, $h=1$):

- HAR-QLIKE-24H vs HAR-OLS-24H: HLN = 1.4291, **two-sided p = 0.1539** (one-sided p = 0.0770), mean diff = 0.076169.
- Rolling-720h vs Persistence: HLN = −0.6347, p = 0.5261, mean diff = −0.143918 → the challenger is *worse* (higher QLIKE) and the difference is not significant.
- Rolling-720h vs HAR-OLS-24H: HLN = −2.8125, p = 0.0052, mean diff = −0.540304.
- HAR-QLIKE-24H vs Persistence: HLN = 5.0436, p < 0.0001, mean diff = 0.472555.

*Note on the p-value quoted in the audit note:* the harness's pre-registered test is two-sided, giving p = 0.1539 for HAR-QLIKE vs HAR-OLS. The one-sided figure is 0.0770, which is the value the audit note quoted (≈0.0773, within rounding). Neither is significant at the 5 % level; the decision is unchanged either way.

### 5.2 168-Hour horizon (`rv7d_var_ann`), N = 47 non-overlapping blocks, issue timestamps 2026-01-01 → 2026-11-19 (last target matures 2026-11-26)

| Model Candidate | Role | Mean QLIKE (pre-fix) | **Mean QLIKE (corrected)** | RMSE | MAE | 95% MCS (computed) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| HAR-RS-DOW-v1.0 | Canonical Baseline (frozen artefact) | 0.14897 | **0.14897** | 0.12462 | 0.08149 | In MCS |
| Persistence (168h) | Naive Baseline | 0.20232 | 0.20232 | 0.14178 | 0.09275 | In MCS |
| Rolling 30D (168h) | Naive Benchmark | 0.24695 | 0.24695 | 0.14626 | 0.09795 | In MCS |
| Rolling-720h HAR-RS | Research Challenger | 0.16208 | **0.51595** | 0.20729 | 0.11243 | In MCS |

- HAR-RS-DOW-v1.0 vs Persistence: HLN = 1.3111, p = 0.1963, mean diff = 0.053354 (unchanged; the canonical model is a frozen artefact evaluated on point-in-time features and is untouched by these repairs).
- Rolling-720h HAR-RS vs HAR-RS-DOW-v1.0: HLN = **−2.1706, p = 0.0352**, mean diff = −0.366984 (pre-fix: HLN = −0.3345, p = 0.7395).

The 168H challenger's score moved from 0.16208 to 0.51595 because the same target-maturity leak (D2) was present at `:170`. Corrected, it is **more than three times worse** than the canonical model and significantly so. This is an additional, unplanned finding of E1 and is recorded as a FAIL for the 168H rolling challenger.

---

## 6. Proof that the look-ahead leak was open, and that it is now closed

The leak fix is not cosmetic. Holding everything else constant (log-space fit, same floor, 720h window, N = 331, α = 1.0) and varying only the window end:

| Window end | Mean QLIKE of Rolling-720h HAR-24H |
| :--- | :---: |
| `idx_ts − 1h` (pre-fix, leaky) | **0.57156** |
| `idx_ts − 24h`, inclusive (causal variant) | 0.93445 |
| `idx_ts − 24h`, half-open (adopted) | **0.95567** |

The leaky window understated the challenger's loss by ≈0.38 QLIKE (≈40 %), because up to 23 rows per fit carried targets that overlap the evaluation target. The adopted half-open bound `(idx_ts − 720h, idx_ts − 24h)` is the most conservative admissible choice and matches the audit's independent estimate of ≈0.957.

This is pinned by `tests/test_volatility_harness_guards_2026_11_28.py::TestLeakClosureRegression::test_shifting_window_end_by_24h_changes_the_score`, which constructs a dataset where the evaluation target is a volatility spike echoed in the 23 rows immediately preceding the origin, then asserts that (a) the two windows produce different predictions, (b) the two windows produce different scores, (c) the leaky window scores *better*, and (d) the causal window never sees the spike. A companion test asserts that the leaky mask admits exactly 23 unmatured targets and that the 168H contract uses a 168h embargo.

---

## 7. Corrected ranking and decisions

### 7.1 24-Hour horizon — corrected ranking (lower is better)

1. HAR-QLIKE-24H-v1.0 — 0.33920
2. HAR-OLS-24H — 0.41537
3. Rolling 30D — 0.49696
4. **Persistence — 0.81175**
5. **Rolling-720h HAR-24H — 0.95567** (previously reported as 9436.8193)

The `Rolling-720h HAR-24H` challenger does **not** beat the naive persistence baseline. It is retained here as a recorded negative result; it was **not** re-specified, re-tuned or given a different window/alpha to make it pass.

### 7.2 Decisions

| Decision | Value | Basis |
| :--- | :--- | :--- |
| **Research Experiment — Rolling-720h HAR-24H** | **FAIL** | Corrected QLIKE 0.95567 > persistence 0.81175 (HLN = −0.6347); the pre-registered criterion is improvement over the naive persistence baseline. |
| **Research Experiment — Rolling-720h HAR-RS (168h)** | **FAIL** | Corrected QLIKE 0.51595 vs canonical 0.14897 (HLN = −2.1706, p = 0.0352). |
| **Research Experiment — HAR-QLIKE-24H-v1.0** | **RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY** | QLIKE 0.33920 vs HAR-OLS 0.41537, HLN two-sided p = 0.1539 (one-sided 0.0770) — better point estimate, **not** statistically significant. |
| **Canonical 168H model** | Unchanged | HAR-RS-DOW-v1.0 remains the sole authorized model for 168-hour volatility risk; these repairs did not touch it or its score. |
| **Prospective evidence** | **COLLECTING** | `engine/prospective_evidence_pipeline.py::get_ledger_summary()` at 2026-11-28: 11 logged forecasts, 6 resolved 24H clean blocks, 5 pending 168H, 0 excluded; hurdle 100. (The audit note's "12 records" was not reproducible on disk at the time of writing; the ledger held 11 records.) |
| **Model authorization** | **OFFLINE_RESEARCH_ONLY** | No challenger inherits production authorization. |
| **Live trading** | **DISABLED** | Unchanged, permanent. |

No claim of production readiness is made or implied by this addendum. The 24H contract (`rv24h_var_ann`, hourly-sampled 24-candle realized-variance proxy) is a distinct target from the 168H contract; a better 24H QLIKE does not transfer to the 7-day horizon, and volatility accuracy is not directional accuracy.

---

## 8. Caveats and residual risks (read before citing the MCS column)

1. **The MCS is under-powered at these sample sizes and does not discriminate.** At N = 331 it retains three 24H models spanning 0.33920 to 0.95567, and at N = 47 it retains all four 168H models. The `T_max` statistic with a seeded stationary bootstrap is not rejecting at these block counts. The MCS column is now *truthful* (it reports what the stored computation returned), but it is **not** the decision gate; the pre-registered gate is the QLIKE comparison against persistence. Do not read "In MCS" as "equivalent to the best model".
2. **Historical replay is not confirmatory evidence.** All 331 + 47 blocks are retrospective development replay. Only post-freeze prospective blocks count for confirmation, and 6 / 100 is far below the hurdle.
3. **Data vintage.** Scores are computed on `data/raw/ohlcv.parquet` through 2026-11-28 16:00 UTC (43,024 rows). The 2026-10-17 report's N = 258 reflects the data vintage of that date; the N = 331 figures here are not a like-for-like restatement of that report, which is why it is left intact rather than edited.
4. **Artefact provenance.** The stored challengers emit variances directly (they apply their own inverse link). Exponentiating them is a latent trap; it was observed during development of this fix (producing a spurious QLIKE of 1.51616 for HAR-QLIKE-24H) and is now documented at the call site and asserted by the corrected headline numbers (0.33920 / 0.41537) in the end-to-end test.
5. **Unchanged statistical machinery.** The DM/HLN implementation and the MCS implementation were not modified by E1; only their inputs (forecasts) and their rendering (report cells) changed. Any weakness in those implementations is out of scope for this addendum and remains an open item.
6. **Scikit-learn version warning.** The stored artefacts were pickled with scikit-learn 1.9.0 and are loaded under 1.9.1, which emits `InconsistentVersionWarning`. Predictions reproduced the pre-fix values to the last digit on the unaffected models, but the artefacts should be re-serialised under a pinned version in a future hardening pass.

---

## 9. Verification evidence

```
cd /home/ubuntu/bt && python3 -m pytest -q -p no:cacheprovider tests/test_volatility_harness_guards_2026_11_28.py
# 24 passed, 9 warnings in 3.06s
```

The 24 tests cover: floor behaviour and scale-awareness, non-finite rejection, the post-guard assertion path, an overflow-safe log-space fit, the audit's negative-prediction reproduction fixture (loss > 1e5 unguarded, < 50 guarded), causal-window bounds for both contracts, the 24h window-shift score regression, timestamp (not positional) fallback, computed MCS cells and date spans, a source-level check that the MCS literal exists only inside `mcs_status()` and that `2026-10-16` no longer appears, and an end-to-end re-run asserting 0.95567 / 0.81175 / 0.33920 / 0.41537.

Reproduce the corrected scorecard without touching the frozen report:

```
cd /home/ubuntu/bt && VOL_CHALLENGER_REPORT_PATH=/tmp/report.md python3 research/experiments/evaluate_volatility_challengers.py
```

Neighbouring suites re-run for collateral damage: `tests/test_volatility_bridge.py`, `tests/test_phase3_volatility_and_range_validation.py` — 5 passed.

---

## 10. Provenance

- Parent report: `research/reports/volatility_challenger_evaluation_report.md` (2026-10-17T04:27:45Z) — **unmodified**, verified with `git status`.
- This addendum: `research/reports/volatility_challenger_evaluation_addendum_2026-11-28.md`.
- Harness: `research/experiments/evaluate_volatility_challengers.py`.
- Regression suite: `tests/test_volatility_harness_guards_2026_11_28.py`.
- No files under `engine/`, `models/`, `api/`, `web/`, `data/` were modified by this work.
