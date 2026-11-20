# BTCognitive V35.0 — Risk Intelligence Model Inventory & Display Contract

**Milestone:** BTCognitive V35.0 — Research Product Finalization and Project Closure  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 3 (Risk Intelligence & Volatility Auditor)  
**Governed Assessment:** `MODEL_INVENTORY_FROZEN` | `OFFLINE_RESEARCH_ONLY`

---

## 1. Executive Summary

Milestone V35.0 established the formal **Model Inventory and Display Contract** for BTCognitive, defining exactly which risk metrics and volatility estimators are authorized for display in the Analysis interface, and codifying the strict suppression of unvalidated predictive models.

### Key Governance Determinations
1. **Standard HAR Retained as Baseline:** Corsi's (2009) Heterogeneous Autoregressive model remains the sole authorized baseline for research volatility forecasting.
2. **HAR-RS-DOW Un-promoted:** Despite an 18% QLIKE loss reduction, its failure to clear Holm-Bonferroni multiple testing significance ($p_{\text{adj}} = 0.2632 > 0.05$) prevents production promotion. It remains strictly `OFFLINE_RESEARCH_ONLY`.
3. **C2 Conformal Prediction Suppressed:** C2 remains strictly `UNAVAILABLE`. No historical Coinbase calibration may be transferred to Bitstamp, and nominal 90% coverage guarantees are forbidden.
4. **Descriptive Risk Intelligence Authorized:** Rich realized-volatility metrics, term-structure curves, and non-directional regime classifications derived from fresh Bitstamp hourly data are safe and fully operational.

---

## 2. Authoritative Model Registry & Lifecycle Inventory

| Model Identifier | Architecture / Family | Primary Role | Holdout QLIKE | Statistical Status | Display Contract Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Standard-HAR-v1.0`** | Corsi (2009) Linear HAR | Authorized Baseline | 0.4025 | Validated baseline ($p < 10^{-4}$ vs. persistence) | **ACTIVE_BASELINE (Offline Research Only)** |
| **`QLIKE-HAR-v1.0`** | Direct Quasi-Likelihood Optimization | Research Challenger | 0.3988 | Insignificant ($p = 0.177$ vs. baseline) | **EXPERIMENTAL_CHALLENGER (Offline Research Only)** |
| **`HAR-RS-DOW-v1.0`** | Semivariance ($\text{RS}^+, \text{RS}^-$) + Day-of-Week | Research Challenger | 0.3976 | Fails Holm correction ($p_{\text{adj}} = 0.2632$) | **CHALLENGER_RESEARCH_ONLY (Unpromoted)** |
| **`C2-Conformal-v1.0`** | Conformalized Variance Intervals | Risk Envelope | N/A | **CALIBRATION_FAILED** (78.02% coverage) | **STRICTLY UNAVAILABLE (Suppressed)** |
| **`Chronos2-Foundation`** | Zero-Shot Foundation Transformer | Exploratory | 0.4120 | Quarantined (High latency, no live edge) | **QUARANTINED** |

---

## 3. Safe Descriptive Risk Metrics Contract

The following metrics are derived causally from the fresh 1,000-candle Bitstamp hourly feed and are authorized for live display:

```
[Fresh Bitstamp 1,000 Hourly Candles]
                 │
                 ├─────────────────────────────────────────────────┐
                 ▼                                                 ▼
      [Realized Volatility Engine]                     [Regime & Excursion Engine]
  - 1h, 4h, 24h, 7d, 30d Annualized RV              - 4h Canonical 5-Regime Classifier
  - Term Structure: Contango / Backwardation        - Parkinson & Garman-Klass Volatility
  - RV Ratio (1h / 24h Volatility Drift)            - Donchian 20-bar Excursion Bounds
```

### Detailed Metric Specifications

1. **Annualized Realized Volatility (RV):**
   $$\text{RV}_{\tau} = \sqrt{\frac{8760}{\tau} \sum_{i=0}^{\tau-1} r_{t-i}^2}$$
   - Computed at 5 canonical horizons: **1h, 4h, 24h, 7d, and 30d**.
   - Annualization convention: 8,760 hours per calendar year.
2. **Volatility Term Structure Shape:**
   - Evaluates ratio $\text{RV}_{1\text{h}} / \text{RV}_{24\text{h}}$ and $\text{RV}_{24\text{h}} / \text{RV}_{30\text{d}}$.
   - Classifications: `CONTANGO_COMPRESSION` (short-term vol < long-term vol), `BACKWARDATION_EXPANSION` (short-term shock > long-term), or `FLAT_EQUILIBRIUM`.
3. **Parkinson High-Low Volatility:**
   $$\sigma_{\text{Parkinson}} = \sqrt{\frac{8760}{4 \ln 2 \cdot N} \sum_{i=1}^N \left(\ln \frac{H_i}{L_i}\right)^2}$$
   - Captures intra-candle range excursion dynamics independent of close-to-close drift.
4. **Canonical 5-Regime Classification:**
   - Evaluated on completed 4-hour closed bars.
   - States: `TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGE_BOUND`, `VOLATILITY_EXPANSION`, `TRANSITION_UNSUPPORTED`.
   - **Display Rule:** Clearly labeled: *"Regime indicates volatility dynamics; does NOT imply directional trade probability."*

---

## 4. Reason Codes for Suppressed & Unavailable Models

Whenever a user inspects advanced risk models or forecasts in the Analysis interface, explicit machine-readable reason codes must accompany any unavailable feature:

| Feature / Model | Display Status | Machine-Readable Reason Code | User-Facing Explanation |
| :--- | :--- | :--- | :--- |
| **C2 Conformal Bands** | `UNAVAILABLE` | `C2_CALIBRATION_UNAVAILABLE` | Conformal coverage failed empirical hurdle (78.02% observed vs 90% nominal). Suppressed for safety. |
| **Production Forecast** | `BLOCKED` | `OFFLINE_RESEARCH_ONLY_LOCKED` | System is governed for offline risk intelligence only; production forecast promotion is locked. |
| **Live Order Execution** | `DISABLED` | `ANALYSIS_ONLY_APPLICATION` | Trading execution is permanently disabled at the architectural boundary. |
| **HTF Breakout Setup** | `DEPRECATED` | `STRATEGY_DEPRECATED_NEGATIVE_EDGE` | Breakout logic deprecated following empirical failure across 17 causal trades (-172.9 bps/trade). |

---

## 5. Governed Epistemic Verdict

The model inventory is finalized and frozen. Zero new speculative models will be introduced. BTCognitive functions as a transparent, high-integrity market risk observatory.

