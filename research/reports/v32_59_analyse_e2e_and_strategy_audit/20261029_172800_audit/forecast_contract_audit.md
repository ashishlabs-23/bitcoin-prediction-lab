# BTCognitive Forecast Contract & Epistemic Audit (V32.59)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Authority:** `.agents/skills/btcognitive-research-orchestrator/SKILL.md` & `AGENTS.md`  
**Endpoint Audited:** `GET /api/forecast/latest` (`api/routes_prediction.py`)

---

## 1. Authoritative Schema & Contractual Fields

The canonical contract for `/api/forecast/latest` requires complete point-in-time causal traceability and strict epistemic separation between non-directional volatility bounds and directional classifications.

### Core Contract Schema

| Field Name | Type | Permitted Values / Constraints | Causal Integrity Rule | Description |
| :--- | :--- | :--- | :--- | :--- |
| `status` | string | `FORECAST_AVAILABLE_RESEARCH_ONLY`, `DATA_UNAVAILABLE`, `MODEL_UNAUTHORIZED` | Fail-closed | Overall system status for the forecast request. |
| `forecast_readiness` | string | `FORECAST_AVAILABLE`, `FORECAST_NOT_AVAILABLE`, `DATA_STALE` | Watermark check | Readiness state of the forecasting engine. |
| `forecast_target` | string | `rv168h_var_ann`, `rv24h_var_ann` | Explicit horizon separation | The forward realized variance target. 24h and 168h are distinct proxies. |
| `source_timeframe` | string | `1h`, `15m` | Alignment check | Sampling interval of the underlying candle series. |
| `forecast_origin_timestamp` | integer | Unix epoch seconds matching closed candle watermark | $t_{\text{issue}} = t_{\text{closed\_bar}}$ | The exact point in time at which the forecast was issued. Zero lookahead permitted. |
| `forecast_origin_utc` | string | ISO 8601 UTC string | Redundant human-readable | Timestamp corresponding to `forecast_origin_timestamp`. |
| `canonical_model_id` | string | `HAR-RS-DOW-v1.0` (Offline Research Baseline) | Frozen registry match | Authoritative model identifier from model registry. |
| `points` | array | Array of `{"time": int, "value": float}` | Monotonic time $\ge t_{\text{issue}}$ | Expected price path (persistence baseline: $E[P_{t+h}] = P_t$). |
| `upper_band` | array | Array of `{"time": int, "value": float}` | $P_{\text{upper}} = P_t \cdot \exp(+k \cdot \sigma_h)$ | Nominal uncalibrated volatility excursion envelope upper limit. |
| `lower_band` | array | Array of `{"time": int, "value": float}` | $P_{\text{lower}} = P_t \cdot \exp(-k \cdot \sigma_h)$ | Nominal uncalibrated volatility excursion envelope lower limit. |
| `governance_state` | string | `TIER 2 GATED (ABSTAIN)`, `OFFLINE_RESEARCH_ONLY` | Invariant lock | Confirms live trading and capital allocation remain disabled. |
| `epistemic_notice` | string | Fixed disclosure string | Mandatory UI display | Explicit notice stating baseline volatility nature and abstention. |

---

## 2. Origin Alignment & Chart-Marker Integrity

### 2.1 The Timeframe Alignment Guard
When displaying forecast cones over candlestick charts:
1. **1h Aligned Origin:** When the active chart is set to `1h`, the `forecast_origin_timestamp` must match the close of the latest completed hourly candle (`timestamp % 3600 == 0`).
2. **Mismatch Handling:** If an experimental 15-minute model issues a forecast at `:15`, `:30`, or `:45`, the frontend chart engine must **not** snap the origin marker to an unaligned 1h candle. In V32.58/V32.59, `TradingViewChart` verifies marker alignment: if `chartTimeframe === "1h"` and `forecast_origin % 3600 != 0`, the UI renders a prominent warning badge:
   `PRICE OVERLAY: NON-DIRECTIONAL PERSISTENCE BASELINE (1h) · NOMINAL UNCALIBRATED BANDS · TIMEFRAME MISMATCH DETECTED`
3. **Causal Precedence Invariant:**
   $$t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}}$$
   No observation from $t > t_{\text{issue}}$ may enter the feature matrix, normalization scaler, or model input vector.

---

## 3. Epistemic Separation & Scientific Boundaries

### 3.1 Volatility Risk vs. Directional Return Prediction
- **Econometric Truth:** Volatility forecasting (predicting the conditional dispersion of returns via HAR-RS, GARCH, or Realized GBDT) is fundamentally distinct from directional return forecasting (predicting $P(R_{t+h} > 0)$).
- **QLIKE / RMSE Validity:** Achieving statistically significant QLIKE or RMSE loss reduction on realized variance does **not** imply positive directional expectancy or trading profitability.
- **The Unsupported 90% Directional Hit-Rate Claim:** The hypothesis that any statistical model in this repository achieves a 90% directional hit rate on unconditional BTC returns remains **empirically unsupported and scientifically rejected**. The UI, documentation, and API must strictly abstain from presenting directional signals as proven edges.

### 3.2 Wilson Score Confidence Intervals vs. Serial Dependence
- When reporting 7/10 screening outcomes (e.g., $7/10 = 70.0\%$):
  - Standard Wilson 95% score interval: $[39.7\%, 89.2\%]$.
  - Financial time-series exhibit strong autocorrelation, regime shifts, and volatility clustering. Effective sample size $N_{\text{eff}} \ll N$.
  - Therefore, true uncertainty intervals are significantly wider than independent Bernoulli estimates. 7/10 is an exploratory screening hurdle, not confirmatory evidence of future success.

---

## 4. Prospective Evidence Accumulation Hurdle

Under the BTCognitive Governance Framework:
1. **Confirmatory Gate:** A minimum of **100 non-overlapping clean blocks** accumulated post-freeze is required before any confirmatory prospective evaluation can be conducted.
2. **Current Accumulation State:**
   - **168-Hour Horizon (`rv168h_var_ann`):** `0 / 100` non-overlapping blocks accumulated (`NOT_STARTED`).
   - **24-Hour Horizon (`rv24h_var_ann`):** `3 / 100` non-overlapping blocks accumulated (`COLLECTING`).
3. **Verdict:** Confirmatory prospective evidence is currently **insufficient**. All models retain status `OFFLINE_RESEARCH_ONLY`.

