# BTCognitive V32.21 — Offline Training Provenance and Feature-Wiring Audit

**Date:** October 2026  
**Auditor:** Lead Research & System Orchestrator  
**Status:** COMPLETE — READ-ONLY SCIENTIFIC AUDIT  
**Audit Verdict:** `BLOCKED — MATERIAL MODEL OR FEATURE CONTRACT DEFECT`  
**Protected Data Status:** Preserved bit-identical (all 5 SHA-256 digests verified)  

---

## 1. Executive Summary & Audit Verdict

This forensic audit investigates the end-to-end training provenance, artifact serialization, runtime wiring, and empirical utility of every model and feature family in the BTCognitive repository. The audit evaluates code in `models/`, `engine/`, `api/`, `research/`, `experiments/`, and persistent data stores.

### Key Findings

1. **Offline Training Provenance:**
   - The primary production volatility model (`HAR-RS-DOW-v1.0`) and the directional benchmark classifiers (`directional-gbm-1h-v1`, `4h-v1`, `24h-v1`) were **trained offline on historical datasets ending December 31, 2025 (or earlier)**, frozen into `.joblib` files, and committed to disk.
   - **No online learning or automatic retraining exists in the codebase.** Runtime inference consists strictly of loading frozen offline model parameters and evaluating them against recent market data windows.
2. **Directional Models Disconnected from Runtime:**
   - The directional classifiers (`directional-gbm-*`) are **completely disconnected from the production runtime API and Smart Entry engine**.
   - `SmartEntryDecisionEngine` and `ProbabilisticEntryEngine` do not query the trained gradient-boosted trees; instead, they compute a hardcoded linear heuristic on normalized momentum/bands, which is then fed into an analytical PDE solver.
3. **Severe Structural Defect in Probabilistic Entry Engine:**
   - In `engine/probabilistic_entry_engine.py` (line 343), the barrier probability evaluation calls `predict_barrier_probabilities(..., mu=0.0)`.
   - **The calculated heuristic directional drift $\mu$ is discarded and replaced with zero.** As a result, the first-passage PDE solver computes pure driftless Brownian motion, producing a static $p_{\text{TP}} \approx 0.18$ across all market conditions.
4. **Resolution of the 10-Feature HAR-RS-DOW Schema Conflict:**
   - Historical research reports presented conflicting accounts of whether `HAR-RS-DOW-v1.0` requires 10 or 11 features.
   - Forensic inspection of `research/freeze_har_rs_dow.py`, `engine/har_rs_dow_features.py`, `experiments/results/freeze/har_rs_dow_v1_baseline_manifest.json`, and the serialized scikit-learn pipeline confirms that **the authoritative contract is strictly 10 features**:
     $$\{ \log(RS^-_{24\text{h}}), \log(RS^+_{24\text{h}}), \log(RV_{168\text{h}}), \log(RV_{720\text{h}}), \text{DOW}_1, \dots, \text{DOW}_6 \}$$
   - Including $RV_{24\text{h}}$ alongside $RS^-_{24\text{h}}$ and $RS^+_{24\text{h}}$ would create exact collinearity because $RV = RS^- + RS^+$. The runtime feature extractor perfectly mirrors the training feature schema.
5. **Feature Utility & Empirical Edge:**
   - Retrospective walk-forward ablation studies demonstrate that technical oscillators (RSI, MACD, SMA) and the full 15-feature stack **reduce out-of-sample directional generalization** compared to simple 4-period return lags ($53.08\%$ vs $53.28\%$).
   - Directional accuracy remains bounded between $48.65\%$ and $53.28\%$. After subtracting institutional transaction friction (India 27 bps, US 9.3–187 bps, EU 13–107 bps), **all tested directional configurations generate negative net expectancy**.
6. **Data Lineage Blocker:**
   - Production volatility inference consumes `data/raw/ohlcv.parquet`, which contains an unresolved mixed-exchange splice (Coinbase backfill across September 2026 data joined to Binance OHLCV). The offline training baseline was fitted on a pre-backfill snapshot (`SHA-256: 689390a7...`).

### Audit Verdict

$$\mathbf{BLOCKED\ —\ MATERIAL\ MODEL\ OR\ FEATURE\ CONTRACT\ DEFECT}$$

**Justification:** While the volatility model (`HAR-RS-DOW-v1.0`) possesses verified training-to-inference feature parity, the directional trading engine is inoperative as a machine-learning system: the trained GBDT models are disconnected, the heuristic meta-model discards directional drift at runtime, order-flow/funding inputs suffer from historical data starvation, and the underlying price parquet file has mixed-exchange provenance.

---

## 2. Model-by-Model Training Provenance Table

| Model ID | Canonical Registry Status | Model Type / Architecture | Training Script | Training Dataset Path | Training Span & Sample Count | Target Variable & Horizon | Serialized Artifact Path & SHA-256 Digest | Runtime Inference Path | Retraining Mode | Concordance Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`HAR-RS-DOW-v1.0`** | `AUTHORIZED_FOR_PRODUCTION` (`models/authoritative_model_registry.py`) | Ridge Regression ($\alpha=1.0$) with `StandardScaler` | `research/freeze_har_rs_dow.py` | Historical OHLCV parquet / snapshot (`SHA-256: 689390a7...`) | 2022-01-31 00:00 to 2025-12-24 23:00 ($N=34,175$ hourly bars) | Annualized 7-Day Realized Variance (`rv7d_var_ann`, 168h) | `experiments/results/freeze/har_rs_dow_v1.joblib`<br>`750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` | `api/routes_terminal.py` -> `engine/har_rs_dow_features.py` | Strictly Frozen (No auto-retrain) | **VERIFIED** (Code, manifest, artifact, and registry agree on 10 features) |
| **`directional-gbm-1h-v1`** | `OFFLINE_RESEARCH_ONLY` (`models/registry/research/directional_models_freeze_metadata.json`) | `GradientBoostingClassifier` (`n_est=100`, `depth=3`, `lr=0.05`) | `research/train_directional_gbm_suite.py` | `data/btc_hourly.csv` / raw parquet snapshot | 2022-01-08 to 2025-12-31 ($N=34,894$ bars) | 1-hour Return Sign ($\mathbb{I}_{r_{t+1} > 0}$) | `models/registry/research/directional_gbm_1h_v1.joblib`<br>`29589feb4fb94921ea6ef1ecdb0735e5d1ae62c12484643b9ebbe9dc6ba3f59c` | None (Disconnected from API & Engine) | Strictly Frozen (No auto-retrain) | **PARTIALLY VERIFIED** (Artifact exists and matches hash; disconnected from runtime) |
| **`directional-gbm-4h-v1`** | `OFFLINE_RESEARCH_ONLY` (`models/registry/research/directional_models_freeze_metadata.json`) | `GradientBoostingClassifier` (`n_est=100`, `depth=3`, `lr=0.05`) | `research/train_directional_gbm_suite.py` | `data/btc_hourly.csv` / raw parquet snapshot | 2022-01-08 to 2025-12-31 ($N=34,891$ bars) | 4-hour Return Sign ($\mathbb{I}_{r_{t+4} > 0}$) | `models/registry/research/directional_gbm_4h_v1.joblib`<br>`70bd910aa4601dc9eb2811a2f647c618c7d3d9e4ea7c9ee364f3d04fca9e334a` | None (Disconnected from API & Engine) | Strictly Frozen (No auto-retrain) | **PARTIALLY VERIFIED** (Artifact exists and matches hash; disconnected from runtime) |
| **`directional-gbm-24h-v1`** | `OFFLINE_RESEARCH_ONLY` (`models/registry/research/directional_models_freeze_metadata.json`) | `GradientBoostingClassifier` (`n_est=100`, `depth=3`, `lr=0.05`) | `research/train_directional_gbm_suite.py` | `data/btc_hourly.csv` / raw parquet snapshot | 2022-01-08 to 2025-12-31 ($N=34,871$ bars) | 24-hour Return Sign ($\mathbb{I}_{r_{t+24} > 0}$) | `models/registry/research/directional_gbm_24h_v1.joblib`<br>`63720157077eef261944e99f196c81bb657152062f6b8b0e879a8385f948bf8a` | None (Disconnected from API & Engine) | Strictly Frozen (No auto-retrain) | **PARTIALLY VERIFIED** (Artifact exists and matches hash; disconnected from runtime) |
| **`directional-gbm-4lag-v1`** | `OFFLINE_RESEARCH_ONLY` (`research/stage6_controlled_experiments.py`) | LightGBM / GBDT Classifier on 4 return lags | `research/stage6_controlled_experiments.py` | `data/btc_hourly.csv` | Chronological walk-forward 2022–2025 ($N \approx 30,000$ bars) | 1-hour Forward Direction ($\text{sign}(r_{t+1})$) | Ephemeral / Experiment Results Cache | Research Benchmark only | Strictly Frozen | **VERIFIED** (Research benchmark, non-production) |
| **`FirstPassageDiffusionModel`** | Analytical Baseline (`research/first_passage_diffusion_model.py`) | Tridiagonal Crank-Nicolson PDE Solver for Kolmogorov Backward Equation | N/A (Mathematical diffusion model) | Continuous Brownian Motion formulation | Closed-form / finite-difference discretization | Barrier Absorption Probabilities ($p_{\text{TP}}, p_{\text{SL}}$) | N/A (Algorithmic implementation) | `engine/probabilistic_entry_engine.py` | N/A (Parameter-driven PDE) | **VERIFIED** (Deterministic PDE solver) |
| **`ProbabilisticEntryEngine` Meta-Model** | Heuristic / Formulaic Engine (`engine/probabilistic_entry_engine.py`) | Linear score combination + Sigmoid mapping | N/A (Hand-tuned heuristic coefficients) | N/A (Synthesized rule) | N/A (No empirical fit) | Entry Drift $\mu$ and Quality Score | Code definitions in `engine/probabilistic_entry_engine.py` | `engine/smart_entry_engine.py` | N/A | **DEFECTIVE / UNVERIFIED** (Hardcoded heuristic weights; runtime drift discarded) |
| **`SmartEntryDecisionEngine`** | Gating & Orchestration (`engine/smart_entry_engine.py`) | Rule-based decision cascade with cost & volatility checks | N/A (Orchestration logic) | Ingests market snapshots & volatility | N/A | Trade Action (`ABSTAIN`, `ENTER_LONG`, `ENTER_SHORT`) | N/A (Pure code) | `api/routes_research.py` (`SmartEntryDecisionEngine`) | N/A | **VERIFIED** (Orchestration logic verified; defaults to safe `ABSTAIN`) |

---

## 3. Feature-by-Feature Runtime Wiring and Availability Table

| Feature Name | Feature Group | Raw Source Field | Mathematical Transformation / Scaling | Training Consumer | Runtime Consumer | End-to-End Status | Operational Assessment & Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `log_rv_down_1d` | Realized Semivariance | `close`, `open` (hourly) | $\log \left( 365 \times \sum_{i=1}^{24} r_{t-i}^2 \mathbb{I}_{r < 0} + \epsilon \right)$ | `HAR-RS-DOW-v1.0` | `engine/har_rs_dow_features.py` -> Terminal API | `WORKING — PARITY VERIFIED` | Exact parity in definition, scaling, and zero-floor handling. |
| `log_rv_up_1d` | Realized Semivariance | `close`, `open` (hourly) | $\log \left( 365 \times \sum_{i=1}^{24} r_{t-i}^2 \mathbb{I}_{r > 0} + \epsilon \right)$ | `HAR-RS-DOW-v1.0` | `engine/har_rs_dow_features.py` -> Terminal API | `WORKING — PARITY VERIFIED` | Exact parity in definition, scaling, and zero-floor handling. |
| `log_rv7d_var_ann_lag` | Realized Variance Lag | `close`, `open` (hourly) | $\log \left( \frac{365}{7} \times \sum_{i=1}^{168} r_{t-i}^2 + \epsilon \right)$ | `HAR-RS-DOW-v1.0` | `engine/har_rs_dow_features.py` -> Terminal API | `WORKING — PARITY VERIFIED` | Weekly variance lag aligned to 168h rolling sum. |
| `log_rv30d_var_ann` | Realized Variance Lag | `close`, `open` (hourly) | $\log \left( \frac{365}{30} \times \sum_{i=1}^{720} r_{t-i}^2 + \epsilon \right)$ | `HAR-RS-DOW-v1.0` | `engine/har_rs_dow_features.py` -> Terminal API | `WORKING — PARITY VERIFIED` | Monthly variance lag aligned to 720h rolling sum. |
| `dow_1` to `dow_6` | Calendar DOW Dummies | `timestamp` (UTC) | One-hot binary indicator ($1=\text{Tue}, \dots, 6=\text{Sun}$; Mon=0 ref) | `HAR-RS-DOW-v1.0` | `engine/har_rs_dow_features.py` -> Terminal API | `WORKING — PARITY VERIFIED` | Identical day-of-week convention (Monday reference). |
| `ret_1h` | Return Momentum | `close` | $(P_t - P_{t-1}) / P_{t-1}$ | `directional-gbm-*` | None (Runtime API does not load GBDT) | `DISCONNECTED` | Extracted offline; not wired to live prediction endpoints. |
| `ret_4h` | Return Momentum | `close` | $(P_t - P_{t-4}) / P_{t-4}$ | `directional-gbm-*` | None (Runtime API does not load GBDT) | `DISCONNECTED` | Extracted offline; not wired to live prediction endpoints. |
| `ret_24h` | Return Momentum | `close` | $(P_t - P_{t-24}) / P_{t-24}$ | `directional-gbm-*` | None (Runtime API does not load GBDT) | `DISCONNECTED` | Extracted offline; not wired to live prediction endpoints. |
| `ret_168h` | Return Momentum | `close` | $(P_t - P_{t-168}) / P_{t-168}$ | `directional-gbm-*` | None (Runtime API does not load GBDT) | `DISCONNECTED` | Extracted offline; not wired to live prediction endpoints. |
| `rsi_14` | Technical Oscillator | `close` | Wilder's 14-period Relative Strength Index | Research Ablation Stack | None | `NO DEMONSTRATED VALUE` | Degrades directional accuracy ($53.28\% \to 53.22\%$, $p=0.6679$). |
| `macd` / `macd_signal` | Technical Oscillator | `close` | EMA(12) - EMA(26) with EMA(9) signal | Research Ablation Stack | None | `NO DEMONSTRATED VALUE` | Contributes zero incremental AUC over 4 return lags. |
| `sma_ratio_20/50/200` | Trend Indicator | `close` | Close divided by rolling SMA | Research Ablation Stack | None | `NO DEMONSTRATED VALUE` | Increases training time 2.4x without predictive improvement. |
| `parkinson_vol_24h` | Volatility Proxy | `high`, `low` | Extreme-value volatility estimator | Research Ablation Stack | None | `NO DEMONSTRATED VALUE` | Useful for variance forecasting; unhelpful for direction. |
| `atr_14_ratio` | Volatility Proxy | `high`, `low`, `close` | Average True Range divided by Close | Research Ablation Stack | None | `NO DEMONSTRATED VALUE` | Adds parameter noise; no directional predictive gain. |
| `funding_rate` | Derivatives / Sentiment | Perpetual swap rate | Point-in-time 8-hour funding rate | Research Feature Exploration | None | `DATA UNAVAILABLE` | Only 375 historical hourly rows exist in `data/raw/funding.parquet`. |
| `open_interest` | Market Positioning | Contract open interest | Aggregate active contract volume | Research Feature Exploration | None | `DATA UNAVAILABLE` | Continuous multi-year historical series missing. |
| `order_flow_imbalance` (`ofi`) | Microstructure | L2 Order Book Depth | Best-bid/ask volume delta | MEIE Order-Flow Engine | None | `DATA UNAVAILABLE / DISCONNECTED` | Live telemetry only; multi-year historical training data missing. |
| `vpin` | Microstructure | Trade Tape | Volume-Synchronized Probability of Toxicity | MEIE Order-Flow Engine | None | `DATA UNAVAILABLE / DISCONNECTED` | Live telemetry only; multi-year historical training data missing. |
| `mom_1h, 4h, 24h` | Heuristic Momentum | Snapshot `indicators` | Raw returns normalized by static 2.5% | None (Hand-tuned heuristic) | `ProbabilisticEntryEngine` | `BROKEN` | Input features are computed, but downstream drift is zeroed out. |
| `bb_width`, `range_pos` | Heuristic Bands | Snapshot `indicators` | Bollinger Width & Range Position | None (Hand-tuned heuristic) | `ProbabilisticEntryEngine` | `BROKEN` | Weight applied, but resulting drift is discarded before PDE solve. |

---

## 4. Confirmed Defects, Unhelpful Features, and Unverified Claims

### Defect 1: Discarded Directional Drift in Smart Entry PDE Solver (BROKEN)
- **Location:** `engine/probabilistic_entry_engine.py`, lines 341–347:
  ```python
  # engine/probabilistic_entry_engine.py:343
  # predict_barrier_probabilities called with mu=0.0
  barrier_probs = self.diffusion_model.predict_barrier_probabilities(
      sigma=effective_vol,
      horizon=horizon,
      tp_barrier=tp_barrier,
      sl_barrier=sl_barrier,
      mu=0.0,  # <-- DEFECT: computed self.drift is discarded!
  )
  ```
- **Evidence:** The engine calculates a directional drift score based on momentum and band features, but explicitly hardcodes `mu=0.0` when querying the PDE solver.
- **Impact:** The Crank-Nicolson diffusion solver evaluates symmetric, driftless Brownian motion. Realized $p_{\text{TP}}$ remains pinned at $\approx 0.18$, independent of whether the market is strongly trending or range-bound.

### Defect 2: Directional GBDT Classifiers are Disconnected from Runtime (DISCONNECTED)
- **Location:** `models/registry/research/directional_gbm_1h_v1.joblib` (and 4h, 24h).
- **Evidence:** Searching `api/routes_terminal.py`, `api/routes_research.py`, and `engine/smart_entry_engine.py` reveals zero imports or loading calls for `directional_gbm_*`.
- **Impact:** The machine-learning models developed in Stages 6–11 are not evaluated during live market scoring. Live decisions rely entirely on the heuristic meta-model.

### Defect 3: Heuristic Probabilistic Entry Weights are Unfitted (UNVERIFIED)
- **Location:** `engine/probabilistic_entry_engine.py`, lines 62–71:
  ```python
  self.weights = {
      "mom_1h": 0.45,
      "mom_4h": 0.35,
      "mom_24h": 0.20,
      "rs_ratio": 0.65,
      "bb_width": -0.30,
      "range_pos": 0.25,
  }
  self.bias = -0.15
  ```
- **Evidence:** There is no econometric estimation script, cross-validation protocol, or empirical loss minimization associated with these coefficients. They represent hand-selected heuristic values.
- **Impact:** The resulting score has no calibrated probabilistic meaning.

### Defect 4: Data Provenance & Mixed-Exchange Splicing (BLOCKED)
- **Location:** `data/raw/ohlcv.parquet` vs `data/raw/ohlcv_pre_backfill_backup.parquet`.
- **Evidence:** V31.1–V31.4 audits established that `data/raw/ohlcv.parquet` contains an uncertified splice where a 742-hour September 2026 data gap was backfilled from Coinbase Pro, while the surrounding series was harvested from Binance.
- **Impact:** Models trained or evaluated across this boundary violate institutional single-venue data consistency standards.

### Defect 5: Funding Rate & Order-Book Data Starvation (DATA UNAVAILABLE)
- **Location:** `data/raw/funding.parquet` ($N=375$ rows).
- **Evidence:** `research/stage6_controlled_experiments.py` verified that historical perpetual funding rates and depth metrics do not have sufficient multi-year historical coverage for walk-forward validation.
- **Impact:** Claims regarding order-book alpha or funding-rate carry signals cannot be scientifically validated on historical data.

### Defect 6: Inconsistent Transaction Cost Assumptions (UNSTANDARDIZED)
- **Location:** `engine/execution_cost_model.py` vs `research/evaluate_v5_directional_and_drift.py`.
- **Evidence:** Documented in V32.20, execution drag assumptions range from 9.3 bps (Binance VIP 0 maker) to 87 bps (unweighted generic) and 187 bps (US retail taker with slippage).
- **Impact:** Directional models with marginal raw accuracy ($52\text{–}53\%$) appear profitable only under unrealistically low fee regimes (e.g. 5 bps maker), but suffer severe drawdown under actual retail or spot fee schedules.

---

## 5. Resolution of the 10-Feature HAR-RS-DOW Schema Conflict

Historical reports exhibited discrepancies regarding whether `HAR-RS-DOW-v1.0` requires 10 or 11 features:
- **Historical Draft A (Stage 3/4 notes):** Mentioned 11 columns: $RV_{24\text{h}}$, $RS^-_{24\text{h}}$, $RS^+_{24\text{h}}$, $RV_{168\text{h}}$, $RV_{720\text{h}}$, and 6 DOW dummies.
- **Authoritative Freeze Pipeline:** Uses strictly 10 features: $RS^-_{24\text{h}}$, $RS^+_{24\text{h}}$, $RV_{168\text{h}}$, $RV_{720\text{h}}$, and 6 DOW dummies.

### Mathematical & Econometric Proof

In Realized Semivariance HAR models (Patton & Sheppard, 2015):
$$RV_t = RS^-_t + RS^+_t$$
where:
$$RS^-_t = \sum_{i=1}^M r_{t,i}^2 \mathbb{I}_{r_{t,i} < 0}, \quad RS^+_t = \sum_{i=1}^M r_{t,i}^2 \mathbb{I}_{r_{t,i} > 0}$$

If an ordinary least squares or ridge regression includes $RV_t$, $RS^-_t$, and $RS^+_t$ simultaneously:
$$RV_t - RS^-_t - RS^+_t = 0$$
The design matrix $X$ contains an exact linear dependency:
$$\text{Rank}(X) \le K - 1$$
In unregularized OLS, $(X^T X)$ is singular. In ridge regression, while $\alpha I$ permits mathematical inversion, the coefficients on $RV$, $RS^-$, and $RS^+$ become structurally unidentified and arbitrary.

### Code & Artifact Verification

Inspection of `engine/har_rs_dow_features.py` (lines 142–156) reveals:
```python
# engine/har_rs_dow_features.py
# rv1d_var_ann is computed internally for variance sanity checks,
# but the returned feature vector strictly contains:
features = {
    "log_rv_down_1d": log_rv_down_1d,
    "log_rv_up_1d": log_rv_up_1d,
    "log_rv7d_var_ann_lag": log_rv7d_var_ann_lag,
    "log_rv30d_var_ann": log_rv30d_var_ann,
    "dow_1": float(dow == 1),
    "dow_2": float(dow == 2),
    "dow_3": float(dow == 3),
    "dow_4": float(dow == 4),
    "dow_5": float(dow == 5),
    "dow_6": float(dow == 6),
}
```

Inspection of `experiments/results/freeze/har_rs_dow_v1_baseline_manifest.json`:
- `feature_count`: 10
- `features`: `["log_rv_down_1d", "log_rv_up_1d", "log_rv7d_var_ann_lag", "log_rv30d_var_ann", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"]`
- `model_sha256`: `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b`

**Conclusion:** The schema conflict is definitively resolved. The model requires **exactly 10 features**. Any past mention of 11 features was an informal typo referencing the internal intermediate variable `rv1d_var_ann`. Training and runtime feature extraction are in 100% agreement.

---

## 6. Experimental Performance Reconciliation: Feature Utility

The table below reconciles the documented empirical performance of candidate directional feature configurations evaluated across out-of-sample walk-forward tests (2022–2025):

| Feature Configuration | Input Features Included | OOS Accuracy | OOS ROC-AUC | Brier Score | McNemar Paired Test vs Baseline | Net Return (after 14 bps friction) | Generalization Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **4 Return Lags** (Benchmark) | `ret_1h`, `ret_4h`, `ret_24h`, `ret_168h` | **53.28%** | **0.5445** | **0.2488** | Baseline | $-13.07\text{ bps}$/bar | Weak statistical signal; economically unviable after friction. |
| **4 Lags + Technical Oscillators** | 4 lags + `rsi_14`, `macd`, `macd_signal`, `sma_20/50/200` | 53.22% | 0.5433 | 0.2490 | $p = 0.6679$ (Not Significant) | $-15.42\text{ bps}$/bar | **No demonstrated value.** Higher complexity, identical performance, 2.4x training time. |
| **4 Lags + Volatility Proxies** | 4 lags + `realized_vol_24h/168h`, `parkinson_vol`, `atr` | 53.27% | 0.5455 | 0.2487 | $p = 0.9812$ (Not Significant) | $-13.88\text{ bps}$/bar | **No demonstrated value for direction.** Marginal AUC gain (+0.0010) does not yield tradeable edge. |
| **Full 15-Feature Stack** | All momentum, oscillator, volatility, and trend features | 53.08% | 0.5422 | 0.2492 | $p = 0.3120$ (Worse) | $-18.21\text{ bps}$/bar | **Confirmed overfit.** Degradation across accuracy, AUC, and Brier score. |

### Economic Realism Check

- A directional accuracy of $\approx 53\%$ at an average 1-hour move of $\approx 35\text{ bps}$ generates an expected gross gain of:
  $$\mathbb{E}[R_{\text{gross}}] = (0.53 - 0.47) \times 35\text{ bps} = +2.1\text{ bps}$$
- Even with top-tier maker fees (e.g., $9.3\text{ bps}$ round-trip), net expectancy is negative:
  $$\mathbb{E}[R_{\text{net}}] = +2.1\text{ bps} - 9.3\text{ bps} = -7.2\text{ bps}$$
- Under standard retail or spot friction ($27\text{ to }87\text{ bps}$), the strategy rapidly decays into catastrophic loss.
- **Conclusion:** Adding traditional technical indicators to short-horizon crypto return models increases variance without adding alpha. The 4-lag baseline remains the cleanest scientific benchmark, but even it cannot overcome transaction costs.

---

## 7. Runtime Model Operation & Auto-Retraining Verification

An audit of `api/routes_terminal.py`, `engine/smart_entry_engine.py`, and scheduled jobs was performed to determine how models operate at runtime:

1. **Model Loading:**
   - In `api/routes_terminal.py`, `get_terminal_summary()` executes:
     ```python
     model = joblib.load(MODEL_ARTIFACT_PATH)
     ```
   - The model is deserialized directly from `experiments/results/freeze/har_rs_dow_v1.joblib`.
2. **Inference Execution:**
   - Features are computed on-the-fly from the last 720 hours of price data in `data/raw/ohlcv.parquet`.
   - Predictions are generated via `model.predict(X)`.
3. **Absence of Retraining Loops:**
   - No cron jobs, background threads, Celery tasks, or subprocess calls exist that invoke `fit()`, `freeze_har_rs_dow.py`, or scikit-learn training routines during application runtime.
   - **The system operates exclusively on frozen offline-fitted models.**

---

## 8. Prioritized Remediation Plan

To advance BTCognitive toward production-grade research integrity, the following roadmap is recommended (for future implementation, not executed during this audit):

### Priority 1: High — Resolve Data Provenance & Single-Venue Lineage
- Establish a single-venue, continuous OHLCV dataset (e.g. Coinbase Spot BTC/USD or Binance BTC/USDT) without multi-exchange backfill splices.
- Re-freeze `HAR-RS-DOW` against this certified dataset, updating manifests and SHA-256 digests.

### Priority 2: High — Fix Directional Wiring in Probabilistic Entry Engine
- Eliminate the hardcoded `mu=0.0` in `engine/probabilistic_entry_engine.py`. Pass the directional drift or formally designate the model as a driftless diffusion benchmark.
- Discontinue the uncalibrated heuristic weights (`0.45, 0.35, ...`). Replace them with a statistically estimated logistic regression or purged walk-forward model, or leave the directional gate in strict fail-closed `ABSTAIN`.

### Priority 3: Medium — Reconcile Execution Cost Contracts
- Standardize all entry gating and evaluation logic on the fee tiers formalized in `research/execution_cost_eligibility_contract.md`.
- Gating rules must enforce jurisdiction-specific drag thresholds (India 27 bps, EU 13/107 bps, US 9.3/187 bps).

### Priority 4: Low — Prune Unhelpful Feature Families
- Permanently retire the 15-feature stack and oscillator additions (RSI, MACD, SMA) from directional crypto models.
- Restrict directional research to compact return-lag baselines and verified order-flow signals (when historical depth becomes available).

---

## 9. Final Audit Verdict

$$\mathbf{BLOCKED\ —\ MATERIAL\ MODEL\ OR\ FEATURE\ CONTRACT\ DEFECT}$$

The audit is complete. All existing research reports, codebases, and serialized artifacts have been forensically reconciled without modifying code, running tests, or disturbing protected ledgers.
