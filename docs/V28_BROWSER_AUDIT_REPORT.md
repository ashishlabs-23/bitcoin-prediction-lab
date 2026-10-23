# BTCognitive V28 — Browser Audit & Frontend Verification Report

**Version:** 28.0.0  
**Audit Date:** October 2026  
**Auditor:** Dedicated Autonomous Browser Subagent  
**Artifact Recording:** [v28_entry_ui_audit_1792431803213.webp](file:///C:/Users/Ashish/.gemini/antigravity-ide/brain/734c52f2-6f55-43ff-b397-80e483a23556/v28_entry_ui_audit_1792431803213.webp)  
**Host Tested:** `http://127.0.0.1:8000/`  

---

## 1. Executive Summary

A comprehensive automated browser audit was conducted using the autonomous `/browser` subagent to verify the BTCognitive V28 web interface across desktop and mobile form factors.

The audit verified:
1. Complete rendering of the new **V28 Probabilistic Entry Quality Engine & Selective Trade Research** panel under the bottom tab navigation.
2. Exact numerical correspondence between frontend card metrics and the backend REST endpoint `/api/research/entry-quality`.
3. Complete adherence to the non-execution invariant: **Live Trading DISABLED — Analysis-Only Research Application**. Zero live trade submission buttons, order entry inputs, or broker connection mechanisms exist.
4. Smooth responsive performance across Desktop ($1536 \times 730$) and Mobile ($390 \times 844$) viewports.

---

## 2. Desktop UI Verification Matrix

| UI Component | Expected State | Observed Frontend Value | Backend API Payload Value | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Governance Banner** | `OFFLINE RESEARCH ONLY` & `TRADING DISABLED` | Red & amber badges rendered with clear warning text | `execution_authorization: DISABLED — ANALYSIS ONLY` | **PASS** |
| **Candidate Side** | `LONG` / `SHORT` toggles | Interactive emerald/red toggle buttons | `side: "LONG"` | **PASS** |
| **Entry Reference Price** | Causal $t_0 + \Delta t$ fill | `$81,242.50` | `entry_reference_price: 81242.5` | **PASS** |
| **Profit Target Price** | $+1.5\sigma$ barrier | `$82,262.00` | `tp_price: 82262.0` | **PASS** |
| **Stop Loss Price** | $-1.0\sigma$ barrier | `$80,562.83` | `sl_price: 80562.83` | **PASS** |
| **Holding Horizon** | 24 Hours Max | `24 Hours (Max Holding)` | Hardened vertical barrier | **PASS** |
| **Calibrated $p_{\text{TP}}$** | Model target probability | `59.2%` | `probabilities.p_tp: 0.592` | **PASS** |
| **Calibrated $p_{\text{SL}}$** | Model stop probability | `32.8%` | `probabilities.p_sl: 0.328` | **PASS** |
| **Calibrated $p_{\text{timeout}}$**| Model timeout probability | `8.0%` | `probabilities.p_timeout: 0.08` | **PASS** |
| **Expected Brier Score** | Reliability metric | `0.4831` | `probabilities.brier_score_expected: 0.4831` | **PASS** |
| **Intrabar Collision Rule**| Conservative resolution | `SL_FIRST (Conservative)` | Conservative contract invariant | **PASS** |
| **Expected Net R** | Gross R minus Friction | `-0.5357 R` | `expected_net_r: -0.5357` | **PASS** |
| **Decision Action** | Abstain on negative edge | `DECISION: ABSTAIN` | `action: "ABSTAIN"` | **PASS** |
| **Primary Reason** | Cost erasure reason | `NEGATIVE_EXPECTANCY_AFTER_COSTS` | `primary_reason: "NEGATIVE_EXPECTANCY_AFTER_COSTS"` | **PASS** |

---

## 3. Subtab Navigation & Interactive Testing

The browser subagent exercised all five subtabs within the V28 Entry Research panel:

1. **`🎯 Candidate Evaluator & Gating`:**
   - Successfully changed Side toggle from `LONG` to `SHORT`.
   - Exercised target multiples ($1.0\sigma, 1.5\sigma, 2.0\sigma, 3.0\sigma$) and stop multiples ($0.5\sigma, 1.0\sigma, 1.5\sigma$).
   - Clicked `🔄 Re-Evaluate` button; observed reactive state re-computation without page reload.
2. **`📊 Walk-Forward Benchmarks (B0-B4)`:**
   - Displayed full historical tournament table comparing B0 Random, B0b Always Long/Short, B3 Structural Rule, B4-lite Logistic Meta-Model, and B4 LightGBM under Base and Conservative friction.
3. **`📐 Barrier Parameterization Grid`:**
   - Rendered parametric grid across 5 frozen barrier ratios with 95% confidence intervals and profit factors.
4. **`🏷️ Abstention Taxonomy`:**
   - Displayed complete 8-code taxonomy (NO_SETUP, MODEL_UNCERTAIN, EV_BELOW_COST, NEGATIVE_EXPECTANCY_AFTER_COSTS, WIN_PROBABILITY_BELOW_SELECTIVE_THRESHOLD, EXECUTION_UNSAFE, DATA_UNAVAILABLE, PROVENANCE_FAILURE).
5. **`📜 Prospective Ledger Audit`:**
   - Rendered real-time table of append-only prospective decisions logged to `data/prospective_entry_ledger.jsonl`.

---

## 4. Mobile Viewport Inspection (390 x 844)

- **Layout Structure:** Flexbox and CSS grid columns wrap cleanly into single-column cards on mobile viewports.
- **Horizontal Overflow:** Tables in the Benchmarks, Grid, and Prospective Ledger subtabs utilize dedicated `overflow-x: auto` containers, preventing layout blowouts.
- **Typography:** JetBrains Mono figures and Outfit headings maintain high contrast and readability against the dark glassmorphic theme.

---

## 5. Security & Epistemic Invariant Verification

- **Live Trading Disabled:** Zero WebSocket trade-order channels exist.
- **No Execution Inputs:** The DOM contains no `<input type="number" name="quantity">`, no `<button>Buy</button>`, and no broker API key fields.
- **Epistemic Clarity:** Every panel explicitly states `OFFLINE RESEARCH ONLY` and highlights that the 70–80% win rate is an unproven aspirational hypothesis.
