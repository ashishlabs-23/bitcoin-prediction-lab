# BTCognitive PRD Amendment V13 — User-Selected Strategy, Live Chart Overlay, Current Setup Evaluation & End-to-End Product Completion

**Document Version:** 13.0.0  
**Effective Date:** October 2026  
**Status:** APPROVED & GOVERNED  
**Supersedes:** PRD V12 Amendment (`docs/BTCognitive_PRD_Amendment_V12.md` preserved in historical records)  
**Parent PRD:** `docs/BTCognitive_Master_PRD.md`, `docs/BTCognitive_Master_PRD_v2_Continuation.md`  

---

## 1. Executive Summary & Core Mission

This Amendment specifies and governs **BTCognitive V13**, resolving the disconnect between the Strategy Tournament, Replay & Counterfactual Lab, and the main price chart.

In V13, the human user—not an automated opaque ranking heuristic—maintains sovereign control over which research strategy hypothesis to inspect, preview, and enable for chart overlay monitoring. 

### Non-Negotiable Operating & Epistemic Boundaries
1. **User Control Without Live Execution Authorization:** User selection of a strategy overlay is strictly a research and paper-monitoring visualization tool. Enabling an overlay **never** authorizes live trading, order submission, broker execution, or automatic production model promotion. `live_trading` remains permanently `DISABLED` and `model_authorization` remains `OFFLINE_RESEARCH_ONLY`.
2. **Overlay Default State:** All strategy overlays default to `OFF` (`OVERLAY_OFF`). An overlay is activated only upon explicit user action.
3. **Single Overlay Exclusivity:** Exactly one strategy candidate may drive the primary chart overlay at any time. Selecting or enabling another candidate instantaneously purges all prior Entry, TP, and SL lines and replaces them with the newly selected candidate's evaluation. No stale levels from prior candidates are permitted to persist.
4. **Zero Level Fabrication:** If a candidate's registered entry rules have not triggered on the latest completed candle, or if the strategy is blocked by market regime or data, the system strictly reports `NO_SETUP`, `BLOCKED_BY_REGIME`, or `BLOCKED_BY_DATA` accompanied by an explicit, transparent explanation. Under no circumstances may arbitrary percentages or fictitious price lines be projected.
5. **Strict Directional Geometry:** For Long setups, geometry must strictly obey $\text{SL} < \text{Entry} < \text{TP}$. For Short setups, geometry must strictly obey $\text{TP} < \text{Entry} < \text{SL}$. Any geometry violation immediately triggers `INVALID_LEVEL_GEOMETRY` and suppresses line rendering.

---

## 2. P0 Resolution: 15-Minute Dataset Integrity & Lineage (1,800 vs 601 Candles)

### Root Cause Audit
In V11, the pipeline ingested 1,800 valid 15-minute candles. In V12, an unparameterized default in `coinbase_15m_adapter.py` (`total_candles = 600`) truncated the historical parquet file on save, reducing valid history to 601 rows and discarding 1,200 verified candles.

### V13 Rectification
1. **Historical Backfill & Verification:** The canonical dataset (`data/cache/ohlcv_15m.parquet`) has been restored to 1,800 continuous 15-minute bars covering `2026-09-29T00:45:00Z` to `2026-10-17T18:30:00Z` (0 gaps, 1 contiguous segment, SHA-256: `e784c17c342ac3a5c9d3991786ec485d336be585ab88ff08ffa780cb8a34803f`).
2. **Atomic Merge & Non-Destructive Ingestion:** `coinbase_15m_adapter.py` default count is set to 1,800. The `persist()` method now performs an atomic merge: existing parquet records are indexed by epoch timestamp, incoming bars are merged and deduplicated, and the combined dataset is atomically written to temporary storage before being replaced. Historical rows are never silently truncated.

---

## 3. P0 Resolution: Drawdown Calculation Defect (>100% Defect Rectification)

### Root Cause Audit
In V12, strategy drawdown was calculated via an uncompounded arithmetic sum of basis-point returns:
$$\text{CumRet}_t = \sum_{i=1}^t \frac{r_{\text{net}, i}}{10{,}000}$$
For a series of consecutive losses, $\text{CumRet}_t$ dropped to $-1.2204$ while the peak was $+0.0236$, resulting in a reported maximum drawdown of:
$$\text{MaxDD}_{\text{arithmetic}} = 0.0236 - (-1.2204) = 1.2440 \quad (124.40\%)$$
For an unleveraged long-only account whose cash equity cannot fall below zero, this metric is mathematically defective.

### V13 Rectification
1. **Compounding Unleveraged Portfolio Equity:**
   Equity evolves multiplicatively from initial capital $E_0 = \$10{,}000$:
   $$E_t = E_{t-1} \cdot \left(1 + \frac{r_{\text{net}, t}}{10{,}000}\right) = E_0 \cdot \prod_{i=1}^t \left(1 + \frac{r_{\text{net}, i}}{10{,}000}\right)$$
   Drawdown at time $t$ is strictly bounded in $[0\%, 100\%]$:
   $$\text{DD}_t = \frac{\max_{0 \le s \le t} E_s - E_t}{\max_{0 \le s \le t} E_s} \times 100\%$$
2. **Initial Capital Prepending:** $E_0$ is prepended to the equity array, ensuring running peak correctly reflects pre-trade capital and accurately measures drawdowns incurred on immediate first-trade losses.
3. **Position-Sized Risk Metric:** In addition to full un-sized equity drawdown (75.60%), the engine calculates 10% risk-sized drawdown ($11.85\%$), reflecting realistic capital allocation.
4. **Audit Transparency:** The legacy metric is retained as `legacy_uncompounded_drawdown_pct` for historical regression verification.

---

## 4. User-Controlled Strategy Workflow Contract

The Live Terminal and Strategy Tournament dashboard provide four distinct user actions for each candidate:

| User Action | Purpose | Behavioral Specification | Live Trading Impact |
| :--- | :--- | :--- | :--- |
| **Inspect Contract** | Examine parameters, formulas, and empirical citations | Opens `ContractInspectionModal` displaying version, mathematical rules, indicators, literature DOIs, current setup state, and cost models. | Strictly read-only (`DISABLED`). |
| **Preview on Chart** | Inspect setup without enabling ongoing overlay | Evaluates current setup on latest completed candle and updates chart diagnostic banner with candidate status without drawing sticky price lines. | Read-only preview (`DISABLED`). |
| **Enable Research Overlay** | Activate chart price lines for real-time paper monitoring | Draws Entry (cyan dashed), TP (green solid), and SL (red solid) lines on main chart when valid setup exists. Displays detailed diagnostic banner. Automatically deactivates prior overlay. | Research monitoring only (`DISABLED`). |
| **Disable Overlay** | Remove active overlay | Clears all strategy price lines, resets chart banner to `OVERLAY: OFF`, and returns candidate button to default state. | None (`DISABLED`). |

---

## 5. Strategy-Specific Current Setup Contract

The backend endpoint `GET /api/tournament/setup/{strategy_id}` evaluates genuine registered rules on the latest completed candle and returns a typed JSON contract:

```json
{
  "strategy_id": "MTF_MOMENTUM_TREND",
  "strategy_name": "MTF Momentum Trend Following (Partial Exits & Breakeven)",
  "version": "1.0.0",
  "specification_hash": "a1b2c3d4e5f67890",
  "asset": "BTC-USD",
  "market_type": "spot",
  "required_timeframe": "1h",
  "source_timeframe": "1h",
  "latest_completed_candle_time": "2026-10-17T18:00:00Z",
  "reference_price": 81242.50,
  "observed_regime": "TRANSITION_UNSUPPORTED",
  "supported_regimes": ["TRENDING_BULL", "TRENDING_BEAR"],
  "is_regime_compatible": false,
  "rule_trigger_status": "NOT_TRIGGERED",
  "setup_state": "BLOCKED_BY_REGIME",
  "user_overlay_enabled": false,
  "direction": "LONG",
  "entry_price": null,
  "tp_price": null,
  "sl_price": null,
  "gross_reward_risk": null,
  "net_reward_risk": null,
  "stop_geometry_valid": true,
  "invalidation_rules": "None",
  "cost_assumptions_bps": 87.0,
  "blocking_reason": "Current market regime (TRANSITION_UNSUPPORTED) is not supported (requires TRENDING_BULL, TRENDING_BEAR).",
  "governance_state": "OFFLINE_RESEARCH_ONLY",
  "model_authorization": "OFFLINE_RESEARCH_ONLY",
  "execution_authorization": "DISABLED",
  "live_trading": "DISABLED"
}
```

### Supported Setup States
- `OVERLAY_OFF`: Overlay disabled by user; candidate evaluated in background.
- `SETUP_AVAILABLE`: Valid setup triggered; entry, TP, and SL calculated from registered rules.
- `SETUP_PREVIEW_AVAILABLE`: Valid setup available but overlay is currently disabled by user.
- `NO_SETUP`: Market regime is compatible, but bar indicators do not satisfy entry conditions.
- `BLOCKED_BY_REGIME`: Observed market regime is incompatible with strategy archetype.
- `BLOCKED_BY_DATA`: Insufficient warm-up history or stale data feed.
- `INVALID_LEVEL_GEOMETRY`: Stop/target geometry violation detected; levels suppressed.
- `ABSTAIN`: Meta-router explicitly abstaining during transition.

---

## 6. Replay & Counterfactual Lab Remediation

### Root Cause Audit
The V12 UI attempted to render `c.tp_price` and `c.sl_price` directly on counterfactual mechanism objects, while the backend API returned nested objects `upper_scenario` and `lower_scenario`. This mismatch caused all rows to fall back to generic placeholders (`Contract available / Inspect Contract`), while Toxicity displayed `Filter context`.

### V13 Rectification
1. **Telemetry & Scenario Binding:** Updated `web/app.js` to extract target prices, expected moves, and Sharpe ratios from `upper_scenario` and `lower_scenario`.
2. **VPIN & Hawkes Microstructure Flow:** Toxicity row now binds live empirical order flow telemetry: VPIN (`0.28`), Hawkes intensity parameter ($\beta = 2.2$), and Gate status (`PASS / BLOCK`).
3. **Working Contract Modal:** Clicking "Inspect Contract" on any mechanism opens `ContractInspectionModal` via `GET /prediction/counterfactual/contract/{genome_id}`, displaying underlying econometric formulas and perturbation parameters.

---

## 7. Verification & Acceptance Criteria Matrix

| Requirement | Acceptance Gate | Verification Evidence | Status |
| :--- | :--- | :--- | :--- |
| **V13-REQ-01** | 15m Dataset Continuity | 1,800 validated candles, 0 gaps, atomic merge persistence | **PASS** (`test_v13_15m_dataset_integrity`) |
| **V13-REQ-02** | Drawdown Mathematical Rectification | Compounded equity drawdown $\le 100\%$, prepended $E_0$ | **PASS** (`test_v13_drawdown_mathematical_correction`) |
| **V13-REQ-03** | Strategy Setup Contract API | Typed contract with geometry validation and blocking reasons | **PASS** (`test_v13_strategy_setup_contract_endpoint`) |
| **V13-REQ-04** | Directional Level Geometry | Long: $\text{SL} < \text{Entry} < \text{TP}$; Short: $\text{TP} < \text{Entry} < \text{SL}$ | **PASS** (`test_v13_strategy_setup_geometry_and_validation`) |
| **V13-REQ-05** | Contract Detail & Source Citations | Literature references (Wilder 1978, Donchian 1960, Deprez 2024) | **PASS** (`test_v13_strategy_contract_detail_endpoint`) |
| **V13-REQ-06** | Replay Lab Telemetry & Modals | True scenarios, VPIN/Hawkes flow, working modal inspection | **PASS** (`test_v13_counterfactual_lab_endpoints`) |
| **V13-REQ-07** | Candidate Leaderboard & Baselines | Top-5 candidates across 3 cost scenarios with setup contracts | **PASS** (`test_v13_tournament_leaderboard_endpoint`) |
| **V13-REQ-08** | Frontend Overlay UI & Single Exclusivity | Overlay buttons, switching exclusivity, clean removal | **PASS** (`test_v13_frontend_script_and_styles_integrity`) |
| **V13-REQ-09** | Desktop Browser Acceptance (1440×900) | Full visual execution, modal inspection, overlay toggle | **PASS** (Browser Subagent desktop recording) |
| **V13-REQ-10** | Mobile Browser Acceptance (390×844) | Zero overflow, zero clipping, responsive layout | **PASS** (Browser Subagent mobile recording) |
| **V13-REQ-11** | Governance Invariants | `live_trading = DISABLED`, `model = OFFLINE_RESEARCH_ONLY` | **PASS** (Enforced across API, engine, and UI) |
