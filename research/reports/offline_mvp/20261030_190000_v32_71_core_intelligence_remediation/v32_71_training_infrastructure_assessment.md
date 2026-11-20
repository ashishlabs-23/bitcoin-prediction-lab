# BTCognitive V32.71 — Priority 5: Training Infrastructure & Offline Pipeline Assessment

**Milestone:** V32.71 Core Intelligence Remediation  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — RE-TRAINING WORKFLOWS & MODEL REGISTRY EVALUATED  

---

## Executive Summary

As BTCognitive pivots toward a private quantitative research and trading-analysis application, the local model training and experimentation infrastructure was audited. This assessment covers:
1. Local Model Training Pipelines (`HAR-RS-DOW`, GARCH, LightGBM)
2. Validation & Walk-Forward Cross-Validation Frameworks
3. Authoritative Model Registry (`models/model_registry.json`)
4. Deep Learning Infrastructure (TFT & Mamba disconnection)
5. Model Comparison, Drift Tracking, and Experiment Reproducibility

**Key Finding:** The core statistical and tree-based training pipelines are CPU-efficient, deterministic, and scientifically sound. However, the deep learning models (Temporal Fusion Transformer and Mamba) remain disconnected architectural prototypes. Retaining CPU-compatible statistical volatility models and gradient boosted ensembles is the optimal path for private, reproducible local experimentation.

---

## 1. Local Training Pipeline Capabilities

### Active Model Architectures:
- **HAR-RS-DOW (Heterogeneous Autoregressive Realized Volatility with Semivariance and Day-of-Week):**
  - **Implementation:** `engine/har_rv_model.py`
  - **Training Speed:** < 2.5 seconds on CPU for 42,000 hourly bars.
  - **Convergence:** Closed-form OLS with Newey-West HAC covariance estimation.
  - **Reliability:** 100% deterministic and mathematically robust.
- **LightGBM Directional Classifier:**
  - **Implementation:** `engine/directional_lgbm.py`
  - **Training Speed:** ~8 seconds across 5 purged cross-validation folds.
  - **Optimization:** CPU-based multithreading, early stopping on validation log loss.
- **GARCH(1,1) / EGARCH / GJR-GARCH:**
  - **Implementation:** `engine/garch_engine.py` (via `arch` library).
  - **Training Speed:** ~12 seconds using SLSQP optimization.

---

## 2. Model Registry & Versioning Status

The model registry is tracked in `models/model_registry.json`.

### Current Registration Records:
1. `har-rv-24h-v1`: Volatility forecasting model (STATUS: `ACTIVE_VALIDATION`, Target: `rv24h_var_ann`).
2. `directional-gbm-4lag-v1`: Directional classification model (STATUS: `OFFLINE_RESEARCH_ONLY`, Target: `sign_return_24h`).
3. `tft-temporal-fusion-v0`: Deep learning prototype (STATUS: `DEPRECATED_DISCONNECTED`).
4. `mamba-ssm-v0`: Deep learning prototype (STATUS: `DEPRECATED_DISCONNECTED`).

### Registry Governance Rule:
Under Phase 5 governance, any model lacking prospective out-of-sample validation or exhibiting negative economic expectancy is automatically tagged `OFFLINE_RESEARCH_ONLY` and cannot be activated for live decision recommendations.

---

## 3. Disconnection of Deep Learning (TFT & Mamba)

The V32.70 audit highlighted that TFT (PyTorch Forecasting) and Mamba (State Space Models) were disconnected from the active runtime.

### Technical & Practical Evaluation:
1. **Computational Overhead:** Training TFT on 42,000 hourly bars requires GPU acceleration (CUDA) and hours of compute, failing the lightweight offline-first CPU design criterion.
2. **Empirical Edge:** Extensive academic literature (and our internal benchmarks) confirms that for low signal-to-noise financial time series, deep sequence models frequently overfit and fail to outperform regularized HAR and tree ensembles out of sample.
3. **Product Manager Decision:** The PM rightly classified DL re-connection as `P2 — evaluate later`. 

**Recommendation:** Formally archive the deep learning stubs to `research/experiments/deep_learning_archive/` and focus resources on refining HAR-RS-DOW and GARCH jump models.

---

## 4. Retraining Blueprint for Future Milestones

To maintain clean local experimentation without data leakage:

```
[Canonical Backfilled Parquet]
            │
            ▼
[Causal Point-in-Time Feature Store] (Strictly t <= issue_time)
            │
            ▼
[Purged K-Fold Cross-Validation] (24h embargo between folds)
            │
            ▼
[Model Optimization & QLIKE/Brier Scoring]
            │
            ▼
[Diebold-Mariano Hypothesis Gate] (HLN 1997 correction vs. Naive Baseline)
            │
            ▼
[Execution Cost Deducted Payoff Simulation]
            │
            ▼
[Model Registry Serialization] (JSON schema with SHA-256 data hash)
```

This workflow guarantees that all newly trained models maintain strict epistemic hygiene.

