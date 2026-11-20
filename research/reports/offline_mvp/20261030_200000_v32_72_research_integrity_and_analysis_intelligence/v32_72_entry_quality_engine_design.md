# BTCognitive V32.72 — Workstream 4: Entry Quality Intelligence Engine Design

**Milestone:** V32.72 Research Integrity & Analysis Intelligence  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — COMPREHENSIVE ARCHITECTURAL DESIGN SPECIFICATION  

---

## Executive Summary

This specification establishes the architectural foundation for the **BTCognitive Entry Quality Intelligence Engine** in direct alignment with the Product Manager's core directive:

> *"Instead of asking only: 'Will BTC go up or down?', we should investigate: 'Under which market conditions does entering a trade produce a favourable risk-adjusted outcome?'"*

The engine is designed as an offline research subsystem. It does not promise unrealistic win rates. It rigorously evaluates setup quality through path-dependent excursion metrics (MFE/MAE), first-passage probabilities across triple barriers, and execution-cost-adjusted expected payoffs.

---

## 1. Five-Stage Architectural Pipeline

```mermaid
flowchart TD
    M1[1. Market Context Engine] --> M2[2. Entry Candidate Detection]
    M2 --> M3[3. Risk & Payoff Excursion Simulation]
    M3 --> M4[4. Entry Quality Scorer & Ranker]
    M4 --> M5[5. Governed Research Decision]
    
    subgraph S1 [Context Inputs]
        M1 --> C1[Regime Classifier: ADX, EMA200]
        M1 --> C2[Volatility Term Structure: HAR-RS-DOW]
        M1 --> C3[Liquidity & Order Imbalance: L2 Depth]
    end
    
    subgraph S3 [Path Excursions]
        M3 --> E1[MFE: Max Favourable Excursion]
        M3 --> E2[MAE: Max Adverse Excursion]
        M3 --> E3[First Passage Probability: P(TP) vs P(SL)]
        M3 --> E4[Execution Friction Deduction]
    end
    
    subgraph S5 [Governed Actions]
        M5 --> A1[BUY: Positive Net EV & Asymmetry > 1.5]
        M5 --> A2[SELL: Downside Asymmetry > 1.5]
        M5 --> A3[WAIT: Setup forming, low excursion edge]
        M5 --> A4[ABSTAIN: Regime mismatch or negative EV]
    end
```

---

## 2. Mathematical Formulations & Target Definitions

### A. Excursion Metrics (Path Dependency)
For any candidate entry at time $t$ with entry price $P_t$ and evaluation horizon $H = 24$ hours:

$$\text{MFE}_{t, H} = \max_{\tau \in [t, t+H]} \frac{P_\tau - P_t}{P_t}$$

$$\text{MAE}_{t, H} = \max_{\tau \in [t, t+H]} \frac{P_t - P_\tau}{P_t}$$

### B. Entry Quality Ratio (EQR)
$$\text{EQR}_{t, H} = \frac{\mathbb{E}[\text{MFE}_{t, H}]}{\mathbb{E}[\text{MAE}_{t, H}]}$$

An entry setup is structurally unviable if $\text{EQR}_{t, H} \le 1.0$ (expected adverse excursion exceeds expected favourable excursion).

### C. Triple-Barrier First Passage Probability
Let $U = P_t \cdot (1 + \Delta_{\text{TP}})$ be the upper take-profit barrier, and $L = P_t \cdot (1 - \Delta_{\text{SL}})$ be the lower stop-loss barrier:

$$\tau_{\text{TP}} = \inf \{ \tau > t \mid P_\tau \ge U \}$$
$$\tau_{\text{SL}} = \inf \{ \tau > t \mid P_\tau \le L \}$$

$$\text{Target Variable } Y_t = \begin{cases}
+1 & \text{if } \tau_{\text{TP}} < \min(\tau_{\text{SL}}, t+H) \\
-1 & \text{if } \tau_{\text{SL}} < \min(\tau_{\text{TP}}, t+H) \\
0 & \text{if } \min(\tau_{\text{TP}}, \tau_{\text{SL}}) > t+H \text{ (Timeout Expiration)}
\end{cases}$$

### D. Cost-Deducted Net Expected Value
$$\mathbb{E}[\text{Net EV}] = P(Y_t = +1) \cdot (\Delta_{\text{TP}} - C_{\text{rt}}) - P(Y_t = -1) \cdot (\Delta_{\text{SL}} + C_{\text{rt}}) + P(Y_t = 0) \cdot (\mathbb{E}[\Delta_{\text{Exp}}] - C_{\text{rt}})$$

Where $C_{\text{rt}}$ is the round-trip transaction cost (fees + slippage + adverse selection).

---

## 3. Causal Feature Engineering (Zero Leakage)

All features must be constructed strictly using information available at closed candle $t$:

1. **Volatility Structure:**
   - Realized Volatility ratio: $\sigma_{24h} / \sigma_{168h}$ (Volatility expansion vs compression).
   - HAR-RS-DOW predicted forward variance $\hat{\sigma}^2_{t+24}$.
   - Garman-Klass efficient volatility estimator.
2. **Trend & Momentum Persistence:**
   - Donchian channel percent rank: $(P_t - L_{168}) / (U_{168} - L_{168})$.
   - EMA alignment score: $\text{sign}(\text{EMA}_{20} - \text{EMA}_{50}) + \text{sign}(\text{EMA}_{50} - \text{EMA}_{200})$.
   - Consecutive bar directional run count.
3. **Liquidity & Microstructure Proxy:**
   - Volume relative to 20-day moving average: $V_t / \bar{V}_{20d}$.
   - High-low spread expansion: $(H_t - L_t) / \text{ATR}_{14}$.
4. **Distance to Invalidation:**
   - Normalized distance to nearest swing high/low: $|P_t - P_{\text{swing}}| / \text{ATR}_{14}$.

---

## 4. Governed Decision Matrix

The engine maps evaluated metrics to discrete, auditable recommendations:

| Action | Preconditions | Rationale |
| :--- | :--- | :--- |
| **`BUY`** | $\mathbb{E}[\text{Net EV}] > +15\text{ bps}$, $\text{EQR} \ge 1.5$, $P(\text{TP}) / P(\text{SL}) \ge 1.3$, Regime is `TRENDING_BULLISH` or `VOLATILITY_EXPANSION`. | Favourable risk asymmetry exceeds all friction hurdles. |
| **`SELL`** | $\mathbb{E}[\text{Net EV}] > +15\text{ bps}$, $\text{EQR} \ge 1.5$, $P(\text{SL}) / P(\text{TP}) \ge 1.3$, Regime is `TRENDING_BEARISH`. | Downside breakdown with positive expected payoff. |
| **`WAIT`** | Regime compatible, but $\text{EQR} \in [1.0, 1.5)$ or entry price is $> 1.5 \text{ ATR}$ away from structural invalidation level. | Setup forming; awaiting pullback to reduce initial adverse excursion risk. |
| **`ABSTAIN`** | $\mathbb{E}[\text{Net EV}] \le 0$, or $\text{EQR} < 1.0$, or regime is `UNKNOWN_OR_INVALID`, or market data is stale. | Negative mathematical expectancy; capital preservation enforced. |

---

## 5. Implementation Roadmap (Post-V32.72)

1. **Offline Research Module (`research/entry_intelligence/`):**
   - Implement `excursion_calculator.py` to compute MFE, MAE, and triple-barrier outcomes across the canonical backfilled dataset.
2. **Purged Cross-Validation Harness:**
   - Evaluate whether tree-based models can predict high $\text{EQR}$ regimes out of sample without lookahead.
3. **Benchmarking vs. Baselines:**
   - Compare proposed entry filtering against naive unconditioned entries and rule-based Donchian breakouts using Diebold-Mariano testing.

