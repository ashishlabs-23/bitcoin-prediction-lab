# Outcome Resolver Architectural Decision — Entry/TP/SL Research Track

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Phase:** `G0 Foundation Remediation`  
**Date:** 2026-10-07  
**Decision Status:** `DECISION_RECORDED`  

---

## 1. Comprehensive Comparison of Existing Resolvers

The BTCognitive codebase contains nine historical and operational outcome-resolution routines. None of these routines was built for the 15-minute decision / 1-minute path-resolution research track, and their underlying physical and statistical assumptions conflict.

| Implementation | Input Data & Interval | Time Semantics & Horizon | Touch & Boundary Rule | Same-Bar TP+SL Policy | Missing/Gap Handling | Price Field Used | Intrabar Order Observable |
|---|---|---|---|---|---|---|---|
| **1. `backtest.simulate::check_position_closure_high_low`** | Single OHLC bar (variable timeframe) | Candle start/end timestamp; bar horizon | Exact touch ($H \ge TP$ or $L \le SL$) | Conservative SL-first | None (single bar only) | `high`, `low`, nominal `tp`, `sl` | No |
| **2. `engine.arena_accounts::evaluate_candle`** | Streaming klines (1m or custom) | Multi-candle timeout + regime expiry | Delegates to `check_position_closure_high_low` | Conservative SL-first | Skips missing bars silently | `high`, `low`, `close` | No |
| **3. `engine.decision_envelope::inline resolution`** | Streaming ticks / bar envelopes | Wall-clock elapsed seconds | Threshold comparison against envelope limits | Stop-first | Drops stale envelopes | `price`, `high`, `low` | No |
| **4. `models.conditional_path_engine::ConditionalPathEngine`** | Historical DataFrame (hourly/daily) | Fixed bar count horizon (e.g. 24 bars) | Barrier multipliers on cumulative path | Stop-first on dual touch | Returns `INVALID` if horizon rows < target | `high`, `low` | No |
| **5. `research.target_validation_v2::triple_barrier`** | Historical OHLC DataFrame | Fixed bar count (vertical barrier) | First bar where high/low touches barrier | Returns `Ambiguous / NaN` (dual touch) | Propagates NaN / drops row | `high`, `low`, `close` | No |
| **6. `research.post_repair_outcome_resolver::PostRepairOutcomeResolver`** | 24-hour prediction ledger | 24-hour fixed elapsed window | MFE/MAE extrema tracking (no discrete TP/SL) | N/A (calculates continuous excursion) | Falls back to synthetic high/low = price | Sparse prediction prices or klines | No |
| **7. `backtest.market_memory::resolve_pending_outcomes`** | Database predictions & current spot price | 24-hour horizon elapsed | Directional return at horizon maturity ($P_{end} - P_{0}$) | N/A (no intermediate barriers) | Evaluates only if $\Delta t \ge 24\text{h}$ | Single close/spot price | No |
| **8. `engine.observatory::ForecastAccuracyObservatory.resolve_outcome`** | Hourly OHLCV series | 168-hour (7-day) realized variance window | Realized variance band containment | N/A (variance bounds, not trade orders) | Requires continuous 168h series | Realized variance ($RV_{168h}$) | No |
| **9. `engine.hawkes_shadow_session::resolve_outcome`** | 5-minute tick/bar stream | 5-minute fixed excursion window | Extrema over 5 minutes | N/A (MFE/MAE tracking) | Drops incomplete windows | High/low ticks | No |

---

## 2. Key Inconsistencies Across Existing Implementations

1. **Dual-Touch (Collision) Divergence:**
   - `backtest.simulate`, `engine.arena_accounts`, and `models.conditional_path_engine` enforce an unconditional **SL-first** policy.
   - `research.target_validation_v2` labels dual-touch bars as **Ambiguous / NaN**.
   - None of the existing implementations explicitly records whether intrabar ordering was physically observable or marks the observation as `UNRESOLVED_INTRABAR_ORDER`.

2. **Horizon and Maturity Incompatibility:**
   - Production/observatory resolvers operate on 24-hour or 168-hour macroscopic windows.
   - The Entry/TP/SL track requires a 15-minute decision interval with fine-grained (1-minute or finer) sub-path resolution over bounded intraday holding horizons (e.g., 1h to 4h).

3. **Data Quality & Gap Semantics:**
   - Production helpers silently bridge or ignore missing bars.
   - Scientific research resolution requires explicit failure tracking (`DATA_GAP`, `INSUFFICIENT_SUBPATH_COVERAGE`, `CORRUPT_SAMPLE_ORDER`) rather than synthetic imputation.

---

## 3. Decision

**Selected Decision:** `B) VERSION_A_NEW_RESEARCH_RESOLVER`

### Rationale:
1. Reconciling an existing operational helper (Decision A) would risk altering legacy production and arena behavior, or force research compromises due to backward-compatibility constraints.
2. The Entry/TP/SL track requires strict scientific determinism, explicit separation of observable vs. unobservable states, and dual-oracle verification (an optimized vector resolver paired with an independent pure-Python oracle).
3. Therefore, a clean, standalone, versioned research resolver (`ResearchOutcomeResolver_v1`) must be established specifically for this research track.

---

## 4. Primary Scientific Policy for Research Resolution

1. **Observed Intrabar Ordering:** When sub-minute / trade-level timestamps distinguish the barrier hits, resolution strictly follows the observed physical sequence.
2. **Unobservable Order Collisions (Same-Bar Dual Touch):**
   - Primary research labeling policy: Conservative **SL-first**.
   - Machine metadata contract MUST record `same_timestamp_collision=true` and `unresolved_intrabar_order=true`.
   - The evaluation framework will retain secondary **TP-first sensitivity analysis** to quantify boundary ambiguity without corrupting the primary conservative baseline.
3. **No Silent Inference:** The resolver will never fabricate or infer tick sequences (e.g., assuming open-to-high-to-low-to-close) when sub-bar order is unobserved.
4. **Failure State Preservation:** Missing data, gaps, or insufficient path lengths will emit explicit categorical states (`DATA_GAP`, `DATA_UNAVAILABLE`) rather than numeric fallbacks.

---

## 5. Next Steps (Gated)

- **G0 Phase:** Establish the non-frozen Draft Resolver Contract and Audit Matrix (`resolver_contract.md`).
- **6A Phase (Once G0 Unblocks):** Scientifically freeze the Resolver Contract.
- **6B Phase:** Implement the versioned resolver, independent reference oracle, and property/differential test suite.
