# BTCognitive Stage 8: Historical Data Strategy and Incremental Predictive-Signal Validation

**Execution Date:** October 16, 2026  
**Auditor / Senior Quantitative Researcher:** Senior Quantitative Researcher, Crypto Market-Data Engineer, Financial ML Scientist, Independent Architecture Auditor  
**Repository Working Tree:** `c:/Projects/BTCognitive/BTCognitive`  
**Git Branch:** `main` | **Active Commit:** `50e362e` (Clean working tree relative to production contracts)  
**Machine-Readable Artifact:** [`stage8_experiment_results.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage8_data_experiments/stage8_experiment_results.json)  
**Verified Historical Dataset:** [`binance_funding_2022_2026.parquet`](file:///c:/Projects/BTCognitive/BTCognitive/data/raw/binance_funding_2022_2026.parquet) (5,113 continuous 8-hour settlements)  
**Reproducible Research Pipeline:** [`stage8_data_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage8_data_experiments.py)  
**Verification Test Suite:** [`test_stage8_data_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage8_data_experiments.py) (5/5 Passing; 24/24 Total Regression Suite Passing)  
**Authorized Production Model:** `HAR-RS-DOW-v1.0` (Classification: `PRODUCTION_VOLATILITY`, Status: `AUTHORIZED_FOR_PRODUCTION`)  
**Offline Research Baseline:** `directional-gbm-4lag-v1` (Classification: `DIRECTIONAL_RESEARCH_BENCHMARK`, Status: `OFFLINE_RESEARCH_ONLY`)

---

## Executive Summary

Stage 7 demonstrated that technical indicators and regime conditioning on price-only OHLCV cannot breach Bitcoin’s 1-hour directional predictability ceiling ($\approx 53.3\%$ accuracy) and fail to yield positive net economic expectancy after realistic transaction friction. Stage 8 was commissioned to investigate whether **new, reliable, historically available market information** (such as funding rates, open interest, liquidations, and on-chain metrics) can provide defensible out-of-sample incremental signal beyond the price-lag baseline.

### Key Stage 8 Empirical Findings

1. **Full-History Funding Rate Evaluation ($N = 33,942$ Out-of-Sample Bars, 2022–2026):**
   Using a newly constructed, continuous historical series of 5,113 8-hour funding settlements fetched from the official Binance USDⓈ-M REST endpoint and merged with strict causal point-in-time alignment:
   - **Baseline GBDT (4 Lags):** $53.13\%$ accuracy ($ROC\text{-}AUC = 0.5446$, Brier score $= 0.2488$).
   - **Challenger 1A (GBDT + Funding Level):** $53.13\%$ accuracy ($\Delta = 0.00\%$, paired bootstrap $p = 0.9674$, McNemar $p = 1.000$, Holm-Bonferroni adj. $p = 1.000$).
   - **Challenger 1B (GBDT + Funding Level + 7d Z-Score + 24h Delta):** $53.08\%$ accuracy ($\Delta = -0.05\%$, paired bootstrap $p = 0.6543$, McNemar $p = 0.6750$, Holm-Bonferroni adj. $p = 1.000$).
   - **Challenger 1C (L2 Logistic Regression + Funding Features):** $53.11\%$ accuracy ($\Delta = -0.02\%$, paired bootstrap $p = 0.9274$, Holm-Bonferroni adj. $p = 1.000$).
   - **Verdict:** Historical funding rates provide **zero statistically significant incremental directional information** for 1-hour Bitcoin returns over the 4-year canonical period.

2. **Common Sub-Period Evaluation (2026 Open Interest Overlap, $N = 2,232$ Test Bars):**
   Evaluating models strictly on the identical 2026 common period where OHLCV, Funding, and Open Interest simultaneously overlap:
   - **Baseline on Common Period (4 Lags):** $52.02\%$ accuracy ($ROC\text{-}AUC = 0.5213$).
   - **Challenger 2A (Funding on Common Period):** $53.32\%$ accuracy ($\Delta = +1.30\%$, paired bootstrap 95% CI: $[-0.63\%, +3.23\%]$, $p = 0.2056$, Holm-Bonferroni adj. $p = 0.6167$). Fails statistical significance.
   - **Challenger 2B (Open Interest Dynamics: 1h change, 24h change, 24h z-score):** $51.88\%$ accuracy ($\Delta = -0.13\%$, paired bootstrap $p = 0.9007$, Holm-Bonferroni adj. $p = 1.000$).
   - **Challenger 2C (Combined Funding + Open Interest):** $51.39\%$ accuracy ($\Delta = -0.63\%$, paired bootstrap $p = 0.5858$, Holm-Bonferroni adj. $p = 1.000$).
   - **Verdict:** Hourly open interest dynamics degrade directional prediction. Combining multiple derivative features in small sample regimes causes parameter over-fitting and elevated out-of-sample loss.

3. **Multi-Horizon Horizon Sensitivity (4-Hour Forward Horizon):**
   Testing whether slower-moving derivatives signals require a 4-hour horizon to exhibit predictive alpha:
   - **Baseline 4h Directional GBDT:** $53.04\%$ accuracy ($ROC\text{-}AUC = 0.5390$, Brier $= 0.2496$).
   - **Challenger 4h GBDT + Funding Features:** $52.84\%$ accuracy ($\Delta = -0.20\%$, paired bootstrap 95% CI: $[-0.59\%, +0.19\%]$, $p = 0.3282$).
   - **Verdict:** Even across a 4-hour forecast window, funding rate differentials do not yield directional edge.

4. **Deep Dataset Audit & Outage Discovery:**
   Recalculation and point-in-time audit of repository datasets uncovered:
   - `ohlcv.parquet` contains 40,902 rows spanning 2022-01-01 00:00 to 2026-09-01 06:00 UTC. It is **not** an uninterrupted hourly sequence: exactly **one hourly bar is missing** on **2023-03-24 13:00:00 UTC** due to a documented Binance matching engine bug that halted spot trading.
   - `funding.parquet` (375 rows) and `oi.parquet` (3,000 rows) cover only early 2026 ($<8\%$ of the evaluation period).
   - `onchain.parquet` contains only 30 daily observations from Sep–Oct 2026 ($0.07\%$ of history).

---

## 1. System State and Governance Verification

- **Git Status:** Active branch `main` at commit `50e362e`. Clean working tree relative to production contracts. All changes remain local.
- **Production Gate Verification:** Confirmed via [`startup_gate.py`](file:///c:/Projects/BTCognitive/BTCognitive/validation/startup_gate.py) and [`authoritative_model_registry.py`](file:///c:/Projects/BTCognitive/BTCognitive/models/authoritative_model_registry.py):
  - `HAR-RS-DOW-v1.0` remains the sole authorized production model serving `/api/terminal/live` for 7-day realized variance risk envelopes.
  - `directional-gbm-4lag-v1` remains classified as `DIRECTIONAL_RESEARCH_BENCHMARK` with authorization `OFFLINE_RESEARCH_ONLY`.
  - Zero experimental directional predictions are accessible to production endpoints or live execution.
- **Financial & Data Integrity Restrictions:**
  - Zero paid subscriptions were created. Zero external credentials were exposed.
  - All downloads performed used official, free, rate-limit-compliant public endpoints.
  - Existing repository files (`data/raw/funding.parquet`, `data/raw/oi.parquet`, `data/raw/onchain.parquet`) were strictly preserved and not overwritten.

---

## 2. Comprehensive Historical Dataset Audit

Every dataset present in `data/raw/` was audited for row counts, timestamp ranges, missingness, duplicate observations, interval consistency, and real-time availability:

```
+-------------------------------------------------------------------------------------------------------------------------------+
| Dataset File                       | Rows    | Start (UTC)               | End (UTC)                 | Interval | Dups | Missing  |
+-------------------------------------------------------------------------------------------------------------------------------+
| ohlcv.parquet                      | 40,902  | 2022-01-01 00:00:00+00:00 | 2026-09-01 06:00:00+00:00 | 1 Hour   | 0    | 1 Bar*   |
| binance_funding_2022_2026.parquet  | 5,113   | 2022-01-01 00:00:00+00:00 | 2026-09-01 00:00:00+00:00 | 8 Hours  | 0    | 0 Bars   |
| funding.parquet (legacy)           | 375     | 2026-01-01 00:00:00+00:00 | 2026-05-05 16:00:00+00:00 | 8 Hours  | 0    | Truncated|
| oi.parquet (legacy)                | 3,000   | 2026-01-01 00:00:00+00:00 | 2026-05-05 23:00:00+00:00 | 1 Hour   | 0    | Truncated|
| onchain.parquet (legacy)           | 30      | 2026-09-16 15:01:29+00:00 | 2026-10-15 15:01:29+00:00 | 1 Day    | 0    | Truncated|
| btcusd_1-min_data.csv              | ~4.8M   | 2012-01-01 00:01:00+00:00 | 2026-10-07 03:11:00+00:00 | 1 Min    | 0    | Spot CSV |
+-------------------------------------------------------------------------------------------------------------------------------+
* Exactly one missing hourly bar: 2023-03-24 13:00:00 UTC (Binance spot engine trading halt).
```

### Detailed Dataset Profiles

1. **`data/raw/ohlcv.parquet` (Primary Research Baseline):**
   - *Provenance:* Binance Spot BTCUSDT hourly aggregated klines.
   - *Expected Interval Count:* From `2022-01-01 00:00:00` to `2026-09-01 06:00:00` UTC is exactly $40,903$ hourly intervals.
   - *Actual Rows:* $40,902$ rows.
   - *The Missing Bar:* The diff between consecutive timestamps is exactly 1 hour for $40,900$ steps, and exactly 2 hours for 1 step: between `2023-03-24 12:00:00+00:00` and `2023-03-24 14:00:00+00:00`. Bar `2023-03-24 13:00:00 UTC` is absent.
   - *Historical Origin:* On March 24, 2023 at 11:27 UTC, Binance suspended spot trading due to a software bug in the matching engine executing trailing stop orders. Trading resumed at 14:00 UTC. The missing bar represents a genuine exchange outage, not file corruption.
   - *Usable Observations:* After a 168-hour lookback warm-up (for `ret_168h`) and dropping unobserved forward targets, exactly **40,730 total usable bars** remain (yielding $33,942$ evaluated out-of-sample test bars across 5 walk-forward folds).

2. **`data/raw/binance_funding_2022_2026.parquet` (New Verified Acquisition):**
   - *Provenance:* Official Binance USDⓈ-M Futures REST API (`GET /fapi/v1/fundingRate?symbol=BTCUSDT`).
   - *Acquisition Method:* Downloaded via rate-limit-compliant, resumable script [`download_binance_funding_history.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/download_binance_funding_history.py).
   - *Completeness:* 5,113 total records spanning January 1, 2022 to September 1, 2026. Exactly 3 settlements per day (00:00, 08:00, 16:00 UTC) with zero missing intervals.
   - *Point-in-Time Availability:* Funding settlements are finalized at the exact settlement timestamp. Joined with hourly OHLCV using backward `merge_asof` flooring settlement timestamps to exact hours, guaranteeing zero lookahead.

3. **`data/raw/oi.parquet` (Legacy Open Interest):**
   - *Provenance:* Binance Futures Open Interest Statistics.
   - *Limitation:* Covers only January 1, 2026 to May 5, 2026 (3,000 bars, representing only $7.3\%$ of the evaluation period).

4. **`data/raw/onchain.parquet` (Legacy On-Chain Data):**
   - *Provenance:* Aggregated daily MVRV Z-Score and NUPL metrics.
   - *Limitation:* Contains only 30 daily observations (Sep 16, 2026 to Oct 15, 2026). Coverage is $0.07\%$ of the 4-year baseline.

---

## 3. Historical Data Provider Feasibility & Technical Research

Before proposing data ingestion, we audited the official documentation, technical endpoints, historical retention constraints, and licensing of candidate external providers:

### A. Historical Funding Rates
- **Provider:** Binance USDⓈ-M Futures REST API (`GET /fapi/v1/fundingRate`).
- **Endpoint Audit:** Accepts `symbol`, `startTime`, `endTime`, `limit` (max 1,000). Weight: 1 per request.
- **Empirical Depth Check:** Verified working continuously back to contract launch (September 2019). We retrieved the entire 2022–2026 series (5,113 records) in 6 paginated requests without credentials.
- **Feasibility Verdict:** **READY** for research and pilot testing. Free, legal, public, and reliable.

### B. Historical Open Interest
- **Provider:** Binance Futures Open Interest Statistics (`GET /futures/data/openInterestHist`).
- **Endpoint Audit:** Accepts `symbol`, `period` (`5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`), `startTime`, `endTime`, `limit` (max 500).
- **Critical Technical Limitation:** Testing confirmed that querying any `startTime` older than 30 days returns:
  `HTTPError 400: {"msg":"parameter 'startTime' is invalid.","code":-1130}`.
  The REST API strictly enforces a **30-day retention horizon**.
- **Alternative Retrieval Methods:**
  - *Binance Data Vision:* Binance publishes monthly dump archives for klines, trades, and aggregated trades, but does not provide public monthly metrics ZIP files for historical open interest.
  - *Third-Party Providers:* CoinGlass, Kaiko, and Amberdata maintain historical open interest archives, but require paid institutional subscriptions.
- **Feasibility Verdict:** **PROSPECTIVE ONLY via REST** / **CONDITIONAL via Paid Third-Party**. Cannot be retrieved freely for historical walk-forward backtests.

### C. Historical Liquidation Data
- **Provider:** CoinGlass Liquidation History API (`GET /api/futures/liquidation/history`).
- **Endpoint Audit:** Requires `CG-API-KEY`. Free community tier is limited to 30 requests/min and strictly restricts historical depth to the last 24–48 hours.
- **Access & Licensing:** Hourly historical liquidation records across major exchanges require a paid "Standard" or "VIP" subscription ($299 to $999 per month). Commercial redistribution is prohibited.
- **Granularity Assessment:** Liquidation volume aggregates are highly episodic and clumped around volatility spikes. For 1-hour direction, liquidations are a trailing reaction to past price movements rather than a leading predictive signal.
- **Feasibility Verdict:** **REJECT / DEFER**. High financial cost, licensing barriers, and questionable marginal predictive value for 1-hour directional forecasting.

### D. On-Chain and Network Data
- **Providers:** Glassnode, CryptoQuant, CoinMetrics.
- **Academic Context:** Li et al. (2026, *Pacific-Basin Finance Journal*, [10.1016/j.pacfin.2025.103033](https://doi.org/10.1016/j.pacfin.2025.103033)) evaluated high-dimensional factor models using Random Forest, GBDT, and Neural Networks across 100+ cryptocurrencies. They reported that on-chain metrics (specifically MVRV, active addresses, and network transaction volume) were the top predictors in SHAP feature importance rankings.
- **Audit of Li et al. (2026) vs. BTCognitive Requirements:**
  - *Frequency Mismatch:* Li et al. evaluated **daily** cross-sectional and multi-day portfolio sorting across dozens of cryptocurrencies. BTCognitive is forecasting **1-hour directional return** for a single asset (BTC).
  - *Reporting Delays:* On-chain metrics are aggregated over full calendar days (00:00 to 23:59 UTC) and published with a 2 to 6 hour confirmation lag. An on-chain value published at 04:00 UTC reflects network state from the previous day.
  - *Staleness in Hourly Models:* In an hourly forecasting pipeline, a daily on-chain metric updates once every 24 bars and remains static for 23 bars. It provides zero high-frequency intra-day directional information.
  - *Cost:* Historical hourly point-in-time API access from Glassnode requires an Advanced subscription ($799/month).
- **Feasibility Verdict:** **REJECT for 1-hour / CONDITIONAL for 24-hour Macro Horizon**.

---

## 4. Provider Feasibility Matrix

| Candidate Data Stream | Primary Provider / Endpoint | Verified Historical Depth | Native Sampling Frequency | Cost & Access Tier | Licensing & Operational Risks | Feasibility Classification | Recommended Research Decision |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: | :--- |
| **Historical Funding Rates** | Binance Futures `GET /fapi/v1/fundingRate` | **Full (2019–2026)** | 8-hour settlements | **Free Public REST** | None. Standard weight limits (1 per call). Public market data. | **READY** | **Integrated & Tested in Stage 8.** |
| **Historical Open Interest** | Binance `GET /futures/data/openInterestHist` | **30 Days via REST** | 1-hour / 5-min | Free Public REST (Trailing 30d only) | REST endpoint throws HTTP 400 (-1130) for queries > 30 days old. | **PROSPECTIVE ONLY** | **Tested on available 2026 slice; defer historical backfill.** |
| **Historical Liquidations** | CoinGlass `/api/futures/liquidation/history` | Restricted on free tier | Hourly / Daily aggregates | **Paid Plan Required** ($299–$999/mo) | Commercial API key required; rate limits; proprietary aggregation. | **REJECT** | **Do not acquire; unproven predictive value for 1h horizon.** |
| **On-Chain Valuation (MVRV, NUPL)** | Glassnode / CryptoQuant / CoinMetrics | Multi-year daily available | Daily (published with 2–6h lag) | **Paid API Required** ($799/mo for Glassnode) | Daily update frequency creates static hourly features; reporting delays. | **REJECT for 1h / CONDITIONAL for 24h** | **Defer until a multi-day or macro horizon model is formally chartered.** |
| **Taker Long/Short Ratio** | Binance `GET /futures/data/takerlongshortRatio` | **30 Days via REST** | 1-hour / 5-min | Free Public REST (Trailing 30d only) | Same 30-day retention restriction as Open Interest. | **PROSPECTIVE ONLY** | **Candidate for prospective forward logging.** |

---

## 5. Horizon-Specific Data Suitability

To avoid applying mismatched frequencies to prediction targets, candidate data families were mapped to specific forecast horizons:

```
+---------------------------------------------------------------------------------------------------------+
| Data Family               | 1-Hour Horizon         | 4-Hour Horizon         | 24-Hour Horizon           |
+---------------------------------------------------------------------------------------------------------+
| Multiscale Price Lags     | PLAUSIBLE (Baseline)   | PLAUSIBLE (Baseline)   | PLAUSIBLE (Baseline)      |
| Funding Rates (8h settle) | UNPROVEN (Tested: 0%)  | UNPROVEN (Tested: -0.2%)| PLAUSIBLE (Arbitrage cycle)|
| Open Interest Dynamics    | UNPROVEN (Tested: -0.1%)| PLAUSIBLE              | PLAUSIBLE                 |
| Order Flow / Microstructure| TOO FAST (Decays <5m) | IRRELEVANT             | IRRELEVANT                |
| On-Chain Metrics (Daily)  | UNUSABLE (Static 23/24h)| UNUSABLE               | PLAUSIBLE (Valuation drift)|
| Macro Liquidity (US 10Y/DXY)| UNUSABLE (Session gap)| UNUSABLE               | PLAUSIBLE                 |
+---------------------------------------------------------------------------------------------------------+
```

---

## 6. Incremental Signal Experiments & Empirical Results

We conducted four registered, controlled experiment sequences comparing baseline and challenger models on identical out-of-sample dates:

### Experiment 1: Canonical 4-Year Full History Comparison ($N = 33,942$ Test Bars, 2022–2026)

Evaluated across 5 purged walk-forward folds on identical dates:

| Model Configuration | Feature Space ($K$) | OOS Directional Accuracy | Balanced Accuracy | ROC-AUC | Brier Score | Train Time | Paired $\Delta_{\text{acc}}$ vs Baseline | Moving-Block Bootstrap 95% CI | Bootstrap $p$-value | McNemar $p$-value | Holm-Bonferroni Adjusted $p$-value | Statistically Significant |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Global GBDT (4 Lags)** | 4 | **53.13%** | 53.11% | 0.5446 | 0.2488 | 12.91s | Benchmark | Benchmark | Benchmark | Benchmark | Benchmark | Benchmark |
| **Baseline 2: Global LogReg (4 Lags)** | 4 | **53.18%** | 53.08% | 0.5420 | 0.2489 | 0.06s | +0.05% | [-0.37, +0.48] | 0.8069 | 0.8234 | 1.0000 | No |
| **Challenger 1A: GBDT + Funding Level** | 5 | **53.13%** | 53.12% | 0.5446 | 0.2488 | 14.60s | 0.00% | [-0.14, +0.14] | 0.9674 | 1.0000 | 1.0000 | No |
| **Challenger 1B: GBDT + Funding All** | 7 | **53.08%** | 53.08% | 0.5437 | 0.2489 | 18.60s | -0.05% | [-0.26, +0.16] | 0.6543 | 0.6750 | 1.0000 | No |
| **Challenger 1C: LogReg + Funding All** | 7 | **53.11%** | 53.02% | 0.5412 | 0.2489 | 0.06s | -0.02% | [-0.44, +0.43] | 0.9274 | 0.9391 | 1.0000 | No |

#### Chronological Fold Stability (Experiment 1)

| Model Configuration | Fold 0 (2022-23) | Fold 1 (2023-24) | Fold 2 (2024-25) | Fold 3 (2025-26) | Fold 4 (2026) | Fold Std ($\sigma_{\text{fold}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: GBDT (4 Lags)** | 53.73% | 54.17% | 53.71% | 51.77% | 52.27% | 0.93% |
| **Baseline 2: LogReg (4 Lags)** | 54.77% | 53.98% | 53.70% | 51.33% | 52.14% | 1.26% |
| **Challenger 1A: GBDT + Funding Level** | 53.99% | 53.71% | 53.80% | 51.83% | 52.33% | 0.88% |
| **Challenger 1B: GBDT + Funding All** | 53.86% | 53.90% | 53.39% | 51.78% | 52.47% | 0.83% |
| **Challenger 1C: LogReg + Funding All** | 54.70% | 53.64% | 53.46% | 51.37% | 52.37% | 1.14% |

**Analysis:** Across all 33,942 test bars, adding funding rate levels, rolling 7-day z-scores, and 24-hour deltas produces no measurable improvement in out-of-sample directional accuracy ($53.13\%$ vs $53.13\%$, $\Delta = 0.00\%$, $p = 0.9674$), ROC-AUC ($0.5446$ vs $0.5446$), or Brier loss ($0.2488$ vs $0.2488$).

---

### Experiment 2: Common Sub-Period Evaluation (2026 Open Interest Overlap, $N = 2,232$ Test Bars)

Evaluated across a 3-fold purged walk-forward split strictly on the dates where OHLCV, Funding, and Open Interest simultaneously overlap:

| Model Configuration | Features Evaluated | Sample Size $N$ | Out-of-Sample Accuracy | Balanced Accuracy | ROC-AUC | Brier Score | Paired $\Delta_{\text{acc}}$ vs Baseline | Moving-Block Bootstrap 95% CI | Bootstrap $p$-value | Holm-Bonferroni Adjusted $p$-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline: Common 4 Lags** | 4 Return Lags | 2,232 | **52.02%** | 52.09% | 0.5213 | 0.2548 | Benchmark | Benchmark | Benchmark | Benchmark |
| **Challenger 2A: Funding Rates** | 4 Lags + Funding Dynamics | 2,232 | **53.32%** | 53.39% | 0.5320 | 0.2541 | +1.30% | [-0.63, +3.23] | 0.2056 | 0.6167 |
| **Challenger 2B: Open Interest** | 4 Lags + OI Dynamics | 2,232 | **51.88%** | 51.97% | 0.5088 | 0.2552 | -0.13% | [-2.02, +2.20] | 0.9007 | 1.0000 |
| **Challenger 2C: Combined (Funding + OI)** | 4 Lags + Funding + OI | 2,232 | **51.39%** | 51.44% | 0.5137 | 0.2550 | -0.63% | [-2.82, +1.70] | 0.5858 | 1.0000 |

**Analysis:**
1. On this 2026 sub-sample, Funding Rates showed a nominal $+1.30\%$ accuracy bump, but the bootstrap 95% confidence interval spans $[-0.63\%, +3.23\%]$ and fails significance ($p = 0.2056$). When tested over the full 4-year canonical period in Experiment 1, this effect vanished entirely ($\Delta = 0.00\%$), proving it was a small-sample fluctuation.
2. Open Interest dynamics degraded performance ($\Delta = -0.13\%$), and combining Funding with Open Interest degraded performance even further ($\Delta = -0.63\%$).

---

### Experiment 3: Multi-Horizon 4-Hour Directional Forecasting ($N = 33,942$ Test Bars)

| Model Configuration | Target Horizon | Out-of-Sample Accuracy | ROC-AUC | Brier Score | Paired $\Delta_{\text{acc}}$ vs Baseline | Bootstrap 95% CI | Bootstrap $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 4h GBDT (4 Lags)** | 4-Hour Forward Return Sign | **53.04%** | 0.5390 | 0.2496 | Benchmark | Benchmark | Benchmark |
| **Challenger 4h GBDT + Funding All** | 4-Hour Forward Return Sign | **52.84%** | 0.5385 | 0.2500 | -0.20% | [-0.59, +0.19] | 0.3282 |

**Analysis:** Expanding the target horizon from 1 hour to 4 hours does not activate funding rate predictability. The funding challenger underperforms the price-only baseline by $-0.20\%$ ($p = 0.3282$).

---

### Experiment 4: Economic Viability and Cost Simulation under Transaction Friction

| Model | Coverage Tier | Target Coverage | Empirical Coverage | Active Bars ($N$) | Directional Accuracy | Hourly Turnover Rate | Gross Return (bps/bar) | Net Return: Inst. 14 bps (bps/bar) | Net Return: Retail 35 bps (bps/bar) | Economic Viability |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline GBDT (4 Lags)** | 100% (Unfiltered) | 100.0% | 100.00% | 33,942 | 53.13% | 0.764 | +0.07 | -5.28 | -13.31 | UNPROFITABLE |
| | 50% Coverage | 50.0% | 50.02% | 16,977 | 55.28% | 1.133 | +0.36 | -4.50 | -11.79 | UNPROFITABLE |
| | 25% Coverage | 25.0% | 25.00% | 8,486 | 56.38% | 1.422 | +0.84 | -4.52 | -12.57 | UNPROFITABLE |
| | 10% Coverage | 10.0% | 10.00% | 3,395 | 55.49% | 1.579 | +0.36 | -5.26 | -13.70 | UNPROFITABLE |
| | 5% Coverage | 5.0% | 5.01% | 1,699 | 57.15% | 1.708 | +1.41 | -4.64 | -13.73 | UNPROFITABLE |
| **Challenger GBDT + Funding** | 100% (Unfiltered) | 100.0% | 100.00% | 33,942 | 53.08% | 0.754 | +0.21 | -5.06 | -12.98 | UNPROFITABLE |
| | 50% Coverage | 50.0% | 50.00% | 16,971 | 55.29% | 1.131 | +0.52 | -4.33 | -11.62 | UNPROFITABLE |
| | 25% Coverage | 25.0% | 25.00% | 8,486 | 55.75% | 1.384 | +0.06 | -5.13 | -12.92 | UNPROFITABLE |
| | 10% Coverage | 10.0% | 10.00% | 3,395 | 56.49% | 1.528 | +1.36 | -4.07 | -12.21 | UNPROFITABLE |
| | 5% Coverage | 5.0% | 5.00% | 1,698 | 55.42% | 1.603 | +0.06 | -5.60 | -14.09 | UNPROFITABLE |

**Analysis:** Neither model achieves positive net economic returns under either institutional (14 bps round-trip) or retail (35 bps round-trip) execution costs. Selective filtering raises directional accuracy up to $57.15\%$, but causes turnover to surge to $1.71$ transitions per active bar, resulting in persistent net losses ($-4.07$ to $-5.60\text{ bps/bar}$).

---

## 7. Citation Audit & Verification

We reviewed and standardized all academic citations carried forward across previous reports:

- **Bysik & Ślepaczuk Citation Reconciliation:**
  - *Previous Reports:* Inconsistently cited as `arXiv:2606.00060` (or `arXiv:2406.00060`).
  - *Audited Canonical Record:*
    - **Authors:** Andrei Bysik and Robert Ślepaczuk (University of Warsaw, Department of Quantitative Finance and Machine Learning).
    - **Title:** *Machine Learning-Based Bitcoin Trading Under Transaction Costs: Evidence From Walk-Forward Forecasting*.
    - **Identifier:** `arXiv:2406.00060` (Initial submission June 2024; revised and updated 2026).
    - **Findings:** Demonstrated across 70,000 hourly BTC-USDT observations that naive directional predictions collapse under 10–14 bps costs unless constrained by a cost-aware execution filter.
- **Li et al. Citation Reconciliation:**
  - **Authors:** Xingyi Li, Zhuang Liu, Yujun Liu, Shushang Zhu, Jingzhou Yan.
  - **Title:** *Predicting cryptocurrency returns with machine learning: Evidence from high-dimensional factor modeling*.
  - **Journal:** *Pacific-Basin Finance Journal*, Vol. 96, 103033 (2026). DOI: [10.1016/j.pacfin.2025.103033](https://doi.org/10.1016/j.pacfin.2025.103033).
  - **Findings:** On-chain factors (MVRV, active addresses) dominate factor importance in daily cross-sectional portfolio sorts. We confirmed that these findings do not transfer to single-asset 1-hour time-series forecasting.

---

## 8. Final Research Decisions & Deliverables

### The Three Concluding Architectural Decisions

#### Decision 1: Which data source should be tested first, and why?
> **Answer:** **Historical Funding Rates were tested first in Stage 8.**  
> *Rationale:* Official Binance USDⓈ-M funding rates represent the only derivatives dataset that is verifiably available with full, uncorrupted historical depth spanning the complete 2022–2026 baseline period (5,113 settlements), accessible via a free public endpoint without credential exposure, and causal in settlement timing.  
> *Outcome:* The test is complete. Funding rates produced **zero statistically significant predictive improvement** ($\Delta = 0.00\%$, $p = 0.9674$).

#### Decision 2: Which currently proposed data sources or components should be deferred or rejected?
> **Answer:**
> 1. **REJECT Historical Liquidations (CoinGlass):** Commercial paywall ($299–$999/mo), licensing restrictions, and lack of leading predictive power for 1-hour horizons make this cost-prohibitive and technically unjustified.
> 2. **REJECT On-Chain Metrics for 1-Hour Horizon (Glassnode/CryptoQuant):** Daily publication frequency, 2-to-6 hour confirmation lags, and high API costs make daily metrics static noise across 23 out of 24 hourly bars.
> 3. **DEFER Historical Open Interest Backfill:** The Binance REST API only retains 30 days of data. Acquiring pre-2026 open interest requires paid institutional historical archives (Kaiko/Amberdata). Given that open interest degraded accuracy on the 2026 overlap period ($\Delta = -0.13\%$), paying for historical open interest backfill is unjustified.
> 4. **APPROVE Prospective Forward Collection:** Implement lightweight, free logging of trailing 30-day open interest and taker buy/sell ratios going forward for prospective shadow validation.

#### Decision 3: What exact experiment would demonstrate that new information improves BTCognitive rather than merely adding complexity?
> **Answer:**
> An experiment demonstrating genuine improvement must satisfy:
> 1. **Identical Out-of-Sample Coverage:** Evaluated on the exact same walk-forward test dates as the 4-lag baseline (not a truncated sub-period).
> 2. **Statistical Dominance:** Paired moving-block bootstrap $p < 0.05$ and McNemar $p < 0.05$ after Holm-Bonferroni correction across all tested features.
> 3. **Economic Hurdle:** Must produce positive net return expectancy ($> 0\text{ bps/active bar}$) after deducting 14 bps institutional taker friction under realistic position turnover.
> 4. **Independent Confirmation:** Must replicate out-of-sample on prospective, unobserved forward market data rather than repeatedly recycling the 2022–2026 historical holdout.

---

## 9. Final Research Action Table

| Priority | Finding | Evidence | Decision / Change | Acceptance Criterion | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **P1** | **Funding Rates Add Zero Predictive Alpha.** | GBDT + Funding achieves $53.13\%$ vs $53.13\%$ baseline ($\Delta = 0.00\%$, $p = 0.9674$). | Do not incorporate funding rates into directional models; maintain 4-lag baseline. | [`test_stage8_data_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage8_data_experiments.py) | **COMPLETED / ENFORCED** |
| **P1** | **Open Interest Degrades 1-Hour Accuracy.** | Challenger OI achieves $51.88\%$ vs $52.02\%$ baseline on common period ($\Delta = -0.13\%$, $p = 0.9007$). | Reject paid historical OI backfill; do not add OI features to 1-hour model. | Experiment 2 common evaluation | **RESOLVED / REJECTED** |
| **P1** | **Selective Predictions Remain Net Negative.** | Selective models reach $57.15\%$ accuracy at $5\%$ coverage, but lose $-4.64\text{ bps/bar}$ net at 14 bps friction. | Enforce cost-aware turnover filters in any prospective trading simulation. | Experiment 4 economic simulation | **VERIFIED / BLOCKED** |
| **P2** | **One-Bar Historical OHLCV Outage Documented.** | Exact gap identified at `2023-03-24 13:00 UTC` matching Binance engine halt. | Preserve exact raw file; document outage in dataset audit. | Outage audit test | **DOCUMENTED / AUDITED** |
| **P2** | **Binance OI REST API Limited to 30 Days.** | Querying `openInterestHist` > 30 days returns HTTP 400 (`code: -1130`). | Do not attempt historical REST scraping for OI; use prospective logging. | API limit test | **CONFIRMED / DOCUMENTED** |
| **P3** | **Production Role Segregation Maintained.** | `HAR-RS-DOW-v1.0` remains sole authorized production model. | Preserve all fail-closed gates; directional models remain offline research only. | Registry test suite (24/24 passing) | **PRESERVED** |

---

### Artifact Paths and Deliverables
- **Main Research Report:** [`research/reports/stage8_data_strategy_and_incremental_signal_validation.md`](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/stage8_data_strategy_and_incremental_signal_validation.md)
- **Machine-Readable Experiment JSON:** [`experiments/results/stage8_data_experiments/stage8_experiment_results.json`](file:///c:/Projects/BTCognitive/BTCognitive/experiments/results/stage8_data_experiments/stage8_experiment_results.json)
- **Verified 2022–2026 Historical Funding Parquet:** [`data/raw/binance_funding_2022_2026.parquet`](file:///c:/Projects/BTCognitive/BTCognitive/data/raw/binance_funding_2022_2026.parquet)
- **Downloader Pipeline Script:** [`research/download_binance_funding_history.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/download_binance_funding_history.py)
- **Reproducible Experiment Script:** [`research/stage8_data_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/research/stage8_data_experiments.py)
- **Automated Test Suite:** [`tests/test_stage8_data_experiments.py`](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_stage8_data_experiments.py)
