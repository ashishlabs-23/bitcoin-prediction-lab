# BTCognitive V32.35 — Independent Browser-QA Self-Loop Verification Report

**Version:** V32.35  
**Date:** October 25, 2026  
**Session Recording:** `research/reports/artifacts/v32_35/v32_35_browser_qa_1792924241806.webp`  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Lead Evaluator:** Agent D (Independent Red-Team & Verification Lead)  

---

## 1. Scope & Objective

This report documents the autonomous end-to-end browser QA evaluation conducted against the live, running BTCognitive application on `http://127.0.0.1:8000`. The objective was to verify that AI forecasting capabilities are clearly visible, intuitive, structurally sound, responsive across viewports, free of console errors, and strictly compliant with epistemic guardrails.

---

## 2. Test Execution & Evidence Log

### Step 1: Landing Page & Navigation Discovery
- **Action:** Opened `http://127.0.0.1:8000/`.
- **Observations:**
  - Navbar contains `#nav-forecast` labeled "AI Forecasts 📈".
  - Hero card 2 (`#hero-card-forecast`) is prominently styled with blue accent border and includes action button `#hero-btn-forecast` ("Open ↗").
  - Top research status banner includes button `#banner-forecast-btn` ("AI Forecasts & Risk 📈").
- **Screenshot:** [landing_page_1792924258392.png](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/v32_35/landing_page_1792924258392.png)
- **Verdict:** `PASS` (One obvious action discovery satisfied).

### Step 2: One-Click Navigation to AI Forecasts Workspace
- **Action:** Clicked `#nav-forecast`.
- **Observations:**
  - URL transitioned immediately to `http://127.0.0.1:8000/#/forecast`.
  - Full `AiForecastRiskOutlookView` (`#v32-35-forecast-outlook-view`) mounted cleanly.
  - Active tab button in bottom workstation bar reflected `tab-btn-forecast` ("📈 AI FORECASTS & RISK").
- **Verdict:** `PASS`.

### Step 3: Directional Research Forecasts (Section A)
- **Action:** Inspected Section A metrics and tested multi-horizon interactive controls.
- **Observations:**
  - Model ID (`#dir-model-id`): displayed `directional-gbm-1h-v1`.
  - Status Badge (`#dir-status-badge`): `PROVENANCE LIMITED / RESEARCH ONLY`.
  - Probability distribution: $P(\text{UP}) = 55.85\%$ (`#dir-prob-up`), $P(\text{DOWN}) = 44.15\%$ (`#dir-prob-down`).
  - Predicted direction (`#dir-predicted-direction`): `UP` with net expectancy tag `NEGATIVE_AFTER_FEES`.
  - Causal candle timestamp: `2026-10-25 10:00:00 UTC` with status `FRESH (Coinbase REST Verified)`.
  - Mandatory Interpretation Callout verified:
    > *"Directional probability is not the probability of a trade hitting take-profit before stop-loss and is not a profit guarantee. All directional models operate under research-only governance with net negative expectancy after transaction friction. Live trading is strictly disabled."*
  - **Horizon Switching Test:**
    - Clicked `#btn-horizon-4h`: `#dir-model-id` updated smoothly to `directional-gbm-4h-v1` with $P(\text{UP}) = 56.76\%$, $P(\text{DOWN}) = 43.24\%$.
    - Clicked `#btn-horizon-24h`: `#dir-model-id` updated smoothly to `directional-gbm-24h-v1` with $P(\text{UP}) = 54.42\%$, $P(\text{DOWN}) = 45.58\%$.
    - Clicked `#btn-horizon-1h`: `#dir-model-id` restored smoothly to `directional-gbm-1h-v1`.
- **Verdict:** `PASS`.

### Step 4: Volatility & Risk Outlook (Section B)
- **Action:** Inspected HAR-RS-DOW continuous realized variance and C2 conformal bounds.
- **Observations:**
  - Realized variance (`#vol-har-rs-dow`): `0.14396` (continuous forward 168h window).
  - Equivalent annualized volatility (`#vol-har-rs-dow-pct`): `37.9%`.
  - C2 Conformal Envelope (`#c2-conformal-envelope`): Nominal 90% Target Coverage, 84.89% Causal 2026 Holdout coverage, bounds `[0.0943, 0.1745]`.
  - Observatory calibration health (`#vol-calibration-health`): `STABLE` (6,777 resolved forecasts, 99.44% 30-day coverage).
  - Structural market regime: `NORMAL VOLATILITY` (Spot ETF Inflow / Structural Compression).
  - Mandatory Conformal Notice verified:
    > *"Empirical conformal coverage is a historical calibration property and does not guarantee the next realized path or trade outcome. Risk envelopes describe historical statistical bounds, not guaranteed support/resistance barriers."*
- **Verdict:** `PASS`.

### Step 5: Foundation & Experimental Models (Section C)
- **Action:** Verified epistemic honesty of foundation and non-operational architectures.
- **Observations:**
  - Amazon Chronos-2: Status badge `#status-chronos-not-executed` clearly displayed `INFERENCE NOT EXECUTED`. Truthful note explaining that zero-shot transformer weights are not executed on CPU.
  - Hawkes Process: Status badge displayed `DATA UNAVAILABLE`. Truthful note explaining that tick-level L3 message feed is required.
  - Mamba State-Space: Status badge displayed `REJECTED`.
  - **Absence of Synthetic Fabrication:** Confirmed zero synthetic, fabricated, or interpolated forecast charts are rendered for Chronos-2 or Hawkes.
- **Verdict:** `PASS`.

### Step 6: Price Baselines & Tournament (Section D)
- **Action:** Inspected price baselines and quantile estimates.
- **Observations:**
  - Random Walk persistence benchmark correctly displayed $E[r]=0$.
  - Ridge L2 regressor and empirical quantiles (P10, P50, P90) cleanly rendered.
- **Verdict:** `PASS`.

### Step 7: Manual Refresh & Error Recovery
- **Action:** Clicked `#btn-refresh-forecasts`.
- **Observations:**
  - Button state changed smoothly to "Refreshing...", re-fetched both endpoints asynchronously, and returned to "Refresh ⟳" without layout shift or UI flickering.
  - Timestamp indicator updated to latest UTC second.
- **Verdict:** `PASS`.

### Step 8: Multi-Viewport Responsive Layout Testing
- **Desktop (1536×800):** Layout spans symmetrically, charts and cards maintain optimal aspect ratio.
  - **Screenshot:** [desktop_viewport_1792924473378.png](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/v32_35/desktop_viewport_1792924473378.png)
- **Tablet (768×1024):** Grid gracefully collapses to 2 columns, horizon tabs wrap cleanly, zero horizontal scrolling.
  - **Screenshot:** [tablet_viewport_1792924455412.png](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/v32_35/tablet_viewport_1792924455412.png)
- **Mobile (375×812):** Grid collapses to single-column card stack, buttons remain comfortably touchable (min 44px hit targets), zero horizontal overflow.
  - **Screenshot:** [mobile_viewport_1792924462199.png](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/artifacts/v32_35/mobile_viewport_1792924462199.png)
- **Verdict:** `PASS`.

### Step 9: Console Hygiene & Network Inspection
- **Console Errors:** **0 errors**.
- **Failed Requests:** **0 failed requests** (all endpoints responded with HTTP 200).
- **Rate-Limiter Health:** Steady-state request volume averaged 29.5 req/min, well below the 60 req/min server ceiling.

---

## 3. Browser QA Summary Verdict

| Category | Result | Details |
| :--- | :--- | :--- |
| **Discoverability** | `PASS` | 4 distinct, obvious navigation entry points across Navbar, Hero, Banner, and Tabs. |
| **Inference Integrity** | `PASS` | Real causal GBDT 1h/4h/24h inference and HAR-RS-DOW 168h variance rendered. |
| **Epistemic Disclaimers** | `PASS` | Directional and conformal non-guarantee notices permanently embedded. |
| **Model Truthfulness** | `PASS` | Chronos-2 `INFERENCE NOT EXECUTED` and Hawkes `DATA UNAVAILABLE` honest disclosures. |
| **Responsive UX** | `PASS` | Clean, responsive rendering across Desktop, Tablet, and Mobile viewports. |
| **Console & Network** | `PASS` | 0 console errors, 0 failed requests, 0 unhandled exceptions. |
