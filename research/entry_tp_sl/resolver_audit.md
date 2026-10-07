# Entry/TP/SL Resolver Audit — G0

**Status: BLOCKED. No resolver was selected, modified, or implemented.** The repository contains no `resolution_service.py`, `ResolutionService`, or `resolution_service` symbol. Existing code is split across incompatible domains and tie policies.

| Implementation | Current role / callers | Semantics and limitations | G0 decision |
|---|---|---|---|
| `backtest/simulate.py::check_position_closure_high_low` | Imported by `engine/arena_accounts.py` and `engine/arena_runner.py`; tests in `tests/test_high_low_closure.py`; also supports existing backtests | Single OHLC bar, stop-first when both barriers touch, fills at barrier price; does not model gaps, latency, actual fill, 1-minute sequencing, data gaps, or full trade lifecycle | Not canonical for new research without versioned specification and differential oracle |
| `engine/arena_accounts.py::evaluate_candle` | Called from Arena evolution flow | Delegates TP/SL to the helper, adds max-hold timeout and regime invalidation; outcome is paper-accounting behavior, not a research resolver | Legacy paper execution; do not use as research authority |
| `engine/decision_envelope.py` inline resolution | Called within the current decision/evidence pipeline | Reimplements OHLC touch detection; stop-first dual touch; timeout based on elapsed seconds. Not independently tested against the Arena helper and does not model exchange fills | Duplicate outcome logic; not canonical |
| `models/conditional_path_engine.py::ConditionalPathEngine` | `api/routes_terminal.py` dynamically instantiates it; test in `tests/test_adaptive_mechanism_lab.py` | Loops over supplied DataFrame bars and barrier multipliers; stop-first on same-bar dual touch; `INVALID` when horizon rows are absent. Input interval/path provenance is not established here | Research/conditional-path analysis only |
| `research/target_validation_v2.py` triple-barrier labeling | Research evaluator and tests | Dual crossing is marked ambiguous/NaN, unlike stop-first execution helpers; labels use OHLC bars and timeout labels | Research label implementation; not a fill resolver |
| `research/post_repair_outcome_resolver.py::PostRepairOutcomeResolver` | Post-repair outcome monitoring | Resolves 24-hour MFE/MAE, not TP-first/SL-first. Can fall back to sparse prediction prices with synthetic high/low=price, which is invalid for entry/TP/SL path resolution | Not suitable; do not reuse |
| `backtest/market_memory.py::resolve_pending_outcomes` | Called by `engine/inference_service.py` | Resolves directional returns from a single current price after a horizon; no barrier-order path | Not suitable |
| `engine/observatory.py::ForecastAccuracyObservatory.resolve_outcome` | HAR terminal and observatory | Resolves 168-hour realized variance envelopes, not intraday trade barriers | Explicitly out of scope |
| `engine/hawkes_shadow_session.py::resolve_outcome` | Hawkes shadow tests/runtime | Resolves 5-minute MFE/MAE outcomes, not chosen TP/SL execution | Shadow-only; not suitable |

## Decision

Do not bind the new track to any existing implementation. At 6A, define a **versioned research resolver** from the frozen EntryOpportunity/TripleBarrier/ExecutionCost contract, then in 6B implement a deliberately simple independent reference oracle and differential/property tests. Required outcomes remain `TP_FIRST`, `SL_FIRST`, `TIMEOUT`, `UNRESOLVED_INTRABAR`, and `DATA_GAP`; no unverified 1-minute path means no outcome label.

Failure states must not collapse:

- `PROVENANCE_FAILURE`: hash, source lineage, timestamp semantics, or PIT integrity cannot be certified.
- `DATA_UNAVAILABLE`: required path interval or coverage is absent.
- `MODEL_FAILURE`: a later model/artifact/runtime fault (no model is built in G0).
- `NO_SIGNAL`: valid inputs and computation, but no eligible setup or an explicit abstention.

This audit changes no existing resolver or outcome implementation.
