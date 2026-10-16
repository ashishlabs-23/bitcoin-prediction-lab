# 📜 Authoritative Model Card: `HAR-RS-DOW-v1.0`

## 1. Model Overview & Authoritative Identity

* **Model ID**: `HAR-RS-DOW-v1.0`
* **Version**: `1.0.0`
* **System Classification**: `PRODUCTION_VOLATILITY`
* **Operational Status**: `AUTHORIZED_FOR_PRODUCTION_VOLATILITY_INTELLIGENCE`
* **Model Architecture**: Heterogeneous Autoregressive model of Realized Variance with Realized Semivariances (Patton & Sheppard, 2015) and Day-of-Week Seasonality (HAR-RS-DOW)
* **Primary Prediction Output**: Annualized Forward 7-Day Realized Variance ($\text{rv7d\_var\_ann}$) and equivalent Annualized Volatility percentage
* **Uncertainty Calibration**: C2 Dependence-Aware Conformal Prediction (alpha = 0.10, nominal 90% risk envelope)
* **Serving Endpoints**: `/api/terminal/live`, `/api/terminal/model-identity`
* **Artifact Location**: `experiments/results/freeze/har_rs_dow_v1.joblib`
* **Artifact SHA256**: `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b`
* **Scientific Contract Hash**: `841deba5fb30118bea849f93ebc9fb7d1984d74fd2d709013544c6d5db94cf07`

---

## 2. Ingested Features & Target Specification

* **Runtime Inference Input Dependency**:
  - `data/raw/ohlcv.parquet` strictly (Coinbase BTC/USD 1-hour OHLCV candles, 2022-01-31 to present).
  - ZERO dependency on `iv7d.parquet` or external derivatives for production inference.
* **Feature Schema (10 Point-in-Time Features)**:
  1. `log_rv_down_1d`: Trailing 24-hour downside realized semivariance (annualized log)
  2. `log_rv_up_1d`: Trailing 24-hour upside realized semivariance (annualized log)
  3. `log_rv7d_var_ann_lag`: Trailing 7-day realized variance (annualized log)
  4. `log_rv30d_var_ann`: Trailing 30-day realized variance (annualized log)
  5. `dow_1` through `dow_6`: Day-of-week binary indicator dummy regressors (Tuesday through Sunday; Monday dropped as reference)
* **Target Definition**:
  - $\text{rv7d\_var\_ann}_t = \frac{8760}{168} \sum_{i=1}^{168} r_{t+i}^2$
  - Forward 168-hour (7 calendar days) sum of squared hourly log returns annualized by $8760/168 = 52.1428$.

---

## 3. Verified Performance & Statistical Rigor

* **Out-of-Sample Holdout**:
  - Chronological boundary: `2026-01-01T00:00:00Z` to present (strictly unobserved during training).
  - Training window: `2022-01-31 00:00:00+00:00` to `2025-12-24 23:00:00+00:00`.
  - Embargo / Purge: 168-hour label horizon gap strictly enforced between train and holdout (zero forward-looking target leakage).
* **Empirical Verification**:
  - **QLIKE Loss**: `0.19300` (Superior to standard HAR-RV and RW baselines).
  - **C2 In-Sample Calibration Containment (Pre-2026)**: `92.84%` (95% CI: `[88.25%, 96.46%]`).
  - **C2 Strictly Causal Out-of-Sample Holdout (2026, N=5,671)**: `84.89%` (95% Stationary Block Bootstrap CI: `[73.14%, 93.14%]`).
  - **Interval Sharpness (2026 Causal)**: Mean Width = `0.4389` | Median Width = `0.2364` | Relative Width = `2.71x` | Mean Winkler Score = `1.0444`.
  - **Extreme Volatility Regime Containment**: `89.47%` (95% CI: `[82.39%, 96.65%]`).
  - **Tail Breach Asymmetry**: Upper: `3.67%` | Lower: `3.43%` ($\Delta = 0.24\%$).
  - **Legacy Leaked Calculation Note**: Earlier reports indicated `92.36%` holdout coverage, which was found in Stage 12 to suffer from 168-hour contemporaneous residual leakage. Strictly causal evaluation establishes `84.89%`.

---

## 4. Epistemic Disclaimers & Prohibitions

1. **Not a Directional Predictor**: This model forecasts realized variance (magnitude of price dispersion), NOT the sign or direction of future returns. A high-volatility forecast does not mean price will rise or fall.
2. **Quantile Containment != Directional Accuracy**: The 92.84% empirical containment rate measures whether realized variance lands inside the C2 risk envelope; it must NEVER be cited as 92.84% directional accuracy.
3. **Non-Execution Invariant**: Live capital deployment and execution routing are disabled in code. This forecast serves decision support and risk envelopes only.
4. **No Automated Retraining**: Auto-retraining is strictly disabled to prevent silent parameter drift or contamination.
