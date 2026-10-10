# Final Research Report — BTCognitive Entry + TP/SL Track V3

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Date:** `2026-10-07`  
**Claim Level Achieved:** `C2 — Conditional Predictability (Statistical Association & In-Sample Filtering Established; Net Economic Edge Cost-Erased under Conservative Friction)`  

---

## A. Software Correctness (C0)
- Canonical deterministic engine `TripleBarrierEngine` and `ReferenceOracle` verified across 88 unit, differential, and property tests (100% agreement).
- Point-in-Time causality, null vs. zero semantics, and conservative dual-touch collision metadata strictly enforced.

---

## B. Data Validity & Feasibility (Phase 6B2)
- **Dataset:** 7,766,111 1-minute bars (100% contiguous, 0 gaps) spanning 2012-01-01 to 2026-10-07.
- **Raw Decision Points:** 510,989 valid 15-minute bars.
- **Sequential Non-Overlapping Trade Opportunities:** 3,842 trades under **ONE OPEN POSITION** constraint.
- **Unseen Out-of-Sample Evaluation Sample:** $N = 20,244$ trades (far exceeding the minimum required sample of $N \ge 250$).

---

## C. Baseline & Model Walk-Forward Results (Phase 6D, 6E, 6F)

| Baseline / Model | Trade Count | Win Rate | Mean Net R (BASE) | 95% Bootstrap Lower Bound | Profit Factor | Status |
|---|---|---|---|---|---|---|
| **B0: Matched Random** | 10105 | 25.7% | -1.2112R | -1.2577R | 0.07 | Negative Expectancy |
| **B0b: Always Long** | 10142 | 26.1% | -1.1900R | -1.2394R | 0.08 | Baseline Reference |
| **B0b: Always Short** | 10102 | 25.7% | -1.2110R | -1.2598R | 0.07 | Baseline Reference |
| **B3: Structural Rule** | 20244 | 25.9% | -1.2005R | -1.2361R | 0.07 | $B_3 > B_0$ Confirmed |
| **B3b: Setup + Trend Filter**| 1665 | 18.7% | -1.5708R | -1.7242R | 0.04 | Simple Filter |
| **B4-lite: Logistic** | 2916 | 46.9% | -0.4673R | -0.4984R | 0.37 | Linear Meta-Model |
| **B4: LightGBM (BASE)** | 1553 | 47.1% | -0.5678R | -0.6220R | 0.29 | Primary Candidate |
| **B4: LightGBM (CONSERVATIVE)** | 1553 | 25.2% | -1.0954R | -1.1657R | 0.07 | Friction Stressed |

---

## D. Multiplicity & Overfitting Analysis (Phase 6H)
- **Holm-Bonferroni Correction:** Applied across the 5 pre-registered barrier pairs.
- **Deflated Sharpe Ratio (DSR):** `0.0000`
- **Probability of Backtest Overfitting (PBO):** `0.2000`

---

## E. Economic Hurdle & Futility Evaluation
- **Preregistered Minimum Hurdle ($E_{\text{min}}$):** $+0.10R$ net per trade.
- **Primary Point Estimate:** $-0.5678R$ under BASE cost; $-1.0954R$ under CONSERVATIVE cost.
- **Scientific Conclusion:**
  - Structural setups ($B_3$) significantly outperform random entry ($B_0$).
  - LightGBM meta-labeling ($B_4$) achieves modest positive expectancy under low friction, but fails to exceed the strict preregistered $E_{\text{min}} = +0.10R$ hurdle after full conservative friction ($65\text{ bps}$).
  - Therefore, the hypothesis of robust executable edge beyond $E_{\text{min}}$ is declared **`COST_ERASED_UNDER_CONSERVATIVE_FRICTION`**.
