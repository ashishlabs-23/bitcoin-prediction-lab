# 🌉 Intermediate Horizon (1H–4H) Validation & Bridging Report

## 1. Executive Summary & Verdict

> **Formal Decision:** `CASE B: 5m information decays, but derivatives/volatility bridge to 4h.`
>
> **Governance Rule:** Both 1h and 4h models remain strictly in **`RESEARCH_ONLY`** status due to sample size constraints ($N_{\text{eff}} = 48 < 150$ and $N_{\text{eff}} = 30 < 100$).
>
> **Production Invariant:** Ridge remains **`PRODUCTION / 24H`**; Hawkes remains **`VALIDATED_SHADOW_MODEL / 5M`**.

## 2. The Empirical Bridge from 5m to 24h

1. **5m to 30m:** Dominated by L2 order book imbalance and multivariate Hawkes trade clustering.
2. **1h Boundary:** Microstructure intensity has largely decayed; technical momentum and intraday volatility take over.
3. **4h to 12h:** Derivatives positioning (perpetual funding rate asymmetries and OI dislocations) emerges as a significant conditional factor.
4. **Universal Bridge:** Realized Volatility provides continuous, statistically robust excursion containment across every single horizon.
