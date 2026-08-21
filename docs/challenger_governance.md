# 🏛️ Challenger Model Governance & Promotion Lifecycle

## 1. Principles of Model Governance

1. **No Chasing Complexity**: Production models are never replaced simply because a newer or more complex deep-learning architecture exists.
2. **Strict Superiority Requirement**: A candidate model must demonstrably beat the active production model across the **8 Promotion Criteria**.
3. **Longitudinal Block-Aware Confirmation**: Superiority must be verified across at least 30 non-overlapping 24-hour independent blocks with block permutation $p < 0.05$.

---

## 2. The 8 Strict Promotion Criteria

1. **MFE Error Superiority**: Lower Mean Absolute Error ($\text{MAE}_{\text{MFE}}$).
2. **MAE Error Superiority**: Lower Mean Absolute Error ($\text{MAE}_{\text{MAE}}$).
3. **Quantile Pinball Loss**: Reduced pinball loss across $P_{10..90}$.
4. **Single-Sided P90 Coverage**: Empirical coverage $\ge 88.0\%$.
5. **Joint Full-Path Containment**: Joint empirical containment $\ge 78.87\%$.
6. **Interval Sharpness**: Equal or narrower mean range width without compromising coverage.
7. **Regime Invariance**: Stable containment across Trending, Sideways, and Breakout regimes.
8. **Volatility Invariance**: Stable containment across Low, Normal, and High Volatility tiers.

---

## 3. Retraining Policy & Periodic Triggers

* **Trigger**: Every additional 30 independent blocks, a validation and drift audit is automatically triggered.
* **Auto-Retrain Policy**: **STRICTLY DISABLED**. Retraining requires human approval following documented evidence of calibration degradation.
