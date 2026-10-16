# BTCognitive Stage 12 — Validation Integrity, Causal Risk Calibration, and Application Readiness Report

**Date:** October 16, 2026  
**Auditor / Roles:** Independent Quantitative Researcher, Financial Machine Learning Engineer, and Production-Systems Auditor  
**Branch:** `main` (commit `50e362e6d92a20a13cd17ac1258c70107ca805af`)  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Evaluation Status:** Completed Independent Validation Integrity Audit, Causal Risk Calibration Repair, and Application Readiness Certification  
**Artifacts Produced:**  
- Stage 12 Prospective Validation Manifest: [`experiments/results/stage12_prospective_validation/stage12_prospective_manifest.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage12_prospective_validation/stage12_prospective_manifest.json)  
- Causal Risk Calibration Engine & Audit: [`research/stage12_causal_conformal_engine.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage12_causal_conformal_engine.py)  
- Causal Risk Calibration Audit Record: [`experiments/results/stage12_prospective_validation/stage12_causal_risk_calibration_audit.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage12_prospective_validation/stage12_causal_risk_calibration_audit.json)  
- Acceptance & Regression Test Suite: [`tests/test_stage12_causal_validation.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage12_causal_validation.py) (8/8 Passed; 58/58 Multi-Stage Regression Passed)  
- Authoritative Model Registry Update: [`models/authoritative_model_registry.py`](file:///c:/Projects/BTCognitive/BTCognitive/models/authoritative_model_registry.py)  
- Production Model Card Update: [`models/registry/HAR-RS-DOW-v1.0/model_card.md`](file:///c:/Projects/BTCognitive/BTCognitive/models/registry/HAR-RS-DOW-v1.0/model_card.md)  
- Runtime Terminal Route Causal Repair: [`api/routes_terminal.py`](file:///c:/Projects/BTCognitive/BTCognitive/api/routes_terminal.py)  

---

## Executive Summary

Stage 12 conducts an unsparing audit of the validation integrity, risk calibration causality, trading economics, feature comparisons, and application readiness of BTCognitive. The objective is not to chase a 70% directional accuracy figure, but to establish which empirical findings are scientifically trustworthy, correct temporal lookahead leakage in adaptive conformal intervals, reconcile unit discrepancies in trading simulations, and ensure the system communicates its true capabilities without exaggeration.

### The Three Most Consequential Findings

1. **Temporal Lookahead Leakage in Risk-Envelope Calibration Discovered & Repaired:**  
   In earlier conformal risk-envelope implementations (`research/run_uncertainty_03_holdout_trial.py`, `api/routes_terminal.py`, and Stage 11 audit scripts), `res_all` was constructed by concatenating training residuals with holdout residuals. When calculating the exponentially weighted moving standard deviation $\sigma_t$ and conformity scores $s_t$, the contemporaneous residual of the 168-hour forward realized variance was included at forecast origin time. Because $\text{rv7d\_var\_ann}_t$ requires 168 future hours to realize, this leaked future volatility spikes into the forecast's scale estimate at time $t$.  
   - When corrected to a **strictly causal delayed-resolution protocol** (where holdout residuals are delayed by 168 hours and only outcomes resolved prior to forecast issuance are used), the empirical holdout coverage on 2026 data ($N = 5,671$) is **84.89%** (95% Stationary Block Bootstrap CI: $[73.14\%, 93.14\%]$), compared to the leaked figure of **92.36%**.  
   - Claims of 92.36% holdout coverage are formally superseded. An automated causality invariance test proves that mutating future unresolved outcomes has zero impact on already-issued forecast intervals.

2. **Stage 11 Prospective Claim Corrected to Historical Replay; Forward Frontier Fixed at October 16, 2026:**  
   Stage 11 claimed a forward evaluation frontier of `2026-09-01T06:00:00Z`. However, forensic execution logs confirm that the forward collector was created and executed on **October 16, 2026**. No collector was running or recording forecast issuance timestamps between September 1 and October 16. That interval is therefore classified as a **HISTORICAL DATA GAP / REPLAY**, not prospective validation.  
   - The genuine prospective evaluation frontier is pinned in `stage12_prospective_manifest.json` to **October 16, 2026 at 10:45:00 UTC** (`2026-10-16T10:45:00Z`).  
   - Furthermore, we document the fundamental limitation of local SHA-256 recursive hash chains: while they guarantee internal tamper-evidence from file creation, they do not prove historical existence prior to creation without an external Timestamp Authority (RFC 3161 TSA) or public blockchain anchor.

3. **Reconciliation of Trading Units, Friction Accounting, and the 70% Accuracy Reality:**  
   Differences between Stage 6 and Stage 11 net returns were traced to denominator and unit definitions: Stage 6 evaluated returns per active bar in selective prediction (and initially omitted the cash exit transition), whereas Stage 11 evaluated per forecast bar across continuous positions. When evaluated as **isolated trades of horizon $H$** under institutional friction (14 bps round-trip):
   - 1-hour trades: Gross = -0.90 bps, Net = **-14.90 bps/trade** (or -5.72 bps/bar under continuous position).
   - 4-hour trades: Gross = +0.39 bps, Net = **-13.61 bps/trade** (or -3.49 bps/bar under continuous position).
   - 24-hour trades: Gross = -13.13 bps, Net = **-27.13 bps/trade** (or -15.43 bps/bar under continuous position).  
   Every tested horizon is economically unprofitable due to high turnover. Unconditional 70% directional accuracy remains scientifically unsubstantiated (the 95% bootstrap upper bound on untouched holdout data is 53.36%, 16.64% below 70.0%).

---

## 1. Verified Repository State and Model Registry Governance

Prior to implementing corrections, the repository state was verified:

| Dimension | Audit Status | Evidence & Audit Trace |
|---|---|---|
| **Git Working Tree** | Local `main` branch, clean working tree | Commit `50e362e6d92a20a13cd17ac1258c70107ca805af` |
| **Active Production Model** | `HAR-RS-DOW-v1.0` (`AUTHORIZED_FOR_PRODUCTION`) | SHA-256: `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` in [`models/authoritative_model_registry.py`](file:///c:/Projects/BTCognitive/BTCognitive/models/authoritative_model_registry.py) |
| **Production Task & Horizon** | 168-Hour Annualized Realized Variance ($\text{rv7d\_var\_ann}$) | Serves point variance and C2 risk envelope at `/api/terminal/live`. ZERO directional claims. |
| **Research Directional Models**| `directional-gbm-*-v1` (`OFFLINE_RESEARCH_ONLY`) | Directional benchmarks; strictly blocked from production serving and live order routing |
| **Startup Gate Safeguards** | Active and verified | [`validation/startup_gate.py`](file:///c:/Projects/BTCognitive/BTCognitive/validation/startup_gate.py) enforces fail-closed checks on required inputs and hashes |
| **Live Execution Guard** | 100% Disabled | Zero exchange trading libraries, zero API keys, zero order execution hooks |

---

## 2. Chronology Audit and Final Classification of Stages 10 & 11

To eliminate ambiguity between historical replay, data gaps, and prospective validation, the temporal timeline was audited:

### Chronology Table

| Period / Event | Calendar Span | Execution Mechanism | Data Nature | Epistemic Classification | Evidence & Trace |
|---|---|---|---|---|---|
| **Pre-2026 Training Span** | 2022-01-31 to 2025-12-24 | Offline model fitting | Historical Coinbase OHLCV | `IN_SAMPLE_TRAINING` | `repaired_scientific_contract_manifest.json` (34,175 bars) |
| **Pre-2026 Label Embargo** | 2025-12-25 to 2025-12-31 | Purged gap | 168h target label horizon | `TRAIN_HOLDOUT_EMBARGO` | Prevents target overlap into 2026 holdout |
| **Stage 10 Holdout Period** | 2026-01-01 to 2026-09-01 | Batch execution on 2026-10-16 | Point-in-time causal historical OHLCV | `VALID_HISTORICAL_OUT_OF_SAMPLE_REPLAY` | `shadow_prediction_ledger.jsonl` (46,515 events created on 2026-10-16) |
| **September-October Data Gap**| 2026-09-01 to 2026-10-16 | Unobserved gap | Historical exchange data | `HISTORICAL_DATA_GAP_UNVERIFIED` | No collector was operating; cannot be claimed as prospective |
| **Genuine Forward Frontier** | 2026-10-16T10:45:00Z onward | Live streaming ingestion | Streaming candle closes | `GENUINE_FORWARD_ONLY_EVALUATION` | `experiments/results/stage12_prospective_validation/stage12_prospective_manifest.json` |

### Limitations of Local SHA-256 Hash Chaining
A local SHA-256 hash chain ($H_i = \text{SHA-256}(\text{JSON}(E_i, H_{i-1}))$) makes retrospective tampering of the file detectable from the moment of creation. However, **a local hash chain alone does not prove historical existence prior to creation**. Without an RFC 3161 Timestamp Authority signature or a transaction hash anchored into a public decentralized blockchain, claims of historical priority against retrospective replay are scientifically unverified. This distinction is formally registered in `stage12_prospective_manifest.json`.

---

## 3. Conformal Risk-Envelope Causality Audit and Corrected Results

### The Contemporaneous Residual Leakage Defect
In adaptive conformal prediction (C2), residual magnitude is normalized by an exponentially weighted moving standard deviation:
$$s_t = \frac{|y_t - \hat{y}_t|}{\sigma_t}$$

In previous scripts:
```python
# Defective pattern:
res_all = np.concatenate([res_train, y_holdout - v_hat_holdout])
rolling_std_all = pd.Series(res_all).ewm(span=720, min_periods=72).std().values
...
std_i = rolling_std_all[t_glob]  # t_glob = N_train + i
```
At index `t_glob`, `rolling_std_all[t_glob]` was computed using `res_all[t_glob] = y_holdout[i] - v_hat_holdout[i]`. Because $y_i = \text{rv7d\_var\_ann}_i$ requires 168 hours into the future to realize, contemporaneous standard deviation leaked the future volatility shock directly into interval width $U_i - L_i$.

### Strictly Causal Delayed-Resolution Sequence
We implemented the causal protocol in [`research/stage12_causal_conformal_engine.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage12_causal_conformal_engine.py):
1. Target $y_t$ matures and resolves strictly at $t + 168$ hours.
2. At forecast origin $t$: only residuals resolved strictly before $t$ ($s \le t - 168$) are known.
3. The scale estimate $\sigma_t$ and conformity score pool are derived strictly from resolved residuals $\le t - 168$.
4. The interval $[L_t, U_t]$ is emitted and logged before $y_t$ is observed.
5. Containment is scored after horizon completion.

### Empirical Results Before and After Causal Correction

| Metric Dimension | Leaked Non-Causal Evaluation | Strictly Causal Evaluation | Delta / Impact | Epistemic Status |
|---|---|---|---|---|
| **Empirical Coverage** | **92.36%** | **84.89%** | **-7.47%** | Causal adaptation lag during rapid vol expansion |
| **95% Bootstrap CI** | $[87.53\%, 95.73\%]$ | **$[73.14\%, 93.14\%]$** | Wider uncertainty | Reflects serial dependence across 168h windows |
| **Mean Interval Width** | 0.4513 | **0.4389** | -0.0124 | Slightly narrower due to lagging scale estimate |
| **Median Interval Width**| 0.2454 | **0.2364** | -0.0090 | Responsive during steady regimes |
| **Mean Relative Width** | 2.45x realized var | **2.71x realized var** | +0.26x | Penalized by regime spikes |
| **Median Relative Width**| 1.82x realized var | **2.06x realized var** | +0.24x | Stable central containment |
| **Mean Winkler Score** | 0.4917 | **1.0444** | +0.5527 | Penalizes out-of-sample boundary breaches |

### Automated Causality Invariance Verification
An automated test ([`tests/test_stage12_causal_validation.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage12_causal_validation.py)::`test_causal_invariance_property`) mutates future unresolved holdout residuals ($y_{t+k} \to 999,999.0$). In the causal engine, already-issued forecast bounds $[L_t, U_t]$ remain **100% invariant** ($\Delta < 10^{-9}$), proving zero forward leakage.

---

## 4. Active Model Target, Horizon, and Semantic Consistency

We audited `HAR-RS-DOW-v1.0` across its model card, training pipeline, inference module, and API routes to eliminate semantic mismatches:

```
+----------------------------------------------------------------------------------------------------+
|                         AUTHORITATIVE ACTIVE MODEL CONTRACT                                        |
|                                                                                                    |
|  Canonical Identifier:   HAR-RS-DOW-v1.0                                                           |
|  Classification:         PRODUCTION_VOLATILITY                                                     |
|  Operational Status:     AUTHORIZED_FOR_PRODUCTION_VOLATILITY_INTELLIGENCE                         |
|  Forecast Target:        Annualized 7-Day Realized Variance (rv7d_var_ann)                         |
|                          rv7d_var_ann_t = (8760 / 168) * sum_{i=1}^{168} r_{t+i}^2                 |
|  Forecast Horizon:       168 hours (7 calendar days)                                               |
|  Output Units:           Annualized Variance (decimal, e.g. 0.1930) & Annualized Volatility (%)    |
|  Directional Alpha:      FALSE (Does NOT predict price direction; sign of return is unmodeled)    |
|  Uncertainty Engine:     C2 Conformal Prediction (alpha=0.10, strictly causal delayed resolution)  |
|  Production Serving:     GET /api/terminal/live, GET /api/terminal/model-identity                  |
|  Execution Hooks:        ZERO (Live trading permanently disabled)                                  |
+----------------------------------------------------------------------------------------------------+
```

### Semantic Separation Enforced in Code
- **Conformal Coverage != Directional Accuracy:** The 84.89% causal holdout containment (and 92.84% pre-2026 calibration) measures whether forward realized variance falls within the C2 variance band. It is NEVER cited as directional prediction accuracy.
- **7-Day Volatility != 24-Hour Excursion:** The legacy 24-hour range prototype (`v3.0.0-excursion-ridge-conformal`) remains archived and fails closed (`BLOCKED_PROVENANCE_UNVERIFIED` / `EXPERIMENTAL_BASELINE`). The production terminal serves exclusively 7-day realized variance.
- **Empirical Coverage != Absolute Guarantee:** The terminal disclaimer explicitly states that empirical coverage is an observed historical estimate and cannot guarantee containment for any individual future interval.

---

## 5. Reconciliation of Trading-Cost and Return Calculations

To reconcile discrepancies between Stage 6 and Stage 11 reports, we audited the friction mechanics and created a deterministic reference test.

### Friction Tier Assumptions
- **Institutional Friction (14 bps round-trip):** 5 bps taker fee + 2 bps half-spread on entry (7.0 bps); 5 bps taker fee + 2 bps half-spread on exit (7.0 bps).
- **Retail Friction (35 bps round-trip):** 15 bps taker fee + 2.5 bps half-spread on entry (17.5 bps); 15 bps taker fee + 2.5 bps half-spread on exit (17.5 bps).

### Root Causes of Reported Discrepancies
1. **Omitted Cash Exit Fee in Stage 6 Selective Prediction:**  
   In Stage 6, when a selective prediction fell below the confidence hurdle, the position transitioned to cash (0), but the exit transition fee was not subtracted from net returns because net returns were only appended on active bars. This was caught and corrected in Stage 9 (adding 1 transition fee on cash exit).
2. **Per-Bar Continuous Position vs Per-Trade Isolated Accounting:**  
   - In Stage 11, the scorecard evaluated continuous positions: $R_{net, t} = \text{signal}_t \cdot r_{t+1} - \Delta pos_t \cdot 7.0$ bps. For 1h, this yielded -5.72 bps/bar (due to 0.689 transitions/bar).  
   - However, for 4h and 24h, the code assigned the multi-hour forward return ($\ln(P_{t+H}/P_t)$) to each hourly step while counting hourly transitions, which conflated per-bar position holding with overlapping multi-hour trades.
   - When properly evaluated as **isolated trades of horizon $H$** (where each trade enters at $t$ and exits at $t+H$, paying 1 full round trip = 14 bps):

| Horizon | Nominal $N$ | Mean Gross Return / Trade | Round-Trip Fee (Inst. 14 bps) | Net Return / Trade (Inst.) | Net Return / Trade (Retail 35 bps) | Economic Status |
|---|---|---|---|---|---|---|
| **1h** | 5,838 | -0.90 bps | 14.0 bps | **-14.90 bps** | **-35.90 bps** | **UNPROFITABLE** |
| **4h** | 5,835 | +0.39 bps | 14.0 bps | **-13.61 bps** | **-34.61 bps** | **UNPROFITABLE** |
| **24h** | 5,815 | -13.13 bps | 14.0 bps | **-27.13 bps** | **-48.13 bps** | **UNPROFITABLE** |

### Deterministic Reference Simulation
A deterministic test ([`tests/test_stage12_causal_validation.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage12_causal_validation.py)::`test_deterministic_trading_cost_accounting`) verifies manual calculation with known prices:
- Prices: $[100, 102, 101, 104, 104]$
- Positions: $[+1, -1, -1, 0]$
- Transitions: $1 + 2 + 0 + 1 = 4$ transitions (exactly 2 complete round trips).
- Fees: $4 \times 7.0 = 28.0$ bps.
- Gross Return: $+3.85$ bps.
- Net Return: $-24.15$ bps.
- Per-bar net return: $-6.04$ bps/bar.
- Per-round-trip net return: $-12.08$ bps/trade.

---

## 6. Correct Statistical Interpretation of Feature and Model Experiments

We audited the statistical comparisons in `stage6_controlled_experiment_results.json`:

| Experiment Comparison | Baseline Model / Features | Challenger Model / Features | Delta Accuracy | 95% Paired Bootstrap CI | McNemar $p$-value | Scientific Determination |
|---|---|---|---|---|---|---|
| **Oscillators Ablation** | 4 Return Lags (53.28%) | + RSI, MACD, SMAs (53.22%) | -0.06% | $[-0.33\%, +0.23\%]$ | $p = 0.6679$ | **NO RELIABLE IMPROVEMENT** (Null not rejected) |
| **Volatility Ablation** | 4 Return Lags (53.28%) | + RV, ATR, Parkinson (53.27%) | -0.01% | $[-0.28\%, +0.27\%]$ | $p = 0.9837$ | **NO RELIABLE IMPROVEMENT** (Null not rejected) |
| **Full Feature Stack** | 4 Return Lags (53.28%) | Full 15 Features (53.08%) | -0.20% | $[-0.52\%, +0.15\%]$ | $p = 0.2426$ | **NO RELIABLE IMPROVEMENT** (Null not rejected) |
| **Model Challenger** | GBDT 4-Lag (53.28%) | L2 Logistic Regression (53.20%)| -0.08% | $[-0.50\%, +0.36\%]$ | $p = 0.7430$ | **STATISTICALLY IDENTICAL** (412x speedup) |
| **Selective Prediction** | 100% Coverage (53.28%) | 8.52% Coverage Tier (56.06%) | +2.78% | Wilson: $[54.24\%, 57.86\%]$ | N/A | **NEGATIVE NET EXPECTANCY** (-10.55 bps/bar) |

### Strict Epistemic Formulations
1. **No Evidence of Incremental Predictive Power:** All paired bootstrap confidence intervals cross zero, and all McNemar $p$-values exceed 0.20. The evidence demonstrates that adding technical indicators or complex non-linear architectures **has not demonstrated a reliable predictive improvement** over the simple 4-lag baseline.
2. **Baseline Does Not "Statistically Dominate":** Because differences are statistically indistinguishable from zero, the 4-lag model does NOT statistically dominate the alternatives; rather, the alternatives fail to justify their added complexity.
3. **The 70% Target Reality Check:** On untouched out-of-sample data, the empirical 95% bootstrap upper bound is **53.36%**. A 70% accuracy claim is empirically unsubstantiated for price-lag models under this data regime. This finding does not claim that 70% is mathematically impossible for every market strategy in existence; it proves that within this data regime, price lags cannot exceed random walk by more than ~2-3%.

---

## 7. Minimal Useful Architecture and Component Classification

To prevent architectural bloat while preserving working code, each major component is classified:

| Architecture Component | Runtime Classification | Operational Necessity | Disposition / Recommendation |
|---|---|---|---|
| `HAR-RS-DOW-v1.0` | **RUNTIME_ESSENTIAL** | Authorized production volatility regressor and C2 risk envelope | **PRESERVE**: Core production model serving `/api/terminal/live`. |
| `engine/har_rs_dow_features.py` | **RUNTIME_ESSENTIAL** | Production feature extractor from `ohlcv.parquet` | **PRESERVE**: Clean point-in-time feature extraction. |
| `directional-gbm-4lag-v1` | **RESEARCH_BENCHMARK** | Offline directional baseline for controlled experiments | **PRESERVE**: Retain in `models/registry/research/` as reference standard. |
| `LogisticRegression (4 Lags)` | **RESEARCH_CHALLENGER** | Lightweight linear benchmark | **PRESERVE**: Fast challenger for offline evaluation. |
| `TFT (Temporal Fusion Transformer)` | **EXPERIMENTAL_DEFERRED** | Deep learning multi-horizon model | **PRESERVE WITHOUT DELETION**: Heavy dependencies. Do not delete in Stage 12; document safe removal procedure if pruned later. |
| `Arena Engine` (`routes_arena.py`) | **RESEARCH_ANALYTICS** | Multi-model evaluation tournament framework | **PRESERVE**: Retain for offline strategy research. |
| `Order-Book (OFI / LOB) Feeds` | **CONDITIONALLY_DEFERRED** | Microstructure flow imbalance | **DEFER**: Missing multiyear historical depth. Classify as unvalidated pending data acquisition. |
| `Funding Rate Feeds` | **CONDITIONALLY_DEFERRED** | Derivatives positioning signal | **DEFER**: Local dataset has only 375 hourly rows. Unvalidated pending longer history. |
| `v3.0.0-excursion-ridge-conformal` | **ARCHIVED_CANDIDATE** | Legacy 24-hour range model | **PRESERVE ARCHIVED**: Fails closed with `BLOCKED_PROVENANCE_UNVERIFIED`. |

---

## 8. Audit of the `iv7d.parquet` Dependency and Safeguards

An audit of `validation/startup_gate.py` and `research/verify_freeze_manifest.py` confirmed that:
1. `data/raw/ohlcv.parquet` and `experiments/results/freeze/har_rs_dow_v1.joblib` are **hard runtime dependencies**. If either is missing or has a corrupted SHA-256 hash, startup fails closed immediately.
2. `data/raw/iv7d.parquet` is a **historical research benchmark** (evaluated in VOL-EDGE-01 trials M4/M5/M6). It is NOT required for `HAR-RS-DOW-v1.0` runtime inference.
3. In `research/verify_freeze_manifest.py`, Check 5 separates runtime inputs (Check 5A) from research benchmarks (Check 5B). If `iv7d.parquet` is absent, an informational warning is logged, but production startup is not blocked.
4. If `--strict` or `--audit-all` is passed, missing research benchmarks fail closed, ensuring reproducibility for full historical audits.

---

## 9. Automated Regression Testing Summary

Testing was conducted using `.venv_win\Scripts\pytest.exe`. All 58 multi-stage regression tests passed:

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Projects\BTCognitive\BTCognitive
configfile: pytest.ini

tests/test_stage5_dependency_and_model_identity.py        ......... [ 15%]
tests/test_stage6_feature_parity_and_runtime_verification.py ..... [ 24%]
tests/test_stage7_regime_experiments.py                   .....     [ 32%]
tests/test_stage8_data_experiments.py                     .....     [ 41%]
tests/test_stage9_integrity_and_next_experiment.py        .......   [ 53%]
tests/test_stage10_shadow_validation.py                   ...........[ 72%]
tests/test_stage11_forward_validation.py                  ........  [ 86%]
tests/test_stage12_causal_validation.py                   ........  [100%]

======================= 58 passed, 1 warning in 22.44s ========================
```

---

## 10. Audit Findings and Action Matrix

| Priority | Finding | Evidence | Change Made or Recommended | Acceptance Test | Status |
|---|---|---|---|---|---|
| **P0** | **Temporal Lookahead in Conformal Calibration** | `res_all` in `run_uncertainty_03_holdout_trial.py` leaked contemporaneous 168h holdout residuals into rolling std. | Implemented strictly causal delayed-resolution calibration in `stage12_causal_conformal_engine.py` and `routes_terminal.py`. True holdout coverage is **84.89%** (not 92.36%). | `test_strictly_causal_conformal_calibration_metrics`, `test_causal_invariance_property` | **COMPLETED** |
| **P0** | **Premature Forward Frontier Claim** | Stage 11 claimed `2026-09-01T06:00:00Z` frontier, but collector was created on 2026-10-16. | Reclassified Sept 1 to Oct 16 as `HISTORICAL_DATA_GAP_UNVERIFIED`. Fixed true prospective frontier to **October 16, 2026 at 10:45:00 UTC** in `stage12_prospective_manifest.json`. | `test_prospective_manifest_and_frontier_chronology` | **COMPLETED** |
| **P1** | **Trading-Cost Unit Ambiguity** | Stage 6 reported per active bar; Stage 11 mixed hourly transitions with 4h/24h forward returns. | Reconciled continuous per-bar vs isolated per-trade units. Proved negative net returns across all horizons (-14.90 bps/trade on 1h; -13.61 bps on 4h; -27.13 bps on 24h). | `test_deterministic_trading_cost_accounting` | **COMPLETED** |
| **P1** | **Overstated Statistical Claims** | Feature ablations had CIs crossing zero and non-significant p-values. | Corrected interpretations: complex models/indicators have **not demonstrated reliable predictive improvement**. Retain 53.36% upper bound reality check. | `test_stage6_statistical_interpretations_reconciliation` | **COMPLETED** |
| **P2** | **Target & Horizon Semantic Consistency** | Active model target is 168h annualized variance, not 24h excursion. | Aligned model card, terminal route, and registry to explicitly state `rv7d_var_ann` and zero directional capability. | `test_active_production_model_target_and_units`, `test_terminal_live_route_causal_calibration` | **COMPLETED** |
| **P2** | **Full Multi-Stage Regression Integrity** | System requires continuous verification across all historical stages. | Created `tests/test_stage12_causal_validation.py` (8/8 passed; 58/58 multi-stage suite passed in 22.44s). | `pytest tests/test_stage*.py` (58 passed, 0 failures) | **COMPLETED** |
