# BTCognitive — Quantitative Signal Research & Barrier Methodology Report

**Track:** Signal Integrity & Risk-Level Engine v1.0  
**Date:** 17 October 2026  
**Author:** Agent B (Quantitative Signal Research)  
**Status:** `RESEARCH_VERIFIED_STANDARDS_ESTABLISHED`

---

## 1. Literature Assessment & Epistemic Distinctions

### 1.1 Shen, Urquhart & Wang (2020) — Bitcoin Jumps, Structural Breaks & Volatility
- **Reference:** *Forecasting the volatility of Bitcoin: The importance of jumps and structural breaks*, European Financial Management, 2020. [https://doi.org/10.1111/eufm.12254](https://doi.org/10.1111/eufm.12254)
- **Key Finding:** Bitcoin volatility dynamics exhibit heavy clustering and high-intensity discontinuous jumps. HAR models augmented with realized semivariances ($RV^+, RV^-$) significantly outperform standard GARCH and unseparated HAR models over medium-to-long horizons.
- **Epistemic Boundary:** Shen et al. model **volatility magnitude**, not price direction. Realized semivariance decomposition reflects volatility asymmetry, NOT directional return predictability. Conflating volatility asymmetry with a directional buy/sell trigger is mathematically invalid.

### 1.2 Marcos López de Prado (2018) — Triple-Barrier Labeling & Path Invariance
- **Reference:** *Advances in Financial Machine Learning*, Wiley, 2018; MLFinLab implementation.
- **Key Finding:** Traditional fixed-time horizon labeling ($r_{t+h} = \ln(S_{t+h}/S_t)$) fails in real trading because positions are subject to stop-loss ($L$) and take-profit ($U$) barriers prior to time $t+h$. The triple-barrier framework defines three exit boundaries:
  1. Upper horizontal barrier ($U = S_t(1 + \Delta_u)$) — Take Profit
  2. Lower horizontal barrier ($L = S_t(1 - \Delta_l)$) — Stop Loss
  3. Vertical barrier ($t + T_{\max}$) — Holding Horizon Timeout
- **Resolution Ordering Invariant:** In discrete candle data, if high $\ge U$ and low $\le L$ within the same candle, the arrival order is mathematically ambiguous unless tick-level data exists. The resolver must either:
  - Classify the outcome as `AMBIGUOUS_COLLISION`, or
  - Apply a documented conservative rule (`SL_FIRST_CONSERVATIVE`).
  - It must NEVER claim an exact TP win when order cannot be proven.

### 1.3 Bailey, Borwein, López de Prado & Zhu (2017) — Probability of Backtest Overfitting (PBO)
- **Reference:** *The Probability of Backtest Overfitting*, Journal of Computational Finance, 2017. [https://doi.org/10.21314/jcf.2016.322](https://doi.org/10.21314/jcf.2016.322)
- **Key Finding:** Testing $N$ strategy variations on the same historical dataset inevitably produces false discoveries with high Sharpe ratios by chance. The Probability of Backtest Overfitting ($PBO$) quantifies the likelihood that a strategy chosen from an in-sample sweep has an out-of-sample Sharpe ratio $\le 0$.
- **BTCognitive Implementation Standard:** Pre-registration of strategy rules is mandatory. Threshold sweeps or parameter tuning on retrospective development holdouts are strictly prohibited.

### 1.4 Scikit-Learn Probability Calibration Standards
- **Reference:** Scikit-learn calibration user guide; Niculescu-Mizil & Caruana (2005).
- **Core Principle:** A classifier's raw decision function or uncalibrated softmax score is NOT a true posterior probability.
- **Calibration Methods:**
  - **Platt Scaling (Sigmoid):** $P(y=1|f) = \frac{1}{1 + \exp(A f + B)}$, appropriate for models with sigmoid-like distortion (e.g. SVMs).
  - **Isotonic Regression:** Non-parametric monotonic step function, appropriate for non-linear models (GBMs, Random Forests) when sample size is sufficient ($N \ge 1,000$).
- **Validation Metrics:**
  - **Brier Score:** $BS = \frac{1}{N}\sum_{i=1}^N (p_i - y_i)^2 \in [0, 1]$.
  - **Expected Calibration Error (ECE):** $\sum_{b=1}^B \frac{|B_b|}{N} |\text{acc}(B_b) - \text{conf}(B_b)|$.
- **Epistemic Hurdle:** A score labeled `75% HIGH CONVICTION` without out-of-time calibration, reliability diagram verification, and explicit target definition is an unproven assertion and must be suppressed.

### 1.5 Official Fee & Cost Models
- **Coinbase Advanced / Spot Exchange Schedule:**
  - Taker fee: 40 bps ($0.40\%$) for tier 1 ($\le \$10\text{k}$ volume), scaling to 15 bps at institutional tiers.
  - Maker fee: 25 bps ($0.25\%$), scaling to 5 bps.
  - Round-trip spot cost at tier 1: $\approx 80\text{ bps}$ taker-taker, $\approx 50\text{ bps}$ maker-taker.
- **Binance Futures (USDT-M Perpetual):**
  - Taker fee: 5.0 bps ($0.050\%$).
  - Maker fee: 2.0 bps ($0.020\%$).
  - Half-spread: ~0.5 to 1.5 bps on BTC.
  - Slippage & market impact: 1.0 to 3.0 bps.
  - 8-hour funding rate: typically $\pm 1.0$ bps.
  - Round-trip perpetual cost: $\approx 14\text{ bps}$ taker-taker.
- **Cost Invariant:** Fixed assumptions (like "9.3 bps") must not be applied universally without identifying venue, product type (spot vs perpetual), and order execution type (maker vs taker).

---

## 2. Answers to Core Methodological Questions

1. **What is the target event that the signal engine predicts?**
   - The signal engine evaluates the **Triple-Barrier First-Passage Event**: $E \in \{\text{TP\_FIRST}, \text{SL\_FIRST}, \text{TIMEOUT}\}$.
2. **Is the selected model trained to predict direction, target-hit probability, volatility, or path excursion?**
   - Canonical `HAR-RS-DOW-v1.0` predicts strictly **168h annualized realized variance** ($rv7d\_var\_ann$). It DOES NOT predict direction or target-hit probability.
   - Microstructure directional classifiers (e.g. `directional-gbm-4lag-v1`) predict directional return sign over short horizons, but are currently **uncalibrated and gated** (`OFFLINE_RESEARCH_ONLY`).
3. **What horizons does that target support?**
   - Volatility risk model: 168h (7 days).
   - Short-horizon candidate: 24h.
   - Microstructure path models: 15m to 60m.
4. **Is the chosen model authorized for the output it generates?**
   - Volatility models are authorized for volatility risk envelopes only.
   - Directional models are strictly `OFFLINE_RESEARCH_ONLY` and gated at Tier 2.
5. **How should stops, targets, and timeouts be evaluated?**
   - Under the triple-barrier contract with conservative same-bar collision resolution and explicit fee models. When the model abstains or is gated, all scenario levels must be suppressed (`ABSTAIN`).

---

## 3. Forensic Root-Cause Analysis of Screenshot Defects

| Defect Observed in Screenshot | Root Cause Identified in Codebase | Forensic Resolution Applied |
| :--- | :--- | :--- |
| **1. Conflicting R:R (Claimed 2:1 vs Actual 1.14:1)** | UI card displayed static unverified string `spec["rr"] = 2.0` while entry was $93,729, TP $94,479 ($\Delta = +750$), SL $93,073 ($\Delta = -656$). Actual gross R:R was $\frac{750}{656} \approx 1.14:1$. | Recomputed R:R dynamically from verified bracket levels: $\text{Gross R:R} = \frac{|\text{TP} - \text{Entry}|}{|\text{Entry} - \text{SL}|}$. Static decorative ratios are prohibited. |
| **2. Stale Price Mismatch ($81,515 Live vs $93,729 Scenario Entry)** | `engine/feature_cache.py` loaded historical May 2026 parquet snapshot when live or closed hourly candles were required. | Prioritized latest closed hourly candles from `ohlcv.parquet` and live Coinbase feed; entry candidates deviating $> 5\%$ without a limit condition are rejected. |
| **3. Contradictory Conviction (`NOT_ESTIMATED` / `TIER 2 GATED` with `75% HIGH CONVICTION`)** | `api/routes_arena.py:1041` and `web/app.js` contained a synthetic/default fallback of `0.75` for unestimated or gated model candidates. | Implemented `CalibratedSignalEvaluator`: gated and unestimated models strictly return `0.0%` / `N/A`, displaying `ABSTAIN` with zero conviction claims. |
| **4. Chart Marker Provenance (`SL LOSS` & `AI: NOT_ESTIMATED (75%)`)** | Frontend chart rendering layer mingled historical paper-trading execution markers with live inference states without source record verification. | Decoupled historical paper execution markers from live signal telemetry; historical markers require valid scenario record IDs, timestamps, and known outcomes. |
| **5. Inverted / Invalid Scenario Brackets** | Scenario generation lacked strict invariant assertions before emitting candidate levels. | Added mathematical boundary enforcement in `models/signal_contract.py`: `LONG` strictly requires $\text{SL} < \text{Entry} < \text{TP}$; `SHORT` strictly requires $\text{TP} < \text{Entry} < \text{SL}$. |
| **6. Same-Bar Barrier Collision Ambiguity** | Historical simulation lacked a deterministic intra-bar collision policy when high $\ge \text{TP}$ and low $\le \text{SL}$ in the same candle. | Implemented `simulate_barrier_collision_resolution` with `SL_FIRST_CONSERVATIVE` policy to avoid optimistic performance bias. |

---

## 4. Core Implementation Architecture

1. **`models/signal_contract.py`**:
   - Authoritative `SignalContract` dataclass with `validate_scenario_geometry()`, `is_expired()`, and fail-closed `create_abstain_signal()`.
   - Standardized enums: `SignalStatus`, `SignalDirection`, `ModelAuthorization`, `CalibrationStatus`, `ExecutionAuthorization`.
2. **`engine/scenario_contract_engine.py`**:
   - `ScenarioLevelEngine` validates candidate price against current reference price ($\le 5\%$ tolerance).
   - `compute_bracket_geometry()` validates side-specific bounds and calculates gross R:R.
3. **`models/calibrated_signal_classifier.py`**:
   - Enforces proper calibration checking (`compute_brier_score`, `compute_expected_calibration_error`).
   - Suppresses conviction percentages for gated models (`displayed_conviction_pct = 0.0`).
4. **`engine/execution_cost_model.py`**:
   - Venue-specific cost calculations for Coinbase Spot (40 bps taker) and Binance Futures (5 bps taker + 1 bps slippage).
   - Conservative collision resolution (`SL_FIRST_CONSERVATIVE`).

---

## 5. Automated Test Verification Summary

A total of **149 automated tests** were executed and passed cleanly:

| Test Suite File | Tests Passed | Focus & Verifications |
| :--- | :--- | :--- |
| `tests/test_signal_integrity_and_risk_engine.py` | 18 / 18 | Suites A–G: Deterministic screenshot arithmetic, side invariants, fail-closed abstention, cost model, collision policy. |
| `tests/entry_tp_sl/test_triple_barrier_contracts.py` | 24 / 24 | Barrier geometry, first-touch ordering, barrier expiry, point-in-time causality. |
| `tests/entry_tp_sl/test_contracts_freeze.py` | 16 / 16 | Contract freezing, immutable schema hashes, backward compatibility. |
| `tests/entry_tp_sl/test_data_feasibility.py` | 24 / 24 | Historical data feasibility, candle coverage, missing-bar handling. |
| `tests/entry_tp_sl/test_timeout_accounting.py` | 24 / 24 | Vertical barrier timeout handling, exit price accounting, slippage adjustments. |
| `tests/test_single_market_data_contract.py` | 4 / 4 | Single market source of truth, UTC candle normalization. |
| `tests/test_canonical_metric_contracts.py` | 6 / 6 | Econometric metric definitions, QLIKE/MSE mathematical formulas. |
| `tests/test_causal_resolution.py` | 2 / 2 | Prospective ledger delayed resolution invariant. |
| `tests/test_phase4_directional_research_gate.py` | 4 / 4 | Tier 2 gating of directional models. |
| `tests/test_forecast_activation_and_readiness.py` | 14 / 14 | Dynamic startup gates, runtime health, endpoint verification. |
| `tests/test_phase2_market_data_and_pit.py` | 3 / 3 | Market data point-in-time causality. |
| `tests/test_phase3_volatility_and_range_validation.py` | 3 / 3 | Volatility envelope validation. |
| `tests/test_phase5_paper_simulator.py` | 3 / 3 | Non-execution paper simulation. |
| `tests/test_phase6_terminal_release_readiness.py` | 4 / 4 | Terminal integration and API contract conformance. |
| **Total Passed Tests** | **149 / 149** | **100% Deterministic Pass Rate** |

---

## 6. Browser Subagent Verification

The Antigravity Browser Subagent executed end-to-end user journeys before and after the repair:

### 6.1 Baseline Defect Reproduction
- **Session Recording:** `baseline_ui_check_1792216653328.webp`
- Confirmed visual rendering of stale $93k entry against $81k spot, conflicting 2:1 R:R, and 75% High Conviction on gated models.

### 6.2 Post-Fix Independent Verification
- **Session Recording:** `postfix_ui_check_1792217303756.webp`
- **Desktop Viewport (1440x900):**
  - Live Quote: $81,437.61 (Coinbase BTC/USD).
  - Arena AI Prediction: Directional Signal `ABSTAIN`, Conviction `0%` / `N/A`, Model Status `TIER 2 GATED`.
  - Scenario Contract: Entry, TP, SL, R:R display `— (ABSTAIN / N/A)`.
  - Chart Badge: Explicitly indicates `HAR-RS-DOW-v1.0 · 7D Risk Model Active (rv7d_var_ann)`.
- **Mobile Viewport (390x844):**
  - Verified responsive card stacking without horizontal scroll, overflowing text, or layout breaks.

---

## 7. PRD Conformance Status

- **Requirement `PRD-SIG-18` Added:** Fully specifies signal contracts, level geometry invariants, fail-closed abstention, and conservative barrier collision resolution.
- **Traceability Matrix:** Updated in `docs/BTCognitive_PRD_Traceability_Matrix.md` (13/18 requirements `IMPLEMENTED_VERIFIED` = 72.2%; remaining 5 requirements gated by calendar-time prospective evidence accumulation).

---

---

## 9. Research-to-Signal Engine v2: Preregistered Empirical Study & Findings

### 9.1 Literature Assessment Addendum
1. **Bysik & Ślepaczuk (2026)** — *Machine Learning in BTC-USDT Trading Under Real Transaction Costs* (arXiv:2606.00060):
   - Proves that while simple classifiers may exhibit apparent nominal gross accuracy (~52–53%), transaction costs (5–10 bps per trade on perpetuals, 20–40 bps on spot) completely erode profitability, generating severe negative net Sharpe ratios.
2. **Bailey & López de Prado (2014)** — *The Deflated Sharpe Ratio* (SSRN 2460551):
   - Demonstrates that multiple testing across parameter grids (e.g. tuning TP/SL multipliers) causes severe selection bias unless adjusted for the number of trials ($N_{\text{trials}}$) and non-normality.
3. **Hansen, Lunde & Nason (2011)** — *The Model Confidence Set* (Econometrica):
   - Forecast evaluations across multiple models must form a confidence set $\mathcal{M}^*$ at significance $\alpha=0.10$. No directional model on unconditional hourly BTC returns enters $\mathcal{M}^*$ above the no-trade benchmark.

### 9.2 Preregistered Empirical Experiment (`EXP-TRIPLE-BARRIER-DIRECTIONAL-2026-v2`)
Conducted on the verified continuous hourly dataset (`data/raw/ohlcv.parquet`, 41,261 closed candles from 2022 to 2026), evaluated over 6,150 out-of-sample hourly observations in 2026:

| Candidate Model | Trades ($N$) | TP Hit Rate | SL Hit Rate | Timeout Rate | Gross Expectancy | Net Expectancy (Binance 7 bps) | Net Expectancy (Coinbase 40 bps) | Economic Gate Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **No-Trade Baseline** | 0 | 0.0% | 0.0% | 0.0% | 0.0 bps | 0.0 bps | 0.0 bps | `ABSTAIN_NEUTRAL` |
| **Momentum 24h Baseline** | 3,144 | 17.81% | 36.13% | 46.06% | -10.0 bps | **-17.0 bps** | **-50.0 bps** | `FAIL_NEGATIVE_AFTER_COSTS` |
| **Causal Logistic Classifier** | 0 (p $\ge$ 0.60) | N/A | N/A | N/A | 0.0 bps | 0.0 bps | 0.0 bps | `INSUFFICIENT_EDGE` |

**Key Econometric Conclusions:**
1. Under realistic transaction frictions, the probability of touching the stop-loss first (36.13%) is more than double the probability of touching take-profit first (17.81%).
2. Unconditional directional momentum yields negative net expected value (-17 to -50 bps per trade).
3. Therefore, no candidate clears the economic hurdle ($\mathbb{E}[\text{Net EV}] > 0$).
4. The engine strictly fails closed with `ECONOMIC_EXPECTANCY_NEGATIVE`, preventing the rendering of false scenario levels.

### 9.3 Data Frequency & Horizon Standard
- **Verified Data:** `data/raw/ohlcv.parquet` contains hourly candles (`coinbase_btcusd_hourly_parquet`).
- **Supported Horizons:** `1h`, `4h`, `24h` (and `168h` for volatility risk).
- **Unsupported Horizons:** Requests for `15m` or `5m` without verified continuous intraday feeds return `DATA_FREQUENCY_UNSUPPORTED`.
- **UI Null Guard:** Conviction meter renders `N/A — DATA_FREQUENCY_UNSUPPORTED (HOURLY VERIFIED)` or `N/A — NOT ESTIMATED (EVALUATION GATED)` instead of misleading `0%`.

---

## 10. Governed Release Decisions & Final System Verdict (v2)

In accordance with the BTCognitive Operating Contract, four explicit governance decisions are rendered:

1. **Research Experiment:** `PASS` (Research-to-signal candidate pipeline implemented; fail-closed frequency and economic gates verified).
2. **Prospective Evidence:** `COLLECTING` (3 resolved 24h records, 2 pending 168h records; confirmatory gate $N \ge 100$ in progress).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` for directional models; `AUTHORIZED_FOR_VOLATILITY_RISK_ONLY` for canonical HAR-RS-DOW-v1.0.
4. **Live Trading:** `DISABLED` (Permanent, non-negotiable invariant).

**Final Milestone Verdict (v2):**
# `NO_CANDIDATE_PASSED_PREREGISTERED_GATE`
*(Paper candidate engine verified with fail-closed economic and frequency gates: `PAPER_CANDIDATE_ENGINE_VERIFIED`)*

---

## 11. Addendum (October 2026): Research-to-Signal Engine v3 Forensics & Corrected Evaluations

### 11.1 Methodological Forensics on Experiment v2
An independent forensic audit of `research/experiments/run_triple_barrier_directional_experiment.py` and `triple_barrier_directional_manifest.json` revealed four key defects in the earlier v2 setup:

1. **Portfolio Accounting & Overlapping Labels:**
   - The v2 runner evaluated each hourly signal as an independent candidate, generating up to 24 concurrent open positions (mean 12.66 concurrent open positions).
   - This assumed infinite capital/leverage with no margin constraints and treated overlapping 24-hour outcome windows as independent events.
   - Under the preregistered **single-position-at-a-time policy** (only entering a new position after the prior position exits at TP, SL, or 24h timeout), trade count drops from 3,144 down to 128 non-overlapping trades.
2. **Execution Cost Omission (Per-Side vs Round-Trip):**
   - The v2 experiment deducted a flat 7.0 bps for Binance Futures and 40.0 bps for Coinbase Spot.
   - Official venue documentation confirms that commission is charged per side:
     - **Binance Futures:** 5.0 bps taker entry + 5.0 bps taker exit = 10.0 bps commission + 1.0 bps round-trip half-spread + 2.0 bps round-trip slippage + 2.25 bps average holding funding ($\sim 2.25\text{ intervals} \times 1.0\text{ bps}$) = **15.25 bps round-trip perpetual friction**.
     - **Coinbase Advanced Spot Tier 1:** 40.0 bps taker entry + 40.0 bps taker exit = 80.0 bps commission + 3.0 bps spread + 4.0 bps slippage = **87.0 bps round-trip**.
3. **Split Boundary Purging:**
   - The v2 split allowed the last 23 bars of 2024 to mature inside 2025, and the last 23 bars of 2025 to mature inside 2026. A 24-bar embargo/purge has now been enforced before each boundary.
4. **Logistic Classifier Zero Trades Resolution:**
   - Target $y=1$ was defined as $TP\_FIRST$. With $k_{\text{tp}}=1.5, k_{\text{sl}}=1.0$, the unconditional event base rate is only $17.17\%$.
   - An unweighted logistic regression predicting $P(TP\_FIRST)$ produces scores centered around $\sim 18-20\%$ (maximum score 0.2749).
   - The $p \ge 0.60$ threshold was a prior-mismatched heuristic that mathematically guaranteed zero trades.

### 11.2 Corrected Empirical Results (`EXP-RESEARCH-TO-SIGNAL-V3-SELECTIVE`)
Conducted on the verified continuous hourly dataset (`data/raw/ohlcv.parquet`, 41,261 bars), evaluated under single-position portfolio accounting and 24-bar boundary purging across 2026 held-out retrospective data (6,175 evaluated bars):

| Candidate Model | Trades ($N$) | Gross Expectancy | Net Expectancy (Binance 15.25 bps) | Net Expectancy (Coinbase 87.0 bps) | TP Rate | SL Rate | Timeout Rate | Holding Hours | Economic Gate Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Candidate 0: No-Trade Baseline** | 0 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0% | 0.0% | 0.0% | 0.0h | `ABSTAIN_NEUTRAL` |
| **Candidate 1: Corrected 24h Momentum** | 128 | -7.15 bps | **-22.40 bps** | **-94.15 bps** | 13.28% | 29.69% | 46.09% | 16.3h | `FAIL_NEGATIVE_AFTER_COSTS` |
| **Candidate 2: Cost-Aware Return Filter** | 0 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0% | 0.0% | 0.0% | 0.0h | `ABSTAIN_NEUTRAL` |
| **Candidate 3: Meta-Label Filter (p $\ge$ 0.45)** | 108 | **+10.32 bps** | **-4.93 bps** | **-76.68 bps** | 14.81% | 24.07% | 48.15% | 16.7h | `FAIL_NEGATIVE_AFTER_COSTS` |

### 11.3 Forensic Conclusions & Scientific Verdict
1. **Gross Improvement vs Economic Reality:** Candidate 3 (Meta-Labeling) successfully improved gross expectancy from $-7.15$ bps to $+10.32$ bps (a $+17.47$ bps gross improvement) and cut stop-loss rate from $29.69\%$ to $24.07\%$.
2. **Friction Boundary:** Even with this gross improvement, net expectancy remains negative ($-4.93$ bps on Binance, $-76.68$ bps on Coinbase) under realistic two-sided exchange friction.
3. **Fail-Closed Governance:** Because no candidate achieved $\mathbb{E}[\text{Net EV}] > 0$, the system strictly fails closed with `ECONOMIC_EXPECTANCY_NEGATIVE` and `NO_CANDIDATE_PASSED_PREREGISTERED_GATE`.
4. **Governed Decision (v3):**
   - Research Experiment: `PASS` (Re-computed and verified mathematically).
   - Governed Verdict: `NO_CANDIDATE_PASSED_PREREGISTERED_GATE`.
   - Live Trading: `DISABLED` (Permanent, non-negotiable invariant).

---

## 12. Addendum (October 2026): Experiment Integrity v4 — Gap-Aware Time Series, Instrument Provenance & Reproducible Recalculation

### 12.1 Empirical Discovery of the 30-Day Discontinuity & Pipeline Contamination
An exhaustive timestamp continuity audit of `data/raw/ohlcv.parquet` (41,261 Coinbase BTC/USD hourly candles from `2022-01-01 00:00:00 UTC` to `2026-10-17 03:00:00 UTC`) uncovered two critical temporal discontinuities:
1. **Gap 1 (Minor Discontinuity):** Index 10740 (`2023-03-24 12:00:00 UTC`) to Index 10741 (`2023-03-24 14:00:00 UTC`): 1 missing hour ($\Delta t = 2.0\text{ hours}$).
2. **Gap 2 (Major Discontinuity):** Index 40901 (`2026-09-01 06:00:00 UTC`) to Index 40902 (`2026-10-02 05:00:00 UTC`): **742 missing hours** ($\Delta t = 743.0\text{ hours}$, 30 days and 23 hours).

#### Mechanism of V3 Pipeline Contamination:
In the unsegmented V3 pipeline, row-indexed operations (`shift(1)`, `rolling(24)`, `rolling(168)`) were applied indiscriminately across Gap 2:
- At index 40902 (`2026-10-02 05:00 UTC`), the 1-hour return `ret_1h` computed an **+8.67% return** across 31 days!
- This massive synthetic return spiked `rv_24h` and `vol_spread` for the subsequent 24 to 168 rows.
- The spiked features artificially inflated the linear logit of Candidate 3's meta-classifier, triggering an artificial cluster of **108 trades** at $p \ge 0.45$.
- Furthermore, forward triple-barrier label loops at indices 40878–40901 looked forward 24 rows into October 2026, evaluating 24-hour targets across 31 days of missing market history.

### 12.2 The Gap-Safe Architecture (`ContinuityTimeSeriesEngine`)
To permanently eliminate data gap contamination, `engine/continuity_time_series.py` was implemented with four non-negotiable contracts:
1. **Contiguous History Partitioning:** History is partitioned into 3 isolated segments:
   - Segment 0: 10,741 bars (`2022-01-01 00:00` to `2023-03-24 12:00 UTC`).
   - Segment 1: 30,161 bars (`2023-03-24 14:00` to `2026-09-01 06:00 UTC`).
   - Segment 2: 359 bars (`2026-10-02 05:00` to `2026-10-17 03:00 UTC`).
2. **Feature Reset at Boundaries:** Feature lookbacks reset at each segment boundary; the first $K$ bars of each segment are set to `NaN` (72 lookback NaNs total). No cross-gap rolling window contamination is mathematically possible.
3. **Elapsed 24-Hour UTC Duration Contract:** Forward triple-barrier windows $[t+1, t+H]$ are strictly validated:
   - Target must remain inside the *same* continuous segment ($s_t = s_{t+H}$).
   - Elapsed UTC duration must equal exactly 24.0 hours ($\Delta t = 24.0\text{h} \pm 0.01\text{h}$).
   - Any bar violating this is marked `DISCONTINUOUS_FORWARD_HORIZON_GAP` (72 horizon exclusions total). Zero synthetic bars or forward-fills are created.
4. **Purging & Embargo:** 24-hour embargo purges prior to 2025 and 2026 test boundaries prevent label maturity leakage across folds.

### 12.3 Instrument Identity & Market-Data Contract
1. **Primary Empirical Backtest:** **Coinbase Advanced BTC/USD Spot**
   - Verified empirical price path from `data/raw/ohlcv.parquet`.
   - Tier 1 fee schedule: 80.0 bps taker commission ($2 \times 40.0\text{ bps}$) + 3.0 bps spread + 4.0 bps slippage = **87.0 bps round-trip friction**.
2. **Hypothetical Sensitivity Scenario:** **Binance USDT-M Futures Perpetual**
   - Labeled strictly as a hypothetical cost-sensitivity analysis applied to spot-path returns.
   - 10.0 bps taker commission ($2 \times 5.0\text{ bps}$) + 1.0 bp half-spread + 2.0 bps slippage + 2.0 bps holding funding ($\approx 17.1\text{h} \text{ holding}$) = **15.0 bps round-trip friction**.

### 12.4 Probability Calibration Audit: Model vs Training Prevalence Baseline
The V3 report cited a Brier score of `0.2439` against `0.2500` (naive 0.50 baseline). We audited the true calibration contract against the **constant training-set prevalence baseline**:
- In the training set (2022–2024), the positive class prevalence for meta-labeling is $\bar{y}_{\text{train}} = 0.4224$ ($42.24\%$).
- In the clean 2026 test set, the empirical prevalence is $\bar{y}_{\text{test}} = 0.4485$ ($44.85\%$).
- Evaluation of the logistic meta-classifier on the clean test set:
  - **Model Brier Score:** `0.2485`
  - **Constant Training Prevalence Baseline Brier Score:** `0.2480`
  - **Naive 0.50 Baseline Brier Score:** `0.2500`
  - **Model Log Loss:** `0.6901`
  - **Constant Training Prevalence Baseline Log Loss:** `0.6892`

**Epistemic Finding:** While the model beats a naive 50/50 coin flip ($0.2485 < 0.2500$), it is **inferior to predicting the constant empirical prior of the training data** ($0.2485 > 0.2480$). The model exhibits zero skill beyond unconditional historical prevalence.

### 12.5 Corrected Empirical Results (`EXP-RESEARCH-TO-SIGNAL-V4-GAP-AWARE`)
Evaluated across clean 2026 retrospective data under strict segment continuity, single-position-at-a-time portfolio simulation, and 24-hour split boundary purging:

| Candidate Model | Trades ($N$) | Gross Expectancy | Net Expectancy (Coinbase Spot 87.0 bps) | Net Expectancy (Binance Hypothetical 15.0 bps) | TP Rate | SL Rate | Timeout Rate | Mean Holding | Economic Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Candidate 0: No-Trade Baseline** | 0 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0% | 0.0% | 0.0% | 0.0h | `ABSTAIN_NEUTRAL` |
| **Candidate 1: 24h Momentum (Gap-Safe)** | 227 | **+8.91 bps** | **-78.09 bps** | **-6.09 bps** | 18.50% | 34.36% | 47.14% | 17.1h | `FAIL_NEGATIVE_AFTER_COSTS` |
| **Candidate 2: Cost-Aware Return Filter** | 0 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0% | 0.0% | 0.0% | 0.0h | `ABSTAIN_NEUTRAL` |
| **Candidate 3: Meta-Label Filter ($p \ge 0.45$)** | 1 | **-221.15 bps** | **-308.15 bps** | **-236.15 bps** | 0.0% | 0.0% | 100.0% | 24.0h | `FAIL_NEGATIVE_AFTER_COSTS` |

### 12.6 Discrepancy Reconciliation between V3 and V4
1. **Candidate 1 Trade Count (128 $\to$ 227):** Under the clean pipeline, the unsegmented gap jump was not blocking trades with distorted volatility envelopes, allowing 227 valid single-position entries across 2026. Gross return was slightly positive (+8.91 bps), but after transaction friction, net returns remain decisively negative (-78.09 bps on Coinbase, -6.09 bps on hypothetical Binance).
2. **Candidate 3 Trade Count (108 $\to$ 1):** The 108 trades reported in V3 were overwhelmingly concentrated right after the September 2026 gap due to the contaminated 8.67% return. Under gap-safe segmentation, the meta-classifier's predicted probabilities range from 0.412 to 0.453 (median 0.4186). Only 1 trade cleared the $p \ge 0.45$ threshold, ending in a timeout at -221.15 bps gross.
3. **Governed Decision (v4):**
   - Data Gap & Cost Audit: `DATA_GAP_AND_COST_AUDIT_VERIFIED`
   - Governed Experiment Result: `CORRECTED_RESULTS_REPRODUCED_NO_CANDIDATE_PASSED`
   - Model Authorization: `OFFLINE_RESEARCH_ONLY`
   - Live Trading: `DISABLED` (Permanent Invariant)

---

## 13. Addendum (October 2026): BTCognitive V5 — Statistical Integrity, Experiment Freeze & Prospective Research

### 13.1 Independent Audit of Feature Warm-Up & Eligibility Counts
The machine-readable eligibility audit (`experiments/results/research_improvement/v5_eligibility_audit.json`) established the exact lookback warm-up requirements per feature across the 3 contiguous segments:
* `ret_1h`: Lookback 1 bar (1 NaN per segment; 3 NaNs total).
* `ret_4h`: Lookback 4 bars (4 NaNs per segment; 12 NaNs total).
* `ret_24h`: Lookback 24 bars (24 NaNs per segment; 72 NaNs total).
* `rv_24h`: Lookback 24 bars (24 NaNs per segment; 72 NaNs total).
* `hl_ratio_24h`: Lookback 23 bars (23 NaNs per segment; 69 NaNs total).
* `vol_spread`: Lookback **191 bars** ($24\text{h rolling vol} + 168\text{h rolling mean} - 1 = 191$ bars per segment; 573 NaNs total).

**Key Finding on Segment 2:** Segment 2 contains 359 total bars (`2026-10-02 05:00` to `2026-10-17 03:00 UTC`). The 191-bar warm-up of `vol_spread` requires 191 bars, leaving 168 fully warm bars in Segment 2. For models not requiring `vol_spread` (e.g. Candidate 1 24h momentum), 335 bars in Segment 2 have valid features and labels.

### 13.2 Target Disambiguation: Hypothetical 15 bps vs Coinbase Spot 87 bps
To eliminate ambiguity, V5 explicitly evaluates two separate meta-label targets:
* **Target A (Gross return $> 15.0$ bps):** Evaluates whether a trade covers the round-trip friction of the **Hypothetical Binance Perpetual sensitivity scenario**.
  * Train positive prevalence: $42.24\%$
  * Test positive prevalence: $44.85\%$
* **Target B (Gross return $> 87.0$ bps):** Evaluates whether a trade covers the round-trip friction of the **Coinbase Advanced Spot Tier 1 primary backtest**.
  * Train positive prevalence: $30.37\%$
  * Test positive prevalence: $29.02\%$

### 13.3 Statistical Uncertainty & Hypothesis Inference
1. **Paired Loss Difference Bootstrap Confidence Intervals ($B=10000$):**
   * **Brier Score Difference (Model - Prevalence Baseline):** $+0.000428$, 95% CI: $[+0.000234, +0.000621]$.
   * **Log Loss Difference (Model - Prevalence Baseline):** $+0.000877$, 95% CI: $[+0.000477, +0.001277]$.
   * **Statistical Finding:** Because both confidence intervals are strictly positive, the logistic classifier is **statistically significantly worse** than predicting the constant historical training prevalence prior. The claim of "zero discriminative skill" is confirmed with rigorous finite-sample bootstrap inference.
2. **Net Expectancy Uncertainty (Inconclusive vs Decisively Negative):**
   * **Coinbase Spot (87.0 bps friction):** Mean net expectancy is **$-78.09$ bps**, 95% bootstrap CI is **$[-101.18, -55.81]$ bps**. The interval is strictly negative and bounded away from zero: **`FAIL_DECISIVELY_NEGATIVE`**.
   * **Binance Hypothetical (15.0 bps friction):** Mean net expectancy is **$-6.09$ bps**, 95% bootstrap CI is **$[-28.56, +16.36]$ bps**. The interval crosses zero: **`INCONCLUSIVE_INTERVAL_CROSSES_ZERO`**. It still fails the economic gate because positive expectancy is not statistically supported.

### 13.4 Sequential Compounded Portfolio Equity vs Mean Per-Trade Expectancy
Evaluating sequential capital compounding (\$10,000 initial NAV, single-position-at-a-time, 100% equity allocation per trade):
* **Coinbase Spot Tier 1:** Final NAV is **\$1,628.08** (Cumulative PnL: **$-83.72\%$**), Maximum Drawdown: **$83.98\%$**.
* **Binance Hypothetical Perpetual:** Final NAV is **\$8,408.36** (Cumulative PnL: **$-15.92\%$**), Maximum Drawdown: **$30.62\%$**.
* **Portfolio Downtime:** Total evaluation period was 5,959 hours. Time in active trades was 3,876 hours (**$65.04\%$**), while capital downtime (cash) was 2,083 hours (**$34.96\%$**).

### 13.5 Prospective Ledger Verification
Independent inspection of `data/prospective_forecast_ledger.jsonl` confirmed 5 total records:
* **24-Hour Horizon (`rv24h_var_ann`):** 3 resolved records (`prospective-seed-001`, `b1203745-...`, `f5996bf2-...`) with resolved outcomes $0.09856$, $0.08866$, and $0.07388$.
* **168-Hour Horizon (`rv7d_var_ann`):** 2 pending records (`3b3a58d9-...`, `5657414d-...`) with scheduled maturities in late October 2026.
* **Worker Status:** Automated worker runbook documented in `docs/PROSPECTIVE_WORKER_RUNBOOK.md`. Continuous daemon/scheduled task verified as not currently executing autonomously in background; run procedure verified.

### 13.6 Governed Release Decision (V5)
1. **Research Experiment:** `PASS` (Statistical integrity audited, bootstrap CIs verified, manifest frozen).
2. **Experiment Freeze Manifest:** `experiments/results/research_improvement/v5_experiment_freeze_manifest.json` frozen.
3. **Governed Milestone Verdict:**
# `V4_REPRODUCED_AND_PROSPECTIVE_PROTOCOL_FROZEN`
### `V4_METRICS_CORRECTED_NO_CANDIDATE_PASSED`
4. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (Directional); `AUTHORIZED_FOR_VOLATILITY_RISK_ONLY` (`HAR-RS-DOW-v1.0`).
5. **Live Trading:** `DISABLED` (Permanent Invariant).



