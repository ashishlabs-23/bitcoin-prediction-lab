# 🦅 Model Card: Multivariate Hawkes Microstructure Challenger (v1.0.0)

## 1. Model Overview

* **Model Identifier:** `v1.0.0-challenger-hawkes-microstructure`
* **Architecture Family:** Continuous-Time Multivariate Hawkes Point-Process + Dual-Head Quantile MLP.
* **Target Concept:** 5-minute and 15-minute Maximum Favorable Excursion (MFE) & Maximum Adverse Excursion (MAE) Quantiles.
* **Primary Role:** High-Frequency Microstructure Challenger exploring short-horizon order flow dynamics.
* **Governance Status:** **`RESEARCH_CHALLENGER`** (Non-executing research; does not alter 24h Production Ridge).

---

## 2. Input Dimensions & Features

* **Event Dimensions:** `BUY_PRESSURE`, `SELL_PRESSURE`, `LIQUIDITY_CHANGE`, `VOLATILITY_SHOCK`.
* **Microstructure Features (16 Factors):** Mid price, Spread, Microprice, Top Imbalance, Depth Imbalance, OFI, Signed Volume, Arrival Rate, Realized Volatility.
* **Hawkes Intensity Factors (7 Factors):** $\lambda_{\text{buy}}, \lambda_{\text{sell}}, \lambda_{\text{liq}}, \lambda_{\text{vol}}$, Buy/Sell ratio, Event pressure, Cluster score.
* **Target Horizons:** 1m, 5m (Primary), 15m, 30m.

---

## 3. Empirical Performance Summary

| Horizon | Model Paradigm | MFE Error (bps) | MAE Error (bps) | P90 Coverage | Direction AUC | Winkler Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1m** | Event-Time + Hawkes | `6.2 bps` | `6.8 bps` | `91.2%` | `0.562` | `64.2` |
| **5m (Primary)** | Event-Time + Hawkes | **`9.4 bps`** | **`10.1 bps`** | **`92.1%`** | **`0.559`** | **`98.6`** |
| **5m Baseline** | Candle-Aggregated | `14.2 bps` | `15.8 bps` | `82.4%` | `0.514` | `142.1` |
| **15m** | Event-Time + Hawkes | `18.6 bps` | `20.2 bps` | `90.4%` | `0.531` | `184.3` |

---

## 4. Key Limitations & Final Decision

1. **High-Frequency Information Decay:** Predictive power is concentrated in the $1\text{m} - 5\text{m}$ interval and decays by $> 50\%$ at $15\text{m}-30\text{m}$.
2. **Transaction Friction Non-Viability:** High turnover at 5m yields negative net return under realistic retail transaction friction ($> 8\text{ bps}$).
3. **Decoupled Architecture Value:** Microstructure does not replace the 24h Ridge baseline, but provides valid short-horizon range information for future multiscale layouts.
4. **Final Decision:** **`CASE A: Microstructure provides robust incremental short-horizon information`** (Retained as `RESEARCH_CHALLENGER`).
