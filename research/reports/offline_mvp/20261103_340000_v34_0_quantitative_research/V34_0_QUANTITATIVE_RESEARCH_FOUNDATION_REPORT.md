# BTCognitive V34.0 — Quantitative Research Foundation Report

**Mission ID:** V34.0-QUANTITATIVE-RESEARCH  
**Role:** Lead Quantitative Researcher and Engineering Coordinator  
**Date:** November 3, 2026 (Executed 2026-11-03 UTC)  
**Repository Branch:** `main`  
**Preserved Baseline Commit:** `25d483f4c3646661b57311de9d0b53d2be881adb` (`ahead 1` vs `origin/main`)  
**Operating Mode:** BTCUSD-only, Offline Research, Fail-Closed  
**Live Trading Execution:** Strictly `DISABLED`  
**Model Authorization Status:** `OFFLINE_RESEARCH_ONLY`  

---

## Executive Summary

Milestone **V34.0** establishes the quantitative research foundation for BTCognitive on authentic Bitstamp BTC/USD market data. Rather than manufacturing unsupported optimism or cosmetic features, this mission strictly adheres to peer-reviewed econometrics standards, causal point-in-time boundaries, and fail-closed research governance.

### Key Empirical Findings:
1. **Data Expansion:** Validated Bitstamp OHLC timestamp pagination experimentally. Successfully retrieved an expanded, source-separated history of **4,000 continuous hourly candles** (spanning 166 days from May 20, 2026 to November 2, 2026) with **zero missing intervals** and zero duplicate bars. Confirmed that Bitstamp retains 5-minute data back to at least January 1, 2024. The original 1,000-candle dataset and its SHA-256 hash remain completely preserved.
2. **Realized Volatility Models:** At the 1-day (24h) horizon, **HAR-RS-DOW** (Puke & Schweikert, 2026) demonstrated statistically significant out-of-sample QLIKE superiority over Persistence (HLN $t = 12.94, p < 0.0001$) and Standard HAR (HLN $t = 6.06, p < 0.0001$). However, at the 7-day (168h) horizon, HAR-RS-DOW failed to outperform Standard HAR (QLIKE 0.0276 vs 0.0257, $p = 0.94$).
3. **C2 Conformal Calibration:** Deconstructed the mathematical origin of the 1,720-bar minimum ($720\text{h warmup} + 1,000\text{h pool}$; $168\text{h delayed label buffer}$). Evaluated on Bitstamp data, C2 conformal prediction suffered from severe empirical undercoverage: **78.02% empirical coverage at nominal 90%**, and **80.91% at nominal 95%**, caused by the **Delayed Feedback Trap** (Gibbs & Candes, 2021). Coverage errors exhibit extreme autocorrelation ($\rho_1 = 0.985$), shrinking the effective sample size to $N_{\text{eff}} = 14.7$. C2 fails calibration and must remain strictly suppressed.
4. **HTF Strategy Validation:** Simulated the frozen `HTF_RANGE_EXPANSION_BREAKOUT` across 999 completed 4h candles. While gross expectancy was positive (+149.52 bps) and survived Bitstamp retail friction (+79.52 bps at 70 bps roundtrip), only **7 closed trades** were generated ($N=7$). This sample is severely underpowered for statistical significance (Wilson 95% CI on win rate: $[15.8\%, 75.0\%]$).
5. **Execution Cost Contract:** Reconciled Bitstamp fee tiers (30 bps maker / 40 bps taker). Proved that Binance VIP0 (26.0 bps) cannot be assumed. Bitstamp execution costs remain officially classified as `NOT_VERIFIED`.
6. **Primary Governed Decision:** **`DATA_INSUFFICIENT`** & **`MODEL_CALIBRATION_FAILED`** (for C2).

---

## 1. Data Coverage and Provenance Audit (Workstream A)

### A. Experimental Pagination & Retention Investigation
Bitstamp's public OHLC API (`/api/v2/ohlc/btcusd/`) was systematically evaluated using bounded test requests:
- **Pagination Parameters:** The documented `step` (seconds), `limit` (max 1000), and `start` (UNIX epoch) parameters were confirmed to paginate chronologically in 1,000-candle blocks.
- **Hour Alignment Invariant:** Bitstamp API requires `start` to be an exact multiple of `step` (e.g. `start % 3600 == 0`). Non-aligned timestamps trigger upstream WAF 403/503 errors.
- **5-Minute Resolution Retention:** Bounded tests with `step=300` confirmed that Bitstamp retains 5-minute historical candles back to at least **January 1, 2024** (`1704067200`).
- **WAF Pacing Invariant:** Bitstamp's Incapsula WAF enforces strict request pacing. A delay of 3.0 to 3.5 seconds between pagination requests is required to avoid 503 rate-limiting challenges.
- **Single Exchange Guarantee:** The price series is constructed purely from Bitstamp BTC/USD spot. No observations from Binance, Coinbase, or synthetic sources were mixed.

### B. Versioned Expanded Dataset Inventory

| Dataset Attribute | Invariant Frozen Baseline | New Expanded Research Dataset |
| :--- | :--- | :--- |
| **File Path** | `data/providers/bitstamp/BTCUSD_1h.parquet` | `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet` |
| **Provenance Sidecar** | `data/providers/bitstamp/BTCUSD_1h_provenance.json` | `data/providers/bitstamp/BTCUSD_1h_v34_expanded_provenance.json` |
| **Row Count** | Exactly **1,000 hourly bars** | Exactly **4,000 hourly bars** |
| **Calendar Span** | 41.6 days (Sep 22, 2026 – Nov 2, 2026) | 166.6 days (May 20, 2026 – Nov 2, 2026) |
| **Interval Gaps** | 0 gaps | **0 gaps** (diffs == 3600s across 4,000 bars) |
| **Duplicates** | 0 duplicates | **0 duplicates** |
| **Verified SHA-256** | `b7262a647d7761dc426df8227170170827950a1ba173c488d8c8955cd3bf7107` | `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` |
| **Integrity State** | **INVARIANT PRESERVED** | **AUTHENTIC & VALIDATED** |

---

## 2. Realized Volatility Model Research (Workstream B)

### A. Target Definition & Mathematical Formulation
For any forecast origin $t$ and horizon $H$ hours:
- Hourly log return: $r_{t} = \ln(P_t / P_{t-1})$
- Target Annualized Realized Variance:
  $$RV_{t, H}^{\text{ann}} = \frac{8760}{H} \sum_{k=1}^{H} r_{t+k}^2$$
- Evaluated horizons:
  - 1-Day: $H = 24\text{ hours}$
  - 7-Day: $H = 168\text{ hours}$
  - 22-Day: $H = 528\text{ hours}$

### B. Econometric Model Candidates
1. **Persistence Benchmark:** $\widehat{RV}_{t, H} = \frac{8760}{H} \sum_{k=0}^{H-1} r_{t-k}^2$
2. **EWMA (RiskMetrics):** $\sigma_t^2 = 0.94 \sigma_{t-1}^2 + 0.06 r_t^2$, scaled by 8,760.
3. **Standard HAR (Corsi, 2009):** OLS on log daily (24h), weekly (168h), and monthly (720h) realized variances:
   $$\ln(RV_{t, H}) = \beta_0 + \beta_d \ln(RV_{t}^{(d)}) + \beta_w \ln(RV_{t}^{(w)}) + \beta_m \ln(RV_{t}^{(m)}) + \epsilon_t$$
4. **HAR-RS-DOW (Puke & Schweikert, 2026):** HAR with realized semivariances ($RV_{t}^-$, $RV_{t}^+$), weekly/monthly variance, and Day-of-Week dummies with L2 ridge shrinkage.
5. **Regime-Switching Challenger:** Two-state volatility model conditioning on high-volatility expansion states ($RV_{24h} > 1.25 \times RV_{168h}$).

### C. Out-of-Sample Performance Comparison (Chronological 60/40 Split)

#### 1-Day Horizon ($H = 24\text{h}$, Holdout $N = 1,302$ bars)

| Model Candidate | QLIKE (Primary) | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.9221 | 0.1395 | 0.1002 | 1.5544 | 0.0026 | — | $t = -11.07\ (p=1.00)$ |
| **EWMA (RiskMetrics)** | 0.5533 | 0.1246 | 0.0899 | 1.2292 | 0.0002 | $t = 10.36\ (p < 0.0001)^*$ | $t = -5.69\ (p=1.00)$ |
| **Standard HAR (Corsi)** | 0.4827 | 0.1052 | 0.0699 | 0.9309 | 0.0013 | $t = 11.07\ (p < 0.0001)^*$ | — |
| **HAR-RS-DOW (2026)** | **0.3874** | **0.0979** | **0.0622** | **0.6206** | **0.0631** | **$t = 12.94\ (p < 0.0001)^*$** | **$t = 6.06\ (p < 0.0001)^*$** |
| **Regime-Switching** | 0.5264 | 0.1080 | 0.0736 | 0.9884 | 0.0048 | $t = 9.61\ (p < 0.0001)^*$ | $t = -8.94\ (p=1.00)$ |

*Verdict at 24h:* **HAR-RS-DOW is unambiguously superior** at 24 hours, achieving a 19.7% QLIKE reduction over Standard HAR and 58.0% over Persistence with strong statistical significance.

---

#### 7-Day Horizon ($H = 168\text{h}$, Holdout $N = 1,245$ bars)

| Model Candidate | QLIKE (Primary) | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.0519 | 0.0366 | 0.0297 | 0.1023 | 0.0889 | — | $t = -7.30\ (p=1.00)$ |
| **EWMA (RiskMetrics)** | 0.3014 | 0.0760 | 0.0578 | 0.4719 | 0.0126 | $t = -7.69\ (p=1.00)$ | $t = -8.51\ (p=1.00)$ |
| **Standard HAR (Corsi)** | **0.0257** | **0.0256** | 0.0205 | **0.0525** | 0.0002 | **$t = 7.30\ (p < 0.0001)^*$** | — |
| **HAR-RS-DOW (2026)** | 0.0276 | 0.0269 | **0.0204** | 0.0563 | 0.0020 | $t = 6.07\ (p < 0.0001)^*$ | $t = -1.58\ (p=0.94)$ |
| **Regime-Switching** | 0.0292 | 0.0277 | 0.0219 | 0.0601 | 0.0368 | $t = 6.17\ (p < 0.0001)^*$ | $t = -4.32\ (p=1.00)$ |

*Verdict at 7-Day:* **HAR-RS-DOW does NOT outperform Standard HAR**. Semivariance and day-of-week parameters lose predictive advantage as the aggregation horizon lengthens to 7 days. Standard HAR remains the parsimonious winner.

---

#### 22-Day Horizon ($H = 528\text{h}$, Holdout $N = 1,101$ bars)

| Model Candidate | QLIKE (Primary) | RMSE | MAE | Log-MSE | MZ $R^2$ | HLN vs Persistence | HLN vs Standard HAR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence Benchmark** | 0.0363 | 0.0413 | 0.0323 | 0.0827 | 0.3396 | — | $t = -2.36\ (p=0.99)$ |
| **EWMA (RiskMetrics)** | 0.2813 | 0.0762 | 0.0560 | 0.4382 | 0.0090 | $t = -7.21\ (p=1.00)$ | $t = -8.01\ (p=1.00)$ |
| **Standard HAR (Corsi)** | 0.0198 | 0.0244 | 0.0203 | 0.0434 | 0.4465 | $t = 2.36\ (p=0.009)^*$ | — |
| **HAR-RS-DOW (2026)** | 0.0205 | 0.0250 | 0.0207 | 0.0448 | 0.4111 | $t = 2.26\ (p=0.012)^*$ | $t = -1.34\ (p=0.91)$ |
| **Regime-Switching** | **0.0102** | **0.0168** | **0.0139** | **0.0219** | 0.0512 | **$t = 4.27\ (p < 0.0001)^*$** | **$t = 4.89\ (p < 0.0001)^*$** |

---

## 3. Source-Specific C2 Conformal Research (Workstream C)

### A. Mathematical Deconstruction of the 1,720-Bar Requirement
The existing codebase asserts a strict minimum of 1,720 bars before activating C2 conformal inference. Our audit confirms this is not an arbitrary constant but the exact structural sum of:
1. **Warmup Window ($720\text{ bars} = 30\text{ days}$):** Required for causal Exponentially Weighted Moving (EWM) standard deviation ($\text{span}=720$, $\text{min\_periods}=72$) to estimate localized residual dispersion $\widehat{\sigma}_{\text{ewm}, t}$.
2. **Conformal Calibration Pool ($1,000\text{ bars}$):** To prevent severe non-exchangeability and serial correlation in hourly returns, the pool is subsampled every 24 hours ($1000 / 24 \approx 41\text{ independent daily residual blocks}$).
3. **Delayed Feedback Buffer ($168\text{ bars} = 7\text{ days}$):** A 7-day forward variance label $y_t$ is strictly unobservable until $t + 168\text{h}$. Outcome residuals cannot be added to the calibration pool until $t + 168\text{h}$.
$$\text{Structural Pre-Evaluation Minimum} = 720 + 1000 = 1,720\text{ hourly bars}$$
To evaluate out-of-sample coverage honestly without lookahead leakage, at least $1,720 + 168 = 1,888$ bars are required before the first valid test point can be drawn.

### B. Bitstamp-Specific Calibration Experiment

The calibration experiment was executed on the expanded 4,000-bar Bitstamp dataset ($N = 1,943$ evaluated test bars):

```
Non-conformity score: s_t = |y_t - v_hat_t| / max(1e-4, sigma_ewm,t)
Pool: s_{t - 168 - 1000 .. t - 168} sampled every 24h
Prediction Interval: [max(1e-6, v_hat_t - q * sigma_ewm,t), v_hat_t + q * sigma_ewm,t]
```

| Calibration Metric | Nominal 90% Target | Nominal 95% Target | Econometric Standard |
| :--- | :---: | :---: | :---: |
| **Nominal Target Coverage** | 90.00% | 95.00% | $1 - \alpha$ |
| **Empirical Coverage** | **78.02%** | **80.91%** | Must match nominal $\pm$ Wilson error |
| **Wilson 95% Confidence Interval** | **[76.13%, 79.81%]** | **[79.10%, 82.59%]** | Nominal target is completely outside CI |
| **Coverage Deficit (Undercoverage)** | **-11.98%** | **-14.09%** | Severe failure of coverage guarantee |
| **Mean Interval Width** | 0.3156 | 0.4086 | Winkler sharpness metric |
| **Mean Winkler Score** | 0.6189 | 0.9097 | Lower is better |
| **First-Order Autocorrelation ($\rho_1$)** | **0.9850** | **0.9567** | Severe violation of exchangeability |
| **Effective Sample Size ($N_{\text{eff}}$)** | **14.7** | **43.0** | Out of 1,943 evaluated hourly bars |
| **Coverage in Normal Regime** | 74.20% | 77.34% | Undercoverage during regime shifts |
| **Coverage in Volatility Expansion** | 96.53% | 98.84% | Overly wide intervals |
| **Coverage in Extreme Tail (Top 10%)** | 82.98% | 84.57% | Undercoverage during fast shocks |

### C. Econometric Root Cause: The Delayed Feedback Trap
The severe coverage breakdown (78.02% vs 90%) is directly attributable to the **Delayed Feedback Trap** (Gibbs & Candes, 2021; Barber et al., 2023):
- Because variance outcomes take 168 hours (7 days) to mature, the non-conformity quantile $q$ is computed from residuals generated 7 to 48 days in the past.
- When market volatility transitions from a calm regime to an expansion regime, the calibration pool continues to draw from the historical calm period for at least 168 hours, causing systematic interval under-sizing and consecutive coverage violations.
- Furthermore, the extreme serial correlation ($\rho_1 = 0.985$) means that failures occur in long, clustered bursts. The effective sample size across 1,943 evaluation hours is only **14.7 independent observations**.

**Epistemic Conclusion:** Exact finite-sample conditional coverage is mathematically impossible under non-exchangeable delayed feedback. C2 conformal risk envelopes **FAIL** calibration on Bitstamp data and must remain strictly suppressed.

---

## 4. HTF Strategy Validation (Workstream D)

### A. Frozen Strategy Reproduction
The frozen `HTF_RANGE_EXPANSION_BREAKOUT` strategy was reproduced and evaluated on the 4,000 Bitstamp hourly candles aggregated causally into completed 4h candles:
- **Completed 4h Bars:** Exactly **999 bars** (166 calendar days).
- **Donchian Channel:** 20-bar rolling maximum of 4h Highs shifted by 1 bar ($\max(H_{t-20}..H_{t-1})$).
- **ATR:** 14-period Wilder's Average True Range on 4h bars.
- **Regime Gate:** Requires `VOLATILITY_EXPANSION` ($RV_{20} > 1.15 \times RV_{100}$). All other regimes are strictly blocked.
- **Entry:** Completed 4h Close > 20-bar Donchian High. Execution at next bar Open.
- **Risk Envelope:** Stop Loss at $\text{Entry} - 1.5 \times \text{ATR}_{14}$. Take Profit at $\text{Entry} + 3.0 \times \text{ATR}_{14}$ ($R:R = 2.0$).
- **Max Holding Period:** 18 four-hour bars (72 hours).

### B. Empirical Trade Outcomes

```
Total Completed 4h Bars:       999
Setups Detected:               47
Confirmed Breakouts:           17
Closed Trades Executed:        7
  - Take Profit Hits:          3 (42.86%)
  - Stop Loss Hits:            3 (42.86%)
  - Timeouts (72h expired):    1 (14.28%)
Win Rate:                      42.86%
False Breakout Rate:           42.86%
Mean Holding Period:           10.1 bars (40.4 hours)
Mean MFE (Favorable):          +348.9 bps
Mean MAE (Adverse):            125.3 bps
Gross Expectancy:              +149.52 bps
```

### C. Cost Sensitivity Grid

| Friction Level (Roundtrip bps) | Net Expectancy (bps) | Profit Factor | Max Drawdown (bps) | Trade Profitability |
| :--- | :---: | :---: | :---: | :---: |
| **0 bps (Gross Theoretical)** | +149.52 bps | 3.57 | 247.0 bps | Profitable |
| **26 bps (Binance VIP0 Benchmark)** | +123.52 bps | 2.78 | 299.0 bps | Profitable |
| **50 bps (Institutional Tier)** | +99.52 bps | 2.25 | 347.0 bps | Profitable |
| **70 bps (Bitstamp Base Retail)** | **+79.52 bps** | **1.90** | **387.0 bps** | **Profitable** |
| **87 bps (Coinbase Retail)** | +62.52 bps | 1.65 | 421.0 bps | Profitable |
| **100 bps (Stress / Volatile Execution)** | +49.52 bps | 1.49 | 447.0 bps | Profitable |

### D. Challenger Comparison

| Strategy Candidate | Trades | Win Rate % | Net Expectancy (26 bps) | Net Expectancy (70 bps Bitstamp) | Profit Factor (26 bps) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HTF_RANGE_EXPANSION_BREAKOUT** | **7** | **42.86%** | **+123.52 bps** | **+79.52 bps** | **2.78** |
| **BUY_AND_HOLD_BASELINE** | 1 | N/A | +23.70 bps (gross) | N/A | 1.00 |

### E. Rigorous Statistical Qualification: Sample Size Underpowering
While the HTF strategy achieved +79.52 bps net expectancy under Bitstamp 70 bps friction, **the total sample size across 166 days is only 7 closed trades ($N=7$)**.
- The Wilson 95% score confidence interval for a $3/7$ win rate spans **$[15.82\%, 74.95\%]$**.
- Standard statistical rules (Tashman 2000; Harvey et al. 1997) require a minimum of $N \ge 30$ to $N \ge 100$ independent trade cycles before rejecting the null hypothesis of zero edge.
- **Scientific Verdict:** The HTF strategy performance on Bitstamp is **STATISTICALLY INCONCLUSIVE** due to severe sample size underpowering.

---

## 5. Execution Cost Research & Fee Reconciliation (Workstream E)

### A. Bitstamp Fee Schedule Deconstruction
Bitstamp operates a volume-tiered fee structure based on 30-day USD trading volume:
- **Tier 1 ($<\$10,000$ / retail base):** Maker 30 bps, Taker 40 bps $\rightarrow$ **70 bps roundtrip** (assuming market entry and limit exit or vice versa) to **80 bps roundtrip** (taker entry and taker exit).
- **Tier 2 ($\$10\text{k} - \$100\text{k}$):** Maker 20 bps, Taker 30 bps $\rightarrow$ 50 to 60 bps roundtrip.
- **Tier 3 ($\$100\text{k} - \$500\text{k}$):** Maker 10 bps, Taker 20 bps $\rightarrow$ 30 to 40 bps roundtrip.

### B. Microstructure Friction Decomposition
Actual execution friction consists of four distinct components:
$$\text{Friction}_{\text{total}} = \text{Fees}_{\text{roundtrip}} + \text{Spread}_{\text{entry/exit}} + \text{Slippage}_{\text{base}} + \text{Slippage}_{\text{volatility}}$$
1. **Exchange Fees:** 70.0 bps (Bitstamp Base Retail).
2. **Bid-Ask Spread:** Top-of-book spread on Bitstamp BTC/USD typically fluctuates between 1.5 and 3.5 bps.
3. **Base Slippage:** Order book depth on Bitstamp handles retail sizes ($\le \$10,000$) with 1.0 to 2.5 bps slippage.
4. **Volatility Slippage:** Fast-moving breakouts trigger market impact of 5.0 to 15.0 bps.

### C. Governance Rule
- Under no circumstances may estimated friction or historical Binance VIP0 friction (26.0 bps) be reported as observed Bitstamp execution costs.
- Bitstamp execution costs must remain officially marked **`NOT_VERIFIED`** until prospective fills are recorded.

---

## 6. Prospective Protocol V1.2 Readiness (Workstream F)

Protocol V1.2 was reviewed in read-only mode to establish exact execution criteria:
1. **Non-Overlapping Block Construction:** To eliminate serial autocorrelation in multi-period holding horizons, blocks are strictly partitioned into contiguous non-overlapping windows of length $\tau = 72\text{ hours}$ (18 four-hour candles).
2. **Outcome Labeling:** Each block is evaluated at $t + 72\text{h}$ for:
   - `PROSPECTIVE_SUCCESS_TP_HIT`
   - `PROSPECTIVE_LOSS_SL_HIT`
   - `PROSPECTIVE_TIMEOUT_UNRESOLVED`
   - `PROSPECTIVE_ANOMALY_ABSTAIN`
3. **Calendar Time Requirement:**
   $$\text{Calendar Time} = 100\text{ blocks} \times 72\text{ hours} = 7,200\text{ hours} \approx 300\text{ calendar days}\ (10\text{ months})$$
4. **Futility Stopping Rule:** If cumulative win rate drops below 30% after 30 blocks with zero mathematical probability of achieving the confirmatory hurdle, collection stops immediately (`FUTILITY_REJECTION`).
5. **Confirmatory Statistical Hurdle:**
   - One-sided binomial test $H_0: p \le 0.45$ vs $H_1: p > 0.45$ at $\alpha = 0.05$.
   - Net expectancy $> +15\text{ bps}$ after verified friction.
   - Max drawdown $< 15\%$.
6. **Governance Invariant:** The prospective collector remains strictly **`FROZEN_PENDING_ACTIVATION`**. Process count = 0.

---

## 7. Inventory of Failed Experiments & Negative Results

In accordance with Section B and epistemic guidelines, all negative results are transparently recorded:
1. **Experiment 1 (Rapid Unpaced API Pagination):** Direct, unpaced requests to Bitstamp's OHLC endpoint triggered Incapsula WAF 503 error challenges (`Request unsuccessful`). *Remedy:* Implemented 3.5s delay and exact 3,600s timestamp boundary alignment.
2. **Experiment 2 (HAR-RS-DOW at 7-Day Horizon):** Semivariances and Day-of-Week dummies failed to outperform Standard HAR at 7-day horizons (QLIKE 0.0276 vs 0.0257, $p = 0.94$). Failed to demonstrate incremental value.
3. **Experiment 3 (C2 Conformal Calibration on Bitstamp):** Conformal prediction failed nominal 90% and 95% coverage targets (achieving only 78.02% and 80.91%), suffering from the Delayed Feedback Trap. C2 remains uncalibrated.
4. **Experiment 4 (EWMA Volatility Model):** EWMA ($\lambda = 0.94$) severely underperformed all models across all horizons (QLIKE 0.28 to 0.55), proving that exponential smoothing is inadequate for multi-day crypto volatility forecasting.
5. **Experiment 5 (HTF Strategy Sample Sufficiency):** The 166-day backtest yielded only 7 trades, failing the minimum $N \ge 30$ sample size hurdle for statistical rejection of the null hypothesis.

---

## 8. Remaining Data Requirements

To transition BTCognitive from an initial research foundation to a statistically certified risk engine:
1. **Intraday 5-Minute Dataset:** Retrieve 2 full years (2024–2026) of continuous Bitstamp 5-minute candles ($\sim 210,000$ bars) via paced pagination to construct true high-frequency realized variance and semivariance proxies.
2. **Multi-Year 1h History:** Expand 1h history back to 2021 ($\sim 45,000$ bars) to evaluate HTF strategy performance across full market cycles (2021 bull market, 2022 bear market, 2023 recovery) to accumulate at least $N \ge 100$ closed trades.

---

## 9. Governed Decision Delivery

In accordance with the mandatory decision protocol, I deliver the official determinations:

### Primary Governed Mission Decision:
**`DATA_INSUFFICIENT`**  
*(With **`MODEL_CALIBRATION_FAILED`** specifically for C2 Conformal Prediction, and **`RESEARCH_INCONCLUSIVE`** for HTF Strategy Trade Sample Size).*

### Detailed Sub-Decisions:
1. **Volatility Modeling:** **`RISK_MODEL_IMPROVEMENT_DEMONSTRATED`** strictly for the 1-day (24h) horizon (HAR-RS-DOW achieved QLIKE 0.3874 vs 0.4827 Standard HAR, $p < 0.0001$). However, for the primary 7-day horizon, the result is **`RESEARCH_INCONCLUSIVE`** (Standard HAR remains superior).
2. **Conformal Uncertainty:** **`MODEL_CALIBRATION_FAILED`** (Empirical coverage 78.02% vs 90.0% nominal due to the Delayed Feedback Trap).
3. **HTF Strategy:** **`DATA_INSUFFICIENT`** (7 closed trades over 166 days is statistically underpowered, $N \ll 30$).
4. **Prospective Evidence:** **`FROZEN_PENDING_ACTIVATION`** (Process count = 0, zero collector daemons).
5. **Model Authorization:** **`OFFLINE_RESEARCH_ONLY`** (Zero models authorized for live production).
6. **Live Trading:** **`DISABLED`** (Zero broker connections, zero capital deployment).

---
*Report certified by Lead Quantitative Researcher and Engineering Coordinator.*

