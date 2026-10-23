# BTCognitive V28 — Evidence Ledger & PRD Traceability Matrix

**Version:** 28.0.0  
**Effective Date:** October 2026  
**Status:** COMPLETE — REPRODUCIBLE RESEARCH EVIDENCE  
**Execution Authorization:** `DISABLED — ANALYSIS ONLY`  
**Model Governance State:** `OFFLINE_RESEARCH_ONLY`  

---

## 1. Executive Summary & Epistemic Verdict

The objective of **BTCognitive V28** is to build an advanced, research-only engine that evaluates candidate BTCUSD long and short entries and estimates whether a defined profit target ($k_{\text{TP}} \sigma$) is likely to be reached before a defined stop-loss ($k_{\text{SL}} \sigma$) within a specified horizon ($H=24\text{h}$).

The research inquiry investigated whether a selective subset of trade opportunities can achieve a high win rate (with 70–80% evaluated as an aspirational research hypothesis) and positive expected net return in R-multiples after realistic transaction friction (35 to 87 bps round-trip).

### Authoritative Findings:
1. **70–80% Win Rate Hypothesis:** Currently **unsupported** by empirical data on unconditional BTC returns and structural setups. While calibrated meta-labeling lifts raw win rates from an unconditional baseline of ~25.9% up to 46.9%–65.0% on selective subsets, demanding a 70–80% win rate on historical out-of-sample data collapses coverage to near-zero ($< 0.5\%$) or relies on curve-fitted, un-embargoed thresholds.
2. **Economic Expectancy Boundary:** A high win rate is mathematically distinct from positive net expectancy. Because Bitcoin trade setups with volatility stops $\sigma \approx 0.8\%$ face round-trip friction of 87 bps ($\sim 1.08R$), the expected net value in R-multiples remains negative ($\mathbb{E}[R_{\text{net}}] = -0.5357R$ at current market volatility). The engine honestly reports this edge as `COST_ERASED_UNDER_CONSERVATIVE_FRICTION` and strictly returns `ABSTAIN`.
3. **Conservative Intrabar Touch:** In 1m or 15m OHLC bars where both profit target and stop loss are touched (intrabar collision), the simulator strictly enforces `SL_FIRST`. Never is an optimistic target fill assumed.
4. **Causal Fill Invariant:** All close-based signals fill causally at $t_0 + \Delta t$ ($O_{t+1} + \text{slippage}$); same-bar close execution is strictly rejected as lookahead contamination.

---

## 2. PRD Requirement Traceability Matrix

| Requirement | PRD Section | Implementation Module | Verification Suite | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Analysis-Only Guardrail** | PRD-SAFE-01 | `engine/probabilistic_entry_engine.py` | `test_v28_fastapi_entry_quality_endpoint` | **PASS** (Zero live orders) |
| **No Auto Promotion** | PRD-SAFE-02 | `models/signal_contract.py` | `test_authorization_consistency.py` | **PASS** (`OFFLINE_RESEARCH_ONLY`) |
| **Causal Executable Fill** | PRD-EXEC-01 | `research/entry_tp_sl/triple_barrier.py` | `test_pit_invariants.py` | **PASS** ($O_{t+1} + \text{slip}$) |
| **Intrabar Ambiguity Resolution** | PRD-BAR-02 | `research/entry_tp_sl/intrabar_ambiguity.py` | `test_intrabar_ambiguity.py` | **PASS** (Strict `SL_FIRST`) |
| **Triple-Barrier Labeller** | PRD-BAR-01 | `research/entry_tp_sl/triple_barrier.py` | `test_triple_barrier.py` | **PASS** ($k_{\text{TP}}, k_{\text{SL}}, H=24\text{h}$) |
| **Point-in-Time Features** | PRD-FEAT-01 | `engine/probabilistic_entry_engine.py` | `test_v28_point_in_time_features` | **PASS** ($RS^+/(RS^+ + RS^-)$, mom, BB) |
| **Calibrated Meta-Model** | PRD-MOD-01 | `engine/probabilistic_entry_engine.py` | `test_v28_calibrated_probabilities_normalization` | **PASS** (Brier score, Isotonic) |
| **Cost-Aware Net Expectancy** | PRD-EV-01 | `engine/probabilistic_entry_engine.py` | `test_v28_friction_and_net_expectancy` | **PASS** ($\mathbb{E}[R_{\text{net}}] = \mathbb{E}[R_{\text{gross}}] - \text{friction}_R$) |
| **Selective Abstention Gate** | PRD-EV-02 | `engine/probabilistic_entry_engine.py` | `test_v28_decision_gate_abstains_on_negative_expectancy` | **PASS** (`ABSTAIN` on cost-erasure) |
| **Append-Only Prospective Ledger** | PRD-PROS-01 | `data/prospective_entry_ledger.jsonl` | `test_v28_prospective_ledger_append_only` | **PASS** (Append-only UTC logging) |
| **UI Entry Research Panel** | PRD-UI-01 | `web/app.js` (`EntryTpSlResearchPanel`) | Dedicated `/browser` Subagent | **PASS** (Interactive live panel) |
| **Regression Test Census** | PRD-TEST-01 | `pytest` runner | 161/161 Passed in 301.54s | **PASS** (Zero exclusions) |

---

## 3. Authoritative Data & Artifact Hashes

| Artifact Path | Format | Records | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | Parquet | 41,273 bars | `43c8881b896ec4a9eef11fc83dbf2ddad5e24ee90f42557e10e408ec210214a1` | Verified canonical 1h |
| `data/raw/btcusd_1-min_data.csv` | CSV | 7,766,111 rows | `1bf91f2780e920d3eb895782787836371ef390632b4b455b7a0fbeadcc6f0761` | Verified Bitstamp 1m |
| `experiments/results/v28_entry_quality_manifest.json` | JSON | Manifest | `a84fb7ce...` | Frozen V28 contract |
| `data/prospective_entry_ledger.jsonl` | JSONL | Append-only | Monotonically growing | Prospective UTC ledger |
| `web/app.js` | JavaScript | 11,706 lines | Syntax validated via Node.js | Live V28 interactive panel |

---

## 4. Test Census Summary

- **Total Tests Collected:** 161
- **Total Tests Executed:** 161
- **Total Tests Passed:** 161 (100.0%)
- **Total Tests Failed:** 0
- **Total Tests Skipped/Excluded:** 0
- **Duration:** 301.54 seconds (~5.0 minutes)
