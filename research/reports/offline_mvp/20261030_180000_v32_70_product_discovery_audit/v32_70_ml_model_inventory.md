# BTCognitive V32.70 — Machine Learning & Model Inventory

**Audit Date:** 30 October 2026  
**Milestone:** V32.70  
**Target:** Authoritative Model Registry, Checkpoints & Training Pipelines  

---

## 1. Authoritative Model Registry Inventory

Every model registered in `models/authoritative_model_registry.py` is audited below against empirical source code and disk artifacts:

### Model 1: `HAR-RS-DOW-v1.0`
- **Algorithm:** Heterogeneous Autoregressive Ordinary Least Squares (OLS) with Realized Semivariances and Day-of-Week Seasonality.
- **Purpose:** Production volatility risk baseline. Provides parametric point forecast of 7-day integrated volatility ($168\text{h}$) to establish risk envelopes.
- **Training Dataset:** `data/raw/ohlcv.parquet` (Historical closed hourly BTC/USD candles, pre-2026 window).
- **Input Features (10):** `['log_rv_down_1d', 'log_rv_up_1d', 'log_rv7d_var_ann_lag', 'log_rv30d_var_ann', 'dow_1', 'dow_2', 'dow_3', 'dow_4', 'dow_5', 'dow_6']`.
- **Target Variable:** Annualized 7-Day Realized Variance (`rv7d_var_ann`).
- **Training Methodology:** Standard OLS regression on log-transformed realized variance components with linear day-of-week indicator terms.
- **Validation Methodology:** Purged holdout evaluation (2026 out-of-sample replay).
- **Inference Location:** `engine/inference_service.py` -> `experiments/results/freeze/har_rs_dow_v1.joblib`.
- **Latest Version:** `1.0.0` (SHA-256: `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b`).
- **Performance Metrics:** Holdout QLIKE: `0.19300`; C2 Conformal 90% coverage: `84.89%` (causal holdout) and `92.84%` (calibration).
- **Known Limitations:** Zero directional price capability. Does not predict $+/-$ return sign. Governed as `OFFLINE_RESEARCH_ONLY`.
- **Used by Analysis Button:** **NO** (Evaluated in background observatory routes, not in 1-click tournament).

---

### Model 2: `directional-gbm-4lag-v1`
- **Algorithm:** LightGBM Gradient Boosted Decision Trees (`max_depth=3`, `n_estimators=100`, `learning_rate=0.03`).
- **Purpose:** Directional research benchmark. Evaluates whether short-horizon log return sign can be predicted from price lags.
- **Training Dataset:** `data/raw/ohlcv.parquet` (33,919 evaluations across 5 purged temporal folds).
- **Input Features (4):** `['ret_lag1', 'ret_lag2', 'ret_lag3', 'ret_lag4']`.
- **Target Variable:** Sign of 1-Hour Forward Log Return (`ret_1h_fwd > 0`).
- **Training Methodology:** Binary classification with early stopping and sample-weight purging.
- **Validation Methodology:** 5-fold Purged Cross-Validation with 168h embargo buffers. Moving-block paired bootstrap (10,000 resamples).
- **Inference Location:** `engine/directional_forecast_service.py`.
- **Latest Version:** `1.0.0` (Manifest in `experiments/results/stage3_validation/stage3_directional_pipeline_results.json`).
- **Performance Metrics:** Out-of-Sample Accuracy: **53.28%** (95% CI: `[52.74%, 53.82%]`). Net simulated return after 7 bps friction: **-13.07 bps/bar**.
- **Known Limitations:** Negative net expectancy after realistic exchange fees. Proves that simple directional ML does not beat market friction.
- **Used by Analysis Button:** **NO** (Served via `/api/research/directional-audit`).

---

### Model 3: `ridge_excursion_core` (Legacy Candidate)
- **Algorithm:** L2 Regularized Ridge Regression with Conformal Quantile Residual Mapping.
- **Purpose:** Historical Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) 24h regressor.
- **Training Dataset:** Multi-source dataset (OHLCV, funding rates, on-chain metrics).
- **Input Features (5):** `['vol_24h', 'rsi_14', 'atr_14', 'funding_rate', 'mvrv_zscore']`.
- **Target Variable:** 24h MFE / MAE percentage excursion bounds.
- **Validation Methodology:** Historical 31-block retrospective evaluation (August 2026).
- **Inference Location:** `models/range_forecaster.py`.
- **Status:** **BLOCKED_PROVENANCE_UNVERIFIED**. Superseded by the HAR-RS-DOW freeze contract.
- **Used by Analysis Button:** **NO** (Routes fail closed).

---

### Model 4: `HAR-QLIKE-v1.0` (Research Challenger)
- **Algorithm:** Heterogeneous Autoregressive Loss-Coherent QLIKE Minimizer with L2 Penalty.
- **Purpose:** Direct numerical minimization of Gaussian QLIKE loss function $\mathcal{L}(y, \hat{y}) = \frac{y}{\hat{y}} - \ln(\frac{y}{\hat{y}}) - 1$.
- **Training Dataset:** `data/raw/ohlcv.parquet`.
- **Target Variable:** Annualized 7-Day Realized Variance (`rv7d_var_ann`).
- **Performance Metrics:** QLIKE: `0.19598` vs Baseline `0.21483` (8.77% raw reduction).
- **Statistical Gate:** Diebold-Mariano test with Harvey-Leybourne-Newbold correction yields $DM = +0.5132, p = 0.3039$ ($p \ge 0.05$).
- **Status:** **OFFLINE_RESEARCH_ONLY**. Retained as a challenger; failed formal significance gate.
- **Used by Analysis Button:** **NO**.

---

### Model 5: `HAR-RS-DOW-24H` & `HAR-QLIKE-24H` (24h Challengers)
- **Algorithm:** Conventional OLS vs. Loss-Coherent QLIKE minimizer on 24-hour annualized variance proxy.
- **Target Variable:** Annualized 24-Hour Realized Variance (`rv24h_var_ann`).
- **Performance Metrics:** OLS QLIKE: `0.37259`, QLIKE Minimizer: `0.31729` (+14.84% gain).
- **Statistical Gate:** HLN corrected $p$-value $= 0.1622$ ($p \ge 0.05$).
- **Status:** **OFFLINE_RESEARCH_ONLY**.
- **Used by Analysis Button:** **NO**.

---

## 2. Checkpoint & Deep Learning Model Audit

Beyond the registered models, the repository contains PyTorch checkpoint files in `models/checkpoints/`:

| Checkpoint File | Size | PyTorch Architecture | Purpose in Codebase | Live Status |
| :--- | :--- | :--- | :--- | :--- |
| `tft.pt` | **1.20 MB** | `TemporalFusionTransformer` (`models/tft_model.py`) | Multi-horizon quantile transformer with self-attention | Standalone prototype; not hooked to API |
| `router.pt` | **186.9 KB** | `NeuralExpertRouter` (`models/router.py`) | Soft routing across specialized regime experts | Research prototype; not wired to live routes |
| `regime.pt` | **10.2 KB** | `RegimeClassifierNN` (`models/regime_detector.py`) | 7-class regime classification neural network | Preempted by causal `MarketRegimeClassifier` |
| `meta.pt` | **10.1 KB** | `MetaLabelerNN` (`models/meta_labeler.py`) | Secondary bet-sizing and Sharpe surrogate loss filter | Research prototype; offline evaluation only |

---

## 3. BTCognitive ML Capability Assessment Matrix

| ML Capability | Status | Implemented Mechanism & Evidence |
| :--- | :--- | :--- |
| **Local Model Training** | **IMPLEMENTED** | Standalone training scripts (`training/retrain_pipeline.py`, `train_tft.py`, `train_mamba_range.py`). |
| **Incremental Retraining** | **PARTIAL** | Script exists (`retrain_pipeline.py`), but no automated online daemon or trigger is active. |
| **Model Versioning** | **IMPLEMENTED** | Rigorous versioning in `models/authoritative_model_registry.py` with immutable SHA-256 hashes. |
| **Model Comparison** | **IMPLEMENTED** | Diebold-Mariano test with Harvey-Leybourne-Newbold (HLN 1997) finite-sample correction (`research/`). |
| **Walk-Forward Validation** | **IMPLEMENTED** | Purged k-fold splits with embargo windows (`validation/purged_split.py`). |
| **Drift Detection** | **PARTIAL** | Population Stability Index (PSI) implemented in `engine/drift_evaluator.py`; not wired to active alerts. |
| **Prediction Calibration** | **IMPLEMENTED** | Isotonic regression calibration, Brier score, and ECE in `models/calibrated_signal_classifier.py`. |
| **Reproducible Experiments** | **IMPLEMENTED** | Pre-registered experiment manifests stored as immutable JSON in `experiments/results/`. |

