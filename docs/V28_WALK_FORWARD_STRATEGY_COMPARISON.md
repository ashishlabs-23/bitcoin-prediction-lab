# BTCognitive V28 — Walk-Forward Strategy Comparison & Benchmark Tournament

**Version:** 28.0.0  
**Status:** COMPLETED EMPIRICAL EVALUATION  
**Sample Window:** 2018–2026 Historical OHLCV ($N = 41,273$ 1h bars, $N = 7,766,111$ 1m bars)  

---

## 1. Experimental Policy Taxonomy

The V28 walk-forward tournament compares five distinct execution and filtering policies across identical historical event occurrences:

1. **B0: Matched Random Baseline:** Randomly triggers candidate long/short trades at timestamps matching empirical setups.
2. **B0b: Always Long / Always Short:** Static directional rules taking every valid structural trigger in a single direction.
3. **B3: Unfiltered Structural Rules (A1/A2):** Evaluates all detected structural setups (liquidity sweep/reclaim, range re-entry) with triple barriers ($k_{\text{TP}}=1.5, k_{\text{SL}}=1.0, H=24\text{h}$) without meta-filtering.
4. **B3b: Setup + Simple Trend Filter:** Enforces trade direction only in alignment with 24h moving average slope.
5. **B4-lite: Calibrated Logistic Meta-Model:** Point-in-time linear meta-model scoring trade quality and gating trades by net expectancy.
6. **B4: Tree-Based Meta-Model (LightGBM):** Evaluated under Base friction (35 bps) and Conservative friction (65–87 bps).
7. **B_ZERO: Zero Exposure Policy:** 100% Cash / Abstention reference.

---

## 2. Tournament Performance Matrix

All metrics are evaluated on out-of-sample walk-forward test folds ($N = 20,244$ total candidate events):

| Policy / Model | Out-of-Sample N | Win Rate (%) | 95% CI (Win Rate) | Mean Net R | 95% CI (Net R) | Profit Factor | Net Expectancy Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B0: Matched Random** | 10,105 | 25.7% | [24.8%, 26.6%] | -1.2112 R | [-1.258R, -1.157R] | 0.07 | Negative (Pure Noise) |
| **B0b: Always Long** | 10,142 | 26.1% | [25.2%, 27.0%] | -1.1900 R | [-1.239R, -1.134R] | 0.08 | Negative (Beta Drag) |
| **B0b: Always Short** | 10,102 | 25.7% | [24.8%, 26.6%] | -1.2110 R | [-1.260R, -1.155R] | 0.07 | Negative (Beta Drag) |
| **B3: Structural Rule (Unfiltered)** | 20,244 | 25.9% | [25.3%, 26.5%] | -1.2005 R | [-1.236R, -1.158R] | 0.07 | Negative (Friction Dominates) |
| **B3b: Setup + Trend Filter** | 1,665 | 18.7% | [16.8%, 20.6%] | -1.5708 R | [-1.724R, -1.385R] | 0.04 | Severe Negative (Whipsaw) |
| **B4-lite: Logistic Meta-Model** | 2,916 | 46.9% | [45.1%, 48.7%] | -0.4673 R | [-0.498R, -0.429R] | 0.37 | Edge Lift, but Cost-Erased |
| **B4: LightGBM (Base 35 bps)** | 1,553 | 47.1% | [44.6%, 49.6%] | -0.5678 R | [-0.622R, -0.506R] | 0.29 | Edge Lift, but Cost-Erased |
| **B4: LightGBM (Conservative 65-87 bps)** | 1,553 | 25.2% | [23.0%, 27.4%] | -1.0954 R | [-1.166R, -1.017R] | 0.07 | Friction Completely Erases Edge |
| **B_ZERO: Zero Exposure (Abstain)** | 0 | 0.0% | N/A | **0.0000 R** | [0.000R, 0.000R] | 1.00 | **Superior to all active policies** |

---

## 3. Key Scientific Conclusions

1. **Unfiltered Trading Loses Heavily:** Every unconditional baseline (B0, B0b, B3) loses approximately $-1.20R$ per trade on average because round-trip friction and negative excursions absorb more than the profit target provides.
2. **Meta-Labeling Produces True Predictive Lift:** B4-lite and B4 lift the raw win rate from $25.9\%$ to $46.9\%-47.1\%$, proving that the point-in-time features contain genuine signal about conditional persistence.
3. **The 70–80% Aspirational Hypothesis:** In no out-of-sample block did an active candidate maintain a 70–80% win rate under un-embargoed conditions. Attempting to force a 70% win rate requires selecting extreme score thresholds ($\theta > 0.85$) which reduces the sample size to $N < 15$ trades, yielding wide confidence intervals $[40\%, 90\%]$ that fail statistical significance.
4. **Abstention Dominance:** Under current market friction (35 to 87 bps round-trip), `ABSTAIN` (B_ZERO with $0.0000R$) strictly dominates every evaluated trading policy.
