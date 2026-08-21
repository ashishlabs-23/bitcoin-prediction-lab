# 🥊 Challenger Bake-Off Methodology & Governance

## 1. 1v1 Bake-Off Protocol

To eliminate noise and avoid overfitting to hyperparameter permutations, BTCognitive evaluates **exactly ONE challenger against production at a time**.

* **Dataset Invariants**:
  - Identical timestamps
  - Identical feature pipeline
  - 24h purge & 24h embargo
  - Non-overlapping evaluation blocks

---

## 2. Statistical Testing Standards

1. **Paired Error Comparison**:
   - For every timestamp $t$, $\Delta_t = \text{Error}_{\text{Prod}}(t) - \text{Error}_{\text{Challenger}}(t)$.
   - Evaluated across MAE, RMSE, Pinball Loss, and Winkler Interval Scores.
2. **Block Bootstrap & Permutation**:
   - $10,000$ block resamples to generate strict 95% Confidence Intervals.
   - Permutation test requiring $p < 0.05$ for confirmed outperformance.
3. **No Win via Excess Width**:
   - Challengers that achieve coverage solely by generating overly wide intervals ($> 8.0\%$) are rejected on interval sharpness.
