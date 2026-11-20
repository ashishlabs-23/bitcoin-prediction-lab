# BTCognitive V33.5 — API and UI Verification Document
**Milestone:** V33.5 — Decoupled Analysis, Actionable Levels, and Historical Evidence  
**Authors:** Agent 10 (Analysis API and Orchestration Engineer) & Agent 11 (Frontend Actionability & User-Experience Engineer)  
**Status:** Governed & Verified Specification  

---

## Section 1: Analysis API Architecture & Endpoints

### 1.1 Endpoint Overview
BTCognitive exposes two core analysis and evidence endpoints under the `/api/tournament` router:
1. `POST /api/tournament/analyse`: Evaluates causal market conditions, computes multi-scale market intelligence, detects 4h HTF breakout setups, and evaluates 5-question trade authorization.
2. `GET /api/tournament/historical-evidence` (with alias `GET /api/historical_evidence`): Serves the authoritative 194-trade retrospective research dataset, including 110-trade retained and 84-trade excluded partitions.

### 1.2 Strict Invariants
- **Non-Execution Invariant:** Live trading is permanently `DISABLED`. The API creates zero simulated trade attempts (`attempts_created = 0`) and operates strictly in `is_read_only = true` mode.
- **Decoupling Invariant:** Stale data or blocked trade eligibility NEVER suppresses or blanks Output A (`market_intelligence`). Market intelligence is served with appropriate data quality notices.
- **Directional Non-Conflation:** Volatility envelopes, excursion quantiles, and Donchian location quality are NEVER conflated with directional return prediction or trade win probability.
- **Concurrency & Idempotency:** Endpoints acquire a 10.0-second execution lock to prevent thread starvation. Duplicate requests with identical payload SHA-256 digests return cached responses within 10 seconds. Duplicate `request_id` keys with differing payloads return HTTP 409 (`Conflict`).
- **Heavy Backtest Decoupling:** `force_fresh_tournament = true` on interactive endpoints is rejected with HTTP 400 (`Bad Request`). Multi-year backtests must run via the offline CLI.

---

## Section 2: Five Decoupled Status Dimensions

To eliminate confusion between technical data feed health, technical breakout signals, research candidate eligibility, and live trading permissions, V33.5 standardizes five independent status dimensions across all responses:

```
+--------------------------------------------------------------------------------------------------+
|                                    BTCognitive V33.5 Status Taxonomy                              |
+--------------------------------------------------------------------------------------------------+
| 1. analysis_execution_status    :: SUCCESS | PARTIAL_SUCCESS | FAILED                             |
| 2. data_freshness_status        :: FRESH | STALE | MISSING | INVALID                             |
| 3. setup_status                 :: NO_SETUP | SETUP_FORMING | TRIGGER_CONFIRMED | BLOCKED |       |
|                                    DATA_UNAVAILABLE                                              |
| 4. research_eligibility_status  :: RESEARCH_CANDIDATE | NOT_ELIGIBLE | INSUFFICIENT_EVIDENCE       |
| 5. authorization_status         :: OFFLINE_RESEARCH_ONLY | DISABLED                               |
+--------------------------------------------------------------------------------------------------+
```

### Detailed State Transitions:
1. **`analysis_execution_status`:**
   - `SUCCESS`: The entire pipeline completed cleanly.
   - `PARTIAL_SUCCESS`: Core market intelligence completed, but optional tournament or live quote degraded gracefully.
   - `FAILED`: Unrecoverable validation failure (e.g., malformed candle series, missing mandatory columns).
2. **`data_freshness_status`:**
   - `FRESH`: Closed candle snapshot observed age $\le 2.0$ hours (or $3.0$ hours depending on configured max age) with 0 missing hourly candles in the last 168 hours.
   - `STALE`: Data timestamp is valid, but observed age exceeds threshold. Live trade evaluation is locked to `BLOCKED`.
   - `MISSING`: Candle payload is empty or dataset file not found.
   - `INVALID`: Candle sequence contains negative prices, non-monotonic timestamps, or non-finite values.
3. **`setup_status`:**
   - `NO_SETUP`: Technical indicators evaluated, regime compatible, but price is within the 20-bar Donchian channel. No breakout condition exists.
   - `SETUP_FORMING`: Price is approaching within 100 bps of the 20-bar range high on the current bar.
   - `TRIGGER_CONFIRMED`: A fully completed 4h candle close has strictly exceeded the 20-bar range high under a confirmed compatible regime.
   - `BLOCKED`: Technical setup disqualified due to incompatible regime (`TRENDING_BEARISH`, `RANGE_BOUND`, `TRANSITION_UNSUPPORTED`) or stale data.
   - `DATA_UNAVAILABLE`: Fewer than 84 hourly bars (21 4h bars) available.
4. **`research_eligibility_status`:**
   - `RESEARCH_CANDIDATE`: Trigger confirmed under compatible regime; qualifies for shadow observation.
   - `NOT_ELIGIBLE`: Disqualified by regime mismatch, stale data, or negative economics.
   - `INSUFFICIENT_EVIDENCE`: Directional evidence unproven ($p \ge 0.20$ vs drift) or prospective hurdle unmet (< 100 clean blocks).
5. **`authorization_status`:**
   - `OFFLINE_RESEARCH_ONLY`: Analysis and research terminal visualization authorized.
   - `DISABLED`: Real broker execution permanently disabled.

---

## Section 3: Actionability Fields Specification

The following four fields are mandatory on both the root response and the `htf_setup` object:

| Field Name | Type | Formula / Origin | Diagnostic Purpose |
| :--- | :--- | :--- | :--- |
| `breakout_reference` | float | 20-bar Donchian channel high $[t-20, t-1]$ | Concrete price level that must be breached by a completed 4h candle close. |
| `distance_to_trigger_bps` | float | $\frac{\text{breakout\_ref} - P_{\text{ref}}}{P_{\text{ref}}} \times 10{,}000$ | Standardized basis point distance to trigger. Positive = below trigger; Negative = breached. |
| `distance_to_trigger_atr` | float | $\frac{\text{breakout\_ref} - P_{\text{ref}}}{\text{ATR}_{14}^{4\text{h}}}$ | Volatility-normalized distance to trigger. Expressed in 4-hour ATR units. |
| `next_required_condition` | string | Explicit deterministic string | Human and machine parseable diagnostic explaining exact market event required. |

---

## Section 4: Frontend Actionability & User-Experience Verification

### 4.1 Component Architecture & DOM Element Directory

The BTCognitive V33.5 Analysis and Strategy Tournament dashboard interface is organized into structural components with standardized DOM IDs:

| DOM Element ID | Component Name | Semantic Role & Content | Accessibility Attributes |
| :--- | :--- | :--- | :--- |
| `#btn-analyse-setup` | Analysis Trigger Button | Initiates integrated market analysis & strategy screening | `role="button"`, `minHeight="44px"`, `minWidth="44px"`, `aria-label` |
| `#analysis-progress` | Workflow Stepper | Renders 4-step execution progress & ms timings | `role="status"`, `aria-live="polite"`, `aria-atomic="true"` |
| `#analysis-market-state` | Market State Bar | Displays feed origin, snapshot timestamp, staleness | Dynamic text node, monospace formatting |
| `#card-primary-htf-assessment` | Primary HTF Strategy Card | Displays Strategy D lifecycle, Donchian bounds, trigger | Glass-card container with semantic hierarchy |
| `#text-htf-analysis-id` | Analysis Trace Tag | Displays unique server analysis hash (`ana_...`) | Font-mono, 0.72rem slate tag |
| `#badge-htf-setup-status` | Setup Lifecycle Badge | High-contrast status indicator (5 states) | `font-weight: 800`, uppercase status |
| `#text-htf-regime` | Confirmed Regime Field | Canonical market regime string | High-contrast bold text |
| `#text-htf-trigger` | Trigger Status Field | Breach status or blocking reason | High-contrast bold text |
| `#text-htf-breakout-ref` | Breakout Reference Level | Upper Donchian Channel ceiling ($CH_t$) | Formatted USD price or "Unavailable" |
| `#text-htf-distance-bps` | Distance to Trigger (bps) | Signed basis points to breakout boundary | Signed bps with color-coded polarity |
| `#text-htf-distance-atr` | Distance to Trigger (ATR) | Remaining distance in 4h ATR multiples | Float multiple (e.g. `0.45x ATR`) |
| `#text-htf-entry` | Entry Reference Field | Causal entry price (next bar open / live) | Formatted USD price or "Unavailable" |
| `#text-htf-stop` | Stop Reference Field | Structural stop loss (channel low) | Formatted USD price or "Unavailable" |
| `#text-htf-target` | Target Reference Field | 1.5R expansion target level | Formatted USD price or "Unavailable" |
| `#text-htf-next-condition` | Next Required Condition | Actionable requirement to transition state | Descriptive narrative guidance |
| `#text-htf-candle-details` | Completed 4h Bar Info | Close, Donchian range, incomplete bar warning | Formatted currency and warning icons |
| `#text-htf-evidence-badges` | Governance Badges Bar | Freshness, Retrospective, Prospective, Auth | Flex container with 4 color-coded badges |
| `#text-htf-explanation` | Detailed Narrative Reason | Comprehensive multi-sentence rationale | Border-top separated text block |
| `#historical-research-evidence-panel` | Historical Evidence Panel | 194-trade backtest statistics & subgroup metrics | Standalone glass-card container |

---

### 4.2 Before vs. After UI Actionability Comparison

| Dimension | Before V33.5 Implementation | After V33.5 Implementation | Operational Benefit |
| :--- | :--- | :--- | :--- |
| **Outcome Heading** | Generic `"ANALYSIS ABSTAINED"` with no immediate visual differentiation. | Explicit lifecycle headings: `"HTF SETUP BLOCKED"`, `"HTF SETUP FORMING"`, `"NO QUALIFYING SETUP"`. | Operator immediately recognizes whether an abstention is due to market conditions, data gaps, or regime filters. |
| **Trigger Distance Visibility** | Hidden inside nested sub-dictionaries (`completed_4h_bar.distance_to_breakout_bps`). | Prominently displayed in Reference Grid as both basis points (`#text-htf-distance-bps`) and ATR multiples (`#text-htf-distance-atr`). | Operators can quantify proximity to entry at a glance. |
| **Breakout Level Reference** | Only visible inside a raw range string `[$76,301 – $81,890]`. | Dedicated prominent metric: `#text-htf-breakout-ref` displaying formatted currency (e.g. `$81,890.00`). | Explicit identification of the technical level required for trade initiation. |
| **Next Required Condition** | Absent. The user had to infer what would make the setup qualify. | Dedicated guidance block (`#text-htf-next-condition`): e.g. `"4h candle close strictly > $81,890.00 under confirmed Bullish Trend"`. | Operators know the exact technical event required to unlock a candidate. |
| **Inactive Stop References** | Potential risk of displaying channel low as an active stop on inactive setups. | Strict fail-closed guard: Stop, Entry, and Target evaluate to `"Unavailable"` whenever status is not `SHADOW_CANDIDATE`. | Prevents catastrophic operator errors and false stop loss anchor assumptions. |
| **Stale Data Disclosure** | Small text disclaimer easily missed. | Prominent amber badge (`Data Freshness: MARKET_DATA_STALE (73.6h old)`) and market state banner. | Prevents execution or decision-making on out-of-date market information. |

---

### 4.3 Component Wireframe & Layout

```
+--------------------------------------------------------------------------------------------------+
|  [Home / Smart Entry Simulator]                                                                 |
|  AI-Assisted Smart Entry Simulator & Strategy Tournament       [🔬 Analyse Setup] [Market Term] |
+--------------------------------------------------------------------------------------------------+
|  🛡️ RESEARCH-ONLY SMART ENTRY SIMULATOR · STRICT NON-EXECUTION  [NO BROKER ROUTING] [ZERO CAPITAL]|
+--------------------------------------------------------------------------------------------------+
|  [Analysis Progress: Complete · Total 637.8 ms]                                                  |
|  1. Validate Candles: Complete | 2. Features/Regime: Complete | 3. Tournament: Not run | 4. Complete|
+--------------------------------------------------------------------------------------------------+
|  BTC-USD · 1h · Feed: Historical snapshot (STALE) · Snapshot close: $76,985.40 (STALE REFERENCE) |
+--------------------------------------------------------------------------------------------------+
|  🏛️ High-Timeframe Range Expansion Breakout (Historical Strategy Evidence)                       |
|  [RETROSPECTIVE RESEARCH ONLY] [Provenance: PARTIALLY_RESOLVED]                                  |
|  +--------------------+ +--------------------+ +--------------------+ +--------------------+    |
|  |       194          | |      43.81%        | |    +9.57 bps       | |     110 / 84       |    |
|  | Historical Trades  | |  Overall Win Rate  | | Net Expectancy (All)| | Retained / Excluded|    |
|  +--------------------+ +--------------------+ +--------------------+ +--------------------+    |
|  Retained Subgroup: +59.25 bps Net EV · 48.18% Win Rate (+6,518.0 bps net)                       |
|  [Separate Current Setup Assessment Banner]  [Prospective Validation: NOT VALIDATED Banner]      |
+--------------------------------------------------------------------------------------------------+
|  🎯 HTF SETUP BLOCKED                                                                            |
|  Market data is stale (73.6h old > 2.0h operational limit). Incompatible regime: Bearish Trend.  |
|                                                                                                  |
|  +--------------------------------------------------------------------------------------------+  |
|  | 🎯 PRIMARY STRATEGY: HTF RANGE EXPANSION BREAKOUT   [ana_ee29321e5f42]  [SETUP: BLOCKED]   |  |
|  |                                                                                            |  |
|  | Confirmed Regime: TRENDING_BEARISH               Trigger Status: STALE_DATA_BLOCKED        |  |
|  | Breakout Reference: $81,890.00                   Distance to Trigger: -567.6 bps (-0.46 ATR)|  |
|  | Entry Reference: Unavailable                     Stop Reference: Unavailable               |  |
|  | Target Reference: Unavailable                    Next Required: Regime change to BULLISH   |  |
|  |                                                                                            |  |
|  | Latest Completed 4h Close: $77,241.91 · 20-bar Donchian Range: [$76,301.02 – $81,890.00]   |  |
|  | ⚠️ Latest 4-hour candle is incomplete (2/4 closed 1h bars). Evaluated on latest closed 4h. |  |
|  |                                                                                            |  |
|  | [Data Freshness: STALE (73.6h)] [Historical Evidence: RETROSPECTIVE] [Prospective: 0/100]  |  |
|  | [Authorization: OFFLINE_RESEARCH_ONLY (Trading DISABLED)]                                   |  |
|  | ------------------------------------------------------------------------------------------ |  |
|  | Explanation: Market data is stale (73.6h old > 2.0h limit). Downward trending regime does   |  |
|  | not support long breakout expansion on Coinbase long-only spot.                            |  |
|  +--------------------------------------------------------------------------------------------+  |
+--------------------------------------------------------------------------------------------------+
```

