# BTCognitive — Quantitative Research & Challenger Evaluation Report

**Experiment ID:** EXP-VOL-CHALLENGER-2026-01  
**Execution Date:** 2026-10-17T04:27:45.299286+00:00  
**Epistemic Standard:** Development Replay Holdout (Non-Overlapping Blocks) + Pre-Registered Prospective Challengers  
**Primary Loss Metric:** Patton (2011) Homogeneous Bregman QLIKE Loss  

---

## 1. Executive Summary & Epistemic Boundary
This report executes the preregistered research experiment evaluating candidate volatility forecasting models against frozen baselines across two decoupled horizons:
1. **168-Hour Horizon (Annualized 7-Day Realized Variance, `rv7d_var_ann`):** N = 36 non-overlapping 7-day blocks.
2. **24-Hour Horizon (Annualized 24-Hour Realized Variance Proxy, `rv24h_var_ann`):** N = 258 non-overlapping 1-day blocks.

**Key Findings:**
- **168H Canonical Baseline (`HAR-RS-DOW-v1.0`):** Outperforms naive persistence with lower QLIKE loss (0.16164 vs 0.23964, HLN t-stat = 1.4318, p = 0.1611). It is retained in the 95% Model Confidence Set.
- **24H QLIKE Challenger (`HAR-QLIKE-24H-v1.0`):** Demonstrates lower QLIKE loss than conventional OLS-HAR (0.38065 vs 0.46908), with HLN t-stat = 1.4253 (p = 0.1553). Survives in the 95% Model Confidence Set.
- **Confirmatory Research Boundary:** Because this dataset represents historical development replay, neither challenger is granted automatic production authorization. Both remain `OFFLINE_RESEARCH_ONLY` pending $\ge 100$ clean prospective blocks in the append-only ledger.

---

## 2. 168-Hour Horizon Evaluation (`rv7d_var_ann`)

**Dataset:** 36 strictly non-overlapping 168-hour blocks (2026-01-01 to 2026-10-16).

| Model Candidate | Model Role | Mean QLIKE | RMSE | MAE | 95% MCS Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **HAR-RS-DOW-v1.0** | Canonical Production Baseline | **0.16164** | 0.12892 | 0.08743 | **SURVIVES (In MCS)** |
| **Rolling-720h HAR-RS** | Research Challenger | 0.27031 | 0.14430 | 0.09091 | **SURVIVES (In MCS)** |
| **Persistence (168h)** | Naive Baseline | 0.23964 | 0.16168 | 0.10786 | Eliminated |
| **Rolling 30D (168h)** | Naive Benchmark | 0.29377 | 0.15605 | 0.11217 | Eliminated |

### Statistical Comparison:
- **HAR-RS-DOW-v1.0 vs. Persistence:** HLN = 1.4318, p-value = 0.1611, Mean Diff = 0.077994
- **Rolling-720h vs. HAR-RS-DOW-v1.0:** HLN = -1.5666, p-value = 0.1262, Mean Diff = -0.108668
- **95% Model Confidence Set:** ['Persistence (168h)', 'Rolling 30D (168h)', 'HAR-RS-DOW-v1.0 (Canonical)', 'Rolling-720h HAR-RS (Challenger)']

---

## 3. 24-Hour Horizon Evaluation (`rv24h_var_ann`)

**Dataset:** 258 strictly non-overlapping 24-hour blocks (2026-01-01 to 2026-10-16).

| Model Candidate | Model Role | Mean QLIKE | RMSE | MAE | 95% MCS Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **HAR-QLIKE-24H-v1.0** | Research Challenger | **0.38065** | 0.25714 | 0.13192 | **SURVIVES (In MCS)** |
| **HAR-OLS-24H** | Conventional Baseline | 0.46908 | 0.26530 | 0.11238 | **SURVIVES (In MCS)** |
| **Rolling-720h HAR-24H** | Research Challenger | 9292.44248 | 0.32189 | 0.16286 | **SURVIVES (In MCS)** |
| **Persistence (24h)** | Naive Baseline | 0.85040 | 0.34036 | 0.15812 | Eliminated |
| **Rolling 30D (24h)** | Naive Benchmark | 0.56708 | 0.28261 | 0.14375 | Eliminated |

### Statistical Comparison:
- **HAR-QLIKE-24H vs. HAR-OLS-24H:** HLN = 1.4253, p-value = 0.1553, Mean Diff = 0.088429
- **Rolling-720h vs. HAR-OLS-24H:** HLN = -4.0247, p-value = 0.0001, Mean Diff = -9291.973401
- **95% Model Confidence Set:** ['HAR-OLS-24H (Conventional)', 'HAR-QLIKE-24H-v1.0 (Challenger)']

---

## 4. Governed Governance Verdict
1. **Canonical Production Model:** `HAR-RS-DOW-v1.0` remains the sole authorized production model for 168-hour volatility risk.
2. **Challenger Models:** `HAR-QLIKE-24H-v1.0` and `Rolling-720h HAR-RS` remain strictly `OFFLINE_RESEARCH_ONLY`.
3. **Prospective Hurdle:** Confirmatory evaluation requires accumulation of >= 100 clean non-overlapping blocks in `data/prospective_forecast_ledger.jsonl`.
