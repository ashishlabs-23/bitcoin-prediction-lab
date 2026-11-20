# BTCognitive V32.35 — Forecast Visibility Defect Ledger & Root Cause Analysis

**Version:** V32.35  
**Date:** October 25, 2026  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY` (Live trading & broker order routing permanently disabled)  
**Evaluator:** Agent D (Independent Red-Team & Verification Lead)  

---

## 1. Executive Summary

Prior to version V32.35, the BTCognitive user interface buried real causal forecasting capabilities under deeply nested sub-tabs and fallback routings. While backend econometric engines (`forecast_engine_15m.py`, `directional_forecast_service.py`, `observatory.py`, and `price_forecast_engine.py`) were generating verified point-in-time LightGBM directional inference and HAR-RS-DOW 168-hour realized variance estimates, end-users landing on the application were greeted with a default Market conditions tab or a blocking error state.

This defect ledger itemizes every diagnosed UI defect, its root cause across the full software stack, and the verified permanent remediation implemented in V32.35.

---

## 2. Itemized Defect Ledger

| Defect ID | Severity | UI Route / Component | Defect Symptom & Failure Mode | Full-Stack Root Cause | Verified Remediation in V32.35 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | **CRITICAL** | Navbar (`web/app.js:NavBar`) | No direct link or button to access AI Forecasts. Users only saw `Terminal`, `Smart Entry`, `Research`, `Arena`. | Missing navigation pill item in `NavBar` items array. | Added `#nav-forecast` ("AI Forecasts 📈") pointing to `#/forecast` immediately adjacent to Live Terminal. |
| **DEF-02** | **HIGH** | App Router (`web/app.js:App`) | Navigating directly to `#/forecast` fell back to default `TerminalView` on the `market` tab. | `App` router had conditional branches for `/landing`, `/smart-entry`, `/research`, `/arena`, but lacked a dedicated `/forecast` handler, defaulting to `TerminalView` with `workstationTab="market"`. | Added explicit `/forecast` route branch in `App` that mounts `TerminalView` with `defaultWorkstationTab="forecast"`. |
| **DEF-03** | **HIGH** | Workstation Tabs (`web/app.js:TerminalView`) | `tab-btn-forecast` had misleading label `"📈 PRICE FORECAST (1h/24h)"` and only rendered a minimal pricing box without directional GBDT metrics. | Forecast tab rendered legacy `FuturePriceForecastingPanel` without integrating real causal LightGBM directional probabilities or HAR-RS-DOW 168h variance. | Built and integrated comprehensive `AiForecastRiskOutlookView` (`#v32-35-forecast-outlook-view`) rendering Sections A, B, C, and D. Tab renamed to `"📈 AI FORECASTS & RISK"`. |
| **DEF-04** | **HIGH** | Hero Landing Card 2 (`web/app.js:HeroSection`) | Card 2 displayed forecast copy but had no clickable action button or direct routing link. | Card was purely static text without an interactive trigger. | Added action button `#hero-btn-forecast` ("Open ↗") directly navigating to `#/forecast`. |
| **DEF-05** | **MEDIUM** | Top Research Banner (`web/app.js:App`) | Header banner had buttons for `Smart Entry` and `View Research Evidence`, but lacked a forecast entry point. | Button was absent from header banner flex container. | Added `#banner-forecast-btn` ("AI Forecasts & Risk 📈") navigating directly to `#/forecast`. |
| **DEF-06** | **HIGH** | Directional Execution Lockout (`web/app.js:AiPredictionEnginePanel`) | Panel displayed a severe yellow blocking error card: `"Model intelligence unavailable · research authorization is blocked."` | `hasVerifiedResearchAuthorization` returned false for directional models under research governance, blocking the entire card without guiding users to research views. | Replaced blocking error card with informative guidance explaining that directional trade execution is gated under research governance, adding direct action buttons to `#tab-btn-forecast` and `#tab-btn-smart-entry`. |
| **DEF-07** | **HIGH** | API Client Gap (`web_src/api_client.js`) | Frontend API client lacked typed helper methods for `/api/forecast/latest` and `/api/terminal/live`. | UI components were making ad-hoc calls or omitting live volatility envelopes. | Implemented `api.fetchForecastLatest(horizon)` and `api.fetchTerminalLive()` with TTL caching, in-flight deduplication, and rate-limit backoff. |
| **DEF-08** | **CRITICAL** | Epistemic Integrity Gap | Directional probabilities lacked mandatory non-guarantee interpretation disclaimers, risking user confusion with trading hit rates. | Omission of standard disclaimers in UI render tree. | Embedded mandatory non-guarantee notices in both Section A and Section B: *"Directional probability is not the probability of a trade hitting take-profit before stop-loss and is not a profit guarantee."* |
| **DEF-09** | **MEDIUM** | Foundation Model Truthfulness | Experimental architectures (Chronos-2, Hawkes, Mamba) lacked transparent status badges. | UI lacked an authoritative registry matrix displaying true execution status. | Implemented Section C Authoritative Model Registry with truthful status badges: Chronos-2 (`INFERENCE NOT EXECUTED`), Hawkes (`DATA UNAVAILABLE`), Mamba (`REJECTED`) — with zero synthetic charts. |

---

## 3. Verification & Closure

Every defect listed above was independently verified through:
1. Automated unit test assertions in `tests_frontend.js` (100% pass rate).
2. End-to-end browser execution recording: `v32_35_browser_qa_1792924241806.webp`.
3. High-resolution multi-viewport screenshot verification across Desktop (1536×800), Tablet (768×1024), and Mobile (375×812).
