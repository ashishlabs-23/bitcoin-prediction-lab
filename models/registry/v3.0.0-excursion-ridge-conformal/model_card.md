# 📜 Model Card: `v3.0.0-excursion-ridge-conformal`

## 1. Model Overview

* **Model ID**: `ridge_excursion_core`
* **Version**: `v3.0.0-excursion-ridge-conformal`
* **Architecture**: Regularized Ridge Regression ($L_2$) with Conformal Empirical Quantile Residual Mapping
* **Primary Prediction Output**: Probabilistic 24H BTCUSD Range & Excursion Envelope ($P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$)
* **Deployment Status**: `PRODUCTION`

---

## 2. Ingested Features & Target Specification

* **Feature Schema**:
  - `vol_24h`: Realized 24h log-return standard deviation
  - `rsi_14`: 14-period Relative Strength Index
  - `atr_14`: 14-period Average True Range normalized by close price
  - `funding_rate`: Binance perpetual 8h funding rate
  - `mvrv_zscore`: On-chain Bitcoin valuation metric
* **Target Definition**:
  - $\text{MFE}_{24h} = (\max_{1..24} H_{t+k} - P_t) / P_t$
  - $\text{MAE}_{24h} = (P_t - \min_{1..24} L_{t+k}) / P_t$
* **Calibration Protocol**: Non-parametric conformal quantile shift matching empirical 90% error boundaries.

---

## 3. Verified Performance Metrics (31 Independent 24h Blocks, 744 Hours)

| Metric Name | Value | Nominal Target | Evaluation Status |
| :--- | :---: | :---: | :---: |
| **MFE P90 Coverage** | **`93.5%`** | $\ge 90.0\%$ | **PASS** |
| **MAE P90 Coverage** | **`96.8%`** | $\ge 90.0\%$ | **PASS** |
| **Joint Full-Path Containment** | **`90.32%`** | $\ge 78.87\%$ | **PASS** |
| **Mean MFE Point Error** | **`0.4120%`** | $\le 0.55\%$ | **PASS** |
| **Mean Range Width** | **`5.92%`** | $\le 8.0\%$ | **PASS** |
| **Paired MAE Delta vs EWMA** | **`-0.0831%`** | $< 0.00\%$ | **PASS ($p = 0.0172$)** |

---

## 4. Regime & Volatility Invariants

* **Regime Stability**:
  - Trending Bull: `90.0%`
  - Trending Bear: `90.0%`
  - Sideways: `90.9%`
  - Breakout: `88.9%`
* **Volatility Stability**:
  - Low Volatility: `91.7%`
  - Normal Volatility: `90.0%`
  - High Volatility: `88.9%`

---

## 5. Governance & Operational Constraints

* **Non-Execution Guarantee**: Real trading is strictly disabled; tradeability scores are informational research metadata only.
* **Auto-Retrain Invariant**: Automated retraining is strictly disabled.
* **Rollback Target**: `None` (Active foundation baseline).
