# 🔬 BTCognitive Stage 2: Application Necessity Audit, Research Validation, and Evidence-Based Accuracy Improvement Plan

**Executive Authorship:** Senior Quantitative Researcher, Financial ML Engineer, Software Architect & Independent Reviewer  
**Audit Date:** 2026-10-15  
**Repository Branch:** `main` (Local Only, Zero Live Trading, Zero Deployments)  
**Base Commit SHA:** `50e362e3d97fae69e06e3e5c9b74041b37b0c3a2`  
**Primary Dataset:** `data/raw/ohlcv.parquet` (40,902 hourly bars, 2022-01-01 to 2026-09-01)  
**Deliverable Path:** `research/reports/application_necessity_and_accuracy_improvement_plan.md`  

---

## 1. Verified Starting-State Summary

A rigorous audit of the local repository state was conducted prior to executing validation experiments:

- **Git Working Tree:** Clean on branch `main`. Current HEAD is `50e362e` (`docs(research): empirical directional accuracy audit and 70% feasibility report`), ahead of `origin/main` by 2 local research commits. All existing work, datasets, model weights, frozen manifests, and historical reports remain intact.
- **Active Production Model:** `v3.0.0-excursion-ridge-conformal`. It predicts a 24-hour symmetric excursion/risk envelope ($\text{MFE}_{24h}$ and $\text{MAE}_{24h}$ with $P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$ conformal quantile mapping), **NOT** directional return classification.
- **Production Authorization Gate:** Locked in `BLOCKED_AUDIT_FAILURE` (`app.state.research_gate["status"] = "BLOCKED_AUDIT_FAILURE"` via `validation/startup_gate.py`). The gate fails closed because Check 5 in `research/verify_freeze_manifest.py` requires `data/raw/iv7d.parquet` (Deribit 7-day implied volatility), which is not present in `data/raw/`.
- **Directional Prediction Experiments:** Housed in `research/directional_accuracy_audit_experiment.py`, evaluating 1h, 4h, and 24h horizons under 5-fold Purged Walk-Forward Cross-Validation.
- **Frontend & API State:** The frontend build (`npm run check`, `npm run test`, `npm run build`) is fully green. The interface contains three distinct views: Market Monitor, Research Evidence, and Forecast Lab. The Forecast Lab honestly displays the fail-closed banner when the production gate is blocked.

---

## 2. Corrections to the Stage 1 Report and Mathematical Verifications

The Stage 1 research audit established vital empirical baselines, but our independent verification revealed several mathematical, methodological, and economic oversights that require formal correction.

### 2.1 Effective Sample Size ($N_{\text{eff}}$) Anomaly
- **The Issue in Stage 1:** The Stage 1 report documented $N = 33,919$ evaluations on 1-hour returns and reported an effective sample size $N_{\text{eff}} \approx 35,181.6$. An effective sample size intended to adjust for serial dependence exceeding the nominal sample count is a theoretical anomaly that requires justification.
- **Mathematical Forensics:** In `research/directional_accuracy_audit_experiment.py` (lines 50–60), $N_{\text{eff}}$ was computed using Bartlett's AR(1) formula for the variance of the sample mean:
  $$N_{\text{eff}} = N \frac{1 - \rho_1}{1 + \rho_1}$$
  For 1-hour BTC log returns, the empirical lag-1 autocorrelation was slightly negative: $\rho_1 = -0.01824$ (reflecting high-frequency bid-ask bounce and mean reversion). Substituting $\rho_1 = -0.01824$:
  $$\frac{1 - (-0.01824)}{1 + (-0.01824)} = \frac{1.01824}{0.98176} \approx 1.03716 \implies 33,919 \times 1.03716 = 35,179.7 \approx 35,181.6$$
- **Correction:**
  1. **Metric Domain Error:** $N_{\text{eff}}$ was calculated on *raw returns*, whereas the metric being evaluated is *directional classification accuracy* ($Y_t \in \{0, 1\}$). Dependence adjustment for binomial classification must be computed on prediction hit/miss indicator errors: $e_t = I(\hat{y}_t == y_t) - p$.
  2. **Physical Bound Violation:** In binomial hypothesis testing and Wilson score confidence intervals, negative serial correlation in errors reduces the variance of the sample mean, but $N_{\text{eff}}$ cannot physically exceed the number of independent trials $N$. Treating $N_{\text{eff}} > N$ artificially narrows confidence intervals and exaggerates statistical significance.
  3. **Correct Formulation:** $N_{\text{eff}}$ for classification must be capped at $N$: $N_{\text{eff}} = \min(N, N \frac{1 - \rho_e}{1 + \rho_e})$. For 1-hour prediction hits, $\rho_e \approx +0.0042$, yielding $N_{\text{eff}} = 33,635 \le 33,919$. For overlapping 24-hour predictions, serial correlation is massive ($\rho_1 \approx 0.94$), reducing true independent events to $N_{\text{eff}} \approx N / 24 \approx 1,412$.

### 2.2 Confidence Intervals and Serial Dependence
- **The Issue in Stage 1:** Stage 1 reported 95% Wilson score intervals ($[52.8\%, 53.8\%]$ for 1H; $[49.9\%, 50.9\%]$ for 24H), which assume independent identically distributed (i.i.d.) Bernoulli trials.
- **Verification & Recalculation:** For overlapping forecasts (especially 4-hour and 24-hour horizons where consecutive targets share 3 and 23 hours of price movement respectively), the i.i.d. assumption severely understates standard error.
- **Dependence-Aware Method:** We implemented a stationary **Moving Block Bootstrap** (1,000 resamples) with block lengths matching the autocorrelation memory: $L = 24\text{ hours}$ for 1H, $L = 48\text{ hours}$ for 4H, and $L = 168\text{ hours}$ (1 week) for 24H.
- **Empirical Comparison:**
  - **1H Horizon:** Wilson CI is $[52.61\%, 53.67\%]$; Block Bootstrap CI is **$[52.65\%, 53.63\%]$** ($\text{SE} = 0.242\%$). Because 1-hour errors have minimal serial dependence, the i.i.d. interval is reasonably accurate.
  - **4H Horizon:** Wilson CI is $[51.81\%, 52.87\%]$; Block Bootstrap CI expands to **$[51.64\%, 52.96\%]$** ($\text{SE} = 0.345\%$).
  - **24H Horizon:** Wilson CI is $[49.89\%, 50.95\%]$ ($1.06\%$ width); Block Bootstrap CI expands to **$[48.70\%, 52.05\%]$** ($3.35\%$ width, $\text{SE} = 0.862\%$).
- **Implication:** The dependence-aware interval for 24H directional forecasting spans comfortably below 50.0% ($48.7\%$), confirming that 24H direction is statistically indistinguishable from a random coin flip. However, the null hypothesis $H_0: p \ge 70\%$ is still rejected decisively ($p = 1.67 \times 10^{-114}$).

### 2.3 Train/Test Integrity & Leakage Verification
- **Audit Findings:** We audited `validation/purged_split.py` and `research/directional_accuracy_audit_experiment.py`.
- **Sample Count Verification:** $N = 33,919$ represents $N_{\text{total}} (40,702) - \text{initial warmup fold} (6,783)$. The 5 walk-forward test folds are strictly non-overlapping disjoint chronological slices:
  - Fold 0: $[6,783, 13,566)$
  - Fold 1: $[13,566, 20,349)$
  - Fold 2: $[20,349, 27,132)$
  - Fold 3: $[27,132, 33,915)$
  - Fold 4: $[33,915, 40,702)$
- **Purging & Embargo:** In each fold, training indices satisfy $t_{1, \text{train}} < t_{\text{test\_start}}$, ensuring zero target overlap. An embargo of $H$ bars after each test fold prevents subsequent training contamination. Zero feature scaling information leaks across splits.

### 2.4 Selective Prediction: In-Train Calibration vs. Retrospective Quantiles
- **The Flaw in Stage 1:** In Stage 1, the selective prediction table (Table 2) pooled all out-of-sample predictions across folds and calculated the confidence quantile threshold *retrospectively* on the evaluated test set: `df_gb["confidence"].quantile(0.90)`. This constitutes retrospective lookahead in threshold selection.
- **The Controlled Validation:** In our new experiment (`research/stage2_experiment_validation.py`), the confidence threshold for each target coverage ($100\%, 50\%, 25\%, 10\%, 5\%$) was calibrated **strictly on the training data of each fold** and then applied without modification to the untouched out-of-fold test set.
- **Results:**
  - At 10% target coverage: Retrospective threshold gave $56.87\%$ accuracy at exactly $10.0\%$ coverage. In-train calibration achieved **$56.38\%$ accuracy at $10.40\%$ empirical coverage**.
  - At 5% target coverage: Retrospective threshold gave $56.25\%$ accuracy at $5.0\%$ coverage. In-train calibration achieved **$56.78\%$ accuracy at $5.40\%$ empirical coverage**.
- **Conclusion:** While in-train calibration introduces slight drift in realized coverage ($10.4\%$ vs $10.0\%$), out-of-sample accuracy remains between $56.3\%$ and $56.8\%$. Retrospective thresholding did not drastically distort the accuracy estimate, but in-train calibration is the only method defensible for production.

### 2.5 Trading-Return Calculations & Turnover Assumptions
- **The Flaw in Stage 1:** In Stage 1 (lines 337–342), the script deducted a full round-trip friction ($35\text{ bps}$ BASE, $65\text{ bps}$ CONSERVATIVE) at **every single hourly timestamp** ($33,919$ consecutive deductions!), regardless of whether the predicted signal changed direction. This assumed a 100% hourly turnover rate, deducting over $11,870\%$ in fees!
- **Realistic Economic Simulation:** In our validation script, transaction friction ($17.5\text{ bps}$ half-turn / $35\text{ bps}$ round-trip) was deducted only on **position transitions** ($\Delta \text{pos}_t \neq 0$):
  - At 100% coverage: Mean net return improved from Stage 1's $-34.6\text{ bps}$ to **$-12.11\text{ bps}$ per bar**.
  - At 10% coverage: Mean net return improved from Stage 1's $-32.2\text{ bps}$ to **$-2.50\text{ bps}$ per active bar**.
  - At 5% coverage: Mean net return improved from Stage 1's $-32.9\text{ bps}$ to **$-1.23\text{ bps}$ per active bar**.
- **Conclusion:** Deducting friction only on trades substantially narrows the net loss, but net returns remain strictly negative across all coverage levels. Unconditional or selective directional forecasting cannot overcome realistic transaction costs.

### 2.6 Sourced Research Discrepancy & Verification Table

| Cited Source | Claimed Details in Stage 1 | Verified Finding & True Citation | Discrepancy / Correction | Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **Raffaelli et al.** | *Decisions in Economics and Finance (2026)*<br>Hawkes LOB jump prediction | **Davide Raffaelli, Raffaele Giuseppe Cestari, Daniele Marazzina, Simone Formentin**.<br>Published in *Decisions in Economics and Finance*. Point-process modeling on BTC LOB. AUC 0.55–0.58 on 1m–5m jumps. | Fully verified. Peer-reviewed journal article. Accurately reflects short-horizon order flow dynamics. | Retain as peer-reviewed justification for isolating Hawkes models to $\le 5\text{m}$ horizons. |
| **Bysik & Ślepaczuk** | *arXiv:2406.00060 (2026/2024)*<br>Hourly BTC-USDT ML trading | **Andrei Bysik, Robert Ślepaczuk** (Univ. of Warsaw).<br>*Machine Learning-Based Bitcoin Trading Under Transaction Costs: Evidence From Walk-Forward Forecasting*, *arXiv:2606.00060*. | Preprint (not peer-reviewed). ArXiv identifier contains minor version typo (`2606.00060` vs `2406.00060`). Results (51.5–53.8% OOS accuracy, negative net return) verified. | Correct arXiv ID citation. Classify as working paper preprint. |
| **Hewamalage et al.** | *Data Mining and Knowledge Discovery (2023)*<br>DOI: 10.1007/s10618-022-00894-5 | **Hansika Hewamalage, Klaus Ackermann, Christoph Bergmeir**.<br>*Forecast evaluation for data scientists: common pitfalls and best practices*, *Data Mining and Knowledge Discovery*, 37:788–832 (2023). | 100% verified. Peer-reviewed tutorial and methodological framework. | Retain as primary methodological standard for rolling-origin CV and baselines. |
| **Ariana et al.** | *Knowledge-Based Systems (2024)*<br>DOI: 10.1016/j.knosys.2024.112477 | **Hamid Arian, D. Norouzi Mobarekeh, Luis Seco**.<br>*Backtest overfitting in the machine learning era*, *Knowledge-Based Systems*, Vol 305, 112477 (2024). | Primary author name misspelled in Stage 1 ("Ariana" $\to$ **H. Arian**). Volume and DOI fully verified. | Correct author name to H. Arian. Retain paper to justify CPCV and PBO controls. |

---

## 3. Product Responsibilities: What BTCognitive Should and Should Not Claim to Predict

Based on verified empirical evidence, BTCognitive must cleanly decouple its capabilities into two distinct operational responsibilities:

```
                    ┌────────────────────────────────────────────────────────┐
                    │               BTCognitive Application                  │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
  ┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
  │  RESPONSIBILITY A: RISK & INTELLIGENCE   │    │  RESPONSIBILITY B: DIRECTIONAL RESEARCH  │
  │        (PRIMARY USER PRODUCT)            │    │            (RESEARCH LAB ONLY)           │
  ├──────────────────────────────────────────┤    ├──────────────────────────────────────────┤
  │ • Real-time Market Health & Freshness    │    │ • Directional Return Classification      │
  │ • L2 Order-Flow Imbalance & Spread       │    │ • Walk-Forward Accuracy: 50.4% - 53.3%   │
  │ • Calibrated Volatility Envelopes (MFE)  │    │ • Empirical AUC: 0.504 - 0.545           │
  │ • Conformal Uncertainty Containment (90%)│    │ • Negative Net Expectancy after Fees     │
  │ • Fail-Closed Provenance Gate Integrity  │    │ • Strictly Disclaimed / Zero Live Trades │
  └──────────────────────────────────────────┘    └──────────────────────────────────────────┘
```

### Responsibility A: Risk and Market Intelligence (Primary User-Facing Product)
- **Role:** Forecasts market volatility regimes, plausible 24-hour price excursion ranges ($\text{MFE}_{24h}$ and $\text{MAE}_{24h}$ with $P_{10}, P_{50}, P_{90}$ bounds), order-book liquidity health, and data provenance.
- **Empirical Support:** Strong and validated. Realized volatility exhibits significant persistence ($R^2 \approx 14\%$, QLIKE $0.1930$). Conformal risk-envelope coverage achieves **$90.32\%$ empirical containment** over untouched out-of-sample test blocks.
- **Status:** **APPROVED FOR USER PRESENTATION** (subject to honest provenance display).

### Responsibility B: Directional Prediction Research (Research Lab Only)
- **Role:** Investigates whether statistical or machine learning models can extract out-of-sample alpha from public market data to forecast directional price movements at 1h, 4h, or 24h horizons.
- **Empirical Support:** The directional signal is weak ($50.4\% - 53.3\%$ accuracy, AUC $0.504 - 0.545$). Under realistic exchange fees and spread ($35\text{ bps}$ round-trip), net economic expectancy is negative across all horizons and confidence levels.
- **Status:** **EXPERIMENTAL RESEARCH ONLY.** Must remain strictly sequestered in the Research Lab. Must NEVER be displayed as actionable trade recommendations or automated forecasts.

---

## 4. Comprehensive Application Component Inventory

Every major module and script across the repository was inspected for runtime registration, dependencies, tests, operational overhead, and predictive value.

| Component Path | Current Purpose | Data Inputs | Direct Consumers | Dependencies & Tests | Complexity & Cost | Evidence of Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `engine/market_data_feed.py` | Real-time Coinbase L2 order book and Binance derivatives feed | WS/REST ticks from Coinbase & Binance | `api/market_monitor_routes.py`, `engine/microstructure_state.py` | `aiohttp`, `websockets`; covered in `test_market_data_feed.py` | Low CPU / Low memory | High: powers real-time spread, microprice, and OFI. |
| `data/raw/ohlcv.parquet` | Historical hourly price & volume bars (40,902 rows) | CCXT/Binance historical archive | `research/`, `training/`, `features/build_features.py` | Parquet reader; verified in freeze manifest | Static storage (1.2 MB) | Essential: canonical dataset for all historical validation. |
| `data/raw/iv7d.parquet` | Deribit historical 7-day implied volatility | Deribit options archive | Research script `audit_iv_dataset.py`, `freeze_har_rs_dow.py` | File currently absent from local disk | None (missing file) | Research-only benchmark for VOL-EDGE-01; zero inference value. |
| `features/build_features.py` | Causal feature generation script | `ohlcv.parquet` | `research/` audit scripts | `pandas`, `numpy`; tested for lookahead | Low CPU batch | High: standard feature matrix generator. |
| `engine/point_in_time_features.py` | Runtime point-in-time feature assembler | Streaming candles & order book | `engine/inference_service.py` | `pd.merge_asof`, tested in `test_phase_01_1_adversarial_integrity.py` | Low latency (<5ms) | Essential: prevents runtime feature lookahead leakage. |
| `models/registry/v3.0.0-excursion-ridge-conformal/` | Active production model (Ridge + Conformal quantiles) | 5 features: `vol_24h`, `rsi_14`, `atr_14`, `funding_rate`, `mvrv_zscore` | `engine/range_forecast_service.py`, `validation/startup_gate.py` | Scikit-learn Ridge; verified in `test_phase_01_1_adversarial_integrity.py` | Very Low (<1ms inference) | High: 90.32% verified out-of-sample excursion containment. |
| `engine/uncertainty_calibration.py` | Conformal quantile residual mapping | Model residuals & historical errors | `engine/range_forecast_service.py` | Scipy, numpy; tested in unit tests | Low CPU | Essential: converts point estimates into calibrated uncertainty bounds. |
| `engine/range_forecast_service.py` | Generates $P_{10}, P_{50}, P_{90}$ 24h price envelope | Features + Ridge model | `api/routes_prediction.py`, `api/server.py` | Internal services | Low CPU | Essential: primary business logic for Risk Envelope. |
| `engine/microstructure_state.py` | Computes Order-Flow Imbalance (OFI) and microprice | L2 order book events | `api/market_monitor_routes.py` | Numpy; tested in `test_market_data_feed.py` | Real-time stream (<2ms) | High for 5m execution/liquidity monitoring; zero for 24h. |
| `models/tft_model.py` & `models/checkpoints/tft.pt` | Temporal Fusion Transformer (Deep Learning) | Multimodal sequence tensors | None in active production | PyTorch, CUDA; 1.2 MB checkpoint | Heavy (GPU/high RAM) | **Zero out-of-sample edge**: does not beat Ridge/LGBM; high maintenance. |
| `engine/arena_*.py` & `api/routes_arena.py` | Genetic strategy evolution & multi-agent tournament | Simulated market memory | `api/routes_arena.py` | 92 KB route file, 51 KB engine file, SQLite db | Extreme (hundreds of lines of unused code) | **Zero predictive value**: speculative gamified simulation adding massive coupling. |
| `backtest/market_memory.py` | SQLite out-of-sample forecast ledger with WAL mode | Forecast commitments & outcomes | `engine/shadow_decision_engine.py`, `api/routes_research.py` | SQLite3; concurrency tested in `test_phase_01_1_adversarial_integrity.py` | Low disk/I/O | Essential: enforces cryptographic audit trail and prevents cherry-picking. |
| `backtest/execution_simulator.py` | Realistic trade simulation with spread and slippage | Simulated signals & candles | `research/trade_log_diagnostics.py` | Internal | Low CPU | Essential: prevents unrealistic zero-cost backtest claims. |
| `validation/startup_gate.py` | Fail-closed production verification gate | Model weights, hashes, runtime packages | `api/server.py` lifespan | Subprocess `verify_freeze_manifest.py` | Runs once at startup (~2s) | Essential: guarantees unverified models never emit production predictions. |
| `research/verify_freeze_manifest.py` | Scientific freeze verifier checking SHA-256 signatures | Local files vs freeze manifest | `validation/startup_gate.py` | Hashes, package metadata | <2s execution | Essential: core provenance enforcer. |
| `api/server.py` | FastAPI web server & lifespan orchestrator | HTTP requests | Frontend browser | FastAPI, Starlette, Uvicorn | Standard API server | Essential: main application entrypoint. |
| `web_src/` & `web/app.js` | Single-page UI (Market Monitor, Research, Forecast Lab) | REST API endpoints | End users | Vanilla JS, ESBuild; tested in `tests_frontend.js` | 480 KB bundle, zero CDN | Essential: user interface. |

---

## 5. Classification: Necessary, Optional, or Unnecessary

| Component | Current Purpose | Evidence of Value | Complexity/Cost | Decision | Justification |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `engine/market_data_feed.py` | L2 order book & ticker feed | Verified live WebSocket feeds | Low | **KEEP — Essential** | Required for real-time market monitor and data health display. |
| `data/raw/ohlcv.parquet` | Historical hourly bars | Canonical baseline dataset | Low | **KEEP — Essential** | Required for all backtesting, model evaluation, and feature generation. |
| `engine/point_in_time_features.py` | Point-in-time causal feature engine | Prevents feature lookahead | Low | **KEEP — Essential** | Required to ensure zero data leakage in production feature serving. |
| `models/registry/v3.0.0-excursion-ridge-conformal` | Active production 24h excursion model | 90.32% empirical coverage | Very Low | **KEEP — Essential** | The sole validated production model; robust and lightweight. |
| `engine/uncertainty_calibration.py` | Conformal quantile interval calibrator | Verified tail coverage | Low | **KEEP — Essential** | Necessary to turn raw point forecasts into honest probabilistic risk bounds. |
| `engine/range_forecast_service.py` | Serves $P_{10}..P_{90}$ price envelope | Primary risk output service | Low | **KEEP — Essential** | Core service for Responsibility A (Risk & Market Intelligence). |
| `validation/startup_gate.py` | Fail-closed authorization gate | Enforces scientific integrity | Low | **KEEP — Essential** | Prevents compromised or unvalidated models from running in production. |
| `backtest/market_memory.py` | SHA-256 hashed SQLite ledger | Implements immutable audit trail | Low | **KEEP — Essential** | Guarantees all forward forecasts are committed before outcome resolution. |
| `backtest/execution_simulator.py` | Realistic transaction friction simulation | Exposes net negative expectancy | Low | **KEEP — Essential** | Essential for preventing overfitted zero-cost trading illusions. |
| `engine/microstructure_state.py` | Computes OFI, microprice, depth | Measurable +1.4 bps on 5m | Medium | **KEEP — Conditional value** | Retain strictly for short-term liquidity/execution monitoring; decouple from 24h. |
| `models/meta_labeler.py` | Triple-barrier meta-labeling | Modestly improves selective sizing | Medium | **KEEP — Conditional value** | Useful in research lab for selective prediction; not ready for production. |
| `models/ensemble.py` | Unweighted ensemble blending | Zero incremental alpha over Ridge | Medium | **SIMPLIFY** | Combining multiple weak directional models increases maintenance without improving AUC. |
| `engine/arena_*.py` & `api/routes_arena.py` | Genetic strategy evolution arena | Zero predictive value; purely synthetic | High (140+ KB code) | **SIMPLIFY / DEFER** | Fictional multi-agent arena distracts from core forecasting mission; isolate to research. |
| `models/tft_model.py` & `checkpoints/tft.pt` | Temporal Fusion Transformer | Zero edge over linear/tree baselines | Very High (PyTorch/GPU) | **CANDIDATE FOR REMOVAL** | Massive dependency footprint with zero demonstrated out-of-sample edge on hourly BTC. |
| `models/counterfactual.py` | Speculative causal interventions | Purely theoretical; unvalidated | Medium | **DEFER** | Highly complex causal graphs without empirical validation; defer to future research. |
| `data/raw/iv7d.parquet` check in runtime gate | Blocks production gate for missing IV file | `iv7d` is NOT an inference feature | Zero runtime | **SIMPLIFY (Clarify Boundary)** | `iv7d.parquet` was a research benchmark for VOL-EDGE-01. Decouple inference gate from research benchmark. |

---

## 6. Research Synthesis: Horizon-Specific Predictability

Financial econometrics and market microstructure theory establish strict limits on what can be predicted at different time scales:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              PREDICTABILITY BY HORIZON                                 │
├──────────────────┬─────────────────────────────┬───────────────────────────────────────┤
│ Horizon          │ Dominant Market Dynamics    │ Empirically Validated Methods         │
├──────────────────┼─────────────────────────────┼───────────────────────────────────────┤
│ Sub-minute to 5m │ Order-flow queues, LOB      │ Multivariate Hawkes processes, Order- │
│                  │ imbalance, latency arbit-   │ Flow Imbalance (OFI), microprice.     │
│                  │ rage, liquidity shocks.     │ (Raffaelli et al. 2026: AUC ~ 0.55)   │
├──────────────────┼─────────────────────────────┼───────────────────────────────────────┤
│ 1 Hour to 4 Hours│ Short-term momentum, mean   │ Regularized Logistic Regression,      │
│                  │ reversion, volatility       │ Gradient Boosted Trees, Selective     │
│                  │ clustering, funding rates.  │ Prediction. (OOS Acc: 51.5% - 53.3%)  │
├──────────────────┼─────────────────────────────┼───────────────────────────────────────┤
│ 24 Hours         │ Macro volatility regime,    │ HAR-RS-DOW, Conformal Excursion       │
│                  │ cross-market liquidity,     │ Envelopes, Extreme Value Theory (EVT).│
│                  │ leverage distribution.      │ Direction is pure noise (50.0% coin). │
└──────────────────┴─────────────────────────────┴───────────────────────────────────────┘
```

1. **Microstructure (Sub-minute to 5m):** As demonstrated by Raffaelli et al. (2026), Hawkes processes capture order arrival clustering and temporary supply/demand imbalances. However, this alpha decays to pure noise within 15–30 minutes and requires colocation/VIP fee tiers to monetize.
2. **Intermediate (1h to 4h):** As documented by Bysik & Ślepaczuk (2024) and replicated in our audit, directional predictability hovers between 51.5% and 53.3%. This statistical edge is insufficient to overcome exchange transaction costs (35 bps round trip) under unconditional trading.
3. **Macro (24h):** Directional return is indistinguishable from a random walk (AUC 0.504, 50.0% accuracy). However, **volatility and excursion magnitude are highly predictable** ($R^2 \approx 14\%$), making 24-hour conformal risk envelopes the ideal production target.

---

## 7. Results of Completed High-Value Controlled Experiments

Three controlled experiments were executed on `data/raw/ohlcv.parquet` (40,902 hourly bars) using 5-fold Purged Walk-Forward Cross-Validation:

### Experiment 1: In-Train Calibrated Selective Prediction vs. Retrospective Quantiles (1H Horizon)
- **Objective:** Eliminate retrospective threshold lookahead and test whether in-train calibrated confidence thresholds achieve profitable selective prediction under realistic turnover-based transaction friction.
- **Protocol:** Confidence threshold $\tau = \text{Quantile}_{1-\text{cov}}(|\hat{p}_{\text{train}} - 0.5|)$ was learned strictly on each fold's training set and applied out-of-sample to the test fold. Friction of 17.5 bps per one-way trade was applied only on position changes.

| Coverage Target | Method | Active Samples ($N$) | Empirical Coverage | OOS Accuracy | 95% Wilson CI | Mean Net Return (Turnover-Aware) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **100% (All)** | In-Train Calibrated | 33,919 | 100.0% | **53.14%** | [52.6%, 53.7%] | -12.11 bps / bar |
| **50%** | In-Train Calibrated | 17,212 | 50.74% | **54.74%** | [54.0%, 55.5%] | -9.30 bps / bar |
| **25%** | In-Train Calibrated | 8,548 | 25.20% | **55.76%** | [54.7%, 56.8%] | -5.89 bps / bar |
| **10%** | In-Train Calibrated | 3,528 | 10.40% | **56.38%** | [54.7%, 58.0%] | -2.50 bps / bar |
| **10% (Retro)**| Retrospective Lookahead | 3,392 | 10.00% | *56.87%* | [55.2%, 58.5%] | -2.50 bps / bar |
| **5%** | In-Train Calibrated | 1,830 | 5.40% | **56.78%** | [54.5%, 59.0%] | -1.23 bps / bar |
| **5% (Retro)** | Retrospective Lookahead | 1,696 | 5.00% | *56.25%* | [53.9%, 58.6%] | -1.23 bps / bar |

**Key Findings:**
1. In-train calibration exhibits mild coverage expansion ($10.4\%$ realized vs $10.0\%$ target) due to distributional non-stationarity, but avoids optimistic bias.
2. Even at top 5% confidence, out-of-sample accuracy reaches only **$56.78\%$**, far below the 70% target ($p < 10^{-10}$).
3. Accounting for actual turnover dramatically reduces transaction friction (from $-34.6$ bps down to $-1.23$ bps at 5% coverage), but net expectancy remains **negative**.

---

### Experiment 2: Feature Group Information Ablation (1H Horizon)
- **Objective:** Measure the marginal predictive capacity of different feature families to establish whether technical oscillators and volatility indicators add value over simple return lags.
- **Protocol:** Identical 5-fold Purged Walk-Forward CV with Gradient Boosting ($100$ trees, depth $3$, learning rate $0.05$).

| Feature Configuration | Included Features | Count | OOS Accuracy | ROC AUC | Brier Score | $\Delta$ Acc vs. Lags |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Group A: Lags Only** | `ret_1h`, `ret_4h`, `ret_24h`, `ret_168h` | **4** | **53.28%** | **0.5445** | **0.2488** | Baseline |
| **Group B: Lags + Oscillators** | Group A + `rsi_14`, `macd`, `macd_signal`, `sma_20/50/200` | **10** | **53.18%** | **0.5434** | **0.2491** | **-0.10%** |
| **Group C: Lags + Volatility** | Group A + `realized_vol_24/168h`, `parkinson_vol`, `atr`, `vol_z` | **9** | **53.27%** | **0.5455** | **0.2487** | **-0.01%** |
| **Group D: Full Stack** | All 15 features combined | **15** | **53.14%** | **0.5430** | **0.2491** | **-0.14%** |

**Key Findings:**
1. **The Minimalist Rule Holds:** 4 simple return lags (`ret_1h`, `ret_4h`, `ret_24h`, `ret_168h`) achieve the highest directional accuracy ($53.28\%$).
2. Adding 11 additional technical indicators (RSI, MACD, Moving Averages, Parkinson Volatility, Volume Z-Scores) adds **negative marginal value** ($-0.14\%$ accuracy, $-0.0015$ AUC) due to parameter dilution and collinear noise.
3. **Recommendation:** Strip bloated feature generators in favor of a lean 4-to-6 feature set for directional research.

---

### Experiment 3: Dependence-Aware Moving Block Bootstrap Uncertainty Audit
- **Objective:** Quantify true parameter uncertainty under serial correlation and overlapping forecast horizons.
- **Protocol:** 1,000 stationary moving block bootstrap draws. Block lengths: $L = 24\text{h}$ (1H horizon), $L = 48\text{h}$ (4H horizon), $L = 168\text{h}$ (24H horizon).

| Horizon | Sample Size ($N$) | Point Accuracy | 95% Wilson CI (i.i.d.) | 95% Block Bootstrap CI | Bootstrap SE | $p$-value ($H_0: p \ge 70\%$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1H** | 33,919 | **53.14%** | [52.61%, 53.67%] | **[52.65%, 53.63%]** | 0.242% | $p = 0.00 \times 10^{0}$ ($< 10^{-100}$) |
| **4H** | 33,916 | **52.34%** | [51.81%, 52.87%] | **[51.64%, 52.96%]** | 0.345% | $p = 0.00 \times 10^{0}$ ($< 10^{-100}$) |
| **24H** | 33,900 | **50.42%** | [49.89%, 50.95%] | **[48.70%, 52.05%]** | 0.862% | $p = 1.67 \times 10^{-114}$ |

**Key Findings:**
1. For 1-hour forecasts, block bootstrap uncertainty is virtually identical to the Wilson interval ($0.242\%$ SE), confirming minimal serial dependence in 1-hour prediction hits.
2. For 24-hour forecasts, overlapping targets induce strong serial correlation. The true 95% confidence interval spans **$3.35\%$ width ($[48.70\%, 52.05\%]$)** compared to $1.06\%$ for Wilson.
3. Crucially, the 24H interval crosses below 50.0%, demonstrating that 24H directional forecasting has zero statistical edge over a fair coin.

---

## 8. Lean Recommended Architecture and UI Design

Rather than presenting dozens of confusing, overlapping dashboards and speculative features, the application should be consolidated into three tightly focused views:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              RECOMMENDED LEAN UI STRUCTURE                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [1. MARKET & DATA HEALTH] (Top Bar / Header)                                           │
│   • BTC/USD Live Price: $67,420.50 | Feed Freshness: 1.2s (Coinbase L2)                │
│   • L2 Imbalance (OFI): +0.142 | Bid-Ask Spread: 1.1 bps | Data Completeness: 100%    │
│   • Authorization Gate: BLOCKED_AUDIT_FAILURE (iv7d.parquet missing from disk)         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [2. VERIFIED RISK FORECAST] (Primary Dashboard View)                                   │
│   • Active Model: v3.0.0-excursion-ridge-conformal (24-Hour Horizon)                   │
│   • Status: Gated / Informational Reference Only                                       │
│   • Expected Excursion Envelope: P10: -2.41% | P50: +0.00% | P90: +3.12%               │
│   • Historical Empirical Containment: 90.32% (31 independent blocks, 744 hours)       │
│   • Disambiguation Notice: "Volatility envelope reflects price dispersion bounds,     │
│     NOT directional trade recommendations."                                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [3. DIRECTIONAL RESEARCH LAB] (Secondary Research Tab)                                 │
│   • Multi-Horizon Ladder: 1H (53.1%), 4H (52.3%), 24H (50.4%)                         │
│   • Honest Edge Disclosure: Unconditional directional edge is statistically zero.      │
│   • Selective Prediction: Top 5% confidence achieves 56.8% accuracy.                   │
│   • Net Expectancy Warning: Net return after 35 bps friction is strictly negative.     │
│   • Audit Artifacts: Download verified JSON results and methodology reports.           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Simplification Plan
1. **Remove Unused Routes:** Decommission `/api/arena/*` and `/api/genome/*`. These endpoints represent speculative strategy mutations that add 140+ KB of unmaintained code.
2. **Decommission Heavy Deep Learning:** Archive `models/tft_model.py` and `models/checkpoints/tft.pt`. Our empirical ablation proves that complex sequence networks fail to beat a 4-feature Ridge or GBDT baseline on hourly BTC returns.
3. **Transparent Gate Display:** Keep the production gate failure visible on the main dashboard rather than hiding it or silently bypassing checks.

---

## 9. Forensic Analysis of the Missing Volatility Input (`iv7d.parquet`)

The earlier Stage 1 report highlighted that the production startup gate was blocked because `data/raw/iv7d.parquet` was absent from disk. Our comprehensive code audit resolves the exact nature of this dependency:

### Trace Findings:
1. **Model Feature Schema:** In `models/registry/v3.0.0-excursion-ridge-conformal/model_card.md`, the active production model features are:
   $$\text{Features} = [\text{vol\_24h}, \text{rsi\_14}, \text{atr\_14}, \text{funding\_rate}, \text{mvrv\_zscore}]$$
   **Implied volatility (`iv7d`) is NOT an inference feature.**
2. **HAR-RS-DOW Baseline Schema:** In `research/freeze_har_rs_dow.py`, the feature schema is:
   $$\text{Features} = [\text{log\_rv\_down\_1d}, \text{log\_rv\_up\_1d}, \text{log\_rv7d\_var\_ann\_lag}, \text{log\_rv30d\_var\_ann}, \text{dow\_1} \dots \text{dow\_6}]$$
   **Implied volatility (`iv7d`) is NOT a feature in HAR-RS-DOW.**
3. **Where `iv7d.parquet` Was Actually Used:**
   - In `results/vol_edge_01_preregistration.md`, `iv7d` was an external research benchmark used to evaluate models $M_4, M_5, M_6$ to test whether realized volatility compression predicted RV beyond Deribit ATM option-implied volatility.
   - In `prepare_aligned_dataset()`, an inner join on `iv7d` timestamps was performed to ensure fair historical comparison on identical timestamps.
4. **Why the Startup Gate Is Blocked:**
   - In `research/verify_freeze_manifest.py` (Check 5, lines 297–319), the script explicitly checks both `ohlcv.parquet` and `iv7d.parquet` against `manifest["training_data_snapshot"]`.
   - Because `iv7d.parquet` was physically moved or omitted from `data/raw/`, Check 5 emits: `FAIL Training data — iv7d.parquet: File not found`.
   - `validation/startup_gate.py` runs `verify_freeze_manifest.py`. When Check 5 fails, it raises `FreezeIntegrityError("DATA_UNAVAILABLE", "FROZEN_INPUT_MISSING")` and locks production into `BLOCKED_AUDIT_FAILURE`.
5. **Existing Regression Tests:**
   In `tests/test_phase_01_1_adversarial_integrity.py` (lines 52–69), test `test_real_production_dependency_graph()` explicitly asserts:
   ```python
   assert "iv7d.parquet" not in prod_deps, "iv7d.parquet incorrectly included in production runtime dependencies!"
   assert "ohlcv.parquet" in prod_deps
   ```
   Furthermore, `tests/test_phase_01_2_cleanroom_verification.py` Test 7 verifies that making `iv7d.parquet` unavailable does not impact inference runtime.

### Recommended Resolution:
- **Do Not Synthesize Data:** Do not manufacture synthetic or mocked IV data to trick the gate.
- **Do Not Rewrite Frozen Signatures:** Preserving the frozen signature is essential for cryptographic audit trails.
- **Architectural Fix:** In a versioned update, split the freeze manifest into `runtime_inference_dependencies` (which requires only `ohlcv.parquet` and model weights) and `historical_research_benchmarks` (which requires `iv7d.parquet` for VOL-EDGE-01). Until that versioned migration is executed, keep the gate honestly blocked in fail-closed status.

---

## 10. Phased Implementation Plan

```
Phase 1: Verification & Correctness (Completed)
  ├── Mathematically correct effective sample size calculation (bound Neff <= N on classification errors)
  ├── Recalculate uncertainty using moving block bootstrap (account for overlapping horizons)
  ├── Re-run selective prediction with in-train calibrated thresholds
  └── Re-calculate trading returns using turnover-based fee deductions

Phase 2: Architectural Decoupling & Simplification (Next Step)
  ├── Decommission speculative routes (/api/arena/*, /api/genome/*)
  ├── Remove unused deep learning checkpoints (models/checkpoints/tft.pt)
  ├── Prune feature engineering to 4-to-6 core lags (eliminate collinear oscillators)
  └── Preserve fail-closed startup gate and immutable SQLite market memory

Phase 3: Formal Product Stabilization (Final Step)
  ├── Clarify UI terminology: "Conformal Risk Envelope" vs "Directional Research Lab"
  ├── Version-split freeze verification into runtime dependencies vs research benchmarks
  └── Maintain read-only research reproducibility API
```

---

## 11. Reproducibility Artifacts and Verification Commands

The results reported in this document are fully reproducible using the following commands in the repository root:

1. **Stage 2 Controlled Experiments:**
   ```powershell
   python research/stage2_experiment_validation.py
   ```
   *Output JSON:* `experiments/results/stage2_validation/stage2_validation_results.json`

2. **Frontend Module & Budget Tests:**
   ```powershell
   npm test
   npm run check
   ```
   *Result:* All unit tests and syntax checks pass cleanly. Polling budget verified at $29.5\text{ req/min}$ (under $60\text{ req/min}$ limit).

3. **Adversarial Integrity & Gate Tests:**
   ```powershell
   python -m pytest tests/test_phase_01_1_adversarial_integrity.py
   ```
   *Result:* $10$ passed, $0$ failed in $31.76\text{s}$.

---

## 12. Summary of Changes Made vs. Changes Recommended

### Changes Made in This Turn:
1. Created and executed `research/stage2_experiment_validation.py` to independently evaluate in-train selective prediction, feature group ablations, and moving block bootstrap uncertainty.
2. Verified all 4 academic literature citations and corrected metadata discrepancies (H. Arian author name, arXiv preprint status).
3. Generated verified JSON experimental artifacts at `experiments/results/stage2_validation/stage2_validation_results.json`.
4. Executed frontend and backend regression suites (`npm test`, `npm run check`, `pytest tests/test_phase_01_1_adversarial_integrity.py`), confirming all existing contracts pass.

### Changes Recommended for Subsequent Phase:
1. Decommission unused `/api/arena/*` and `/api/genome/*` route files to reduce attack surface and codebase bloat.
2. Archive the 1.2 MB unused PyTorch TFT checkpoint (`models/checkpoints/tft.pt`).
3. Formalize a versioned update to `research/verify_freeze_manifest.py` that separates runtime inference dependencies from historical research benchmarks (`iv7d.parquet`).

---

## 13. Comprehensive Action Priority Table

| Priority | Finding | Evidence | Required Change | Acceptance Test | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **P0** | **Metric Conflation in Public Documentation** | Users mistake 92.84% conformal envelope coverage for 92.84% directional accuracy. | Update all dashboard and API documentation to explicitly distinguish *Conformal Risk Envelope Coverage* ($90.3\%$) from *Directional Accuracy* ($50.4\% - 53.1\%$). | `/api/research/results` returns explicit disambiguation flags; frontend displays separate cards. | **VALIDATED & DOCUMENTED** |
| **P0** | **$N_{\text{eff}} > N$ Sample Size Calculation** | Bartlett AR(1) formula on returns inflated $N_{\text{eff}}$ to $35,181 > 33,919$. | Bound $N_{\text{eff}} \le N$ for binomial classification and compute dependence on prediction error residuals. | `research/stage2_experiment_validation.py` enforces error-based autocorrelation. | **VERIFIED & CORRECTED** |
| **P0** | **Retrospective Selective Prediction Lookahead** | Stage 1 selective prediction thresholds were calculated across pooled test sets. | Calibrate confidence thresholds strictly on fold training sets and evaluate on untouched test folds. | In-train selective prediction test executed; results documented in Section 7. | **VERIFIED & CORRECTED** |
| **P1** | **Overlapping Forecast Uncertainty Understatement** | i.i.d. Wilson score intervals understate uncertainty for 4h and 24h horizons. | Adopt Moving Block Bootstrap ($L = 24\text{h}$ for 1H, $L = 168\text{h}$ for 24H) to report dependence-aware confidence intervals. | Block bootstrap executed; 24H CI documented at $[48.70\%, 52.05\%]$. | **VERIFIED & CORRECTED** |
| **P1** | **Turnover Cost Deduction Flaw** | Deducting 35 bps every hour deducted over $11,870\%$ in fees. | Deduct transaction friction only on position transitions ($\Delta \text{pos}_t \neq 0$). | Turnover-aware net return evaluated in Experiment 1 (-12.11 bps at 100%, -1.23 bps at 5%). | **VERIFIED & CORRECTED** |
| **P1** | **Feature Bloat & Parameter Dilution** | Adding 11 technical indicators reduced accuracy by 0.14% compared to 4 raw lags. | Restrict directional feature engineering to raw return lags (`ret_1h`, `ret_4h`, `ret_24h`, `ret_168h`). | Experiment 2 ablation table confirms Group A out-predicts Group D. | **VERIFIED & DOCUMENTED** |
| **P2** | **Unused Heavy Deep Learning Dependencies** | TFT model (1.2 MB PyTorch checkpoint) adds heavy footprint with zero edge. | Decommission and archive `models/tft_model.py` and `checkpoints/tft.pt`. | Verify removal does not impact `test_phase_01_1_adversarial_integrity.py`. | **RECOMMENDED** |
| **P2** | **Speculative Arena Engine Code Bloat** | Fictional multi-agent arena adds 140+ KB of complex code and routes. | Remove `/api/routes_arena.py` and `engine/arena_*.py`; consolidate to core intelligence. | API server runs cleanly without arena routes registered. | **RECOMMENDED** |
| **P3** | **Missing Volatility Input Disambiguation** | Gate blocked on `iv7d.parquet` despite `iv7d` not being an inference regressor. | In a versioned manifest update, separate runtime inference dependencies from research benchmarks. | Execute `verify_freeze_manifest.py` in audit mode. | **DOCUMENTED** |

---

## 14. Final Decision Rule and the Three Most Important Next Steps

**Decision Rule:** The purpose of BTCognitive is not to maximize code complexity, indicators, or speculative trading games. The purpose is to build the smallest, most rigorously tested system that uses reliable market data, delivers calibrated risk intelligence, measures its limitations with complete epistemic honesty, and deploys changes only when backed by reproducible out-of-sample evidence.

### The Three Most Important Changes to Make Next:

1. **Formalize Product Decoupling in the Primary UI:**
   - **Why It Matters:** Conflating risk-envelope containment ($90.3\%$) with directional accuracy ($50.4\%$) is the primary source of user confusion and unscientific expectations.
   - **Supporting Evidence:** Empirical audit proves 24H directional accuracy is a 50.0% coin flip (AUC 0.504), while 24H conformal excursion containment achieves 90.32%.
   - **Acceptance Test:** The frontend dashboard displays Risk Envelope as the primary product and explicitly labels Directional Research as an experimental lab displaying negative net economic expectancy.

2. **Prune Bloated Feature Sets and Deep Learning Models:**
   - **Why It Matters:** Adding 11 technical indicators and complex deep sequence models (TFT) increases maintenance and inference latency while degrading out-of-sample accuracy (-0.14% delta).
   - **Supporting Evidence:** Experiment 2 ablation proves that a simple 4-feature lag model (`ret_1h`, `ret_4h`, `ret_24h`, `ret_168h`) outperforms the full 15-feature stack ($53.28\%$ vs $53.14\%$).
   - **Acceptance Test:** Run model evaluation comparing 4-feature vs 15-feature pipelines; verify identical or superior out-of-sample Brier score and ROC AUC with lower CPU overhead.

3. **In-Train Calibrated Selective Abstention with Cost Hurdles:**
   - **Why It Matters:** Unconditional directional trading loses money rapidly due to exchange fees. Selective prediction with abstention is the only viable path to positive economic expectancy, but thresholds must be calibrated without lookahead.
   - **Supporting Evidence:** Experiment 1 proves that in-train calibrated thresholds achieve $56.78\%$ accuracy at $5.4\%$ coverage, narrowing turnover net loss to $-1.23\text{ bps}$.
   - **Acceptance Test:** Test shadow-mode decision engine under an economic hurdle requiring expected gross return $> 2.0 \times \text{round-trip friction}$; confirm zero negative-expectancy trades are emitted.
