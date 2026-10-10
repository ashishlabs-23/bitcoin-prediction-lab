# Draft Resolver Contract & Audit Specification

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Document Status:** `DRAFT_CONTRACT — NOT SCIENTIFICALLY FROZEN (FREEZE DEFERRED TO 6A)`  
**Resolver Version Target:** `resolver_v1`  
**Date:** 2026-10-07  

---

## 1. Scope and Purpose

This document specifies the draft machine-readable contract, outcome state taxonomy, field definitions, and validation invariants for the entry/TP/SL outcome resolution engine.

> **CRITICAL INVARIANT:**  
> This specification is an architecture draft. It is **NOT** scientifically frozen. Scientific freeze occurs exclusively during Phase 6A after all G0 data, environment, and rights prerequisites are satisfied.

---

## 2. Machine-Readable Schema & Field Definitions

Every resolved trade outcome event must conform to the following schema structure:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TradeOutcomeResolutionEvent",
  "type": "object",
  "required": [
    "resolver_version",
    "decision_timestamp",
    "entry_timestamp",
    "fill_timestamp",
    "side",
    "upper_boundary",
    "lower_boundary",
    "vertical_horizon",
    "path_timestamps",
    "path_price_source",
    "first_touch",
    "same_timestamp_collision",
    "observed_order",
    "unresolved_intrabar_order",
    "timeout",
    "data_gap",
    "exact_boundary_touch",
    "crossing_between_samples",
    "realized_return",
    "outcome_state"
  ],
  "properties": {
    "resolver_version": { "type": "string", "example": "resolver_v1.0.0" },
    "decision_timestamp": { "type": "string", "format": "date-time", "description": "ISO 8601 UTC timestamp of the 15-minute decision bar close." },
    "entry_timestamp": { "type": "string", "format": "date-time", "description": "ISO 8601 UTC timestamp when entry order was evaluated/submitted." },
    "fill_timestamp": { "type": ["string", "null"], "format": "date-time", "description": "ISO 8601 UTC timestamp when entry order filled, or null if unfilled." },
    "side": { "type": "string", "enum": ["LONG", "SHORT"] },
    "upper_boundary": { "type": "number", "exclusiveMinimum": 0.0, "description": "Nominal price level of the upper barrier (TP for LONG, SL for SHORT)." },
    "lower_boundary": { "type": "number", "exclusiveMinimum": 0.0, "description": "Nominal price level of the lower barrier (SL for LONG, TP for SHORT)." },
    "vertical_horizon": { "type": "integer", "minimum": 60, "description": "Max holding duration in seconds from fill timestamp." },
    "path_timestamps": {
      "type": "array",
      "items": { "type": "string", "format": "date-time" },
      "description": "Monotonically increasing UTC timestamps of evaluated 1m path samples."
    },
    "path_price_source": { "type": "string", "enum": ["SPOT_1M_OHLCV", "SUB_MINUTE_TRADES", "ORDERBOOK_L2"] },
    "first_touch": {
      "type": ["string", "null"],
      "enum": ["UPPER", "LOWER", "VERTICAL_TIMEOUT", null],
      "description": "Barrier touched first in temporal sequence, or null if unresolvable."
    },
    "same_timestamp_collision": {
      "type": "boolean",
      "description": "True if both upper and lower boundaries were reached within the same discrete time sample."
    },
    "observed_order": {
      "type": ["string", "null"],
      "enum": ["UPPER_FIRST", "LOWER_FIRST", null],
      "description": "True physical touch order if sub-sample ticks were observable; null if unobservable."
    },
    "unresolved_intrabar_order": {
      "type": "boolean",
      "description": "True if same_timestamp_collision occurred and sub-sample tick order was unobservable."
    },
    "timeout": { "type": "boolean", "description": "True if vertical horizon elapsed without touching upper or lower boundary." },
    "data_gap": { "type": "boolean", "description": "True if missing bars or irregular timestamps exceeded allowable gap tolerance." },
    "exact_boundary_touch": { "type": "boolean", "description": "True if high/low touched the barrier exactly without exceeding it." },
    "crossing_between_samples": { "type": "boolean", "description": "True if price gapped over the barrier between consecutive samples." },
    "realized_return": { "type": ["number", "null"], "description": "Net realized return fraction including slippage and fees; null on data failure." },
    "outcome_state": {
      "type": "string",
      "enum": [
        "TP_FIRST",
        "SL_FIRST",
        "TIMEOUT",
        "UNRESOLVED_INTRABAR",
        "DATA_GAP",
        "DATA_UNAVAILABLE",
        "PROVENANCE_FAILURE"
      ]
    }
  }
}
```

---

## 3. Strict Distinctions & Semantic Invariants

### 3.1 Null vs. Zero Semantics
- `UNOBSERVABLE = null`: Represents information that physically does not exist in the source dataset (e.g. sub-minute order of high/low within a 1m OHLCV bar).
- `OBSERVED_ZERO = 0.0`: Represents an explicitly observed numerical quantity equal to zero (e.g. `realized_pnl = 0.0` on a breakeven exit).
- Implementations must NEVER substitute `0` for `null` or vice-versa.

### 3.2 Dual-Touch Collision Resolution Policy
When a single 1-minute bar satisfies both $High \ge UpperBoundary$ and $Low \le LowerBoundary$:
1. If `observed_order` is `null`:
   - Primary conservative resolution: `outcome_state = "SL_FIRST"`.
   - Flags set: `same_timestamp_collision = true`, `unresolved_intrabar_order = true`.
2. Secondary sensitivity analysis:
   - Evaluator must run parallel TP-first sensitivity passes to quantify labeling ambiguity.
   - Ambiguous samples must not be silently coerced into unambiguous positive training labels.

---

## 4. Comprehensive Resolver Audit Matrix

| Component / Module | Resolution Mechanism | Strengths | Blocking Deficiencies for Track V3 | Action Required |
|---|---|---|---|---|
| `backtest.simulate::check_position_closure_high_low` | Single-bar high/low comparison; stop-first | Fast, lightweight | No sub-path sequencing; no latency/gap modeling; no collision metadata | Retain for legacy backtests; do not use as research authority |
| `engine.arena_accounts::evaluate_candle` | Streaming multi-candle evaluator | Handles timeouts | Paper accounting logic; silent bar drop | Retain for Arena live evaluation |
| `engine.decision_envelope` | Inline tick/bar thresholding | Dynamic wall-clock tracking | Tightly coupled to UI pipeline; duplicate code | Keep isolated in engine |
| `models.conditional_path_engine` | Multi-bar vector path evaluation | Vectorized pandas operations | Fixed horizon only; no gap/provenance audit | Keep in conditional research |
| `research.target_validation_v2` | Triple barrier labeling | Distinguishes dual-touch ambiguity | Omits fill simulation; labels as NaN rather than recording structured metadata | Reference for 6B test oracle |
| `research.post_repair_outcome_resolver` | 24-hour MFE/MAE tracking | Measures continuous excursion | Fallback to synthetic high/low=close | Incompatible with discrete barrier exits |
| `backtest.market_memory::resolve_pending_outcomes` | 24-hour directional return at horizon | Fast batch database updater | No barrier touch or path evaluation | Operational persistence only |
| **`ResearchOutcomeResolver_v1` (New — Planned 6A/6B)** | Sub-path 1m discrete barrier traversal + dual-oracle verification | Strictly adheres to schema; records collisions & unobservables; deterministic | Requires approved 1m dataset snapshot and 6A scientific freeze | **Implement in Phase 6B** |

---

## 5. Dual-Oracle Verification Plan (Phase 6B Preview)

When implemented in Phase 6B, `ResearchOutcomeResolver_v1` will be paired with an independent, pure-Python reference oracle `ReferenceOracle_v1`.

- **Test Architecture:** Hypothesis property-based testing and 10,000-trial differential testing.
- **Tolerance:** 0.0% divergence on all discrete outcome states (`TP_FIRST`, `SL_FIRST`, `TIMEOUT`, `UNRESOLVED_INTRABAR`, `DATA_GAP`).
