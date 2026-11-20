# BTCognitive V33.3C — Execution-Cost Reproduction & Sensitivity

**Milestone:** V33.3C — HTF Strategy Final Evidence Reconciliation  
**Date:** 2026-10-31  
**Target:** Reconcile 24.0 bps vs 26.0 bps Execution Economics across V33.3A and V33.3B  
**Authoritative Ledger:** `v33_3c_cross_milestone_trade_mapping.csv`  

---

## 1. Executive Summary: The 24.0 vs 26.0 bps Paradox Resolved

The Manager identified an apparent mathematical contradiction:
> *"The new handover reports 26 bps total friction... It reports Baseline: +9.57 bps, Filtered: +59.26 bps. However, the previous V33.3A calculation reported the same net EV figures under a 24 bps cost assumption. For identical trades and gross returns, increasing costs from 24 to 26 bps cannot leave average net EV unchanged..."*

### The Code-Level Audit Finding
An audit of `scripts/qa/v33_3a_validation_engine.py` (lines 25–36 and 136–140) reveals exactly why:

```python
# scripts/qa/v33_3a_validation_engine.py (Lines 25-36)
scenarios = {
    "BINANCE_VIP0_24BPS": 24.0,
    "COINBASE_INSTITUTIONAL_18BPS": 18.6,
    "BINANCE_PERP_15BPS": 15.0,
    "COINBASE_RETAIL_87BPS": 87.0
}
for scen_name, cost_bps in scenarios.items():
    cost_frac = (cost_bps + 2.0) / 10000.0  # including 2 bps expansion slippage
```

In `v33_3a_validation_engine.py`, the scenario dictionary key was named `"BINANCE_VIP0_24BPS"`, reflecting Binance's standard VIP0 taker fee baseline (20 bps commission + 2 bps spread + 2 bps base slippage = 24.0 bps).  
However, the author hardcoded an automatic **`+ 2.0 bps` expansion slippage penalty** inside the simulation loop (`cost_frac = cost_bps + 2.0`).  
Therefore:
$$\text{Actual Cost Deducted in V33.3A} = 24.0 + 2.0 = \mathbf{26.0\text{ bps}}$$
$$\text{Baseline Net EV} = 35.5715\text{ (Gross)} - 26.0 = \mathbf{+9.5715\text{ bps}}$$
$$\text{Filtered Net EV} = 85.2546\text{ (Gross)} - 26.0 = \mathbf{+59.2546\text{ bps}}$$

In V33.3A, the summary report referred to the scenario by its dictionary label ("24.0 bps"), but the script had already subtracted 26.0 bps.  
In V33.3B, the author explicitly itemized the four cost components ($20 + 2 + 2 + 2 = 26\text{ bps}$) without changing the underlying mathematical deduction.  
**Thus, the deducted cost was 26.0 bps in both milestones.**

---

## 2. Complete Five-Venue Cost Sensitivity Matrix

Below is the verified, itemized breakdown of returns across all 194 trades for all five venue scenarios:

| Venue Scenario | Commission | Spread | Base Slippage | Expansion Penalty | Total Cost Deducted | Baseline Net EV ($N=194$) | Filtered Net EV ($N=110$) | Excluded Net EV ($N=84$) | Filter Advantage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Binance VIP0 (26 bps Modeled)** | 20.0 bps | 2.0 bps | 2.0 bps | 2.0 bps | **26.0 bps** | **+9.57 bps** | **+59.25 bps** | **−55.49 bps** | **+49.68 bps** |
| **Binance VIP0 Pure (24 bps)** | 20.0 bps | 2.0 bps | 2.0 bps | 0.0 bps | **24.0 bps** | **+11.57 bps** | **+61.25 bps** | **−53.49 bps** | **+49.68 bps** |
| **Coinbase Institutional** | 15.0 bps | 1.6 bps | 2.0 bps | 2.0 bps | **20.6 bps** | **+14.97 bps** | **+64.65 bps** | **−50.09 bps** | **+49.68 bps** |
| **Binance Perpetual** | 10.0 bps | 2.0 bps | 3.0 bps | 2.0 bps | **17.0 bps** | **+18.57 bps** | **+68.25 bps** | **−46.49 bps** | **+49.68 bps** |
| **Coinbase Retail** | 80.0 bps | 5.0 bps | 2.0 bps | 2.0 bps | **89.0 bps** | **−53.43 bps** | **−3.75 bps** | **−118.49 bps** | **+49.68 bps** |

### Breakeven Cost Ceilings
- **Unfiltered Baseline:** Breakeven occurs at **35.57 bps**. Any cost above 35.57 bps renders the baseline unprofitable. Under Coinbase Retail (89.0 bps), it loses −53.43 bps per trade.
- **Regime-Filtered Strategy:** Breakeven occurs at **85.25 bps**. The filter provides an additional **+49.68 bps of cost tolerance**, surviving Binance VIP0 (+59.25 bps), Coinbase Institutional (+64.65 bps), and Binance Perpetual (+68.25 bps).

---

## 3. Chronological Cost Breakdown (Binance VIP0 26.0 bps)

| Cohort | Baseline Gross EV | Cost Deducted | Baseline Net EV | Filtered Gross EV | Cost Deducted | Filtered Net EV | Excluded Net EV |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **In-Sample (2022–2023, $N=75$)** | +46.51 bps | 26.0 bps | **+20.51 bps** | +144.70 bps | 26.0 bps | **+118.70 bps** | **−135.25 bps** |
| **Out-of-Sample (2024–2026, $N=119$)** | +28.68 bps | 26.0 bps | **+2.68 bps** | +42.53 bps | 26.0 bps | **+16.53 bps** | **−13.43 bps** |
| **Full Period (2022–2026, $N=194$)** | +35.57 bps | 26.0 bps | **+9.57 bps** | +85.25 bps | 26.0 bps | **+59.25 bps** | **−55.49 bps** |

### Conclusion
The execution cost methodology is 100% consistent across all 194 trades. The apparent discrepancy was an artifact of V33.3A using the string key `"BINANCE_VIP0_24BPS"` for a computation that included a +2.0 bps expansion slippage adder ($24 + 2 = 26\text{ bps}$). All trade-level cost items are verified in `v33_3c_cross_milestone_trade_mapping.csv`.

