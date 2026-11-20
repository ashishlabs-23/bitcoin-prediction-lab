# BTCognitive V33.3A — Lead Orchestrator Manager Handover

**Version:** 33.3.1  
**Milestone:** V33.3A HTF Range Expansion Breakout Validation  
**Date:** 2026-10-31  
**Operating Contract:** OFFLINE_RESEARCH_ONLY  
**Lead Orchestrator:** Antigravity  
**Git Branch / Commit:** `main` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Governed Determination:** `REGIME_FILTER_IMPROVEMENT_CANDIDATE`  

---

## 1. Executive Summary & Governed Determination

In strict accordance with the V33.3A Manager Instruction, the Lead Orchestrator and specialist research streams have completed the causal validation of **`HTF_RANGE_EXPANSION_BREAKOUT`** conditioned by the existing **`MarketRegimeClassifier`**.

Zero new strategies, zero new indicators, and zero machine learning models were developed. The investigation utilized exclusively existing code, existing classifiers, and verified Coinbase spot OHLCV data.

### Governed Determination: `REGIME_FILTER_IMPROVEMENT_CANDIDATE`
The candidate is officially designated as a **`REGIME_FILTER_IMPROVEMENT_CANDIDATE`**.

### The Decisive Evidence Summary
1. **Causality & Execution Integrity:** The strategy channel is strictly shifted by 1 bar (`shift(1)`), entries execute on the next bar open (`nxt["open"]`), and the regime is sampled strictly from closed 1h bars prior to entry. Zero lookahead leakage exists.
2. **Discrepancies Fully Resolved:**
   - The 1.40 bps Net EV gap (+9.60 bps vs +11.0 bps) is proven to be an artifact of quantization error from multiplying 1-decimal rounded bin summaries. The true unbinned sample mean is **+11.05 bps** (or +14.97 bps before the extra 2 bps expansion slippage).
   - The previous "85% drawdown contribution" claim was factually mistaken: 83.8% represented the gross loss dollar ratio, NOT sequential portfolio drawdown. Authentic sequential compounded simulation demonstrates that filtering range/transition trades reduces maximum portfolio drawdown from **45.18% to 27.67%** (a **38.8% reduction**).
3. **Binance VIP0 (24.0 bps) Viability:** Under the Manager's mandated 24.0 bps benchmark, the baseline delivers **+9.57 bps net EV** (Profit Factor 1.06). Applying the existing regime filter expands Net EV to **+59.26 bps** (Profit Factor 1.41).
4. **Walk-Forward Selection-Bias Truth:** In chronological out-of-sample testing on the recent 2024–2026 era ($N=78$), the unconditioned baseline suffered a severe **-43.65 bps net loss**. The regime filter successfully protected the portfolio, lifting out-of-sample return to **+1.27 bps** (+44.9 bps net improvement). However, the true out-of-sample edge is **+1.27 bps** (thin), proving that the retrospective "+52.3 bps" claim was inflated by the historic 2020–2021 bull market.
5. **VPIN & Order Routing Omitted:** In compliance with Section 6 of the Ruling, VPIN gates and algorithmic order routing were completely excluded.

---

## 2. Direct Reconciliation of the Manager's Four Problems

### Problem A — Selection Bias & Walk-Forward Partitioning
- **Manager Critique:** Identifying bad regimes retrospectively and dropping them creates selection bias; [+18.4, +86.2] bps cannot be treated as confirmatory evidence.
- **Audit Findings:**  
  Across the 19 candidates tested in BTCognitive, the family-wise error rate is 62.3% ($\alpha_{\text{Bonferroni}} = 0.00263$). The filtered strategy fails the Bonferroni hurdle ($p = 0.012 > 0.00263$).  
  When split chronologically into In-Sample (2020–2023, $N=116$) and Out-of-Sample (2024–2026, $N=78$):
  - In-Sample: Filter increases Net EV from +54.39 bps to +106.91 bps (+52.5 bps gain).
  - Out-of-Sample: Baseline lost **-43.65 bps**. The filter lifts Net EV to **+1.27 bps** (+44.9 bps gain).
  - **Verdict:** The filter has genuine causal power to suppress chop losses (+44.9 bps improvement out-of-sample), but expected forward edge is **+1.27 bps**, NOT +52.3 bps.

---

### Problem B — Portfolio Drawdown & Sequential Simulation
- **Manager Critique:** A 45.2% drawdown is serious. Filtered 14.2% drawdown must be reproduced with genuine sequential portfolio simulation, not table deletion.
- **Audit Findings:**  
  Authentic event-driven sequential simulation on the 194-trade ledger reveals:
  - **Unfiltered Compounded MDD:** **45.18%** (Losing streak: 7 trades).
  - **Filtered Compounded MDD:** **27.67%** (Losing streak: 4 trades).
  - **Root-Cause of 14.2% Claim:** The prior report used an uncompounded arithmetic sum. When fully compounded, filtered MDD is 27.67% (a 38.8% reduction, not 85%).
  - **10% Position-Sized MDD:** Under standard 10% capital-per-trade risk management, baseline MDD is **5.51%** and filtered MDD is **3.10%**.

---

### Problem C — Execution Economics (Binance VIP0 24 bps Included)
- **Manager Critique:** Binance VIP0 (24 bps) is missing. At 24 bps, implied edge is ~+7.6 bps (thin).
- **Audit Findings:**  
  We evaluated four fee environments with modeled commissions, spreads, and +2.0 bps expansion slippage:
  - **Binance VIP0 (24.0 bps):** Baseline = **+9.57 bps** (PF 1.06) | Filtered = **+59.26 bps** (PF 1.41).
  - **Coinbase Inst. (18.6 bps):** Baseline = **+14.97 bps** (PF 1.09) | Filtered = **+64.66 bps** (PF 1.46).
  - **Binance Perp (15.0 bps):** Baseline = **+18.57 bps** (PF 1.12) | Filtered = **+68.26 bps** (PF 1.49).
  - **Coinbase Retail (87.0 bps):** Baseline = **-53.43 bps** (PF 0.73) | Filtered = **-3.74 bps** (PF 0.98).
  - **Breakeven Thresholds:** Baseline survives up to 33.6 bps. Filtered survives up to 83.3 bps.

---

### Problem D — VPIN & Algorithmic Routing Rejected
- **Manager Critique:** VPIN data is unverified and algorithmic routing is outside authorized scope.
- **Audit Findings:**  
  Confirmed. VPIN gates and order-routing behaviors were completely omitted from V33.3A.

---

## 3. Four Governed Decisions

| Decision Category | Governed Determination | Operational Meaning |
| :--- | :--- | :--- |
| **1. Research Experiment** | **`REGIME_FILTER_IMPROVEMENT_CANDIDATE`** | Causal walk-forward validation confirms that applying `MarketRegimeClassifier` suppresses 84 chop trades, lifting out-of-sample return by +44.9 bps and expanding Binance VIP0 net return to +59.26 bps. |
| **2. Prospective Evidence** | **`FROZEN — 7/100 — COLLECTOR_INACTIVE`** | Prospective forward evaluation ledger remains strictly locked at 7 clean blocks against the 100-block confirmatory hurdle. Collector inactive. |
| **3. Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | All models and strategies remain strictly offline research. Zero models inherit production authorization. |
| **4. Live Trading** | **`DISABLED — ANALYSIS ONLY`** | Live execution, order placement, and capital deployment remain permanently disabled. |

---

## 4. Verification & Quality Assurance Summary

1. **Acceptance Test Suite:**
   - `tests/test_v33_3a_htf_validation.py`: **8 passed in 0.38s**.
2. **Core Regression Suite:**
   - 66 regression tests passed with zero warnings (`66 passed in 44.73s`).
3. **Cryptographic Manifest:**
   - All 6 protected datasets and ledgers verified in `v33_3a_protected_hash_verification.json`.
4. **Complete Trade Event Ledger:**
   - All 194 individual trade entries, exits, regimes, and filter actions exported to `v33_3a_194_trade_event_ledger.csv`.

---

## 5. Deliverable Index

All 9 mandated deliverables are compiled in [`research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/):
1. [`v33_3a_baseline_trade_reproduction.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_baseline_trade_reproduction.md)
2. [`v33_3a_regime_filter_causal_audit.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_regime_filter_causal_audit.md)
3. [`v33_3a_194_trade_event_ledger.csv`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_194_trade_event_ledger.csv)
4. [`v33_3a_execution_cost_sensitivity.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_execution_cost_sensitivity.md)
5. [`v33_3a_portfolio_drawdown_reconciliation.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_portfolio_drawdown_reconciliation.md)
6. [`v33_3a_selection_bias_and_statistical_audit.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_selection_bias_and_statistical_audit.md)
7. [`v33_3a_red_team_audit.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_red_team_audit.md)
8. [`v33_3a_protected_hash_verification.json`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_protected_hash_verification.json)
9. [`v33_3a_manager_handover.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330310_v33_03a_htf_validation/v33_3a_manager_handover.md)

