# BTCognitive V32.68 — Core Workflow & Latency Performance Report

**Report Date:** 30 October 2026  
**Milestone:** V32.68 — Offline Core-Workflow Verification & Provider Rights Delta  
**Execution Environment:** Isolated Loopback (`127.0.0.1:8098`) in `DATA_MODE=fixture`  
**Browser Engine:** Headless Chrome 130+ via Chrome DevTools Protocol (CDP)  
**Overall Verdict:** `PASS` (Core-Workflow Verification Only; Public Provider Release Remains Blocked)

---

## 1. Executive Summary

This report establishes the first empirical real-browser and API performance benchmarks for the core charting workflows in BTCognitive V32.68:
1. **The "Analyse Setup" Workflow:** Evaluated across initial ready state, first-feedback latency, full execution, rapid double-click debouncing, malformed/stale data rejection, and 30 warm benchmark runs.
2. **The "Enter (Simulated)" Workflow:** Evaluated across state safety gates (abstention rejection), paper-journal persistence (`smart_entry_attempts.jsonl`), duplicate idempotency, zero fabricated quote on outage, and absolute zero broker/exchange trading calls.

All 8 scenarios and 30 warm benchmark iterations passed with zero errors, zero network leaks, and zero modifications to historical protected datasets.

---

## 2. Analyse Button Performance & Latency Breakdown

### 2.1 Benchmark Distribution Across 30 Warm Iterations
Across 30 consecutive warm executions of `POST /api/tournament/analyse` using deterministic fixture candles on loopback port 8098:

| Metric | Measured Value (ms) | Target SLA / Hurdle | Status |
| :--- | :--- | :--- | :--- |
| **Sample Size ($N$)** | 30 runs | $\ge 30$ | Verified |
| **Latency $p_{50}$ (Median)** | **82.36 ms** | $< 250.0 \text{ ms}$ | **EXCEEDED** |
| **Latency $p_{90}$** | **110.86 ms** | $< 400.0 \text{ ms}$ | **EXCEEDED** |
| **Latency $p_{95}$** | **131.66 ms** | $< 500.0 \text{ ms}$ | **EXCEEDED** |
| **Latency Max** | **171.77 ms** | $< 1000.0 \text{ ms}$ | **PASS** |
| **Error Count** | **0 / 30 (0.0%)** | 0 errors | **PASS** |

### 2.2 Monotonic Per-Stage Backend Breakdown ($p_{50}$)
The tournament analytics engine reports monotonic execution timestamps across all sub-stages:

| Pipeline Stage | Function / Logic | Median Latency ($p_{50}$) | Proportion of Total |
| :--- | :--- | :--- | :--- |
| **Stage 1: Screening** | OHLCV parsing, boundary checks, feature cache alignment | **4.19 ms** | 5.09% |
| **Stage 2: Tournament Engine** | Evidence routing, model evaluation, regime inference | **0.08 ms** | 0.10% |
| **Stage 3: Decision Gate** | EV hurdle check, directional consensus, trade proposal | **0.03 ms** | 0.04% |
| **Total Backend Execution** | Internal server execution time | **4.33 ms** | 5.26% |
| **Transport & Serialization** | HTTP parse, JSON serialize/deserialize, loopback I/O | **78.03 ms** | 94.74% |
| **End-to-End API Roundtrip** | Complete client-measured duration | **82.36 ms** | 100.00% |

### 2.3 UI Feedback & Debouncing Integrity
- **Initial Feedback:** Clicking `#btn-analyse-setup` in the browser disables the button and activates the in-flight indicator in **215.1 ms**, well within the 300 ms human-perceptual feedback threshold.
- **Debouncing:** When two rapid clicks are delivered within 50 ms, `analysisInFlightRef.current` immediately suppresses the second event. Exactly one execution payload is sent to the backend.
- **Stale / Malformed Data Rejection:** When candles lack timestamps or contain discontinuities, the engine immediately yields `status: ABSTAIN` (`MALFORMED_CANDLES`), rendering an explicit abstention badge without freezing or crashing the UI.

---

## 3. Entry Button Safety & Simulation Isolation

### 3.1 Safety Gating & Validation Rules
The "Enter (Simulated)" button (`#btn-enter-simulated-trade`) was red-teamed against invalid and adversarial states:

1. **Abstention Gate:** Attempting to enter while the proposal is `ABSTAIN` or invalid is rejected with HTTP 400 (`Cannot enter simulated trade: candidate decision is not SMART_ENTRY_AVAILABLE`). Zero records are written.
2. **Provenance Gate:** Submitting an entry request without verified chart provenance (e.g. stale timestamp $> 7200\text{s}$ or missing candle window SHA-256) is rejected with HTTP 409 (`Entry blocked: proposal candle-window provenance is incomplete`).
3. **Paper Persistence:** A valid `SMART_ENTRY_AVAILABLE` proposal creates an attempt in `data/smart_entry_attempts.jsonl` with fixed entry price and immutable take-profit / stop-loss geometry.
4. **Idempotency:** Re-submitting the same payload with an identical `idempotency_key` returns the existing attempt (`att_34a8e0f7c490`) without duplicate ledger records.

### 3.2 Outage Behavior & Zero Quote Fabrication
During network disconnects or simulated provider outages:
- The comparator route (`/api/market/comparator`) returns `status: DATA_UNAVAILABLE` with `primary_price_usd: null` and `divergence_reason: EXTERNAL_NETWORK_BLOCKED`.
- **Zero \$80,000 Fallback Regression:** No synthetic or hardcoded prices are returned or displayed.

### 3.3 Zero Broker / Order Placement Assertion
A network audit captured **143 browser and API network requests** during the full workflow test.
- Prohibited exchange order placement endpoints (`coinbase.com/orders`, `kraken.com/AddOrder`, `binance.com/order`, `bitstamp.net/buy`): **0 detected (0.0%)**.
- External non-loopback network calls: **0 detected (0.0%)**.
- Real capital execution capability: **Permanently absent / disabled**.

---

## 4. Visual Evidence Artifacts

The following timestamped artifacts were captured via Chrome DevTools Protocol and are archived in `browser_evidence/`:
1. `01_analyse_initial_ready.png` (225,804 bytes): Initial state of the charting terminal with Analyse button active.
2. `02_analyse_in_flight_progress.png` (224,760 bytes): Analyse button disabled with progress indicator during calculation.
3. `03_analyse_complete_result.png` (223,318 bytes): Completed analysis displaying strategy breakdown.
4. `04_analyse_rapid_click_debounced.png` (221,139 bytes): Clean debouncing showing single-thread execution.
5. `05_analyse_stale_or_blocked_state.png` (228,114 bytes): Clean abstention handling on malformed/stale candles.
6. `06_entry_unauthorized_abstention.png` (224,276 bytes): Entry button safely disabled during abstained setup.
7. `07_entry_simulated_persisted.png` (223,068 bytes): Active simulated trade attempt persisted in paper ledger.
8. `08_monitoring_zero_fake_quote_null_price.png` (222,823 bytes): Clean data-unavailable state with zero synthetic prices.

