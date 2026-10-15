# 🔬 BTCognitive: Directional Prediction Accuracy Audit & 70% Feasibility Assessment

**Executive Authorship:** Senior Quantitative Researcher, Financial ML Engineer & Independent Software Auditor  
**Audit Date:** 2026-10-15  
**Repository Branch:** `main`  
**Base Commit SHA:** `2eb78cd190962f8e9ff0d89e072406d95b46dcd1`  
**Evaluation Dataset:** `data/raw/ohlcv.parquet` (40,902 hourly bars, 2022-01-01 to 2026-09-01)  
**Governance Invariant:** Research & Audit Only — Zero Live Trades, Zero Cloud Deployments  

---

## 1. Executive Verdict

### Is a $\ge 70\%$ Directional Prediction Accuracy Target Achievable?
**Verdict:** **SCIENTIFICALLY CONTRADICTED BY AVAILABLE EMPIRICAL EVIDENCE AND FINANCIAL ECONOMETRICS.**

1. **Unconditional Directional Forecasting (100% Coverage):**
   - On out-of-sample BTC/USD returns across 1-hour, 4-hour, and 24-hour horizons over 4.5 years ($N = 33,900+$ evaluations per horizon under 5-fold Purged Walk-Forward CV), the best machine learning models achieve **$50.40\%$ to $53.30\%$ directional accuracy** (ROC AUC $0.5066$ to $0.5448$).
   - A $70\%$ directional accuracy target is rejected with $p < 10^{-10}$ across all horizons and model families.
   - In economic terms, achieving an unconditional $70\%$ directional accuracy on hourly or daily returns on a multi-billion dollar liquid macro asset is equivalent to an annualized Sharpe ratio $> 8.0$, which is an economic impossibility in an open, competitive arbitrage market.

2. **Selective / High-Confidence Forecasting (Abstention Allowed):**
   - When filtering predictions to the top $10\%$ highest-confidence quantile, out-of-sample directional accuracy on 1-hour returns rises to **$57.05\%$** ($95\%$ Wilson CI: $[55.37\%, 58.70\%]$), but remains far below $70\%$. At 24-hour horizons, top $10\%$ confidence yields **$54.03\%$** ($95\%$ Wilson CI: $[52.37\%, 55.68\%]$).
   - Under both BASE ($35\text{ bps}$) and CONSERVATIVE ($65\text{ bps}$) round-trip transaction costs, net economic expectancy remains **strictly negative** ($-32.2\text{ bps}$ to $-64.8\text{ bps}$ per trade), confirming that statistical confidence filters do not overcome transaction friction.

3. **Conformal Risk-Envelope Coverage vs. Directional Accuracy Disambiguation:**
   - Previous local reports documenting **$92.84\%$** empirical coverage (`uncertainty-04`) and **$91.80\%$** coverage (`production_accuracy.csv`) reflect **conformal volatility risk-envelope containment** ($\text{MFE} / \text{MAE}$ boundary containment), **NOT** directional price prediction.
   - Across identical evaluation periods, the active system's directional accuracy was measured at exactly **$50.0\%$** (AUC $0.504$ — random coin flip) across $34$ resolved forecasts and $31$ independent 24h blocks.

---

## 2. Verified Architecture & End-to-End Data Flow

```
[Exchange Feeds]
  Coinbase L2 (Spot BTC-USD) ──> [CoinbaseL2OrderBook] ──> OFI, Microprice, Depth Imbalance
  Binance Futures (BTCUSDT)   ──> [BinanceDerivatives]  ──> Funding Rate, Open Interest
  Historical Corpus          ──> [data/raw/ohlcv.parquet] (40,902 bars, 2022-2026)
                                         │
                                         ▼
                             [Point-in-Time Features]
                               (pit_v1.0.0, causal)
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [Active Production System]                  [Research & Forecasting Ladder]
        Model: Ridge Excursion Core                 Baseline A: Zero-Drift (P50 = 0.0)
        Artifact: v3.0.0-excursion-ridge-conformal  Challenger C: LightGBM / Tree Quantiles
        Target: MFE24h & MAE24h Range Bounds        Challenger D: Hawkes LOB (5m Microstructure)
        Output: P10/P50/P90 Conformal Envelope                  │
                   │                                            ▼
                   │                              [Shadow-Mode Decision Engine]
                   ▼                                SHA-256 Commitments, 35/65 bps Hurdles
      [Production Research Gate]                                │
        BLOCKED_AUDIT_FAILURE (data/raw/iv7d.parquet missing)   ▼
        Zero Live Capital / Execution Hard-Blocked      [Read-Only Research API]
                   │                                    /api/research/results
                   ▼                                    Allowlist, Checksums, Conflict Flags
      [User Interface (web/app.js)]                             │
        3 Distinct Pillars: Market Monitor, Research Evidence,  ▼
        Forecast Lab (Explicitly Disclosing Blocked Status)     [Archived Research Reports]
```

### Active Model vs. Experimental / Research Models
- **Active Production Model:** `v3.0.0-excursion-ridge-conformal`. It produces a **symmetric volatility/excursion envelope** ($\text{MFE}_{24h}$ and $\text{MAE}_{24h}$), **NOT** directional trades. It is locked and gated.
- **Production Gate Status:** `BLOCKED_AUDIT_FAILURE` (`app.state.research_gate["status"] = "BLOCKED_AUDIT_FAILURE"`). The gate correctly fails closed because the raw Deribit IV file `data/raw/iv7d.parquet` is missing from the local filesystem.
- **Experimental Models:**
  - `Baseline A` (`NaiveBaselineForecaster`): Zero-drift reference model ($P_{50} = 0.0$, historical volatility quantiles).
  - `Challenger C` (`QuantileTreeChallengerForecaster`): Quantile tree regressor optimizing pinball loss for $P_{10}, P_{50}, P_{90}$.
  - `Hawkes Microstructure Model` (`models/checkpoints/`): 5-minute multivariate Hawkes intensity model for event-level order flow.

---

## 3. Disambiguation: What "70% Prediction Accuracy" Means

In quantitative finance, conflating different metrics is a primary source of investor ruin and methodological failure:

| Claimed / Target Metric | True Definition | BTCognitive Observed Value | Does It Support 70% Directional Edge? |
| :--- | :--- | :--- | :--- |
| **Conformal Risk-Envelope Coverage** | Fraction of price excursions remaining inside $P_{10}..P_{90}$ boundaries. | **`92.84%`** (`uncertainty-04`)<br>**`91.80%`** (`production_accuracy.csv`) | **NO.** A wide symmetric band contains 90%+ of price paths while providing zero directional alpha. |
| **Directional Accuracy (All Forecasts)** | Percentage of time $\text{sign}(\hat{y}) == \text{sign}(y_{t+H})$ on $100\%$ of bars. | **`50.40% - 53.30%`** (1h, 4h, 24h)<br>**`50.0%`** (`metric_reconciliation.csv`) | **NO.** Marginally above random coin flip; within statistical noise. |
| **Selective Directional Accuracy** | Percentage of time correct when model confidence exceeds a high threshold (e.g., top 10%). | **`57.05%`** (1H, top 10% confidence)<br>**`54.03%`** (24H, top 10% confidence) | **NO.** Reaches $\le 57\%$, decaying to $\le 54\%$ at longer horizons. |
| **Trading Win Rate** | Percentage of executed trades hitting Take-Profit before Stop-Loss. | **`47.13%`** (`Track V3 LightGBM`, $N=1,553$) | **NO.** Net return is $-0.5678R$ due to fees and stop-outs. |
| **Directional ROC AUC** | Area under the Receiver Operating Characteristic curve. | **`0.504 - 0.545`** across all horizons | **NO.** $0.50$ represents a pure random walk. $0.70$ accuracy requires $\text{AUC} \approx 0.75 - 0.80$. |

### Observed 70% vs. Dependable 70%
- **Observed 70% (Sample Artifact):** Can easily occur on a small sample (e.g., 7 wins out of 10 trades). However, the 95% Wilson confidence interval for $7/10$ is $[39.7\%, 89.2\%]$, which spans deep into negative-expectancy territory ($< 50\%$).
- **Dependable 70% (Statistical Reality):** To establish that true population accuracy is $\ge 70\%$ at the 95% confidence level ($p < 0.05$ against a $50\%$ null) on an untouched test set, one would need:
  $$N_{\text{eff}} \ge 185 \text{ independent events with zero overlap}$$
  where the model consistently scores $\ge 70\%$. In our 40,902-bar dataset ($N = 33,900+$ evaluations), the empirical upper bound of the 95% confidence interval is **$53.8\%$** for 1H and **$50.9\%$** for 24H.

---

## 4. Reproduced Baseline & Controlled Experiment Results

A controlled audit experiment was executed across the full historical dataset (`data/raw/ohlcv.parquet`, 40,902 hourly bars from 2022 to 2026) using 5-fold Purged Walk-Forward Cross-Validation with horizon-matched embargoes.

### Table 1: Multi-Horizon Directional Prediction Ladder (All Forecasts, 100% Coverage)

| Horizon | Model Architecture | Evaluated ($N$) | Effective $N_{\text{eff}}$ | Directional Accuracy | 95% Wilson CI | ROC AUC | Brier Score | Mean Net Return (BASE 35 bps) | Null Test ($H_0: p \ge 70\%$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1H** | Majority Class Baseline | 33,919 | 35,181.6 | **50.40%** | [49.9%, 50.9%] | 0.4973 | 0.2500 | -34.8 bps | $p < 10^{-10}$ |
| **1H** | Momentum / Persistence | 33,919 | 35,181.6 | **47.09%** | [46.6%, 47.6%] | 0.4708 | 0.5291 | -35.6 bps | $p < 10^{-10}$ |
| **1H** | Logistic Regression ($L_2$) | 33,919 | 35,181.6 | **52.74%** | [52.2%, 53.3%] | 0.5417 | 0.2488 | -35.1 bps | $p < 10^{-10}$ |
| **1H** | Random Forest | 33,919 | 35,181.6 | **53.25%** | [52.7%, 53.8%] | 0.5448 | 0.2485 | -34.9 bps | $p < 10^{-10}$ |
| **1H** | Gradient Boosting | 33,919 | 35,181.6 | **53.30%** | [52.8%, 53.8%] | 0.5435 | 0.2490 | -34.6 bps | $p < 10^{-10}$ |
| **4H** | Majority Class Baseline | 33,916 | 4,970.1 | **50.60%** | [50.1%, 51.1%] | 0.4963 | 0.2500 | -34.0 bps | $p < 10^{-10}$ |
| **4H** | Momentum / Persistence | 33,916 | 4,970.1 | **46.93%** | [46.4%, 47.5%] | 0.4691 | 0.5307 | -35.6 bps | $p < 10^{-10}$ |
| **4H** | Logistic Regression ($L_2$) | 33,916 | 4,970.1 | **52.96%** | [52.4%, 53.5%] | 0.5368 | 0.2493 | -35.4 bps | $p < 10^{-10}$ |
| **4H** | Random Forest | 33,916 | 4,970.1 | **52.64%** | [52.1%, 53.2%] | 0.5392 | 0.2490 | -35.3 bps | $p < 10^{-10}$ |
| **4H** | Gradient Boosting | 33,916 | 4,970.1 | **52.54%** | [52.0%, 53.1%] | 0.5329 | 0.2510 | -34.3 bps | $p < 10^{-10}$ |
| **24H** | Majority Class Baseline | 33,900 | 851.3 | **49.72%** | [49.2%, 50.3%] | 0.4925 | 0.2503 | -41.7 bps | $p < 10^{-10}$ |
| **24H** | Momentum / Persistence | 33,900 | 851.3 | **47.74%** | [47.2%, 48.3%] | 0.4765 | 0.5226 | -29.9 bps | $p < 10^{-10}$ |
| **24H** | Logistic Regression ($L_2$) | 33,900 | 851.3 | **50.49%** | [50.0%, 51.0%] | 0.5066 | 0.2525 | -42.9 bps | $p < 10^{-10}$ |
| **24H** | Random Forest | 33,900 | 851.3 | **50.53%** | [50.0%, 51.1%] | 0.5109 | 0.2544 | -42.8 bps | $p < 10^{-10}$ |
| **24H** | Gradient Boosting | 33,900 | 851.3 | **50.40%** | [49.9%, 50.9%] | 0.5066 | 0.2598 | -41.9 bps | $p < 10^{-10}$ |

### Table 2: Selective Prediction & Abstention Analysis (Gradient Boosting)

| Horizon | Confidence Threshold | Active Trades ($N$) | Empirical Coverage | Accuracy | 95% Wilson CI | Mean Net Return (BASE 35 bps) | Mean Net Return (CONSERVATIVE 65 bps) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1H** | Top 100% (All) | 33,919 | 100.0% | **53.30%** | [52.8%, 53.8%] | -34.6 bps | -64.6 bps |
| **1H** | Top 50% | 16,960 | 50.0% | **54.98%** | [54.2%, 55.7%] | -34.6 bps | -64.6 bps |
| **1H** | Top 25% | 8,482 | 25.0% | **55.87%** | [54.8%, 56.9%] | -33.9 bps | -63.9 bps |
| **1H** | Top 10% | 3,392 | 10.0% | **57.05%** | [55.4%, 58.7%] | -32.2 bps | -62.2 bps |
| **1H** | Top 5% | 1,696 | 5.0% | **56.19%** | [53.8%, 58.5%] | -32.9 bps | -62.9 bps |
| **4H** | Top 100% (All) | 33,916 | 100.0% | **52.54%** | [52.0%, 53.1%] | -34.3 bps | -64.3 bps |
| **4H** | Top 25% | 8,479 | 25.0% | **54.86%** | [53.8%, 55.9%] | -33.1 bps | -63.1 bps |
| **4H** | Top 10% | 3,394 | 10.0% | **53.03%** | [51.4%, 54.7%] | -35.7 bps | -65.7 bps |
| **24H** | Top 100% (All) | 33,900 | 100.0% | **50.40%** | [49.9%, 50.9%] | -41.9 bps | -71.9 bps |
| **24H** | Top 25% | 8,475 | 25.0% | **50.47%** | [49.4%, 51.5%] | -51.3 bps | -81.3 bps |
| **24H** | Top 10% | 3,411 | 10.1% | **54.03%** | [52.4%, 55.7%] | -37.7 bps | -67.7 bps |
| **24H** | Top 5% | 1,696 | 5.0% | **53.30%** | [50.9%, 55.7%] | -48.8 bps | -78.8 bps |

### Table 3: Breakdown Across Market Regimes (1H Horizon)

| Market Regime | Definition | Evaluated ($N$) | Majority Class Acc | Gradient Boosting Acc | 95% Wilson CI |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Trending Bull** | $SMA_{20} > SMA_{50}$ and $R_{24h} > 0$ | 13,775 | 48.83% | **54.12%** | [53.3%, 55.0%] |
| **Trending Bear** | $SMA_{20} < SMA_{50}$ and $R_{24h} < 0$ | 12,486 | 51.80% | **52.88%** | [52.0%, 53.8%] |
| **Ranging / Sideways** | Incongruent moving average and return signs | 7,658 | 50.93% | **52.51%** | [51.4%, 53.6%] |

---

## 5. Dedicated Data-Leakage & Correctness Audit

| Inspection Area | Findings & Implementation Evidence | Verdict | Severity |
| :--- | :--- | :--- | :---: |
| **Feature Lookahead** | Verified `features/build_features.py` and `engine/point_in_time_features.py`. Returns use strictly historical shifts (`shift(1)` for 1h, `shift(4)` for 4h). Moving averages, Wilder RSI, ATR, and volatilities use strictly backward rolling windows. Merges use `pd.merge_asof` matching on `available_time`. | **NO LEAKAGE CONFIRMED** | PASS |
| **Label Window Purging** | Verified `validation/purged_split.py`. The purge filter strictly evaluates $t_1 < \text{test\_start\_time}$ and adds an effective embargo window dynamically scaled to label horizons. | **NO LEAKAGE CONFIRMED** | PASS |
| **Scaling & Preprocessing** | Verified that normalization and imputers are wrapped in `sklearn.pipeline.Pipeline` or fitted inside fold training sets only. Zero test data informs feature scalers. | **NO LEAKAGE CONFIRMED** | PASS |
| **Intrabar Ambiguity** | Verified `labeling/targets.py` lines 156-159. When upper barrier and lower barrier are both touched within the same candle wick, the resolver conservatively triggers stop-loss first (`label = -1`). | **DEFECT PREVENTED** | PASS |
| **SQLite Concurrency & Schema** | Concurrency locks in `backtest/market_memory.py` resolved via `_db_lock`, WAL mode, and `busy_timeout=30000`. Column `expected_return_net_pct` properly migrated. | **RESOLVED & VERIFIED** | PASS |
| **Missing Production Input** | `research/verify_freeze_manifest.py` confirmed `data/raw/iv7d.parquet` is missing from disk. The production gate correctly fails closed (`BLOCKED_AUDIT_FAILURE`). | **GATE HONESTLY BLOCKED** | PASS |

---

## 6. Sourced Academic Literature Review

| Source Citation | Type | Asset / Frequency | Target / Horizon | Reported Metrics | Realistic Transaction Costs? | Transferability to BTCognitive |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Raffaelli, Cestari, Marazzina, Formentin (2026)**<br>*Decisions in Economics and Finance*<br>DOI: [10.1007/s10203-026-00570-z](https://doi.org/10.1007/s10203-026-00570-z) | Peer-reviewed | BTC/USD, BTC/USDT<br>Sub-second & Event-level LOB | Order-flow intensity, short-term price jump (sub-minute to 5m) | AUC $\approx 0.55 - 0.58$ for event-level jumps. Directional accuracy $\approx 53 - 55\%$. | Evaluated execution latency; friction erases low-frequency edge. | **Partially Transferable.** Demonstrates Hawkes intensity captures microstructural order clustering on 1m-5m horizons, but signal decays to pure noise by 1h/24h. Does NOT support 70% accuracy. |
| **Bysik & Ślepaczuk (2026 preprint / 2024)**<br>*arXiv:2406.00060*<br>[arXiv:2406.00060](https://arxiv.org/abs/2406.00060) | Preprint | BTC-USDT<br>Hourly (1h) | Hourly return sign, walk-forward trading performance | Out-of-sample directional accuracy $\approx 51.5\% - 53.8\%$. Gross returns positive; net returns negative. | **YES.** Detailed fee tiers (Binance VIP0/VIP1, 5-10 bps maker/taker + slippage). | **Directly Transferable.** Proves that statistical directional accuracy ($\approx 53\%$) cannot overcome exchange transaction costs in hourly walk-forward trading. 70% directional accuracy is completely absent. |
| **Hewamalage, Ackermann, Bergmeir (2023)**<br>*Data Mining and Knowledge Discovery*<br>DOI: [10.1007/s10618-022-00894-5](https://doi.org/10.1007/s10618-022-00894-5) | Peer-reviewed | Benchmark time-series datasets | Forecast evaluation pitfalls & best practices | Demonstrates how random K-fold CV leaks future temporal structure and creates spurious high scores. | Conceptual / Methodological | **Directly Transferable.** Mandates rolling-origin / purged walk-forward cross-validation, proper naive baselines, and dependence-corrected significance testing. |
| **Ariana, Mobarekeh, Seco (2024)**<br>*Knowledge-Based Systems*<br>DOI: [10.1016/j.knosys.2024.112477](https://doi.org/10.1016/j.knosys.2024.112477) | Peer-reviewed | Multi-asset synthetic & real financial series | Combinatorial Purged CV (CPCV) vs. Walk-Forward | Quantifies Probability of Backtest Overfitting (PBO). Shows walk-forward tests have high variance and false discovery risks. | Evaluates overfitting under market friction. | **Directly Transferable.** Requires Deflated Sharpe Ratio (DSR) and PBO controls before promoting model candidates to avoid mistaking backtest noise for generalization. |

---

## 7. Root-Cause Analysis: What Actually Limits Directional Accuracy

| Rank | Bottleneck Category | Empirical Evidence | Limiting Mechanism | Implementation Difficulty | Feasible Remedy |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | **Market Efficiency & Noise-to-Signal Ratio** | BTC 24h direction is a 50.0% coin flip (AUC 0.504). Hourly direction tops out at 53.3%. | Semi-strong market efficiency: All public technical indicators (RSI, MACD, Moving Averages) are continuously priced in by high-frequency arbitrageurs. Unconditional directional predictability is near zero. | Fundamental | **Pivot away from unconditional directional classification.** Focus on volatility range forecasting, conditional liquidity imbalances, and execution optimization where market signals persist. |
| **2** | **Exchange Transaction Friction vs. Gross Edge** | Net return is negative ($-34.6\text{ bps}$ BASE, $-64.6\text{ bps}$ CONSERVATIVE) across all horizons. | Binance/Coinbase round-trip fees ($10-30\text{ bps}$) plus bid-ask spread and slippage exceed the gross statistical edge ($\approx 5-15\text{ bps}$) of any hourly directional forecast. | Structural | **Implement strict economic hurdle filters ($E_{\text{min}} \ge 10\text{ bps}$ net)**. Abstain on trades where expected return does not exceed conservative transaction friction. |
| **3** | **Horizon Mismatch (Applying Microstructure to Macro Candles)** | Hawkes order-book intensity improves 5m MFE error by $1.4\text{ bps}$, but has zero predictive power for 24h candles. | Microstructure signals (OFI, depth imbalance, signed volume) have an information half-life of seconds to minutes. By 1 hour, order-book states have reset multiple times. | Architectural | **Align model family to horizon.** Use Hawkes/LOB only for execution timing and sub-minute execution; use macro/volatility models (HAR-RS-DOW, Ridge Conformal) for 24h risk envelopes. |
| **4** | **Label Ambiguity & Symmetric Noise** | CUSUM and triple-barrier touches often hit both boundaries or time out with near-zero returns. | Symmetric horizontal barriers in choppy markets generate 50/50 outcomes with high churn. | Methodological | **Use meta-labeling and asymmetric excursion targets** (separate sizing and probability from directional entry). |

---

## 8. 70% Accuracy Feasibility Assessment

### What Would Need to Be True for 70% Accuracy to Be Defensible?
For a directional accuracy claim of $\ge 70\%$ to be statistically and economically valid, the following conditions must hold simultaneously:

1. **Massive Information Asymmetry (Non-Public Flow):** The model would need access to proprietary, sub-millisecond private order flows, exchange internal liquidations, or dark-pool inventory that other institutional participants cannot observe. Public OHLCV candles and standard indicators cannot provide this edge.
2. **Extreme Sample Filtering (Ultra-Low Coverage):** If the model only predicts during extreme, once-a-month forced liquidation cascades, accuracy might transiently approach 65–70%. However:
   - In our empirical audit, filtering to the top 5% highest-confidence predictions only yielded **$56.19\%$** accuracy (1H).
   - A strategy predicting only $1\%$ of the time ($8$ times a year) cannot power an automated daily/hourly intelligence dashboard.
3. **Statistical Sample Size Verification:** To prove $\ge 70\%$ accuracy with 95% statistical confidence against a 50% null hypothesis:
   $$N_{\text{independent}} \ge 150 \text{ non-overlapping events with } \ge 75\% \text{ observed win rate}$$
   On BTC/USD, 150 independent 24-hour periods requires nearly half a year of continuous, untouched, out-of-sample forward tracking without a single regime-induced breakdown.

### Conclusion on 70% Target
**The 70% directional accuracy target is unachievable for standard unconditional 1h, 4h, or 24h BTC/USD price forecasting.** Any system claiming 70% directional accuracy on daily/hourly crypto price movements using public data is suffering from **data leakage, lookahead bias, backtest overfitting, or metric conflation** (confusing conformal range containment or trading win rate with directional accuracy).

---

## 9. Application & UI Audit

1. **Market Monitor (`/`):**
   - Correctly displays real-time spot price, order book depth, Order-Flow Imbalance (OFI), and freshness status backed by `CoinbaseL2OrderBook` and `BinanceDerivativesCollector`.
   - Clear distinction between spot BTC-USD and perpetual BTCUSDT.
2. **Research Results (`/research`):**
   - Successfully serves hash-verified archived research reports (`uncertainty-04`, `entry-tp-sl-v3`, `metric-reconciliation`, `production-health`) via `/api/research/results`.
   - Explicitly displays the `CONFLICT_REQUIRES_RECONCILIATION` flag explaining why 92.84% risk-envelope containment does not confer directional trading edge.
3. **Forecast Lab (`PredictionPanel`):**
   - Correctly renders the fail-closed banner: *"Production forecast unavailable: Frozen research inputs and evaluation provenance are not authenticated."*
   - Does not fabricate synthetic forecasts, fake probabilities, or misleading signals while production gates remain unverified.

---

## 10. Reproducibility & Environmental Provenance

- **Execution Command:** `python research/directional_accuracy_audit_experiment.py`
- **Output Artifacts:**
  - `experiments/results/directional_accuracy_audit/empirical_accuracy_audit_results.json`
  - `experiments/results/directional_accuracy_audit/empirical_accuracy_tables.md`
- **Environment:** Windows 11, Python 3.13.14, pandas 2.2.3, scikit-learn 1.6.1, scipy 1.15.1.
- **Git Commit:** `2eb78cd190962f8e9ff0d89e072406d95b46dcd1` (main branch).

---

## 11. Safety, Governance & Operational Confirmation

- **No Remote Deployment:** Zero cloud services (AWS, GCP, Netlify, Fly.io, Render) were configured or deployed.
- **Zero Live Execution Pathways:** Live-capital trading remains hard-blocked. All execution experiments are strictly offline simulations or shadow-mode SQLite records with SHA-256 commitments.
- **Zero Gate Tampering:** The production authorization gate (`BLOCKED_AUDIT_FAILURE`) was preserved intact. No hashes or manifests were rewritten to force verification to pass.

---

## 12. Prioritized Actionable Improvement Plan

| Priority | Finding | Evidence | Proposed Action | Validation Test | Expected Benefit | Risk / Effort |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **P0** | **Metric Conflation in Documentation** | Users and stakeholders confuse 92.84% conformal envelope coverage with 92.84% directional accuracy. | Update UI and reporting headers to strictly label `Conformal Risk Envelope Coverage (Symmetric Volatility Bounds)` and display `Directional Accuracy: 50.0% (No Measurable Directional Edge)`. | Verify `/api/research/results` returns explicit disambiguation flags. | Eliminates false expectations; establishes epistemic honesty. | Very Low effort / Zero risk |
| **P0** | **Missing Production Raw Parquet** | `verify_freeze_manifest.py` fails on missing `data/raw/iv7d.parquet`, keeping production gate blocked. | Document exact provenance of Deribit IV dataset or formalize replacement with verified exchange open interest/funding rates without rewriting historical frozen hashes. | Execute `verify_freeze_manifest.py` in audit mode. | Clear documentation of exact gate requirements for future activation. | Low effort / Zero risk |
| **P1** | **Cost-Aware Abstention Filter** | Unconditional directional models lose 32–65 bps per trade due to round-trip fees and spread. | Implement a strict economic hurdle gate in `engine/shadow_decision_engine.py` that abstains unless estimated expected return exceeds $2.0 \times \text{round-trip friction} + 10\text{ bps}$. | Run walk-forward simulation comparing unfiltered vs hurdle-filtered trade expectancy. | Prevents negative-expectancy trade generation in shadow mode. | Low effort / Low risk |
| **P1** | **Short-Horizon Microstructure Specialization** | Hawkes intensity and L2 Order-Flow Imbalance provide a measurable +1.4 to +4.8 bps reduction in 5-minute excursion error. | Restrict Hawkes/LOB feature pipelines strictly to sub-15-minute execution and horizon monitoring rather than daily candles. | Deterministic regression test in `tests/test_market_data_feed.py`. | Captures genuine event-time order book information where signal-to-noise ratio is highest. | Medium effort / Low risk |
| **P2** | **Conformal Asymmetric Volatility Calibration** | Realized volatility is predictable ($R^2 \approx 14\%$, QLIKE $0.1930$), but upside vs downside excursions have asymmetric tails. | Upgrade `engine/uncertainty_calibration.py` to support separate upper/lower pinball loss quantile regressors conditioned on prevailing volatility regime. | Conformal coverage evaluation across high-volatility vs low-volatility test partitions. | Tightens interval width while maintaining $\ge 90\%$ tail containment. | Medium effort / Medium risk |
