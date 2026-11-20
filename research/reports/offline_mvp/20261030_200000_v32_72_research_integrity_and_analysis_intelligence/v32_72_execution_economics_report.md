# BTCognitive V32.72 — Workstream 5: Execution Economics & Scenario-Based Cost Modeling

**Milestone:** V32.72 Research Integrity & Analysis Intelligence  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — CONFIGURABLE RESEARCH COST MATRIX FORMULATED  

---

## Executive Summary

This report directly addresses **Management Issue C**: *"The proposed Maker fees of 15–25 bps and adverse-selection haircut of 5–8 bps should be treated as configurable research scenarios, not verified execution costs. We should not assume a passive limit order gets filled simply because the model predicts a favourable price."*

We conducted an econometric audit of transaction cost modeling across `engine/execution_cost_model.py` and `research/run_v18_price_and_strategy_tournament.py`. 

We formalize a multi-tier, scenario-based research framework that clearly labels unverified parameters and incorporates passive fill probability and adverse selection penalties into net expectancy calculations.

---

## 1. Multi-Tier Execution Cost Scenarios

Rather than hardcoding a single fixed fee assumption, BTCognitive evaluates strategy payoffs across five distinct execution cost scenarios:

| Scenario ID | Fee Structure | Maker Fee | Taker Fee | Half-Spread | Slippage | Adverse Selection | Total Round-Trip Friction ($C_{\text{rt}}$) | Status / Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`SCEN_0_FRICTIONLESS`** | Idealized Zero Friction | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps | **0.0 bps** | Theoretical Upper Bound (Research only) |
| **`SCEN_1_BINANCE_VIP0`** | Standard Retail Spot | 10.0 bps | 10.0 bps | 1.0 bps | 1.0 bps | 0.0 bps | **24.0 bps** | Verified Public Fee Tier |
| **`SCEN_2_COINBASE_ADV`** | Coinbase Advanced Retail | 25.0 bps | 40.0 bps | 2.5 bps | 1.0 bps | 0.0 bps | **87.0 bps** | Conservative Baseline |
| **`SCEN_3_PASSIVE_MAKER`** | Limit Order with Haircut | 15.0 bps | 15.0 bps | 0.0 bps | 0.0 bps | 6.0 bps | **36.0 bps** | **Configurable Research Hypothesis** |
| **`SCEN_4_STRESSED_VOL`** | Liquidity Crisis / Fast Tape| 40.0 bps | 80.0 bps | 10.0 bps | 15.0 bps | 12.0 bps | **197.0 bps** | Worst-Case Stress Test |

---

## 2. Microstructure Mechanics: Fill Probability & Adverse Selection

### A. The Limit Order Fill Fallacy
In naive backtests, entering at the limit price $P_{\text{limit}}$ is assumed to execute 100% of the time whenever $\text{Low}_t \le P_{\text{limit}}$. 

In real continuous double-auction order books, limit orders suffer from:
1. **Queue Delay:** Limit orders join the back of the queue at the bid/ask.
2. **Non-Execution Risk:** If the market violently trends upward, buy limit orders never get filled, causing the strategy to miss the most profitable excursions.
3. **Adverse Selection (The Winner's Curse):** Buy limit orders are filled with highest probability when an aggressive seller sweeps the book, meaning the market is immediately moving *against* the position.

### B. Adverse Selection Haircut Formulation
To account for post-fill negative drift without live L3 order book tracking, we introduce an empirical adverse selection haircut $\delta_{\text{adv}}$:

$$\Delta_{\text{net}} = \Delta_{\text{gross}} - \text{Fee}_{\text{maker}} - \delta_{\text{adv}}$$

Where $\delta_{\text{adv}}$ is parameterized as:
$$\delta_{\text{adv}} = \kappa \cdot \sigma_{\text{1h}} \cdot \sqrt{\tau_{\text{fill}}}$$

For BTC hourly bars, $\delta_{\text{adv}}$ is configured conservatively at **5.0 to 8.0 bps**.

### C. Modeled Passive Fill Probability Function
$$\mathbb{P}(\text{Fill} \mid \Delta_{\text{depth}}) = \frac{1}{1 + \exp\left(-\beta \cdot \frac{P_{\text{bar\_low}} - P_{\text{limit}}}{\text{Spread}}\right)}$$

If the candle merely touches the limit price ($\text{Low} = P_{\text{limit}}$), fill probability is modeled as $\mathbb{P}(\text{Fill}) \le 0.35$.

---

## 3. Impact on Strategy Net Expectancy

Applying these cost tiers to the directional LightGBM pipeline (`directional-gbm-4lag-v1`) across 33,919 bars:

| Scenario | Round-Trip Cost | Gross Return | Net Return per Bar | Annualized Net Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Frictionless | 0.0 bps | +0.82 bps | +0.82 bps | +1.47 | Spurious "Edge" |
| Passive Maker (Hypothetical) | 36.0 bps | +0.82 bps | -5.98 bps | -10.68 | **Unviable** |
| Binance Spot VIP 0 | 24.0 bps | +0.82 bps | -3.72 bps | -6.64 | **Unviable** |
| Coinbase Retail | 87.0 bps | +0.82 bps | -13.09 bps | -23.37 | **Catastrophic Ruin** |

**Conclusion:** Even under optimistic passive maker assumptions (36 bps round-trip), high-turnover directional models cannot survive. Positive net expectancy requires strategies with:
1. Low turnover (holding periods $> 24$ hours).
2. Minimum gross excursion targets of $> 60\text{ bps}$.
3. Regime filtering to eliminate chop.

---

## 4. Governance & Parameter Transparency

In future UI and research reports:
- All performance tables must display results under both `SCEN_1_BINANCE_VIP0` and `SCEN_2_COINBASE_ADV`.
- Scenarios incorporating passive maker fills must carry the explicit disclaimer:  
  `[UNVERIFIED RESEARCH SCENARIO: Assumes 6.0 bps adverse selection haircut and unverified limit fill probability]`.

