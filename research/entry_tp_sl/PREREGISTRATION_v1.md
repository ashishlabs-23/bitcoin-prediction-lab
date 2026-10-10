# Master Preregistration Specification (v1.0.0) — Entry/TP/SL Research Track

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Preregistration Version:** `PREREG_V1_20261007`  
**Date of Preregistration:** `2026-10-07T16:30:00Z`  
**Status:** `SCIENTIFICALLY FROZEN`  

---

## A. Primary Research Question
Does predictive information available at decision timestamp $t_0$ permit a selective, cost-aware directional trading rule with positive net expectancy beyond matched random and rule-based baselines under unseen walk-forward evaluation data?

**Explicit Exclusions:**
This research track is **NOT** testing:
- Exact price forecasting or point prediction.
- 90% directional accuracy claims.
- Guaranteed profitable trading.
- Continuous MFE/MAE as a final execution success criterion.
- Every-bar unconditional prediction.
- Trade frequency maximization.

---

## B. Primary Instrument
- **Symbol:** `BTC/USD` spot.
- **Venue:** Bitstamp spot exchange.
- **Base / Quote:** BTC / USD.
- **Bar Granularity:** 1-minute discrete OHLCV.
- **Timezone:** UTC.

---

## C. Data Snapshot & Cryptographic Provenance
- **Canonical Snapshot:** `data/raw/btcusd_1-min_data.csv`
- **File Size:** `393,952,273` bytes
- **SHA-256 Checksum:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- **Coverage:** `7,766,111` rows from `2012-01-01 00:01:00 UTC` to `2026-10-07 03:11:00 UTC`.
- **License / Rights:** CC BY-SA 4.0 (formally approved by user).

---

## D. Decision Timing & Cadence
- **Cadence:** 15-minute decision intervals (:00, :15, :30, :45 UTC).
- **$t_0$ (Decision Timestamp):** The exact close timestamp of a completed 15-minute decision bar.
- **Signal Generation:** Instantaneous at $t_0$.

---

## E. Point-in-Time (PIT) Invariants
- **Strict Rule:** $\text{available\_timestamp} \le t_0$.
- No forming or in-progress bar data may enter feature or signal computation.
- No asynchronous lookahead or retroactive dataset revisions.

---

## F. Entry Execution Model
- **Order Mechanism:** Marketable taker order submitted at $t_0$.
- **Fill Timestamp:** $t_{\text{fill}} = t_0 + 60\text{ seconds}$ (open of the immediate next 1-minute bar).
- **Fill Price Basis:** $\text{Open}(t_{\text{fill}})$.
- **Gap at Open:** If price gaps at open, filled at actual open. If next 1m bar is missing, order fails closed (`DATA_GAP`).
- **Maker/Taker:** Strict `TAKER`.

---

## G. Volatility Estimator
- **PRIMARY:** $\text{ATR}_{14}$ on 15-minute decision bars, normalized: $\sigma_{t0} = \text{ATR}_{14}(15\text{m}) / P_{t0}$.
  - *Rationale:* Causal, robust to jump discontinuities, directly matched to high-low boundary touch mechanics.
- **PRE-REGISTERED SECONDARY:** $\text{RealizedVolatility}_{24\text{h}}$ (standard deviation of 96 15-minute log returns).

---

## H. Predetermined Barrier Grid
Each pair is a distinct pre-registered configuration in the confirmatory family:
1. `barrier_pair_01` (PRIMARY REFERENCE): $k_{\text{TP}} = 1.0$, $k_{\text{SL}} = 1.0$, Horizon = 240m (4h)
2. `barrier_pair_02`: $k_{\text{TP}} = 1.5$, $k_{\text{SL}} = 1.0$, Horizon = 240m (4h)
3. `barrier_pair_03`: $k_{\text{TP}} = 2.0$, $k_{\text{SL}} = 1.0$, Horizon = 240m (4h)
4. `barrier_pair_04`: $k_{\text{TP}} = 0.75$, $k_{\text{SL}} = 0.75$, Horizon = 120m (2h)
5. `barrier_pair_05`: $k_{\text{TP}} = 2.0$, $k_{\text{SL}} = 1.5$, Horizon = 240m (4h)

---

## I. Vertical Time Horizon
- **PRIMARY:** $H = 240\text{ minutes}$ (4 hours / 16 decision intervals / 240 1-minute path bars).
- **SECONDARY:** $H = 120\text{ minutes}$ (2 hours).

---

## J. TP/SL Touch & Boundary Semantics
- **Long:** $Upper = P_{\text{entry}} \times (1 + k_{\text{TP}} \times \sigma_{t0})$, $Lower = P_{\text{entry}} \times (1 - k_{\text{SL}} \times \sigma_{t0})$.
- **Short:** $Lower = P_{\text{entry}} \times (1 - k_{\text{TP}} \times \sigma_{t0})$, $Upper = P_{\text{entry}} \times (1 + k_{\text{SL}} \times \sigma_{t0})$.
- **Touch Condition:** Evaluated on 1-minute $\text{High}$ and $\text{Low}$. High $\ge Upper$ or Low $\le Lower$.

---

## K. Intrabar Ambiguity Policy
- **Observable Order:** If sub-minute ticks exist, follow observed order.
- **Unobservable Dual Touch (Same 1m Bar):** Primary conservative policy resolves to **`SL_FIRST`**.
- **Metadata Required:** Must record `same_timestamp_collision = true` and `unresolved_intrabar_order = true`.
- **Ambiguity Bounds:** Secondary TP-first sensitivity analysis will be executed alongside to bound uncertainty.

---

## L. Timeout Treatment
- If neither barrier is touched within $H = 240$ minutes, trade exits at the exact $\text{Close}$ of the 240th 1-minute bar.
- **Critical Invariant:** Timeout is **NEVER** hard-coded to $-1R$. Gross R is computed from actual exit price:
  $$\text{Gross R}_{\text{timeout}} = \frac{\text{Direction} \times (P_{\text{timeout}} - P_{\text{entry}})}{P_{\text{entry}} \times k_{\text{SL}} \times \sigma_{t0}}$$

---

## M. Opportunity Clustering & Position Lifecycle
- **Capacity:** Strictly **ONE open position** per instrument at any time.
- **Concurrent Signals:** While a position is active, subsequent signals emit `ABSTAIN_CONCURRENT_POSITION_EXISTS`.
- **Uniqueness Weighting:** $w_i = 1 / (\text{number of concurrent signals in window})$.
- **Effective Sample Size:** $N_{\text{eff}} = \frac{(\sum w_i)^2}{\sum w_i^2}$.

---

## N. Cost Scenarios
Costs are positive deductions from gross trade economics:
- **BASE:**
  - Taker fee: 10 bps entry + 10 bps exit = 20 bps
  - Slippage: 5 bps entry + 5 bps exit = 10 bps
  - Half-spread: 2.5 bps each side = 5 bps
  - **Total Round-Trip: 35 bps (0.0035)**
- **CONSERVATIVE:**
  - Taker fee: 15 bps entry + 15 bps exit = 30 bps
  - Slippage: 10 bps entry + 15 bps stop exit = 25 bps
  - Half-spread: 5 bps each side = 10 bps
  - **Total Round-Trip: 65 bps (0.0065)**

---

## O. 1R Definition & Net Outcome Accounting
- **1R Basis:** $1R_{\text{USD}} = P_{\text{entry}} \times k_{\text{SL}} \times \sigma_{t0}$.
- **Net R Formula:**
  $$\text{Net R} = \text{Gross R} - \frac{\text{Total Cost Fraction}}{k_{\text{SL}} \times \sigma_{t0}}$$

---

## P. Pre-Registered Comparison Chain
1. **$B_0$:** Matched random-entry baseline (same opportunity timestamps, random direction/abstention).
2. **$B_3$:** Fixed structural rule baseline (e.g. breakout / ATR threshold).
3. **$B_4\text{-lite}$:** Calibrated logistic regression baseline.
4. **$B_4$:** LightGBM cost-aware selective classifier.
- **Confirmatory Chain:** $B_3 > B_0 \implies B_4 > B_3 \implies B_4 > B_4\text{-lite} \implies B_4 \ge E_{\text{min}}$.

---

## Q. Primary Endpoint
- **Endpoint:** Mean net R per independent trade ($\bar{R}_{\text{net}}$) on unseen walk-forward evaluation data under the BASE cost scenario.
- **Sign Convention:** Positive indicates net positive expectancy after all fees and slippage.

---

## R. Secondary Endpoints
1. Mean net R under CONSERVATIVE cost scenario.
2. Net Profit Factor ($\sum R_{\text{wins}} / \sum |R_{\text{losses}}|$).
3. Calmar Ratio and Maximum Peak-to-Trough Drawdown in R.
4. Brier score and calibration curve slope.
5. Selection frequency and trade coverage.

---

## S. Formal Success Criteria
The experiment achieves scientific success if and only if **BOTH** conditions hold:
1. Point estimate $\bar{R}_{\text{net}} \ge E_{\text{min}} = +0.10R$.
2. Lower one-sided 95% stationary block bootstrap confidence bound $> 0.00R$.

---

## T. Formal Futility Criteria
The experiment is declared futile and halted if:
1. Point estimate $\bar{R}_{\text{net}} < 0.00R$ after $N \ge 150$ independent evaluation trades.
2. Upper one-sided 95% confidence bound $< E_{\text{min}}$ on the complete evaluation sample.

---

## U. Confidence Interval Methodology
- Stationary circular block bootstrap with block length $L = 32\text{ bars}$ (8 hours) and $B = 10,000$ resamples.
- Significance level $\alpha = 0.05$ (one-sided lower bound).

---

## V. Multiple-Testing Policy
- **Primary Family:** Holm-Bonferroni step-down procedure applied across the 5 pre-registered barrier pairs $\times$ model comparison chain.
- **Secondary Family:** Benjamini-Hochberg (BH) False Discovery Rate (FDR) control at $q = 0.10$.
- **Multiple Rule Adjustment:** Deflated Sharpe Ratio (DSR) and Superior Predictive Ability (SPA / White's Reality Check).

---

## W. Walk-Forward Architecture
- Anchored or rolling walk-forward cross-validation with minimum 3-year in-sample training and 6-month out-of-sample test folds.

---

## X. Purge and Embargo
- **Purge Window:** All samples overlapping the 4-hour ($H = 240\text{m}$) holding window between train and validation folds are purged.
- **Embargo Window:** Additional 24-hour embargo applied after each validation segment.

---

## Y. Abstention Semantics & Rules
Allowed categorical abstention states:
- `NO_SETUP`, `MODEL_UNCERTAIN`, `EV_BELOW_COST`, `EXECUTION_UNSAFE`, `RISK_LIMIT`, `DATA_UNAVAILABLE`, `PROVENANCE_FAILURE`, `MODEL_FAILURE`, `LATENCY_EXCEEDED`, `BREAKEVEN_INFEASIBLE`.
- Selection thresholds are fitted strictly in-sample and locked prior to out-of-sample evaluation.

---

## Z. Explicit Exclusions
- Hourly OHLCV (`data/raw/ohlcv.parquet`) is excluded from path resolution.
- Deribit IV (`iv7d.parquet`) and legacy HAR artifacts are excluded.
- Synthetic price data is forbidden.

---

## AA. Missing Data & Gap Rules
- Gaps $\le 3$ consecutive minutes: forward-filled with zero volume.
- Gaps $> 3$ consecutive minutes during active path: trade resolves to `DATA_GAP` (fails closed, excluded from positive training labels).

---

## AB. Stopping Rules
- Automatic experiment termination on 3 consecutive walk-forward fold failures or futility threshold trigger.

---

## AC. Trial Counting Rules
- Every executed variation of features, barrier pairs, or hyperparameters increments the global immutable trial ledger.

---

## AD. Holdout Policy
- Final 12 months of available data (`2025-10-07` to `2026-10-07`) is strictly sequestered as a pristine test holdout, accessed exactly once at final confirmation.

---

## AE. Version Information
- Preregistration Version: `1.0.0`
- Target Architecture: `BTCognitive Entry + TP/SL V3`

---

## AF. Cryptographic Hashes
- Dataset SHA-256: `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- Environment Fingerprint: `1f327cf5edf52a160282f6f2f08ad8b4536a161851dc5cea4e25cfa770c6ea62`
