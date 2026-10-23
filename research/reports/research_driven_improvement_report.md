# BTCognitive — Research-Driven Improvement Sprint Report

**Document Version:** 1.0  
**Date:** 16 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Product Posture:** Research-First BTCUSD Market Intelligence (Non-Execution)  
**Authoritative Documents & References:**
- [docs/BTCognitive_Master_PRD.md](file:///c:/Projects/BTCognitive/BTCognitive/docs/BTCognitive_Master_PRD.md) (v1.0, 16 October 2026)
- Product Blueprint v2.0 (16 October 2026)
- Machine-Readable Experiment Register: [experiments/results/research_improvement/experiment_register.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/research_improvement/experiment_register.json)
- Challenger Evaluation Report: [experiments/results/research_improvement/candidate_a_qlike_eval_report.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/research_improvement/candidate_a_qlike_eval_report.json)
- Preregistered Evaluation Manifest: [experiments/results/research_improvement/preregistered_evaluation_manifest.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/research_improvement/preregistered_evaluation_manifest.json)
- Challenger Model Artifact: [experiments/results/research_improvement/har_qlike_v1.joblib](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/research_improvement/har_qlike_v1.joblib)

---

## 1. Executive Summary & Epistemic Verdicts

This Research-Driven Improvement Sprint was conducted using native Antigravity multi-agent orchestration across five specialist workstreams to resolve empirical contradictions in earlier validation reports, implement literature-grounded forecasting challengers, and upgrade the Research Terminal with transparent experiment tracking.

### Core Discoveries & Results:

1. **Resolution of the 92.36% vs 84.89% Coverage Contradiction:**
   - Forensic inspection of legacy scripts (`run_uncertainty_03_holdout_trial.py`, `stage10_shadow_scorecard_corrected.json`) reveals that the legacy 92.36% figure suffered from a **168-hour contemporaneous residual lookahead defect** (`res_all` included unobserved future holdout residuals in rolling exponential scale estimation).
   - Re-evaluating the frozen active baseline `HAR-RS-DOW-v1.0` under a **strictly causal online delayed-resolution protocol** (where holdout residuals are delayed by 168 hours and only resolved outcomes are used for conformal calibration) independently reproduces and confirms the true empirical holdout coverage of **84.89%** ($95\%$ Stationary Block Bootstrap CI: $[73.14\%, 93.14\%]$).
   - The 2026 dataset (2026-01-01 to 2026-09-01, 5,838 hourly bars) has been repeatedly exposed across Stage 10–12 and Phase 1–6 audits. It is a **Valid Retrospective Out-of-Sample Replay**, NOT an untouched prospective holdout.
2. **Candidate A: QLIKE-Coherent HAR Challenger (Puke & Schweikert, 2026):**
   - Implemented [HARQLIKEChallenger](file:///c:/Projects/BTCognitive/BTCognitive/models/challengers/har_qlike_challenger.py), directly optimizing sample QLIKE loss rather than OLS MSE on log-variance.
   - On the 5,671 resolved out-of-sample holdout bars, `HAR-QLIKE-v1.0` achieves an **8.77% raw reduction in sample QLIKE loss** (0.19598 vs baseline 0.21483) and reduces the mean Winkler score from 1.0444 to 0.9745.
   - However, when adjusting for 168-hour serial correlation using the Newey-West long-run variance kernel ($h=168$), the Diebold-Mariano paired loss test yields **$DM = +0.5132$ (HLN-corrected: $0.4980$, $p = 0.3039$)**.
   - Because $p \ge 0.05$, the challenger **does not achieve statistical significance**. In accordance with strict preregistered acceptance criteria, `HAR-RS-DOW-v1.0` is retained as the baseline, and `HAR-QLIKE-v1.0` is recorded in the Research Register as `OFFLINE_RESEARCH_ONLY`.
3. **Candidate B (Options IV) & Candidate C (Cross-Crypto SPCA) Data Audits:**
   - **Candidate B (Wang et al., 2026):** Historical options implied volatility (`iv7d.parquet`) is classified as an offline research benchmark and is not present in local raw datasets. Real-time options data requires external provider keys. The paper evaluated 1h, 6h, and 24h horizons, which cannot be casually extrapolated to 168h variance. In compliance with PRD rules, it is explicitly classified as `BLOCKED_EXTERNAL_DEPENDENCY` without fabricating mock data.
   - **Candidate C (Yi et al., 2022):** Cross-crypto OHLCV (ETH, SOL, etc.) is not present in local raw data. In compliance with PRD rules, it is preserved as an offline research hypothesis rather than inventing synthetic cross-market feeds.
4. **Research Terminal & Lab Enhancements:**
   - Added `/api/research/experiments` returning a machine-readable, typed experiment register.
   - Added `HAR-QLIKE-v1.0` to [models/authoritative_model_registry.py](file:///c:/Projects/BTCognitive/BTCognitive/models/authoritative_model_registry.py) as an `EXPERIMENTAL_CHALLENGER`.
   - Preserved strict non-execution: `trading_enabled = false`, `live_capital_authorized = false` across all routes. All 59 focused tests pass in 16.47s.

---

## 2. Literature Grounding & Academic Synthesis

| Research Reference | Scientific Contribution | Applicability & Impact on BTCognitive |
| :--- | :--- | :--- |
| **Puke & Schweikert (2026)**<br/>*Journal of Forecasting*, 45(4), 1714–1729.<br/>DOI: `10.1002/for.70114` | Proves that parameter estimation aligned with the evaluation loss function (QLIKE) reduces finite-sample forecast error for realized volatility. | Direct inspiration for Candidate A (`HAR-QLIKE-v1.0`). Demonstrates an 8.77% raw QLIKE loss reduction on BTC/USD, but highlights the necessity of serial-dependence adjustments for overlapping horizons. |
| **Wang, Rao & Zhuo (2026)**<br/>*Finance Research Letters*, 106013.<br/>Advance online publication / pre-proof | Investigates hourly Bitcoin options ATM implied volatility and term-structure slope for short-horizon (1h, 6h, 24h) risk forecasting. Reports 1.5–3.8% RMSE gains; direction remains unpredictable. | Motivates Candidate B. Verified as an advance online publication (listed ahead of print in ScienceDirect). Validates that direction is unforecastable from options, but confirms data dependency (Deribit feeds required). |
| **Yi, He & Zhang (2022)**<br/>*NAJEF*, 62, 101731.<br/>DOI: `10.1016/j.najef.2022.101731` | Explores out-of-sample Bitcoin realized volatility prediction using external crypto data via fold-level Scaled-PCA. | Motivates Candidate C. Requires fold-isolated PCA transformations. Highlighted data availability blocker: local datasets contain verified Coinbase BTC-USD only. |
| **Diebold & Mariano (1995)**<br/>*JBES*, 13(2), 253–263.<br/>Harvey, Leybourne & Newbold (1997) | Rigorous paired loss testing under serial correlation and non-normality with finite-sample HLN correction. | Mandated as the statistical hurdle for all model comparisons. Prevents raw sample error differences from being misdiagnosed as statistically significant alpha. |
| **Bailey & López de Prado (2014)**<br/>*JPM*, 40(5), 94–107.<br/>Bailey et al. (2015), *JCF* | Deflated Sharpe Ratio (DSR) and Probability of Backtest Overfitting (PBO). Controls for selection bias across multiple trials. | Governs experiment selection. All evaluated models (including failed challengers) are logged in the experiment register to prevent file-drawer bias. |
| **Gneiting & Raftery (2007)**<br/>*JASA*, 102(477), 359–378. | Strictly proper scoring rules for probabilistic forecasts (QLIKE, Winkler score, Pinball loss). | Ensures evaluation metrics are loss-coherent. Variance is scored via QLIKE; prediction intervals are scored via Winkler score. |

---

## 3. Discrepancy Resolution & Epistemic Audit

### 3.1 The 92.36% vs 84.89% Coverage Discrepancy

Earlier reports contained a glaring contradiction: `stage10_shadow_scorecard_corrected.json` and `run_final_accuracy_gate.py` cited **92.36%** coverage for `HAR-RS-DOW-v1.0`, while `phase_1_scientific_integrity_audit.md` and `test_stage12_causal_validation.py` established **84.89%**.

```mermaid
flowchart TD
    subgraph LegacyLeaked["Legacy Defective Implementation (92.36%)"]
        L1["Concatenate res_train + res_holdout"]
        L2["Compute rolling_std_all on full series"]
        L3["Leak: Step t uses res_all[t] containing future 168h variance!"]
        L4["Result: Artificially inflated coverage of 92.36%"]
        L1 --> L2 --> L3 --> L4
    end

    subgraph CausalDelayed["Strictly Causal Delayed Resolution (84.89%)"]
        C1["Forecast origin i emitted before y_i observed"]
        C2["Residual pool strictly limited to origins <= i - 168"]
        C3["Rolling scale computed strictly on resolved outcomes"]
        C4["Result: True empirical out-of-sample coverage of 84.89%"]
        C1 --> C2 --> C3 --> C4
    end
```

#### Detailed Forensic Analysis:
1. **Source of Defect:** In `research/run_uncertainty_03_holdout_trial.py`, `res_all` concatenated training residuals with all holdout residuals. At holdout step $i$, `rolling_std_all[N_train + i]` was computed using `res_all[N_train + i]`, which directly depended on $y_i = \text{rv7d\_var\_ann}_i$. Because 7-day realized variance requires 168 hours to mature, this leaked future unresolved price dispersion into the contemporaneous interval width.
2. **Causal Correction:** In `research/stage12_causal_conformal_engine.py`, holdout residuals are delayed by exactly 168 hours. At forecast origin $i$, the scaling standard deviation and conformity pool draw exclusively from origins $k \le i - 168$.
3. **Empirical Reproduction:**
   - Legacy Non-Causal Leaked Coverage: **92.36%** ($N=5,671$).
   - Strictly Causal Delayed-Resolution Coverage: **84.89%** ($95\%$ CI: $[73.14\%, 93.14\%]$).
4. **Reconciliation Action:** All model cards, API responses, and reports are reconciled to cite the true causal figure of **84.89%**. The 92.36% figure is permanently marked as superseded by the causal delayed-resolution audit.

### 3.2 Prior Exposure of the 2026 Dataset
The 2026 holdout (2026-01-01 to 2026-09-01, 5,838 hourly bars) was utilized across:
- Stage 10 Shadow Validation
- Stage 11 Forward Validation
- Stage 12 Causal Validation
- Phase 1 Scientific Integrity Audit
- Master Delivery Orchestration

Therefore, this sample is **NOT an untouched, blind holdout**. It represents an authentic, point-in-time retrospective out-of-sample replay. To claim genuine prospective validation, clean evidence blocks must be accumulated forward in calendar time. Following the quarantine of 71 synthetic mock records, clean prospective blocks currently stand at **0**.

---

## 4. Forecasting Challenger Evaluation: Candidate A (HAR-QLIKE-v1.0)

### 4.1 Model Specifications
- **Reference Baseline:** `HAR-RS-DOW-v1.0` (frozen OLS log-variance model in `experiments/results/freeze/har_rs_dow_v1.joblib`, SHA256: `750b5d15...`).
- **Challenger:** `HAR-QLIKE-v1.0` (direct QLIKE loss minimization with L2 shrinkage $\lambda = 0.10$).
- **Sample Window:** 
  - Training: 2022-01-31 to 2025-12-24 (34,175 bars).
  - Out-of-Sample Holdout: 2026-01-01 to 2026-09-01 (5,671 resolved blocks).
- **Features:** Identical 10 point-in-time features (`log_rv_down_1d`, `log_rv_up_1d`, `log_rv7d_lag`, `log_rv30d`, `dow_1..dow_6`).

### 4.2 Out-of-Sample Comparison Results

| Evaluation Metric | Baseline (`HAR-RS-DOW-v1.0`) | Challenger (`HAR-QLIKE-v1.0`) | Absolute $\Delta$ | Relative Improvement |
| :--- | :--- | :--- | :--- | :--- |
| **QLIKE Loss (Primary)** | **0.21483** | **0.19598** | **-0.01885** | **+8.77%** |
| **RMSE** | 0.14045 | 0.14032 | -0.00013 | +0.09% |
| **MAE** | 0.08812 | 0.08794 | -0.00018 | +0.20% |
| **Strictly Causal Conformal Coverage** | **84.89%** | **84.22%** | -0.67% | Maintained |
| **Mean Interval Width** | 0.4389 | 0.4388 | -0.0001 | Identical sharpness |
| **Mean Winkler Interval Score** | 1.0444 | 0.9745 | -0.0699 | **+6.70%** |

### 4.3 Diebold-Mariano Paired Loss Test (Serial Dependence Adjusted)
Because the forecast horizon is $h = 168$ hours, consecutive forecast errors exhibit strong autocorrelation. The Diebold-Mariano test was computed using a Bartlett kernel with lag bandwidth $h = 168$:

$$\hat{V}(\bar{d}) = \frac{1}{T} \left( \hat{\gamma}_0 + 2 \sum_{k=1}^{167} \left(1 - \frac{k}{168}\right) \hat{\gamma}_k \right)$$

- **Sample Mean Loss Differential ($\bar{d}$):** $+0.018846$
- **Newey-West Long-Run Standard Error:** $0.036722$
- **Diebold-Mariano Statistic ($DM$):** **$+0.5132$**
- **Harvey-Leybourne-Newbold Statistic ($HLN$):** **$+0.4980$**
- **One-Sided p-value ($H_1: \text{Challenger} < \text{Baseline}$):** **$0.30391$**
- **Statistically Significant at $\alpha = 0.05$:** **False**

### 4.4 Gate Decision & Scientific Rationale
**VERDICT: REJECT FOR PRODUCTION PROMOTION; RETAIN IN RESEARCH REGISTER.**  
While loss-coherent parameter estimation achieves an 8.77% raw reduction in sample mean QLIKE loss and improves the Winkler interval score, the overlapping 168-hour horizon inflates forecast variance such that the performance difference is not statistically distinguishable from chance ($p = 0.304$). Under strict preregistered governance rules, a model must achieve $p < 0.05$ under a dependence-corrected paired test to replace a frozen production baseline. `HAR-RS-DOW-v1.0` remains the active production model.

---

## 5. Candidate B & C Dependency and Feasibility Audit

### 5.1 Candidate B: Bitcoin Options-Implied Volatility (Wang, Rao & Zhuo, 2026)
- **Status:** **BLOCKED_EXTERNAL_DATA_DEPENDENCY**.
- **Audit Findings:**
  1. The paper evaluates ATM implied volatility and term-structure slope for short-term risk forecasting (1h, 6h, 24h). The paper explicitly reports that directional return predictability was not robustly improved.
  2. In BTCognitive, historical options data (`iv7d.parquet`) is categorized as an offline research benchmark and is missing from local raw datasets.
  3. Real-time options data requires external provider connections (Deribit).
  4. Extrapolating a 1h/6h/24h options study to the active 168h realized variance baseline without verified data would violate PRD Data Principle 1.
  5. Action: Documented as an unconfigured dependency. No synthetic data was generated.

### 5.2 Candidate C: Cross-Crypto Realized Volatility (Yi, He & Zhang, 2022)
- **Status:** **BLOCKED_EXTERNAL_DATA_DEPENDENCY**.
- **Audit Findings:**
  1. The method requires point-in-time aligned cross-asset OHLCV (ETH, BNB, SOL) with fold-level Scaled-PCA fitting.
  2. Local datasets contain verified Coinbase BTC-USD only (`data/raw/ohlcv.parquet`).
  3. Expanding the feature set with unverified or unaligned third-party feeds introduces leakage risk and maintenance overhead.
  4. Action: Preserved in the research backlog until multi-asset historical ingestion pipelines are formally verified.

---

## 6. Master Experiment Register Summary

The machine-readable register is persisted at [experiments/results/research_improvement/experiment_register.json](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/research_improvement/experiment_register.json):

```json
{
  "register_version": "BTC-EXP-REG-2026-v1.0",
  "total_experiments": 3,
  "experiments": [
    {
      "experiment_id": "EXP-2026-01-QLIKE-HAR",
      "candidate_name": "HAR-QLIKE-v1.0",
      "research_source": "Puke & Schweikert (2026)",
      "target": "rv7d_var_ann (168h)",
      "baseline_qlike": 0.21483,
      "challenger_qlike": 0.19598,
      "raw_qlike_delta": -0.01885,
      "diebold_mariano_stat": 0.5132,
      "p_value": 0.30391,
      "decision": "REJECT_FOR_PRODUCTION_RETAIN_IN_RESEARCH"
    },
    {
      "experiment_id": "EXP-2026-02-OPTIONS-IV",
      "candidate_name": "HAR-RS-IV-ATM-SLOPE",
      "research_source": "Wang, Rao & Zhuo (2026)",
      "target": "rv7d_var_ann / rv24h",
      "decision": "BLOCKED_EXTERNAL_DEPENDENCY"
    },
    {
      "experiment_id": "EXP-2026-03-CROSS-CRYPTO-SPCA",
      "candidate_name": "HAR-SPCA-CROSS-VOL",
      "research_source": "Yi, He & Zhang (2022)",
      "target": "rv7d_var_ann (168h)",
      "decision": "BLOCKED_EXTERNAL_DEPENDENCY"
    }
  ]
}
```

---

## 7. Four Separate Release Decisions

```mermaid
graph TD
    subgraph Decisions["BTCognitive Four Separate Release Decisions"]
        D1["1. Software Completion<br/><b>PASS</b><br/>All 7 areas, experiments API, PIT engine working."]
        D2["2. Data & Evidence Readiness<br/><b>CONDITIONAL / REPRESENTATIVE</b><br/>Historical replay verified; prospective clean blocks = 0."]
        D3["3. Predictive Model Validation<br/><b>BASELINE RETAINED / CHALLENGER RESEARCH-ONLY</b><br/>HAR-RS-DOW verified; QLIKE challenger statistically equal; direction rejected."]
        D4["4. Operational Authorization<br/><b>BLOCKED FROM INFERENCE / TRADING DISABLED</b><br/>Fail-closed status active; zero live execution."]
    end
```

1. **Software Completion:** **PASS**. All mandatory PRD capabilities, FastAPI endpoints, the 7 Terminal views, the new `/api/research/experiments` endpoint, point-in-time invariant features, and safety gates are implemented and pass end to end (59 focused tests pass).
2. **Data & Evidence Readiness:** **CONDITIONAL / REPRESENTATIVE READINESS**. Historical out-of-sample datasets are verified point-in-time. However, following the quarantine of 71 synthetic mock records, clean prospective evidence blocks currently stand at **0**.
3. **Predictive Model Validation:** **BASELINE RETAINED / CHALLENGER RESEARCH-ONLY**. `HAR-RS-DOW-v1.0` remains the verified baseline for 7-day realized variance. The `HAR-QLIKE-v1.0` challenger shows an 8.77% raw loss reduction but does not achieve statistical significance ($p = 0.304$). Directional models remain at ~52% with negative net expectancy.
4. **Operational Authorization:** **BLOCKED FROM INFERENCE / TRADING DISABLED**. `HAR-RS-DOW-v1.0` remains set to `BLOCKED_AUDIT_FAILURE` pending prospective clean blocks. `HAR-QLIKE-v1.0` is classified as `OFFLINE_RESEARCH_ONLY`. Live broker order execution and real capital trading are permanently disabled.

---

## 8. Highest-Value Next Research Question

**Research Question:**  
*Does a multi-horizon QLIKE-loss formulation at shorter, non-overlapping or weakly-overlapping horizons (e.g., 24-hour realized variance, where serial dependence is reduced by 7x compared to 168 hours) enable the QLIKE-coherent estimator to achieve statistical significance ($p < 0.05$) under the Diebold-Mariano test?*

**Rationale:**  
At the 168-hour horizon, the effective sample size is heavily constrained by overlapping labels ($N_{\text{eff}} \approx 5,671 / 168 \approx 34$ independent blocks), requiring massive effect sizes to cross the $p < 0.05$ threshold. At a 24-hour horizon, the effective sample size increases to $\sim 236$ independent blocks, which significantly increases statistical power to resolve whether loss-coherent parameter estimation provides genuine, exploitable alpha in cryptocurrency volatility modeling.
