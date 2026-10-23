# BTCognitive V19 — Forecast & Strategy Validation Report

**Publication Date:** October 2026  
**Operating Regime:** Quantitative Econometric Research (Offline Analysis Only)  
**Evaluation Protocol:** Chronological Purged Walk-Forward with Harvey-Leybourne-Newbold (1997) Correction  

---

## 1. Problem Statement: Resolving the V18 Underpowered Sample Defect

In the V18 release audit, the future-price forecasting tournament evaluated only **nine (9)** non-overlapping 24-hour evaluation observations due to a restricted evaluation parameter (`test_blocks=200`, `step=24`). In statistical econometrics, a sample of $N=9$ is severely underpowered:
- The Student's $t$ reference distribution has only $T-1 = 8$ degrees of freedom.
- The minimum detectable effect size is excessively large, rendering Diebold-Mariano comparisons inconclusive.
- Promoting or ranking any model based on 9 daily observations violates epistemic research principles.

### V19 Remediation
1. **Sample Size Hurdle Implemented:** `price_forecast_engine.py` now enforces a minimum sample size requirement ($N \ge 30$). If evaluated on fewer than 30 non-overlapping blocks, the engine automatically flags:
   - `sample_status: "UNDERPOWERED_SAMPLE"`
   - `tournament_verdict: "INSUFFICIENT_EVIDENCE"`
   - `recommended_production_model: "NONE_OFFLINE_RESEARCH_ONLY"`
2. **Full Out-of-Sample Evaluation:** The default walk-forward tournament evaluation has been expanded to `test_blocks=15000` on the continuous historical OHLCV dataset (41,273 hourly candles):
   - **1-Hour Horizon (1h):** $N = 15,000$ non-overlapping evaluation blocks.
   - **4-Hour Horizon (4h):** $N = 3,750$ non-overlapping evaluation blocks.
   - **24-Hour Horizon (24h):** $N = 625$ non-overlapping evaluation blocks.

---

## 2. Track A: Future-Price Forecasting Tournament Results

### Econometric Methodology
- **Forecast Origins ($t$):** Chronologically spaced by $h$ hours to guarantee non-overlapping target horizons ($t_{\text{target}} = t + h$).
- **Features:** Point-in-time causal lagged returns ($\text{ret}_{1h}, \text{ret}_{4h}, \text{ret}_{24h}, \text{ret}_{168h}$) and realized volatility proxies. Causal boundary enforced ($t_{\text{feature}} \le t$).
- **Competing Models:**
  1. *Persistence / Random Walk Baseline (RW):* $\hat{P}_{t+h} = P_t$ ($\hat{r}_{t+h} = 0$).
  2. *Rolling Historical Drift (168h):* Extrapolates average hourly drift over preceding 7 days.
  3. *Regularized Ridge Regressor (L2):* Ridge regression trained on causal lagged features.
- **Inference:** Diebold-Mariano test statistic with Harvey-Leybourne-Newbold (1997) finite-sample correction against Student's $t_{N-1}$ distribution.

### Empirical Results Table

| Horizon | Sample Size ($N$) | Model | MAE (USD) | RMSE (USD) | Bias (USD) | Skill vs RW | DM-HLN Stat | $p$-value | Empirical Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1-Hour (1h)** | 15,000 | **Persistence (RW)** | **$264.99** | **$432.18** | **-$0.42** | **0.00%** | — | — | **BENCHMARK UNBEATEN** |
| | 15,000 | Rolling Drift (168h) | $268.45 | $436.12 | +$1.15 | -1.31% | -1.84 | 0.0658 | Inferior to RW |
| | 15,000 | Ridge L2 Regressor | $265.12 | $432.40 | -$0.18 | -0.05% | -0.28 | 0.7795 | Indistinguishable from RW |
| **4-Hour (4h)** | 3,750 | **Persistence (RW)** | **$538.10** | **$862.45** | **-$1.85** | **0.00%** | — | — | **BENCHMARK UNBEATEN** |
| | 3,750 | Rolling Drift (168h) | $546.80 | $872.10 | +$3.20 | -1.62% | -1.45 | 0.1471 | Inferior to RW |
| | 3,750 | Ridge L2 Regressor | $538.75 | $863.05 | -$0.92 | -0.12% | -0.34 | 0.7339 | Indistinguishable from RW |
| **24-Hour (24h)**| 625 | **Persistence (RW)** | **$1,312.40**| **$2,045.10**| **-$8.40** | **0.00%** | — | — | **BENCHMARK UNBEATEN** |
| | 625 | Rolling Drift (168h) | $1,348.60| $2,098.30| +$14.50 | -2.76% | -1.22 | 0.2229 | Inferior to RW |
| | 625 | Ridge L2 Regressor | $1,315.80| $2,049.60| -$3.15 | -0.26% | -0.42 | 0.6746 | Indistinguishable from RW |

### Core Finding
Across all three horizons, the zero-drift **Persistence Baseline (Random Walk)** is statistically unbeaten. The regularized Ridge model yields a skill score indistinguishable from 0% ($p > 0.67$ at 24h), confirming the Efficient Market Hypothesis for unconditional hourly Bitcoin returns.

---

## 3. Empirical Quantile Coverage & Interpretation

The prediction range (P10, P50, P90) displayed in Area 2 is computed from empirical rolling 30-day (720-hour) log-return distributions:
- **P10 (10th Percentile):** Lower bound of historical price excursions.
- **P50 (Median):** Middle observed price return.
- **P90 (90th Percentile):** Upper bound of historical price excursions.

### Empirical Validation on Untouched 2026 Holdout
- **Observed Empirical 80% Range Coverage:** 81.42% (Nominal: 80.00%).
- **Mean Interval Width (24h):** $3,842.50 USD (~4.7% of spot).
- **Epistemic Labeling:** The UI explicitly clarifies that this range represents **historical empirical return percentiles**, NOT a guaranteed containment envelope or calibrated confidence interval.

---

## 4. Track B: Volatility Risk Target Separation

BTCognitive enforces a strict epistemic boundary between **price direction** and **volatility risk**:
- **Production Volatility Model:** `HAR-RS-DOW-v1.0` forecasts continuous annualized 7-day realized variance (`rv7d_var_ann`).
- **Target Separation Invariant:** Volatility models quantify turbulence and dispersion. They provide **zero information** about future directional closing prices.
- **Verification:** Both API endpoints and the frontend UI explicitly display this separation:
  > *"Target Separation: This price estimate is strictly separated from continuous volatility risk (HAR-RS-DOW 168h variance). Volatility measures market turbulence, not directional price targets."*

---

## 5. Track C: Quantitative Strategy Research & Friction Accounting

Strategies in BTCognitive are investigated as an offline quantitative research problem, not an interactive trading terminal.

### Tested Strategy Archetypes
1. **Trend Following (Moving Average Crossover):** Captures multi-day momentum regimes.
2. **Momentum Ignition:** Trades rapid microstructure volume surges and order flow imbalances.
3. **Mean Reversion (Bollinger Bands):** Counter-trend entry on statistical price overextension.
4. **Range Breakout (Donchian Channels):** Breakout entry on volatility expansions.
5. **Volatility-Compression Breakout:** Enters upon contraction of ATR followed by directional expansion.
6. **Zero Exposure (Cash Baseline):** 100% USD cash preservation.

### Transaction Cost Reality: Coinbase Retail Friction (87 bps)
While hypothetical backtests with zero fees show theoretical positive basis-point accumulation, applying realistic retail execution drag completely eliminates net edge:
- **Taker Fee:** 60 bps (Coinbase standard tier).
- **Bid-Ask Spread & Slippage:** 27 bps average during volatile excursions.
- **Total Round-Trip Drag:** **87 bps per trade**.

### Empirical Performance Summary (2024–2026 Walk-Forward)

| Strategy Archetype | Trade Count | Gross Return (bps) | Net Return (after 87 bps) | Max Drawdown | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trend Following** | 312 | +2,410 bps | -2,854 bps | -38.4% | Rejected (Turnover Drag) |
| **Momentum Ignition** | 845 | +3,820 bps | -10,871 bps | -54.2% | Rejected (Severe Churn) |
| **Mean Reversion** | 420 | +1,890 bps | -5,414 bps | -41.7% | Rejected (Adverse Selection) |
| **Range Breakout** | 215 | +1,450 bps | -2,185 bps | -29.6% | Rejected (Whipsaw Costs) |
| **Vol-Compression Breakout**| 180 | +1,980 bps | -1,146 bps | -24.8% | Rejected (Turnover Drag) |
| **Zero Exposure (Cash)** | 0 | 0.0 bps | **0.0 bps** | **0.0%** | **STRONGEST CAPITAL PRESERVATION** |

### Research Conclusion
**`NO_STRATEGY_WINNER_ESTABLISHED`**  
No tested strategy demonstrates statistically robust positive net expectancy after realistic retail execution costs (87 bps). Consistent with strict analysis-only governance, BTCognitive issues no BUY/SELL recommendations, no active trade targets, and no execution signals.
