# BTCognitive V34.0 — Quantitative Research Completion Gate Final Report

**Mission ID:** V34.0-COMPLETION-GATE  
**Role:** Senior Quantitative Research Lead  
**Date:** November 3, 2026 (Executed 2026-11-03 UTC)  
**Repository Branch:** `main`  
**Preserved Baseline Commit:** `25d483f4c3646661b57311de9d0b53d2be881adb` (`ahead 1` vs `origin/main`)  
**Operating Mode:** BTCUSD-only, Offline Research, Fail-Closed  
**Live Trading Execution:** Strictly `DISABLED`  
**Model Authorization Status:** `OFFLINE_RESEARCH_ONLY`  

---

## Executive Summary

This report establishes the final quantitative research findings for BTCognitive Milestone **V34.0**, reconciling the empirical evidence across Bitstamp BTC/USD data expansion, multi-horizon realized volatility models, C2 conformal prediction calibration limits, high-timeframe (HTF) strategy validation, and test suite health.

In strict adherence to the BTCognitive Prime Directive and peer-reviewed econometrics standards, research models are evaluated out-of-sample under loss-coherent scoring rules (QLIKE) and dependence-aware hypothesis testing (Harvey–Leybourne–Newbold 1997). Software implementation health is strictly decoupled from quantitative performance claims: passing unit tests does not imply empirical trading edge or universal risk coverage.

### Key Conclusions:
1. **Data Provenance & Continuous Pagination:** Verified the newly retrieved **4,000-candle Bitstamp hourly dataset** (spanning 166 continuous days from May 20, 2026 to November 2, 2026). Proved exact 3,600.0-second continuity across all page boundaries with **0 gaps and 0 duplicates**. The original 1,000-candle baseline dataset and historical datasets remain 100% bitwise invariant.
2. **Volatility Forecasts (Workstream B):**
   - **1-Day (24h) Horizon:** `HAR-RS-DOW` (Puke & Schweikert, 2026) demonstrated statistically significant out-of-sample QLIKE reduction over Persistence ($t = 12.94, p < 0.0001$) and Standard HAR ($t = 6.06, p < 0.0001$).
   - **7-Day (168h) Horizon:** Standard HAR (Corsi, 2009) outperformed HAR-RS-DOW (QLIKE 0.0257 vs 0.0276, $t = -1.58, p = 0.94$). Semivariance and day-of-week terms lose predictive power as horizons expand.
   - **22-Day (528h) Horizon:** Regime-switching challenger achieved lowest QLIKE (0.0102).
3. **C2 Conformal Calibration (Workstream C):** The 1,720-bar requirement was mathematically deconstructed into $720\text{h warmup} + 1,000\text{h calibration pool}$. Evaluated on Bitstamp data, C2 conformal prediction failed empirical coverage guarantees (**78.02% coverage at nominal 90%**), suffering from the **Delayed Feedback Trap** (Gibbs & Candes, 2021). Effective sample size collapsed to $N_{\text{eff}} = 14.7$. C2 remains strictly uncalibrated on Bitstamp.
4. **HTF Strategy (Workstream D):** Backtest across 999 4h bars produced positive gross expectancy (+149.52 bps) and positive net expectancy (+79.52 bps under Bitstamp 70 bps friction), but generated only **7 closed trades** ($N=7$). This sample is statistically underpowered ($N \ll 30$, Wilson 95% CI on win rate $[15.8\%, 75.0\%]$).
5. **Regression Verification:** Full core regression suite (39 tests) and unified test runner (118 tests) confirmed 100% passed in completed subprocesses.
6. **Final Governed Verdict:** **`DATA_INSUFFICIENT`** (with **`VALIDATION_FAILED`** for C2 Conformal Prediction and **`RESEARCH_INCONCLUSIVE`** for HTF Strategy Edge).

---

## 1. Retrieved Data Verification & Pagination Proof (Workstream A)

### A. Dataset Attributes

| Attribute | Verified Value | Verification Method | Audit State |
| :--- | :--- | :--- | :--- |
| **File Location** | `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet` | Filesystem check | Separate versioned file |
| **Provenance Sidecar** | `data/providers/bitstamp/BTCUSD_1h_v34_expanded_provenance.json` | JSON format check | Validated |
| **Source Symbol** | `BTC/USD` (`btcusd` spot) | In-dataframe metadata | Pure Bitstamp spot |
| **Step / Timeframe** | 3,600 seconds (1 hour) | Delta verification | Uniform 1-hour step |
| **Row Count** | Exactly **4,000 candles** | Parquet metadata | Complete |
| **First Timestamp** | `2026-05-20T02:00:00+00:00` | Minimum timestamp | Chronological |
| **Last Timestamp** | `2026-11-02T17:00:00+00:00` | Maximum timestamp | Closed at 18:00 UTC |
| **Incomplete Candle Handling**| The forming bar (`18:00+ UTC`) is strictly excluded | `(ts + 3600) <= retrieval_epoch` | Excluded |
| **Exact SHA-256** | `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` | Direct hash audit | Verified authentic |
| **Duplicate Timestamps** | Exactly **0** | `df['timestamp'].duplicated().sum()` | Zero duplicates |
| **Interval Gaps** | Exactly **0** | `(diffs != 3600).sum()` | Zero gaps |

### B. Pagination Architecture & Official Bitstamp Behavior
Bitstamp documentation notes:
- Endpoint: `GET https://www.bitstamp.net/api/v2/ohlc/{currency_pair}/`
- Parameters: `step`, `limit` (max 1000), `start`, `end`.
- Documentation caveat: When both `start` and `end` are provided, `end` takes precedence and the query returns candles preceding `end`.
- **Implementation Design:** To prevent the `end` precedence conflict and ensure forward monotonic retrieval, our pagination architecture in [`scripts/research/fetch_bitstamp_expanded_history.py`](file:///C:/Projects/BTCognitive/BTCognitive/scripts/research/fetch_bitstamp_expanded_history.py) supplies **only `start` and `limit=1000`** (omitting `end`).
- **Hour Boundary Alignment:** The `start` parameter is strictly floored to an exact 3,600-second boundary (`start % 3600 == 0`). Non-aligned timestamps are rejected by Bitstamp WAF.
- **Pacing:** Each page request is spaced by 3.5 seconds to respect Imperva Incapsula rate limits.

### C. Mathematical Continuity Proof Between Pages
The 4,000-candle dataset was assembled across 4 distinct pagination requests of 1,000 bars each:
- **Page 1 (Bars 0 to 999):** `2026-05-20T02:00:00Z` to `2026-06-30T17:00:00Z`
- **Page 2 (Bars 1,000 to 1,999):** `2026-06-30T18:00:00Z` to `2026-08-11T09:00:00Z`
- **Page 3 (Bars 2,000 to 2,999):** `2026-08-11T10:00:00Z` to `2026-09-22T01:00:00Z`
- **Page 4 (Bars 3,000 to 3,999):** `2026-09-22T02:00:00Z` to `2026-11-02T17:00:00Z`

Audit of the exact page boundaries:
- **Boundary 1 (Page 1 $\rightarrow$ Page 2):**
  - Index 999 Close: `2026-06-30T17:00:00+00:00` (Close: $62,718.50)
  - Index 1,000 Open: `2026-06-30T18:00:00+00:00` (Open: $62,718.50)
  - Inter-page delta: **$3,600.0\text{ seconds}$** (Exact continuity).
- **Boundary 2 (Page 2 $\rightarrow$ Page 3):**
  - Index 1,999 Close: `2026-08-11T09:00:00+00:00` (Close: $59,342.10)
  - Index 2,000 Open: `2026-08-11T10:00:00+00:00` (Open: $59,342.10)
  - Inter-page delta: **$3,600.0\text{ seconds}$** (Exact continuity).
- **Boundary 3 (Page 3 $\rightarrow$ Page 4):**
  - Index 2,999 Close: `2026-09-22T01:00:00+00:00` (Close: $63,550.00)
  - Index 3,000 Open: `2026-09-22T02:00:00+00:00` (Open: $63,550.00)
  - Inter-page delta: **$3,600.0\text{ seconds}$** (Exact continuity).

### D. Protected Historical Dataset Invariance
- `data/providers/bitstamp/BTCUSD_1h.parquet`: `b7262a647d7761dc426df8227170170827950a1ba173c488d8c8955cd3bf7107` (**100% BITWISE INVARIANT**).
- `data/raw/ohlcv.parquet`: `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` (**100% INVARIANT**).
- `data/raw/coinbase_15m.parquet`: `bfd4295f563141c66924b5a91593bb491cd1f4706b4e95c526fc46e693ff2ac4` (**100% INVARIANT**).

---

## 2. Volatility Forecast Audit & Out-of-Sample Comparison (Workstream B)

All models were evaluated on identical chronological out-of-sample holdout partitions (60% Train / 40% Holdout).

### A. Econometric Metrics & Loss Formulation
- **Target Realized Variance:** $y_t = RV_{t, H}^{\text{ann}} = \frac{8760}{H} \sum_{k=1}^H r_{t+k}^2$.
- **QLIKE Loss (Patton 2011; Puke & Schweikert 2026):**
  $$\text{QLIKE}(y_t, \widehat{y}_t) = \frac{y_t}{\widehat{y}_t} - \ln\left(\frac{y_t}{\widehat{y}_t}\right) - 1$$
- **Hypothesis Testing:** Paired loss differentials $d_t = \text{Loss}_{\text{base}} - \text{Loss}_{\text{chall}}$ evaluated using Diebold–Mariano with Harvey–Leybourne–Newbold (1997) finite-sample correction and Student's $t_{T-1}$ distribution. Newey–West lag bandwidth set to $h-1$.

---

### B. Horizon 1: 1-Day ($H = 24\text{h}$) Out-of-Sample Results
- **Target:** 24-hour annualized forward realized variance ($RV_{24h}^{\text{ann}}$)
- **Observations:** $N_{\text{total}} = 3,255$ bars (Train = 1,953, Holdout = 1,302)
- **Evaluation Period:** `2026-09-08T11:00:00Z` to `2026-11-01T16:00:00Z` (54 days)

| Model Candidate | QLIKE | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.9221 | 0.1395 | 0.1002 | 1.5544 | 0.0026 | — | $t = -11.07\ (p=1.00)$ |
| **EWMA ($\lambda=0.94$)** | 0.5533 | 0.1246 | 0.0899 | 1.2292 | 0.0002 | $t = 10.36\ (p < 0.0001)^*$ | $t = -5.69\ (p=1.00)$ |
| **Standard HAR (Corsi)** | 0.4827 | 0.1052 | 0.0699 | 0.9309 | 0.0013 | $t = 11.07\ (p < 0.0001)^*$ | — |
| **HAR-RS-DOW (2026)** | **0.3874** | **0.0979** | **0.0622** | **0.6206** | **0.0631** | **$t = 12.94\ (p < 0.0001)^*$** | **$t = 6.06\ (p < 0.0001)^*$** |
| **Regime-Switching** | 0.5264 | 0.1080 | 0.0736 | 0.9884 | 0.0048 | $t = 9.61\ (p < 0.0001)^*$ | $t = -8.94\ (p=1.00)$ |

*Finding:* At 24 hours, **HAR-RS-DOW is significantly superior**, reducing QLIKE by 19.7% over Standard HAR and 58.0% over Persistence with $p < 0.0001$.

---

### C. Horizon 2: 7-Day ($H = 168\text{h}$) Out-of-Sample Results
- **Target:** 7-day annualized forward realized variance ($RV_{168h}^{\text{ann}}$)
- **Observations:** $N_{\text{total}} = 3,111$ bars (Train = 1,866, Holdout = 1,245)
- **Evaluation Period:** `2026-09-04T20:00:00Z` to `2026-10-26T00:00:00Z` (51 days)

| Model Candidate | QLIKE | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.0519 | 0.0366 | 0.0297 | 0.1023 | 0.0889 | — | $t = -7.30\ (p=1.00)$ |
| **EWMA ($\lambda=0.94$)** | 0.3014 | 0.0760 | 0.0578 | 0.4719 | 0.0126 | $t = -7.69\ (p=1.00)$ | $t = -8.51\ (p=1.00)$ |
| **Standard HAR (Corsi)** | **0.0257** | **0.0256** | 0.0205 | **0.0525** | 0.0002 | **$t = 7.30\ (p < 0.0001)^*$** | — |
| **HAR-RS-DOW (2026)** | 0.0276 | 0.0269 | **0.0204** | 0.0563 | 0.0020 | $t = 6.07\ (p < 0.0001)^*$ | $t = -1.58\ (p=0.94)$ |
| **Regime-Switching** | 0.0292 | 0.0277 | 0.0219 | 0.0601 | 0.0368 | $t = 6.17\ (p < 0.0001)^*$ | $t = -4.32\ (p=1.00)$ |

*Finding:* At 7 days, **HAR-RS-DOW fails to beat Standard HAR** ($t = -1.58, p = 0.94$). Semivariance decomposition does not improve out-of-sample accuracy at weekly horizons. Standard HAR is the parsimonious winner.

---

### D. Horizon 3: 22-Day ($H = 528\text{h}$) Out-of-Sample Results
- **Target:** 22-day annualized forward realized variance ($RV_{528h}^{\text{ann}}$)
- **Observations:** $N_{\text{total}} = 2,751$ bars (Train = 1,650, Holdout = 1,101)
- **Evaluation Period:** `2026-08-26T20:00:00Z` to `2026-10-11T00:00:00Z` (46 days)

| Model Candidate | QLIKE | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.0363 | 0.0413 | 0.0323 | 0.0827 | 0.3396 | — | $t = -2.36\ (p=0.99)$ |
| **EWMA ($\lambda=0.94$)** | 0.2813 | 0.0762 | 0.0560 | 0.4382 | 0.0090 | $t = -7.21\ (p=1.00)$ | $t = -8.01\ (p=1.00)$ |
| **Standard HAR (Corsi)** | 0.0198 | 0.0244 | 0.0203 | 0.0434 | 0.4465 | $t = 2.36\ (p=0.009)^*$ | — |
| **HAR-RS-DOW (2026)** | 0.0205 | 0.0250 | 0.0207 | 0.0448 | 0.4111 | $t = 2.26\ (p=0.012)^*$ | $t = -1.34\ (p=0.91)$ |
| **Regime-Switching** | **0.0102** | **0.0168** | **0.0139** | **0.0219** | 0.0512 | **$t = 4.27\ (p < 0.0001)^*$** | **$t = 4.89\ (p < 0.0001)^*$** |

*Finding:* At 22 days, the **Regime-Switching Challenger** achieves the lowest QLIKE (0.0102), but the effective number of independent 22-day blocks in a 46-day evaluation window is only $\approx 2.1$ blocks. Consequently, this horizon is marked **`INCONCLUSIVE`** due to overlapping block dependence.

---

## 3. C2 Conformal Calibration Requirements & Deconstruction (Workstream C)

### A. Architectural Origin of the 1,720-Bar Requirement
An audit of all codebase references to minimum history confirms that 1,720 bars represents four distinct causal stages:
1. **Model Initialization / Warmup ($720\text{ bars} = 30\text{ days}$):**
   - Required for `rv30d_var_ann` feature calculation (`min_periods=720`).
   - Required for localized residual standard deviation: $\widehat{\sigma}_{\text{ewm}, t} = \text{EWM}(\text{span}=720, \text{min\_periods}=72)$.
2. **Conformal Calibration Pool ($1,000\text{ bars}$):**
   - To mitigate severe hourly autocorrelation, the residual pool is subsampled every 24 hours ($1000 / 24 \approx 41\text{ daily residual points}$).
3. **Delayed Resolution Buffer ($168\text{ bars} = 7\text{ days}$):**
   - For a 7-day variance forecast issued at $t$, the true realized outcome $y_t$ is unobservable until $t + 168\text{h}$. Residuals cannot enter the calibration pool earlier without lookahead leakage.
4. **Structural Pre-Evaluation Hurdle:**
   $$\text{Pre-Evaluation Minimum} = \text{Warmup (720)} + \text{Calibration Pool (1000)} = 1,720\text{ bars}$$
   Adding the 168-hour delay means that independent holdout evaluation cannot begin until bar $1,720 + 168 = 1,888$.

```
[--- 720h Warmup ---][--------- 1,000h Calibration Pool ---------][-- 168h Delay --][--- Holdout Testing ---]
0                   720                                         1720               1888                      4000
```

### B. Bitstamp-Specific Calibration Results

Evaluated across 1,943 out-of-sample hourly observations on Bitstamp data:
- **Nominal 90% Target:** Empirical coverage is **78.02%** (Wilson 95% CI: $[76.13\%, 79.81\%]$). Coverage deficit = **-11.98%**.
- **Nominal 95% Target:** Empirical coverage is **80.91%** (Wilson 95% CI: $[79.10\%, 82.59\%]$). Coverage deficit = **-14.09%**.
- **First-Order Autocorrelation:** $\rho_1 = 0.9850$.
- **Effective Sample Size:** $N_{\text{eff}} = 1,943 \times \frac{1 - 0.985}{1 + 0.985} = \mathbf{14.7\text{ independent observations}}$.
- **Coverage in Extreme Tail Shocks (Top 10% Volatility):** Only 82.98% (undercoverage during market turbulence).

### C. Theoretical Qualification & Governed Rule
As proven by Gibbs & Candes (2021) and Barber et al. (2023), exact finite-sample conditional coverage is mathematically impossible under non-exchangeable delayed feedback. Volatility regime shifts create systematic lags in quantile adjustment (**The Delayed Feedback Trap**).
- **Governed Rule:** C2 conformal prediction **FAILS** calibration on Bitstamp. C2 must remain strictly unavailable in production. No 90% coverage claim may be made.

---

## 4. HTF Strategy Reconciliation (Workstream D)

### A. Frozen Strategy Reproduction
The frozen `HTF_RANGE_EXPANSION_BREAKOUT` was simulated on the 4,000 Bitstamp hourly candles aggregated into completed 4h bars:
- **Total Completed 4h Candles:** 999 bars (166 calendar days).
- **Eligible Setups Detected:** 47.
- **Confirmed Breakout Triggers:** 17.
- **Completed Trades:** Exactly **7 closed trades**.
- **Outcomes:** 3 TP hits (42.86%), 3 SL hits (42.86%), 1 Timeout (14.28%).
- **Mean Holding Duration:** 10.1 4h bars (40.4 hours).
- **Mean MFE (Favorable Excursion):** +348.9 bps.
- **Mean MAE (Adverse Excursion):** 125.3 bps.
- **Gross Expectancy:** +149.52 bps.

### B. Cost Sensitivity & Execution Scenario

| Friction Scenario | Roundtrip Fee | Net Expectancy | Profit Factor | Max Drawdown | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Gross Theoretical** | 0.0 bps | +149.52 bps | 3.57 | 247.0 bps | Profitable |
| **Binance VIP0 Baseline** | 26.0 bps | +123.52 bps | 2.78 | 299.0 bps | Baseline Reference |
| **Bitstamp Active Tier** | 50.0 bps | +99.52 bps | 2.25 | 347.0 bps | Profitable |
| **Bitstamp Base Retail** | **70.0 bps** | **+79.52 bps** | **1.90** | **387.0 bps** | **Survives Retail Fee** |
| **Coinbase Retail** | 87.0 bps | +62.52 bps | 1.65 | 421.0 bps | Profitable |
| **Volatile Market Stress** | 100.0 bps | +49.52 bps | 1.49 | 447.0 bps | Profitable |

### C. Challenger Comparison
- `HTF_RANGE_EXPANSION_BREAKOUT`: Net +79.52 bps at Bitstamp retail friction (PF = 1.90).
- `BUY_AND_HOLD_BASELINE`: +23.70 bps gross return across the same 166-day window.

### D. Statistical Limitation: Severe Sample Underpowering
Although the strategy generated +79.52 bps net expectancy, **the sample size of 7 trades ($N=7$) cannot reject the null hypothesis of zero edge**:
- Wilson 95% CI on win rate: $[15.82\%, 74.95\%]$.
- A minimum of $N \ge 30$ to $N \ge 100$ independent trades is required by econometric standards (Tashman 2000; Harvey et al. 1997).
- **Verdict:** Strategy edge is **STATISTICALLY INCONCLUSIVE** due to insufficient sample size.

---

## 5. Regression Verification & Task Audit (Workstream 5)

The previous handover background test processes were audited to verify completion:
- **Core Test Suite Task:** `1ae7aeff-968f-4a42-b599-198389cab42b/task-11032`
  - Exact Command: `cd BTCognitive; .venv_win\Scripts\pytest.exe tests/test_v33_8_failure_injection.py tests/test_v33_7_bitstamp_integration.py tests/test_v33_5_analysis_reliability.py tests/test_v33_4m_htf_analysis.py -q`
  - Exit Code: **0**
  - Passed Tests: **39**
  - Failed Tests: **0**
  - Skipped Tests: **0**
  - Duration: **44.98 seconds**
- **Unified 118-Node Test Runner:** `task-10823`
  - Exact Command: `.venv_win\Scripts\pytest.exe tests/test_v33_8_failure_injection.py tests/test_v33_7_bitstamp_integration.py tests/test_v33_5_analysis_reliability.py tests/test_v33_4m_htf_analysis.py tests/test_v33_4h_backtest_isolation.py tests/test_v33_4g_presentation_integrity.py tests/test_v33_4f_decision_stability.py tests/test_v33_4l_historical_evidence.py tests/test_v33_1_entry_and_analysis_decoupling.py tests/test_v32_49_scenario_qa.py -v`
  - Exit Code: **0**
  - Passed Tests: **118**
  - Failed Tests: **0**
  - Duration: **43.26 seconds**

---

## 6. Inventory of Failed Experiments & Negative Evidence

1. **Unpaced API Pagination:** Direct requests without inter-page delays triggered Incapsula WAF 503 errors. Resolved by enforcing 3.5s spacing.
2. **HAR-RS-DOW at 7-Day Horizon:** Failed to outperform Standard HAR ($t = -1.58, p = 0.94$). Semivariance decomposition is ineffective at 7-day horizons on Bitstamp data.
3. **C2 Conformal Calibration:** Failed empirical coverage targets (78.02% vs 90.0% nominal), invalidating unconditional coverage claims.
4. **EWMA ($\lambda=0.94$):** Grossly inferior across all horizons (QLIKE 0.28 to 0.55), failing as a crypto volatility model.
5. **HTF Strategy Sample Size:** 166 calendar days produced only 7 trades, failing sample sufficiency gates.

---

## 7. Recommended Next Research Steps

1. **Ingest Historical 5-Minute Bitstamp Dataset:** Retrieve 2 full years (2024–2026) of 5-minute bars ($\sim 210,000$ bars) to compute authentic intraday realized variance, semivariance, and jump components.
2. **Multi-Year 1h History Expansion:** Expand 1h history back to 2021 ($\sim 45,000$ bars) across full market regimes to accumulate $N \ge 100$ completed HTF trades.
3. **Adaptive Conformal Inference (ACI):** Investigate online gradient step-size updates (Gibbs & Candes 2021) to counteract the Delayed Feedback Trap.

---

## 8. Final Governed Verdict

In accordance with Section 7 instructions, the final governed determination is:

# **`DATA_INSUFFICIENT`**

### Detailed Category Adjudication:
- **Primary Mission Verdict:** **`DATA_INSUFFICIENT`** (166 days / 4,000 bars is insufficient to generate a statistically powered trade sample for strategy validation or multi-regime risk testing).
- **Conformal Uncertainty:** **`VALIDATION_FAILED`** (C2 empirical coverage 78.02% vs 90% nominal).
- **7-Day Volatility Forecasting:** **`RESEARCH_INCONCLUSIVE`** (HAR-RS-DOW failed to beat Standard HAR).
- **1-Day Volatility Forecasting:** **`RISK_MODEL_IMPROVEMENT_DEMONSTRATED`** (HAR-RS-DOW achieved QLIKE 0.3874 vs 0.4827 Standard HAR, $p < 0.0001$).
- **HTF Strategy Edge:** **`RESEARCH_INCONCLUSIVE`** (Sample size $N=7$ underpowered).
- **Prospective Governance:** **`FROZEN_PENDING_ACTIVATION`** (Process count = 0).
- **Trading Authorization:** **`OFFLINE_RESEARCH_ONLY`** (Live trading strictly `DISABLED`).

---
*Report certified by Senior Quantitative Research Lead.*

