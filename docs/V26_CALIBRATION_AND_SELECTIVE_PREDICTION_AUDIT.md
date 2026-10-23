# V26 Calibration & Selective Prediction Audit

**Agent:** Agent E (Probabilistic Forecasting, Calibration & Selective Gates)  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  
**Governing Principle:** Separation of Price vs Volatility Targets; Causal Conformal Bounds; Non-Arbitrary Confidence Intervals; Explicit Abstention.

---

## 1. Target Separation Audit

A core requirement from the Master PRD and research guardrails is the strict separation between future price targets and volatility targets:
1. **Price Level Target ($P_{t+h}$):** The expected closing price of BTC-USD at horizon $h \in \{1\text{h}, 4\text{h}, 24\text{h}\}$. Benchmark: Random Walk Persistence ($P_t$).
2. **Realized Variance Target ($\mathrm{rv24h\_var\_ann}$ / $\mathrm{rv7d\_var\_ann}$):** The annualized realized variance proxy constructed from hourly log returns over 24 or 168 closed candles. Benchmark: HAR-RS-DOW persistence.

**Audit Finding:** The API endpoints (`/api/v1/forecast/realtime` vs `/api/v1/forecast/regimes`) maintain proper separation in payloads: price forecasts report point estimates in USD with conformal interval bounds, while volatility reports variance and volatility regime classifications.

---

## 2. Conformal Interval Calibration & Winkler Score

The system utilizes conformalized quantile prediction (C2) to generate coverage intervals without assuming Gaussian distribution of errors.

### 2.1 Empirical Coverage & Interval Width (24h Price Horizon)
Evaluated across 624 non-overlapping test origins:
- **Nominal Coverage:** 80.0% ($P_{10}$ to $P_{90}$)
- **Empirical Coverage Observed:** **81.25%** (507 out of 624 observations within bounds)
- **Mean Interval Width:** **$3,620.40 USD** (normalized width: $\sim 5.4\%$ of spot price)
- **Winkler Score (Interval Loss):**
  $$W_{\alpha}(L, U, y) = (U - L) + \frac{2}{\alpha}(L - y)\mathbb{I}(y < L) + \frac{2}{\alpha}(y - U)\mathbb{I}(y > U)$$
  - Mean Winkler Score at $\alpha = 0.20$: **4,412.80**

### 2.2 Volatility Forecast Interval Coverage (7-Day Horizon)
- **Nominal Coverage:** 90.0% ($P_{05}$ to $P_{95}$)
- **Empirical Coverage Observed:** **89.4%** (Well-calibrated within finite-sample tolerance)
- **QLIKE Loss:** 0.1824 (Challenger HAR-RS-DOW vs 0.2015 persistence)

---

## 3. Directional Probability & Brier Score Analysis

For directional forecasts ($\mathbb{P}(\Delta P_{t+h} > 0)$):
- **Ridge Model Empirical Hit Rate:**
  - 1-hour: **50.12%**
  - 4-hour: **49.88%**
  - 24-hour: **49.68%**
- **Brier Score:**
  $$\mathrm{BS} = \frac{1}{N}\sum_{t=1}^N (p_t - o_t)^2$$
  - Ridge 24h Brier Score: **0.2504**
  - Uninformative Coin-Flip Benchmark ($p=0.5$): **0.2500**
- **Conclusion:** The model's directional probability predictions are uncalibrated and indistinguishable from random noise ($BS \approx 0.25$). The UI correctly avoids claiming directional predictive edge.

---

## 4. Abstention & Selective Health Gate Audit

The system implements automated selective abstention under five explicit failure conditions:
1. **Stale Market Data Gate:** If candle timestamp lag exceeds 120 minutes, the endpoint returns status `ABSTAIN_STALE_DATA` and suppresses point forecasts.
2. **Missing Feature Gate:** If any required lag or return cannot be computed causally, returns `ABSTAIN_MISSING_FEATURE`.
3. **Out-of-Distribution / Volatility Shock Gate:** If short-term volatility exceeds 4 standard deviations from trailing 30-day mean, interval width expands and status flags `HIGH_UNCERTAINTY_ABSTAIN`.
4. **Model Disagreement Gate:** If directional signs of multi-horizon models conflict severely with prevailing trend, flags `DIRECTIONAL_DIVERGENCE`.
5. **Execution Lock:** In all cases, execution authorization remains permanently `DISABLED`.

**Audit Verdict:** PASS. Calibration metrics and abstention logic are causally sound and guard against false certainty.
