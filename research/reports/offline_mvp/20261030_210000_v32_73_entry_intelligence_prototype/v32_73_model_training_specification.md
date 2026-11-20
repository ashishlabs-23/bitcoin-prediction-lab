# V32.73 Model Training Specification — Entry Intelligence Prototype

**Milestone:** V32.73 — Entry Intelligence Prototype  
**Date:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  
**Document Type:** DESIGN SPECIFICATION for V32.74+  
**Model Authorization:** OFFLINE_RESEARCH_ONLY  
**Live Trading:** DISABLED  

> **IMPORTANT:** No model training or promotion occurs in V32.73. This document is a forward-looking design specification to guide implementation in V32.74 and later milestones. All governance constraints from AGENTS.md Phase 5 apply.

---

## 1. Purpose and Scope

This specification defines the prediction targets, feature schema, training protocol, acceptance criteria, and governance guardrails for the supervised learning pipeline to be implemented starting in V32.74. The empirical basis is the triple-barrier labelling and barrier outcome analysis completed in V32.73 (see `v32_73_cost_sensitivity_report.md` and `v32_73_verification_report.md`).

The objective is to train a conditional signal model that identifies sub-populations of entry bars where TP_FIRST probability is sufficiently elevated to produce positive net EV under SCEN_1_BINANCE_VIP0 (14 bp round-trip).

---

## 2. Dataset

| Property | Value |
|----------|-------|
| Source file | `ohlcv.parquet` |
| Total rows | 42,233 |
| Bar frequency | 1-hour (inferred) |
| Gap-free window | Bars 1000–20900 (confirmed, 0 gaps) |
| TP | +1.50% |
| SL | -0.75% |
| Horizon | 24 hours (24 bars) |

---

## 3. Prediction Targets

Four prediction targets are defined. All targets must be computed using **strictly causal** (point-in-time) logic: the target value for bar `t` is derived from price action in bars `[t+1, t+H]`, where `H` is the horizon. Features for bar `t` must use only information available at or before bar `t`.

### Target A — EQR Binary Classification

| Property | Value |
|----------|-------|
| Type | Binary classification |
| Label encoding | 1 if EQR > 1.5, else 0 |
| EQR definition | MFE_pct / MAE_pct (or MAE_pct / MFE_pct for SHORT, as appropriate) |
| Threshold | 1.5 (configurable; 1.5 is the V32.73 default) |
| Positive class interpretation | Favourable excursion ratio; trade moved more in the profitable direction than the loss direction |
| Class imbalance note | Expected positive rate ~30–40% based on V32.73 batch; stratified sampling required |

### Target B — Triple-Barrier Label (3-Class Classification)

| Property | Value |
|----------|-------|
| Type | 3-class classification |
| Classes | +1 (TP_FIRST), -1 (SL_FIRST), 0 (EXPIRED or AMBIGUOUS) |
| Label source | Triple-barrier engine output (v32_73 implementation) |
| AMBIGUOUS handling | Assign to class 0 (neutral); flag separately in audit log |
| Class distribution (LONG, empirical) | -1: 62.0%, +1: 27.5%, 0: 10.5% |
| Class distribution (SHORT, empirical) | -1: 61.5%, +1: 25.0%, 0: 13.5% |
| Loss function | Weighted cross-entropy with inverse-frequency class weights |

### Target C — MFE Regression

| Property | Value |
|----------|-------|
| Type | Continuous regression |
| Label | Maximum Favourable Excursion (MFE) as a percentage of entry price |
| Causal constraint | MFE computed over bars `[t+1, t+H]` only |
| Units | Percentage (e.g., 0.3347 for 0.3347%) |
| Loss function | Mean Squared Error (MSE) or Huber loss (robust to outliers) |
| Directional note | For LONG: MFE = max(high[t+1:t+H+1] - close[t]) / close[t]; for SHORT: MFE = (close[t] - min(low[t+1:t+H+1])) / close[t] |

### Target D — MAE Regression

| Property | Value |
|----------|-------|
| Type | Continuous regression |
| Label | Maximum Adverse Excursion (MAE) as a percentage of entry price |
| Causal constraint | MAE computed over bars `[t+1, t+H]` only |
| Units | Percentage (e.g., 4.3348 for 4.3348%) |
| Loss function | Mean Squared Error (MSE) or Huber loss |
| Directional note | For LONG: MAE = (close[t] - min(low[t+1:t+H+1])) / close[t]; for SHORT: MAE = max(high[t+1:t+H+1] - close[t]) / close[t] |

---

## 4. Feature Schema

All features listed below are **causal**: they use only information available at or before entry bar `t`. No future price, volume, or derived quantity may appear as a feature. Lookahead leakage is prohibited and must be verified by assertion (see Section 6).

| Feature Name | Description | Formula / Source | Type |
|-------------|-------------|-----------------|------|
| `vol_ratio_1h_24h` | Ratio of short-term to long-term realized volatility | `rv_1h / rv_24h` where `rv_1h` = realized variance over last 1 hour, `rv_24h` = over last 24 hours | Float |
| `trend_persistence` | Normalized EMA crossover momentum | `(EMA_12 - EMA_48) / ATR_14` where EMAs are of close price | Float |
| `atr_distance_pct` | Distance of current price from ATR-based band | `(close[t] - atr_band[t]) / ATR_14[t]`; ATR band definition to be specified in implementation (e.g., close - 1*ATR) | Float |
| `volume_profile_ratio` | Current bar volume relative to recent mean | `volume[t] / mean(volume[t-23:t+1])` (24-bar trailing mean including current bar) | Float |
| `log_rv24h` | Log of 24-hour realized variance | `log(rv24h_var_ann[t])` — already present in feature store | Float |
| `log_rv7d` | Log of 7-day realized variance | `log(rv7d_var_ann[t])` — already present in feature store | Float |
| `dow_sin` | Cyclical encoding of day-of-week (sine component) | `sin(2 * pi * dow / 7)` where `dow` = day of week (0=Monday) | Float |
| `dow_cos` | Cyclical encoding of day-of-week (cosine component) | `cos(2 * pi * dow / 7)` | Float |

**Notes on existing features (`log_rv24h`, `log_rv7d`):** These features are already computed and stored in the model feature store from prior milestones. Their causal integrity has been verified in prior phases. No recomputation is needed unless the feature store schema changes.

**Feature count:** 8 features (7 columns + 1 split into 2 cyclical components).

---

## 5. Training Protocol

### 5.1 Cross-Validation Scheme

- **Method:** Expanding window out-of-sample (OOS) with temporal ordering preserved.
- **Folds:** 5 folds (as per the experiment manifest registered in prior milestones).
- **Embargo:** 24-hour gap between the last training bar and the first test bar in each fold, preventing bar-level leakage from multi-bar features.
- **Minimum training samples:** 500 labeled, non-ambiguous samples per fold.
- **Walk-forward direction:** Training window expands forward in time; test window is always strictly after training window.

### 5.2 Test Set (Holdout)

| Property | Value |
|----------|-------|
| Fold | Last fold (Fold 5) |
| Approximate date range | 2025-07 to 2026-03 |
| Usage | Final model evaluation only — must not be used for hyperparameter selection |
| Access restriction | Holdout must not be inspected until all hyperparameter decisions are frozen |

### 5.3 Labelling Integration

- Labels are generated by the V32.73 triple-barrier engine for each direction (LONG, SHORT) independently.
- AMBIGUOUS-labelled bars are excluded from training and test sets. They are logged separately for audit.
- The same bar may appear as LONG-labelled and SHORT-labelled in separate model runs (direction-specific models).

### 5.4 Class Imbalance Handling (Targets A and B)

- Use stratified k-fold splitting to preserve label distribution across folds.
- Apply inverse-frequency class weights in loss computation.
- Do NOT use SMOTE or other synthetic oversampling on time-series data (lookahead risk).

### 5.5 Model Candidates (V32.74 Scope)

The following model families are proposed for evaluation in V32.74. Selection is deferred; this document does not prescribe a final model.

- Gradient Boosted Trees (LightGBM or XGBoost) — primary candidate for tabular features.
- Logistic Regression with L2 regularization — interpretability baseline.
- Random Forest — ensemble baseline for comparison.

All candidates must run on CPU. No GPU-dependent libraries are permitted without explicit approval.

---

## 6. Acceptance Criteria

A model implementation passes V32.74 acceptance gates if and only if all of the following criteria are satisfied.

### 6.1 Statistical Significance

- **Test:** Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction, using Student's t_{T-1} reference distribution.
- **Null hypothesis:** Model forecast errors are equal to or worse than the naive all-ABSTAIN (constant zero) benchmark.
- **Required:** p < 0.05 (one-sided, model better than baseline) on the holdout test set.
- **Applicable to:** Target B (triple-barrier label) as primary; Target A as secondary.

### 6.2 Economic Significance

- **Condition:** Conditional on model predicting TP_FIRST (class +1), the empirically realized net EV must be positive under SCEN_1_BINANCE_VIP0 (14 bp round-trip cost).
- **Confidence requirement:** Net EV must remain positive after subtracting a 1.5-sigma confidence interval margin (estimated from test-set sample variance).
- **Formula:** `Net EV_conditional = P(TP_FIRST | model=+1) * 1.50% + P(SL_FIRST | model=+1) * (-0.75%) - 0.14%`

### 6.3 Causal Integrity (Lookahead Leakage Assertion)

For every feature `f` of every sample at bar index `t`:

```
assert feature_timestamp[f, t] <= entry_bar_timestamp[t]
```

This assertion must be run as an automated test on every training dataset build. Any violation causes the build to fail and raises a data integrity alert.

### 6.4 Prospective Evidence Gate

- Before any model result is treated as confirmatory, a minimum of **100 non-overlapping clean blocks** of prospective (post-freeze) observations must be accumulated and resolved.
- Current prospective evidence status: **NOT_STARTED**.
- Prospective gate is a governance requirement; it is not waivable.

---

## 7. Governance and Authorization

| Governance Item | Status |
|----------------|--------|
| Model training in V32.73 | NOT PERMITTED — design doc only |
| Model promotion to staging | BLOCKED until V32.74 acceptance criteria met |
| Model authorization level | OFFLINE_RESEARCH_ONLY |
| Production inference authorization | NOT AUTHORIZED |
| Live order execution | DISABLED |
| Prospective evidence gate | NOT_STARTED |
| Experiment registered in manifest | Pending V32.74 |

### 7.1 Research-Only Boundary

Models produced under this specification carry the `OFFLINE_RESEARCH_ONLY` classification. This classification means:

- The model output must not be used to place, influence, or recommend any real capital trade.
- Model weights and predictions are for internal research analysis only.
- The `OFFLINE_RESEARCH_ONLY` flag must be embedded in the model registry entry and the serialized model metadata.
- Promotion to any higher authorization tier requires a separate governance review that is out of scope for V32.73 and V32.74.

### 7.2 Audit Trail Requirements

- All training runs must log: dataset version hash, feature schema version, label generation parameters (TP, SL, horizon), fold boundaries, and random seed.
- Model registry entries must include: training date, dataset hash, OOS metric summary, DM test result, lookahead assertion pass/fail, and authorization level.
- Experiment IDs must be linked to the relevant V32.x milestone in the research ledger.

---

## 8. Implementation Checklist (V32.74)

The following items are required before V32.74 model training begins. This checklist is not exhaustive; additional items may be added during V32.74 planning.

- [ ] Implement and unit-test `vol_ratio_1h_24h` feature with causal timestamp assertion
- [ ] Implement and unit-test `trend_persistence` (EMA_12, EMA_48, ATR_14)
- [ ] Implement and unit-test `atr_distance_pct`
- [ ] Implement and unit-test `volume_profile_ratio` (24-bar trailing mean)
- [ ] Verify `log_rv24h` and `log_rv7d` schema compatibility with feature store
- [ ] Implement `dow_sin` / `dow_cos` cyclical encoding
- [ ] Build labeled dataset for LONG and SHORT directions, all 4 targets
- [ ] Verify 0 AMBIGUOUS samples in training set (or correct exclusion logic)
- [ ] Run lookahead leakage assertion across full dataset
- [ ] Register experiment in manifest with frozen hyperparameter grid
- [ ] Run 5-fold expanding OOS with 24h embargo
- [ ] Compute DM test vs all-ABSTAIN baseline on holdout
- [ ] Compute conditional net EV under SCEN_1_BINANCE_VIP0 on holdout
- [ ] Log all results to experiment ledger

---

## 9. References

- AGENTS.md — BTCognitive Permanent Operating Contract V1.0.0
- `v32_73_cost_sensitivity_report.md` — Empirical barrier outcome and net EV analysis
- `v32_73_verification_report.md` — Triple-barrier engine verification (bar-level and batch)
- Harvey, D., Leybourne, S., Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting*, 13(2), 281-291.
- Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. (Triple-barrier method, embargo, purging.)

---

*Report generated by BTCognitive Research Orchestrator — V32.73. This is a design document for V32.74+. No model training, promotion, or live deployment is authorized under V32.73.*
