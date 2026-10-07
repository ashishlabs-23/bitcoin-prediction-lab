# Repository Outcome Resolver Reachability & Authority Audit (Phase 6B)

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Resolver Version:** `ENTRY_TP_SL_RESOLVER_V1`  
**Audit Date:** `2026-10-07`  
**Status:** `AUDIT_COMPLETE`  

---

## 1. Executive Summary

This audit establishes the explicit reachability and domain boundaries of all outcome-resolution code in the BTCognitive repository following the implementation of Phase 6B.

> **PRIMARY AUTHORITY INVARIANT:**  
> `research.entry_tp_sl.triple_barrier.TripleBarrierEngine` is the **EXCLUSIVELY AUTHORIZED CANONICAL RESOLVER** for the Entry/TP/SL Research Track.  
> No legacy, product, or test resolver may be invoked or referenced for scientific label generation, backtesting, or model evaluation within this track.

---

## 2. Complete Classification Matrix

| Module & Symbol | Domain / Callers | Scientific / Runtime Behavior | Reachability Classification | Boundary Rule |
|---|---|---|---|---|
| **`research.entry_tp_sl.triple_barrier::TripleBarrierEngine`** | Entry/TP/SL Track V3 (`research/entry_tp_sl/`) | Discrete 1-minute path evaluator; frozen ATR14 barriers; conservative SL-first collision resolution with collision metadata; exact timeout price accounting. | **`RESEARCH_CANONICAL`** | **Primary Scientific Authority for Track V3.** |
| **`research.entry_tp_sl.reference_resolver::ReferenceOracle`** | Entry/TP/SL Test Harness (`tests/entry_tp_sl/`) | Independent pure-Python procedural oracle used for differential testing and property verification. | **`TEST_FIXTURE`** | Test-time oracle only. Not called in production. |
| **`backtest.simulate::check_position_closure_high_low`** | `engine/arena_accounts.py`, `engine/arena_runner.py`, legacy backtests | Single-bar high/low check; fills at nominal barrier; no gap or sub-minute sequence modeling. | **`LEGACY`** | Retained for backward compatibility with legacy 1h/4h backtests. **Forbidden in Track V3.** |
| **`engine.arena_accounts::evaluate_candle`** | Arena live paper execution engine | Evaluates streaming candles with max-holding timeout and regime invalidation. | **`PRODUCT`** | Operational live paper trading. **Forbidden in Track V3 research.** |
| **`engine.decision_envelope` (inline resolution)** | API / UI Terminal evidence router | Inline price thresholding for real-time dashboard visualization envelopes. | **`PRODUCT`** | UI/Terminal operational feature only. **Forbidden in Track V3.** |
| **`models.conditional_path_engine::ConditionalPathEngine`** | `api/routes_terminal.py` | Multi-bar vector excursion evaluator over arbitrary DataFrames. | **`LEGACY`** | Historical research tool. **Forbidden in Track V3.** |
| **`research.target_validation_v2::triple_barrier`** | Legacy research evaluation scripts | Triple barrier labeling that marks dual-touch as ambiguous/NaN. | **`TEST_FIXTURE`** | Legacy test fixture. **Forbidden in Track V3.** |
| **`research.post_repair_outcome_resolver::PostRepairOutcomeResolver`** | 24-hour longitudinal monitor | Continuous 24-hour MFE/MAE excursion resolver with synthetic price fallback. | **`LEGACY`** | Incompatible with discrete barrier stops. **Forbidden in Track V3.** |
| **`backtest.market_memory::resolve_pending_outcomes`** | `engine/inference_service.py`, `api/candle_manager.py` | Operational database updater computing directional horizon returns. | **`PRODUCT`** | Operational persistence layer only. **Forbidden in Track V3.** |
| **`engine.observatory::ForecastAccuracyObservatory.resolve_outcome`** | Observatory and HAR terminal | Resolves 168-hour realized variance containment envelopes. | **`PRODUCT`** | HAR-specific product feature. **Forbidden in Track V3.** |
| **`engine.hawkes_shadow_session::resolve_outcome`** | Hawkes shadow session monitor | 5-minute tick-based MFE/MAE tracking. | **`TEST_FIXTURE`** | Hawkes-specific shadow testing. **Forbidden in Track V3.** |

---

## 3. Structural Isolation Guarantees

1. **Zero Cross-Importation:** `research/entry_tp_sl/` imports zero resolution functions from `engine/`, `backtest/`, or legacy `research/`.
2. **Deterministic Inputs:** `TripleBarrierEngine` accepts only explicit `TradeContract` instances and `PathBar` sequences.
3. **No Dynamic Dispatch:** No factory or runtime registry can dynamically substitute a legacy resolver for `TripleBarrierEngine`.
