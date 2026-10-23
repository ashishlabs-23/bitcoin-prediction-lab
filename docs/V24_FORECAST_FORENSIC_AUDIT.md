# BTCognitive V24 — Forecast Forensics & Statistical Verification Audit

**Specialist Role:** Agent A (Quantitative Forecast Auditor)  
**Date:** 19 October 2026  
**Status:** Canonical Reconciliation Complete — `PERSISTENCE_BASELINE_UNBEATEN`  
**Dataset SHA-256:** `43c8881b57431759f68fcb7036d78432449d079b11bcaea45f0d0ecfa287e2f6` (`data/raw/ohlcv.parquet`, 41,273 rows)  

---

## 1. Executive Summary & Root-Cause Forensic Resolution

A core objective of V24 was to definitively resolve the reported discrepancy between the V20 and V23 forecast error metrics:
- **Reported V20 Persistence Values:** 4h RMSE = **$843.34**; 24h RMSE = **$2,073.67**.
- **Reported V23 Text Narrative:** 4h Persistence RMSE = **$868.51**; 24h Persistence RMSE = **$2,243.68**.

Both reports claimed to evaluate on the same canonical parquet dataset hash (`43c8881b...`).

### The Forensic Finding
By executing an independent parametric windowing and origin-sampling audit (`scratch/rmse_forensics.py`) directly against `data/raw/ohlcv.parquet`, the following root cause was established:
1. **The Canonical Machine Manifests Agree:** Both `experiments/results/v20_forecast_reproducibility_manifest.json` and `experiments/results/v23_canonical_forecast_manifest.json` specify identical, deterministic values:
   - **1-hour ($N=15,000$):** Persistence MAE = **$283.66**, RMSE = **$435.32**; Ridge MAE = **$283.68**, RMSE = **$435.36**.
   - **4-hour ($N=3,750$):** Persistence MAE = **$560.48**, RMSE = **$843.34**; Ridge MAE = **$560.64**, RMSE = **$843.52**.
   - **24-hour ($N=625$):** Persistence MAE = **$1,458.31**, RMSE = **$2,073.67**; Ridge MAE = **$1,458.54**, RMSE = **$2,075.47**.
2. **Origin of the $868.51 / $2,243.68 Figures:** During preliminary V23 research, an exploratory evaluation window shifted by +2,000 to +4,000 bars into the higher-volatility regime of mid-to-late 2026 was evaluated. While the code properly generated the canonical manifest based on the preregistered $[20000, 35000]$ evaluation range, the narrative markdown table in `docs/V23_FORECAST_REPRODUCIBILITY_REPORT.md` inadvertently transcribed numbers from the exploratory run.
3. **Remediation:** The narrative table in `docs/V23_FORECAST_REPRODUCIBILITY_REPORT.md` has been aligned with the canonical manifest. `experiments/results/v23_canonical_forecast_manifest.json` is reaffirmed as the single authoritative source of truth.

---

## 2. Walk-Forward Tournament Protocol Verification

The deterministic tournament protocol is implemented in `scripts/reproduce_v20_forecast_tournament.py` and strictly enforces point-in-time causal integrity:
- **Causal Feature Timing:** $t_{\text{feature}} \le t_{\text{origin}} < t_{\text{target}}$.
- **Closed Candles Only:** No incomplete or forming bars are included.
- **Initial Training Window:** $N_{\text{train}} = 20,000$ hourly bars (Jan 2022 to mid 2024).
- **Evaluation Origins:** $N_{\text{eval}} = 15,000$ bars ($[20,000, 35,000]$), strictly non-overlapping with evaluation step size equal to horizon $h$:
  - $h=1\text{h}$: Evaluation step = 1 bar, $N = 15,000$ non-overlapping origins.
  - $h=4\text{h}$: Evaluation step = 4 bars, $N = 3,750$ non-overlapping origins.
  - $h=24\text{h}$: Evaluation step = 24 bars, $N = 625$ non-overlapping origins.
- **Held-out Prospective Buffer:** Remaining 6,273 bars ($[35,000, 41,273]$) represent retrospective out-of-sample data reserved for prospective ledger validation.

---

## 3. Metric Calculations and Formulas

All metrics are computed directly from realized price $y_{t+h}$ and model prediction $\hat{y}_{t+h|t}$:

### Mean Absolute Error (MAE)
$$\text{MAE} = \frac{1}{N} \sum_{i=1}^N \left| y_i - \hat{y}_i \right|$$

### Root Mean Squared Error (RMSE)
$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$

### Mean Error (Bias)
$$\text{Bias} = \frac{1}{N} \sum_{i=1}^N (\hat{y}_i - y_i)$$

### Baseline-Relative Skill Score
$$\text{Skill} = 1.0 - \frac{\text{MSE}_{\text{challenger}}}{\text{MSE}_{\text{persistence}}}$$
A negative skill score demonstrates that the challenger model performs worse than the simple random-walk persistence baseline ($\hat{y}_{t+h|t} = y_t$).

---

## 4. Diebold-Mariano & Harvey-Leybourne-Newbold (HLN) Test Audit

The statistical significance of loss differentials is assessed via the Diebold-Mariano (1995) test with Harvey, Leybourne, and Newbold (1997) finite-sample correction:

1. **Loss Differential:** $d_t = L(e_{t,\text{persistence}}) - L(e_{t,\text{challenger}})$, where $L(e) = e^2$ (squared error loss).
2. **Mean Differential:** $\bar{d} = \frac{1}{T} \sum_{t=1}^T d_t$.
3. **Autocovariance & Long-Run Variance:** Because evaluations use non-overlapping blocks of step $h$, serial correlation of forecast errors is minimized. However, for finite samples, the spectral variance estimator $\hat{\gamma}_0 + 2\sum_{k=1}^{h-1} \hat{\gamma}_k$ is computed.
4. **HLN Finite-Sample Modification:**
   $$\text{DM}^* = \text{DM} \times \left[ \frac{T + 1 - 2h + h(h-1)/T}{T} \right]^{1/2}$$
5. **Reference Distribution:** Critical values and $p$-values are evaluated against Student's $t$-distribution with $T-1$ degrees of freedom ($\nu = T-1$), avoiding Gaussian asymptotic overconfidence.

### Statistical Results Summary:

| Horizon | Sample Size ($N$) | Persistence MAE | Persistence RMSE | Ridge L2 MAE | Ridge L2 RMSE | Skill Score | DM-HLN Stat | $p$-value | Preregistered Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Hour** | 15,000 | **$283.66** | $435.32 | $283.68 | $435.36 | -0.016% | -1.2208 | 0.2222 | `PERSISTENCE_BASELINE_UNBEATEN` |
| **4 Hours** | 3,750 | **$560.48** | $843.34 | $560.64 | $843.52 | -0.044% | -0.9695 | 0.3324 | `PERSISTENCE_BASELINE_UNBEATEN` |
| **24 Hours** | 625 | **$1,458.31** | $2,073.67 | $1,458.54 | $2,075.47 | -0.173% | -0.6955 | 0.4870 | `PERSISTENCE_BASELINE_UNBEATEN` |

**Statistical Conclusion:** For all horizons, Ridge regression yields negative skill scores relative to persistence, and the null hypothesis of equal predictive accuracy cannot be rejected ($p > 0.20$). Persistence remains the undefeated future-price baseline.

---

## 5. Preregistered Model Governance Boundary

1. **Target Separation:** This evaluation exclusively measures future price level prediction ($P_{t+h}$). It does not govern HAR-RS-DOW, which models 7-day annualized realized variance (`rv7d_var_ann`) and operates under a separate research contract.
2. **Model Status:** Ridge L2 is classified strictly as `OFFLINE_RESEARCH_ONLY`.
3. **Execution Gate:** No forecasting model is authorized for live trading. Live trading remains `DISABLED`.
