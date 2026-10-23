# V27 Feature Readiness & Ablation Protocol

**Date:** October 2026  
**Status:** APPROVED FOR EXPERIMENTAL PLANNING  
**Governing Rule:** No model promotion without pre-registered out-of-sample ablation; final holdout remains untouched.

---

## 1. Scientific Principles for Feature Adoption

In accordance with Section 2 of `AGENTS.md`, collecting a new market data feature does **NOT** guarantee predictive value. A feature may only be incorporated into a candidate model if an incremental ablation study proves statistically superior out-of-sample forecasting performance relative to the frozen baseline.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Feature Ablation Decision Gate                        │
├────────────────────────────────┬────────────────────────────────────────────┤
│ Statistical Condition          │ Governed Architectural Action              │
├────────────────────────────────┼────────────────────────────────────────────┤
│ Challenger beats Baseline      │ Retain simpler baseline model;             │
│ p >= 0.05 (or t <= 0)          │ reject feature candidate.                  │
├────────────────────────────────┼────────────────────────────────────────────┤
│ Challenger beats Baseline      │ Retain feature candidate as OFFLINE        │
│ p < 0.05 (DM-HAC or CW-HAC)   │ RESEARCH ONLY for prospective validation.  │
└────────────────────────────────┴────────────────────────────────────────────┘
```

---

## 2. Pre-Registered Ablation Experiments

### Experiment 1: Hourly Realized Semi-Variance on 168h Variance Forecasts
- **Hypothesis:** Incorporating downside semi-variance $RS^-_{168\text{h}}$ into the HAR model improves 168-hour variance prediction during market sell-offs compared to aggregate $RV_{168\text{h}}$.
- **Target:** 168-hour annualized realized variance (`rv7d_var_ann`).
- **Baseline:** Authoritative `HAR-RS-DOW-v1.0` model.
- **Evaluation Metric:** QLIKE loss with Diebold–Mariano HAC test.
- **Success Hurdle:** Statistically significant QLIKE reduction ($p < 0.05$ via DM-HAC, two-sided).

### Experiment 2: Cross-Venue Spot Divergence on Volatility Expansion
- **Hypothesis:** Absolute fiat divergence $|\Delta_{\text{Fiat}}|$ between Coinbase and Kraken predicts immediate 4-hour volatility expansion.
- **Target:** 4-hour realized variance (`rv4h_var_ann`).
- **Baseline:** Autoregressive persistence baseline.
- **Success Hurdle:** Clark–West HAC statistic $> +1.645$ (one-sided $p < 0.05$).

### Experiment 3: Perpetual Funding Rate on Asymmetric Tail Risk
- **Hypothesis:** Extreme funding rates ($>0.03\%$ per 8h) predict asymmetric mean-reversion over a 24-hour horizon.
- **Target:** 24-hour direction and excursion quantiles ($P_{10}, P_{90}$).
- **Baseline:** Random walk persistence with symmetric historical return quantiles.
- **Success Hurdle:** Winkler score improvement on conformal interval coverage ($p < 0.05$).

---

## 3. Epistemic Safeguards

1. **Untouched Final Holdout:** All ablation tuning must occur strictly on development partitions ($t \le 35,000$). The final holdout ($t > 35,000$) is preserved for confirmatory gates.
2. **Missingness Policy:** If an external feed fails, the feature pipeline must emit `NaN` and trigger model abstention (`ABSTAIN_MISSING_FEATURE`). Silent forward-fill or imputation is prohibited.
3. **Execution Guardrail:** All models evaluated under this protocol inherit the status `OFFLINE_RESEARCH_ONLY`. Trading remains permanently `DISABLED`.
