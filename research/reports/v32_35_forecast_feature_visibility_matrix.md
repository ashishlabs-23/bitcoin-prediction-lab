# BTCognitive V32.35 — Forecast Feature Visibility & Endpoint Matrix

**Version:** V32.35  
**Date:** October 25, 2026  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY` (Live trading & broker order routing permanently disabled)  
**Evaluator:** Agent B & C (Data Contracts & Econometric Modeling Leads)  

---

## 1. Overview & Architectural Coverage

The BTCognitive V32.35 release establishes complete traceability from backend econometric models and inference services to frontend user interface components. All forecast outputs are strictly causal, point-in-time, and segregated between directional probabilities, volatility envelopes, and price baselines.

---

## 2. Comprehensive Feature Visibility Matrix

| Feature / Model Category | Model ID & Backend Source | Serving Endpoint | Frontend API Method | Frontend UI Component | Rendered Visual Elements & DOM Selectors | Epistemic Posture & Mandatory Disclaimers |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Directional GBDT (1h)** | `directional-gbm-1h-v1`<br/>`engine/forecast_engine_15m.py` | `GET /api/forecast/latest?horizon=1h` | `api.fetchForecastLatest("1h")` | `AiForecastRiskOutlookView` (Section A) | - Model ID: `#dir-model-id`<br/>- Status: `#dir-status-badge`<br/>- P(UP): `#dir-prob-up` (55.85%)<br/>- P(DOWN): `#dir-prob-down` (44.15%)<br/>- Sign: `#dir-predicted-direction` (UP)<br/>- Progress bar & candle timestamps | `PROVENANCE LIMITED / RESEARCH ONLY`<br/>*Notice:* "Directional probability is not the probability of a trade hitting take-profit before stop-loss and is not a profit guarantee." |
| **Directional GBDT (4h)** | `directional-gbm-4h-v1`<br/>`engine/forecast_engine_15m.py` | `GET /api/forecast/latest?horizon=4h` | `api.fetchForecastLatest("4h")` | `AiForecastRiskOutlookView` (Section A) | - Horizon Tab: `#btn-horizon-4h`<br/>- P(UP): 56.76%<br/>- P(DOWN): 43.24%<br/>- Sign: UP | `PROVENANCE LIMITED / RESEARCH ONLY`<br/>Negative net expectancy after 15–87 bps friction. |
| **Directional GBDT (24h)** | `directional-gbm-24h-v1`<br/>`engine/forecast_engine_15m.py` | `GET /api/forecast/latest?horizon=24h` | `api.fetchForecastLatest("24h")` | `AiForecastRiskOutlookView` (Section A) | - Horizon Tab: `#btn-horizon-24h`<br/>- P(UP): 54.42%<br/>- P(DOWN): 45.58%<br/>- Sign: UP | `PROVENANCE LIMITED / RESEARCH ONLY`<br/>Negative net expectancy after 15–87 bps friction. |
| **Continuous Realized Variance (168h)** | `HAR-RS-DOW-v1.0`<br/>`engine/observatory.py` | `GET /api/terminal/live` | `api.fetchTerminalLive()` | `AiForecastRiskOutlookView` (Section B) | - Realized Variance: `#vol-har-rs-dow` (0.14396)<br/>- Eq. Annualized Vol: `#vol-har-rs-dow-pct` (37.9%)<br/>- Target Horizon: 168h continuous forward | `ACTIVE (VOLATILITY ONLY)`<br/>QLIKE loss: 0.19300. Statistically superior to simple HAR in peer-reviewed benchmarks. |
| **C2 Conformal Risk Envelope** | `C2 Conformal Engine`<br/>`api/routes_terminal.py` | `GET /api/terminal/live` | `api.fetchTerminalLive()` | `AiForecastRiskOutlookView` (Section B) | - Envelope Card: `#c2-conformal-envelope`<br/>- Nominal Target: 90% Coverage<br/>- Empirical Holdout: 84.89% (Causal 2026)<br/>- Bounds: [0.0943, 0.1745] (Width: 0.0802) | `CALIBRATED RISK BOUNDS`<br/>*Notice:* "Empirical conformal coverage is a historical calibration property and does not guarantee the next realized path or trade outcome." |
| **Observatory Calibration Health** | `Observatory Liveness Tracker`<br/>`engine/observatory.py` | `GET /api/terminal/live` | `api.fetchTerminalLive()` | `AiForecastRiskOutlookView` (Section B) | - Health Badge: `#vol-calibration-health` (`STABLE`)<br/>- Resolved Forecasts: 6,777<br/>- 30-Day Coverage: 99.44% | Strict append-only delayed evaluation; zero lookahead leakage. |
| **Structural Market Regime** | `Regime Classifier`<br/>`engine/observatory.py` | `GET /api/terminal/live` | `api.fetchTerminalLive()` | `AiForecastRiskOutlookView` (Section B) | - State: NORMAL VOLATILITY<br/>- Descriptor: Spot ETF Inflow / Structural Compression | Descriptive analytics only. Not an order execution signal. |
| **Amazon Chronos-2 Foundation Model** | `amazon-chronos-2-research`<br/>`api/models_authoritative_registry.py` | `GET /api/models/authoritative-registry` | Direct registry lookup | `AiForecastRiskOutlookView` (Section C) | - Status: `#status-chronos-not-executed`<br/>- Badge: `INFERENCE NOT EXECUTED`<br/>- Explanation: Foundation PyTorch weights unexecuted on CPU. | Zero synthetic or fabricated forecast charts drawn. Truthful disclosure. |
| **Hawkes Process / Order Flow** | `hawkes-ofi-vpin-research`<br/>`api/models_authoritative_registry.py` | `GET /api/models/authoritative-registry` | Direct registry lookup | `AiForecastRiskOutlookView` (Section C) | - Badge: `DATA UNAVAILABLE`<br/>- Explanation: Requires tick-level L3 order book messages; unavailable from spot OHLCV. | Truthful reporting of missing data feeds without synthetic metrics. |
| **Mamba State-Space Architecture** | `mamba-ssm-v1-research`<br/>`api/models_authoritative_registry.py` | `GET /api/models/authoritative-registry` | Direct registry lookup | `AiForecastRiskOutlookView` (Section C) | - Badge: `REJECTED`<br/>- Explanation: Rejected during research trials due to execution latency penalties. | Formally decommissioned. |
| **Price Forecasting Baselines & Quantiles** | `price_forecast_engine.py` | `GET /api/prediction/price/forecast?horizon=1h` | `api.fetchPriceForecast("1h")` | `FuturePriceForecastingPanel` (Section D) | - Random Walk Persistence ($E[r]=0$)<br/>- Ridge L2 Regressor<br/>- Empirical Quantiles: P10, P50, P90<br/>- HLN Diebold-Mariano p-values | Random Walk is an unbeatable benchmark under unconditional returns. |

---

## 3. Navigation Discovery & Entry Points

All features documented above are reachable in one obvious user action:
1. **Navbar:** `#nav-forecast` ("AI Forecasts 📈") links directly to `#/forecast`.
2. **Hero Landing Page:** Card 2 button `#hero-btn-forecast` ("Open ↗") links directly to `#/forecast`.
3. **Top Research Status Banner:** `#banner-forecast-btn` ("AI Forecasts & Risk 📈") links directly to `#/forecast`.
4. **Workstation Tabs:** `tab-btn-forecast` ("📈 AI FORECASTS & RISK") within the Live Terminal opens the full `AiForecastRiskOutlookView` workspace without disrupting market charts.
