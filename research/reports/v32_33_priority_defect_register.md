# BTCognitive V32.33 — Priority-Ranked Defect Register & Resolution Ledger

**Date:** 2026-10-25  
**Version:** V32.33  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Governing Priority Formula:**  
$$\text{Priority} = \text{Severity} \times \text{User Impact} \times \text{Likelihood} \times \text{Downstream Dependency}$$  
(Scale: 1 to 5 per dimension; Max Priority = 625)

---

## 1. Master Defect Priority Ledger

| Defect ID | Title & Summary | Severity (1-5) | Impact (1-5) | Likelihood (1-5) | Dependency (1-5) | Priority Score | Status | Resolution Phase |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DEF-01** | **MEIE Sub-Hourly Empirical Regression vs Multi-Venue Cost Coupling** | 5 | 4 | 5 | 5 | **500** | **RESOLVED** | Phase 4 (Fixed & Tested) |
| **DEF-02** | **Sub-Hourly 15m Scenario Preview AI Frequency Mismatch** | 4 | 4 | 4 | 4 | **256** | **RESOLVED** | Phase 4 (Fixed & Tested) |
| **DEF-03** | **Microstructure Feature Requests on Pure Historical OHLCV** | 4 | 3 | 4 | 4 | **192** | **RESOLVED** | Phase 4 (Fixed & Tested) |
| **DEF-04** | **Client-Side Indicator Recomputation Overhead on 1m Timeframe** | 2 | 3 | 3 | 2 | **36** | **PLANNED (P2)** | Documented Workaround |

---

## 2. In-Depth Root-Cause Analysis & Verification Logs

### Defect DEF-01: MEIE Sub-Hourly Empirical Regression vs Multi-Venue Cost Coupling
- **Priority Score:** **500 / 625** (P0-C: Quantitative Validity & Economic Edge)
- **Symptom:** `test_meie_ignition_reproduction` in `tests/test_v9_data_integrity.py` failed with:
  `AssertionError: assert 71.7 == 32.2 ± 0.1` on `up["net_ev_bps"]`.
- **Root Cause Analysis:**  
  When `engine/strategy_selection.py` was updated to support multi-venue execution costs from `ExecutionCostModel`, it defaulted to `"COINBASE_ADVANCED_87BPS"` (87.0 bps round-trip friction) and scaled gross EV by `volatility_sigma * 10000.0` when parameters were omitted from the market snapshot. However, the canonical sub-hourly (15m) MEIE mechanisms have specific empirical itemized drag schedules (`MEIE-IGNITION`: 9.3 bps, `MEIE-ABSORPTION`: 3.5 bps, `MEIE-VACUUM`: 6.5 bps, `MEIE-TOXICITY`: 9.5 bps, `MEIE-COMBINED`: 8.0 bps) and calibrated regression formulas:
  $$\text{gross\_long} = \text{round}((\text{tp\_long} - 50.0) \times 1.8 + 8.0, 1)$$
  $$\text{drag\_long} = 9.3\text{ bps}$$
  $$\text{net\_long} = 41.5 - 9.3 = 32.2\text{ bps}$$
- **Implemented Fix:**  
  In [strategy_selection.py](file:///c:/Projects/BTCognitive/BTCognitive/engine/strategy_selection.py), established clean parameter dispatch:
  1. If `snap.get("cost_scenario")` is present, query `ExecutionCostModel.get_round_trip_friction_bps()`. If omitted, default to the mechanism's canonical empirical drag.
  2. If `snap.get("volatility_sigma")` is present, scale gross EV by volatility. If omitted, apply the calibrated empirical regression formulas.
- **Regression Verification:**  
  - `python -m pytest tests/test_v9_data_integrity.py -v` -> 5 passed in 1.98s.
  - `python -m pytest tests/test_strategy_selection_engine.py -v` -> 9 passed in 0.45s.
  - `python -m pytest tests/test_v32_16_audit_resolutions.py -v` -> 6 passed in 0.39s.
- **Resolution Status:** **CLOSED / VERIFIED**.

---

### Defect DEF-02: Sub-Hourly 15m Scenario Preview AI Frequency Mismatch
- **Priority Score:** **256 / 625** (P0-A: Safety & Research Boundaries)
- **Symptom:** Sub-hourly (15m) scenario preview requests could erroneously request hourly volatility model forecasts from `HAR-RS-DOW-v1.0`, resulting in temporal lookahead or frequency mismatch.
- **Root Cause Analysis:**  
  The primary production volatility risk model (`HAR-RS-DOW-v1.0`) is calibrated exclusively on hourly candles for a 168-hour variance target. Evaluating it on 15m candles without frequency adjustment violates econometric temporal alignment.
- **Implemented Fix:**  
  In `engine/scenario_contract_engine.py` and `api/routes_arena.py`, sub-hourly requests return typed `DATA_FREQUENCY_UNSUPPORTED` and `MODEL_TIMEFRAME_INCOMPATIBLE`, while preserving verified hourly reference price, freshness timestamps, and continuity segment IDs.
- **Regression Verification:**  
  - `test_scenario_contract_subhourly_preserves_verified_hourly_metadata` PASSED.
  - `test_arena_active_paper_position_returns_typed_subhourly_state` PASSED.
- **Resolution Status:** **CLOSED / VERIFIED**.

---

### Defect DEF-03: Microstructure Feature Requests on Pure Historical OHLCV
- **Priority Score:** **192 / 625** (P0-B: Market-Data Integrity)
- **Symptom:** Historical backtest scripts querying order-flow features (OFI, VPIN, Hawkes intensity, bid-ask spread) against `data/raw/ohlcv.parquet` could fall back to synthetic constants, corrupting empirical validity.
- **Root Cause Analysis:**  
  Pure historical OHLCV data contains only price and volume candles; it does not contain Level-2 order book depth or signed trade ticks. Substituting synthetic placeholders (e.g. `0.65` for OFI, `2.2` for Hawkes) disguised missing data as empirical observations.
- **Implemented Fix:**  
  In `engine/data_verification.py` and `engine/strategy_selection.py`, all fallback placeholder substitutions were eliminated. When required order-flow telemetry is absent, the system fails closed with typed reason `UNAVAILABLE_ORDER_FLOW_TELEMETRY` and forces an `ABSTAIN` decision.
- **Regression Verification:**  
  - `test_missing_telemetry_causes_archetype_abstain` PASSED.
  - `test_no_placeholder_constants_in_strategy_and_router` PASSED.
- **Resolution Status:** **CLOSED / VERIFIED**.

---

### Defect DEF-04: Client-Side Indicator Recomputation Overhead on 1m Timeframe
- **Priority Score:** **36 / 625** (P2: Maintainability & Efficiency)
- **Symptom:** On the 1m timeframe with all 6 indicator overlays enabled (EMA 20/50, BB, Conformal, RSI, ATR, ADX), client CPU utilization spikes during rapid Coinbase WebSocket ticker updates.
- **Root Cause Analysis:**  
  Indicator series are currently recomputed synchronously on each WebSocket bar update on the main browser thread.
- **Current Mitigations & Workaround:**  
  - Frontend enforces in-flight request deduplication and 29.5 req/min polling budget limiter.
  - Steady-state rendering operates smoothly without browser freezing.
  - Long-term enhancement: Offload client-side indicator math to a dedicated Web Worker during rapid market bursts (scheduled for P2).
- **Resolution Status:** **MONITORED / ACCEPTED MITIGATION**.
