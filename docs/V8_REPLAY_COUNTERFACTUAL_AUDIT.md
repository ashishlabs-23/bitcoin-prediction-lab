# BTCognitive V8 — Replay & Counterfactual Lab: End-to-End Functional Completion & Red-Team Audit Report

**Report Version:** 1.0.0  
**Audit Date:** October 17, 2026  
**Auditor:** Antigravity Research Orchestrator & Independent Red-Team  
**Scope:** Replay & Counterfactual Lab (`ReplayCounterfactualLab`), Mechanism Contracts, Toxicity Gate, Inspect Contract Modal, Execution Badges & 15m Timeframe Reconciliation  
**Final Release Verdict:** `V8_VERIFIED_WITHIN_DECLARED_SCOPE`  
**Live Capital Execution:** `PERMANENTLY_DISABLED`  
**Directional Recommendation:** `DISABLED`  

---

## 1. Executive Summary

In BTCognitive V7, the Analytical Scenario Planner was hardened with causal input freshness and stationary bootstrap reproduction. However, the **Replay & Counterfactual Lab** (`ReplayCounterfactualLab`) remained in an incomplete, placeholder state exhibiting acceptance-test failures:
1. `IGNITION`, `ABSORPTION`, `VACUUM`: Static placeholder text `"Contract available / Inspect Contract"` with dead click handlers and unpopulated barrier prices.
2. `TOXICITY`: Unconditionally hardcoded `"Filter context"` with no evaluated metrics or filter controls.
3. `COMBINED`: Generic placeholders lacking composition inputs or constituent dependency tracking.
4. Surrounding Interface Discrepancy: Summary badge displaying `"EXECUTION: AVAILABLE (GATED)"` while the lab declared `"SYSTEM DIRECTIONAL RECOMMENDATION: DISABLED"`.
5. Timeframe Contract Discrepancy: Microstructure narrative advertising 15-minute order flow while scenario planning operated on hourly data.

Under the **BTCognitive V8 sprint**, a complete vertical slice was engineered and independently verified across the contract engine, FastAPI endpoints, React frontend, automated regression tests, and dedicated browser subagent tests at both desktop (1440×900) and mobile (390×844) viewports.

---

## 2. Phase 0 — Root Cause Audit Matrix

| UI Element | Code Path | Real Source Object | Failure Condition | Prior Failure Evidence | Required Fix Implemented |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IGNITION, ABSORPTION, VACUUM Rows** | `web/app.js` (lines 5570–5644) | `GET /prediction/counterfactual` | Endpoint returned `{"status": "BLOCKED_PROVENANCE_UNVERIFIED", "scenarios": []}` without `counterfactuals` array. Frontend fell back to dummy objects with null TP/SL. | `tp !== "—" ? ... : "Contract available"` | Implemented `engine/counterfactual_contract_engine.py` evaluating live double-barrier first-passage geometry, Net EV, and Drag. Connected `api/routes_prediction.py`. |
| **Inspect Contract Action** | `web/app.js` (lines 5638–5640) | None (dead text span) | Rendered as plain text `<span>Inspect Contract</span>` with zero click handlers, zero modal state, and zero API routes. | Dead text span without `onClick` handler | Built `ContractInspectionModal` displaying parameters, invalidation rules, assumptions, and added `GET /prediction/counterfactual/contract/{id}` route. |
| **TOXICITY Row** | `web/app.js` (lines 5622–5626) | `engine/strategy_selection.py` (`MEIE-TOXICITY`) | Rendered unconditional string `"Filter context"` with no calculation, no filter status, and no interactive toggle. | `isToxicity && h("span", ..., "Filter context")` | Connected VPIN/Hawkes order-flow toxicity sentinel. Displays `PASS · NORMAL FLOW` vs `BLOCK · ADVERSE SELECTION ALERT`. |
| **COMBINED Row** | `web/app.js` (line 5576), `engine/strategy_selection.py` | `MEIE-COMBINED` | Fell into generic dummy fallback; no composition calculation or dependency tracking. | Generic placeholder | Implemented Bayesian confluence engine: tracks constituent dependencies and explicitly reports when `MEIE-ABSORPTION` is gated. |
| **Execution Badge Discrepancy** | `web/app.js` (line 7026) | Static text in `DecisionAnatomyCard` | Static string `"EXECUTION: AVAILABLE (GATED)"` caused confusion between technical service readiness and live trading authorization. | User screenshot conflict | Separated into distinct badges: `EXECUTION ADAPTER: CONNECTED (STANDBY)` and `TRADING AUTH: DISABLED (GOVERNED)`. |
| **15m Order-Flow Narrative** | `web/app.js` (line 7014) | Static fallback string | Conflated 15m microstructure order flow (OFI, Hawkes, VPIN) with 1h macro scenario planning. | Missing timeframe contract clarity | Explicitly declared: 15m order flow stream (Coinbase BTC-USD) is high-frequency path evidence; macro barriers anchor to hourly realized variance. |

---

## 3. Architectural Implementation Details

### 3.1 Five Canonical MEIE Mechanisms
The 5 canonical Market Microstructure & Execution Intelligence (MEIE) archetypes defined in `engine/evidence_router.py` and `engine/strategy_selection.py` are now fully evaluated:
1. **`MEIE-IGNITION`**: Momentum Ignition & Volatility Breakout (Regimes: `VOL_EXPANDING`, `TRENDING_BULL/BEAR`; Drag: 9.3 bps; Target R:R: 2.0).
2. **`MEIE-ABSORPTION`**: Iceberg Order Absorption & Mean-Reversion (Regimes: `VOL_NORMAL`, `VOL_COMPRESSION`, `CHOP`; Drag: 3.5 bps; Target R:R: 1.2).
3. **`MEIE-VACUUM`**: Liquidity Vacuum Pocket Snap-Back (Regimes: `LIQUIDITY_VACUUM`, `VOL_COMPRESSION`; Drag: 6.5 bps; Target R:R: 1.5).
4. **`MEIE-TOXICITY`**: Toxic Flow Sentinel & Adverse Selection Gate (Regimes: `PEAK_VOLATILITY`, `TOXIC_BURST`; Drag: 9.5 bps; Target R:R: 1.0).
5. **`MEIE-COMBINED`**: Multi-Expert Bayesian Confluence Ensemble (Combines active, unblocked experts).

### 3.2 Dual-Scenario Point-in-Time Symmetry
Both **UPPER-TARGET (H_LONG)** and **LOWER-TARGET (H_SHORT)** scenarios are generated from the **identical point-in-time market snapshot**, same live Coinbase spot reference price, and same timestamp.
- Upper Target ($H_{\text{long}}$): Take-profit barrier $P_{\text{TP}} = S_0 (1 + \text{MFE})$, stop-loss barrier $P_{\text{SL}} = S_0 (1 - \text{MAE})$.
- Lower Target ($H_{\text{short}}$): Take-profit barrier $P_{\text{TP}} = S_0 (1 - \text{MFE})$, stop-loss barrier $P_{\text{SL}} = S_0 (1 + \text{MAE})$.
- Barrier geometry is strictly validated using `compute_bracket_geometry()` from `engine/scenario_contract_engine.py`, guaranteeing positive reward and risk distances.

### 3.3 Toxicity Sentinel & Adverse Selection Gate
- When $\text{VPIN} \le 0.65$ and Hawkes intensity $\le 4.0$: Order flow is non-toxic (`PASS · NORMAL ORDER FLOW`). Passive limit absorption (`MEIE-ABSORPTION`) evaluates normally.
- When $\text{VPIN} > 0.65$ or toxic burst occurs: Order flow triggers `BLOCK · ADVERSE SELECTION ALERT`. `MEIE-ABSORPTION` transitions to `BLOCKED · TOXICITY_GATE` with the explicit reason `"Passive limit absorption blocked: elevated adverse selection (VPIN > 0.65)"`.
- The interactive filter test controls (`[Auto (Live)]`, `[Normal Flow]`, `[Toxic Shock (VPIN>0.65)]`) allow researchers and auditors to verify this protective gate dynamically.

### 3.4 Multi-Expert Bayesian Composition (`MEIE-COMBINED`)
`MEIE-COMBINED` dynamically tracks its constituent dependencies:
- Under normal flow: `"Bayesian confluence of 4 unblocked experts"`.
- Under toxic shock: Excludes `MEIE-ABSORPTION`, reporting `"Confluence: 3/4 experts (Absorption Gated)"` and recalculating confluence weights without double-counting.

### 3.5 Contract Inspection Modal & Information Hiding
Clicking `Inspect Contract` on any mechanism launches `ContractInspectionModal`:
- Displays: Strategy ID, Name, Version, Governing Horizon (15m), Scenario Type, Evaluated Geometry (TP, SL, Gross R:R, $P(\text{TP})$, Gross EV, Drag, Net EV), Sample Size $N$, Effective $N_{\text{eff}}$, 90% Confidence Interval, Invalidation Conditions, and Econometric Assumptions.
- Information Hiding: Zero server stack traces, zero internal filesystem paths, zero secrets exposed. Closes cleanly via Escape key, close button (✕), or backdrop click.

---

## 4. Automated Verification & Test Execution

### 4.1 Focused V8 Test Suite
Executed test suite: `tests/test_replay_counterfactual_lab_v8.py`  
Command: `.venv_win\Scripts\python -m pytest tests/test_replay_counterfactual_lab_v8.py`  
**Results:** **10 passed in 1.57s** (Exit Code: 0)

Test Breakdown:
1. `test_all_five_mechanisms_present_and_ordered`: Verified all 5 mechanisms rendered in canonical order.
2. `test_dual_scenario_point_in_time_consistency`: Verified identical spot price, timestamp, and geometric barrier validity across Upper and Lower columns.
3. `test_toxicity_normal_flow_unblocks_absorption`: Verified `MEIE-ABSORPTION` is `AVAILABLE` under normal flow.
4. `test_toxicity_burst_blocks_passive_absorption`: Verified `MEIE-ABSORPTION` is `BLOCKED` with adverse selection narrative under toxic flow.
5. `test_meie_combined_composition_tracks_constituents`: Verified `MEIE-COMBINED` adjusts constituent count from 4/4 to 3/4 when absorption is gated.
6. `test_counterfactual_contract_detail_route`: Verified `GET /prediction/counterfactual/contract/{id}` returns complete technical metadata.
7. `test_invalid_contract_id_raises_404`: Verified 404 error handling without internal leaks.
8. `test_zero_or_negative_price_fails_closed`: Verified fail-closed behavior when spot price is missing.
9. `test_strict_governance_invariants`: Verified live trading remains `DISABLED` and single-instance disclaimer is preserved.
10. `test_timeframe_contract_reconciliation`: Verified 15m microstructure vs 1h macro scenario reference clarity.

### 4.2 Combined Regression Suite
Command: `.venv_win\Scripts\python -m pytest tests/test_scenario_freshness_and_contract_v7.py tests/test_replay_counterfactual_lab_v8.py tests/test_scenario_planner_and_inference_v6.py`  
**Results:** **32 passed in 2.84s** (Exit Code: 0)

---

## 5. Dedicated Browser Acceptance Evidence

Executed via `/browser` subagent at `http://127.0.0.1:8000/#/terminal`:

| Viewport | Test Step | Visual Observation & Acceptance Evidence | Artifact File |
| :--- | :--- | :--- | :--- |
| **Desktop (1440×900)** | Full Replay Lab Table | All 5 mechanism rows populated with real TP, SL, P(TP), Net EV, and Drag. No generic placeholders. | `counterfactual_lab_table_1792236094811.png` |
| **Desktop (1440×900)** | Inspect Contract Modal | Clicked `Inspect Contract` on IGNITION. Modal opened cleanly showing MEIE-IGNITION, TP $81,851, SL $81,520, P(TP) 68.6%, Net EV +32.2 bps, invalidation rules, assumptions. | `contract_inspection_modal_1792236125572.png` |
| **Desktop (1440×900)** | Modal Close | Closed modal cleanly via Escape key. Modal removed from DOM. | `modal_closed_1792236174651.png` |
| **Desktop (1440×900)** | Toxic Shock Simulation | Clicked `Toxic Shock (VPIN>0.65)`. Toxicity tag displayed `BLOCK · ADVERSE SELECTION ALERT`. `MEIE-ABSORPTION` transitioned to `BLOCKED · TOXICITY_GATE` with explicit reason. | `blocked_state_1792236199372.png` |
| **Desktop (1440×900)** | Combined Confluence | `MEIE-COMBINED` displayed `Confluence: 3/4 experts (Absorption Gated)` with evaluated Net EV and TP/SL. | `combined_blocked_state_1792236211428.png` |
| **Desktop (1440×900)** | Risk & Execution Badges | Verified summary row displays `EXECUTION ADAPTER: CONNECTED (STANDBY)` and `TRADING AUTH: DISABLED (GOVERNED)`. Narrative explains 15m order flow vs 1h macro levels. | `execution_adapter_summary_1792236238175.png` |
| **Mobile (390×844)** | Mobile Responsiveness | Resized to 390×844. Lab rendered responsively with zero horizontal overflow, all controls accessible, and clean wrapping. | `mobile_counterfactual_lab_1792236273981.png` |

---

## 6. Governed Four-Part Release Decision

1. **Research Experiment:** `PASS` (Replay & Counterfactual Lab functional slice complete).
2. **Prospective Evidence:** `COLLECTING` (Prospective worker pipeline operating; awaiting 100 clean blocks).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (Tier 0 descriptive replay only; no live trading promotion).
4. **Live Trading:** `DISABLED` (Permanent operating contract enforced).

**Final Sprit Verdict:** `V8_VERIFIED_WITHIN_DECLARED_SCOPE`
