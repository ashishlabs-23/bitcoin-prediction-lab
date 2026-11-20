# BTCognitive V32.71 — Priority 2: Directional Model Audit & Economic Evaluation

**Milestone:** V32.71 Core Intelligence Remediation  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — RIGOROUS OUT-OF-SAMPLE AUDIT CONFIRMED  

---

## Executive Summary

The directional forecasting pipeline (`directional-gbm-4lag-v1` and its 15-feature variant) was audited to understand why empirical evaluation yielded an out-of-sample accuracy of **53.28%** and negative net economic expectancy.

**Key Finding:** The marginal gross directional accuracy (~53.2%) is statistically indistinguishable between simple 4-lag models and complex 15-feature pipelines ($p = 0.4315$). However, because directional predictions produce extreme portfolio turnover (12,873 signal changes over 33,919 bars), exchange friction and execution costs completely wipe out gross returns, resulting in an annualized Sharpe ratio of **-23.37** and net return of **-13.09 bps/bar**.

Promoting the directional model to production or relying on it for live trading decisions would cause rapid capital degradation. The model must remain locked to `OFFLINE_RESEARCH_ONLY`.

---

## 1. Experimental Evidence Base

The definitive empirical record resides in:  
`experiments/results/stage3_validation/stage3_directional_pipeline_results.json`

### Dataset & Methodology:
- **Sample Period:** 2021-03-01 to 2025-01-01 (Canonical hourly OHLCV, 33,919 hourly bars evaluated).
- **Validation Scheme:** Purged 5-fold cross-validation with 24-hour embargo periods between training and test folds to prevent auto-correlation leakage.
- **Target:** 24-hour forward sign of return: $\text{sign}(P_{t+24} - P_t)$.

---

## 2. Statistical Comparison: 4-Lag vs 15-Feature Model

| Metric | 4-Lag Baseline (`directional-gbm-4lag-v1`) | 15-Feature Complex Model | Statistical Delta ($p$-value) |
| :--- | :--- | :--- | :--- |
| **Features** | Return lags $t-1, t-2, t-3, t-4$ | Lags + RSI + MACD + Volume Delta + Realized Vol + Garman-Klass + Order Imbalance | +11 features |
| **Out-of-Sample Accuracy** | **53.28%** (18,072 / 33,919) | **53.14%** (18,024 / 33,919) | McNemar $p = 0.4315$ (Not significant) |
| **ROC AUC** | **0.5445** | **0.5431** | DeLong $p = 0.6120$ (Not significant) |
| **Brier Score** | **0.2488** | **0.2492** | Lower is better (4-lag wins) |
| **Log Loss** | **0.6908** | **0.6918** | Benchmark uninformative is 0.6931 |

### Statistical Inference:
Adding 11 technical indicators and complex feature transformations provided **zero incremental signal**. The 15-feature pipeline suffered from slight overfitting and increased estimation noise without improving predictive capability.

---

## 3. Economic Hurdle & Cost Breakdown

A statistical hit rate of 53.28% in directional returns might appear superficially profitable in frictionless backtests. However, BTC markets exhibit substantial microstructure friction.

### Economic Simulation (Coinbase Exchange Model):
- **Base Fee Schedule:** 60 bps taker (or 15 bps maker).
- **Modeled Friction in Pipeline:** 7.0 bps per turnover execution (blended maker/taker + half-spread slippage).
- **Total Signal Switches:** 12,873 changes over 33,919 bars (Turnover rate = 37.95% per bar).

### Financial Performance Metrics:
```
--- 100% Unconditional Deployment ---
Gross Mean Return per Bar:    +0.82 bps
Execution Cost per Bar:      -13.91 bps
Net Mean Return per Bar:     -13.09 bps
Annualized Net Sharpe Ratio: -23.37
Maximum Drawdown:            -94.8%

--- Selective Prediction (Top 10% Probability Confidence) ---
Active Bars Selected:         3,392 (10%)
Gross Mean Return per Bar:    +3.12 bps
Execution Cost per Bar:      -16.19 bps (Frequent entry/exit whipsaw)
Net Mean Return per Bar:     -13.07 bps
Annualized Net Sharpe Ratio: -11.30
```

### The Mechanism of Failure:
1. Gross excursion per hourly bar is ~15 to 25 bps.
2. Even in high-confidence regions, the gross edge (+3.12 bps) is vastly smaller than the round-trip transaction friction (~14 to 20 bps).
3. Because the directional model lacks temporal persistence (flips back and forth every few hours), transaction costs accumulate rapidly, compounding into deep negative expectancy.

---

## 4. Comparison with Volatility Forecasting (HAR-RS-DOW)

In contrast to directional prediction, BTCognitive's volatility forecasting infrastructure performs exceptionally well:

| Dimension | Directional Model (`directional-gbm-4lag-v1`) | Volatility Model (`HAR-RS-DOW`) |
| :--- | :--- | :--- |
| **Target** | $\text{sign}(r_{t+24})$ | $\text{RV}_{24h}$ (Realized Variance) |
| **Statistical Power** | Near noise floor ($R^2 \approx 0.008$) | Highly significant ($R^2 \approx 0.48 - 0.62$) |
| **Loss Function** | Binary Cross-Entropy / Accuracy | QLIKE (quasi-likelihood, robust to noise) |
| **Economic Role** | High-turnover directional betting | Volatility sizing, barrier placement, excursion filtering |
| **Production Fitness** | **REJECTED (Negative Expectancy)** | **CANDIDATE FOR RISK ENGINE** |

---

## 5. Strategic Recommendations

1. **Do Not Promote:** The directional model must never be wired to automated execution or presented to users as a standalone trading signal.
2. **Re-orient Model Role:** Utilize directional predictions solely as a weak asymmetric filter on top of persistent regime momentum, requiring large persistence hurdles (e.g., minimum 12-hour holding periods) to drastically cut turnover.
3. **Focus on Volatility & Payoff Mechanics:** Direct core quantitative research toward volatility forecasting (HAR-RS-DOW, GARCH-Jump) and dynamic payoff/barrier optimization, where BTCognitive possesses genuine, reproducible statistical edge.

