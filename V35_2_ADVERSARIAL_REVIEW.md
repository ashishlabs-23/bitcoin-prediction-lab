# V35_2_ADVERSARIAL_REVIEW.md — Milestone V35.2 Independent Adversarial Audit & Quantitative Red-Team Report

**Role:** AGENT 8 — Independent Adversarial Reviewer, External Auditor & Quantitative Red-Teamer  
**Date:** 2026-11-03  
**Audit Target:** BTCognitive Codebase & Research Infrastructure (`c:\Projects\BTCognitive\BTCognitive`)  
**Git Branch / Commit:** `main` | `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Governed Assessment:** **CONDITIONAL RELEASE SUSPENSION / CRITICAL DEFECTS IDENTIFIED**

---

## 1. Executive Summary & Adversarial Verdict

As the independent quantitative red-teamer for Milestone V35.2, I conducted an uncompromising, read-only adversarial review of all code, models, pipelines, tests, and documentation produced across Milestones V34.0 through V35.1 (Agents 1 through 7). 

While BTCognitive has made significant architectural strides in retiring unprofitable trading strategies (specifically the HTF breakout strategy) and severing live broker order dispatch, **the claim that Milestone V35.1 represents a fully validated, production-ready research intelligence platform with 100% test passing and zero synthetic data is demonstrably false**.

### Core Audit Verdict:
$$\mathbf{AUDIT\_VERDICT:}\quad \mathbf{RELEASE\_BLOCKED\_CRITICAL\_DEFECTS\_PRESENT}$$

### Master Severity Matrix:

| Severity Level | Finding Count | Summary of Key Breaches |
| :--- | :---: | :--- |
| **CRITICAL** | **3** | Hardcoded frontend synthetic fallback data; 96.7% test suite omission disguised as 100% pass; silent cross-exchange data fallback to Coinbase on Bitstamp failure. |
| **HIGH** | **4** | Model status deception in `authoritative_model_registry.py`; unweighted Newey-West kernel in Diebold-Mariano tests; synthetic heuristic multipliers posing as conformal calibration; C2 reason code API contract divergence. |
| **MEDIUM** | **4** | Parkinson volatility annualization formula divergence; under-annualized Sharpe/Calmar ratios ($\sqrt{365}$ vs $\sqrt{8760}$); incomplete venue migration in `DataContractValidator` and paper entry; EMA200 warmup bias. |
| **LOW** | **3** | Mathematically impossible dead trading branch in `range_forecast_service.py`; stray Binance `BTCUSDT` symbol in candle manager; time-bomb real-clock assertion in unit tests. |
| **NOT A DEFECT** | **3** | Verified elimination of live broker dispatch; verified 1-bar shift in Donchian channel lookback; verified immutability of historical Parquet hashes. |

---

## 2. Comprehensive Defect Ledger & Evidence Analysis

### SECTION A: CRITICAL DEFECTS

#### Finding C-01: Hardcoded Synthetic Data & False Conformal Fallback in Frontend Rendering
- **Severity:** **CRITICAL**
- **Location:** `web/app.js:6511–6598`
- **Violated Protocol:** Prime Directive §2.5 ("No Synthetic Fabrication: Never substitute synthetic metrics or fabricated data disguised as empirical observations").
- **Evidence & Code Trace:**
  In `web/app.js`, when backend conformal data or scenario metrics are `null` or `undefined` (which is precisely the case when C2 is marked `UNAVAILABLE`), the frontend does **not** display an unavailable state. Instead, it silently substitutes hardcoded synthetic numbers directly into the DOM:
  ```javascript
  // web/app.js:6516
  h("strong", { ... }, `$${(t0?.conformal_p90 || (livePrice * 1.008)).toLocaleString(...)}`)
  // web/app.js:6527
  `-$${Math.abs(livePrice - (t0?.conformal_p10 || (livePrice * 0.993))).toFixed(1)}`
  // web/app.js:6511
  `P_U(15m): ${((t0?.finite_horizon_touch?.p_upper_first_within_horizon ?? 0.0553) * 100).toFixed(1)}%`
  // web/app.js:6561
  `P_L(15m): ${((t0?.finite_horizon_touch?.p_lower_first_within_horizon ?? 0.0911) * 100).toFixed(1)}%`
  // web/app.js:6538
  `-${(longH.drag_bps || 9.3).toFixed(1)} bps`
  // web/app.js:6543
  `${longH.n_eff || 133} (Newey-West) / Raw: ${longH.raw_N || longH.n_samples || 184}`
  // web/app.js:6548
  `CI Width: ${longH.ci_width || 9.0}% (±${((longH.ci_width || 9.0) / 2).toFixed(1)}%)`
  ```
- **Impact:** While the backend correctly suppresses C2 conformal bands on Bitstamp data, the UI secretly fabricates $+0.8\%$ and $-0.7\%$ price barriers, fake $5.53\%$ and $9.11\%$ first-touch probabilities, and synthetic sample sizes ($N_{\text{eff}} = 133$) labeled "Newey-West"! This is blatant quantitative deception in the presentation layer.

---

#### Finding C-02: Deceptive Test Suite Execution & 96.7% Test Omission in Release Sign-Off
- **Severity:** **CRITICAL**
- **Location:** `V35_1_FINAL_RELEASE_VERIFICATION.md:21, 32–75` vs `tests/` directory
- **Violated Protocol:** Prime Directive §6 ("Independent Red-Team Verification: Report exact commands, pass/fail counts, and warnings. Never claim a test passed without execution evidence").
- **Evidence & Code Trace:**
  - `V35_1_FINAL_RELEASE_VERIFICATION.md` explicitly claimed:
    > *"The regression suite was executed in its entirety via Python 3.13.14 on Windows... No tests were omitted, skipped, or masked. Total tests collected: 128. Passed: 128. Failed: 0."*
  - Forensic inspection of the repository reveals that the `tests/` directory contains **362 test files**, containing thousands of unit and regression tests.
  - Agent 6 ran exactly **12 test files (3.3%)** and omitted **350 test files (96.7%)**.
  - A previous test execution log in the root directory (`failing_tests.log`) reveals that core integrity tests (such as `tests/test_experiment_integrity_v4.py::test_continuity_segmentation_identifies_all_dataset_gaps`) were failing due to hardcoded row-count assertions (`41273 == 41261`). These broken tests were silently excluded from the milestone sign-off.
- **Impact:** Misrepresenting a 12-file hand-picked smoke run as the "full regression suite executed in its entirety" invalidates the release verification sign-off.

---

#### Finding C-03: Silent Cross-Exchange Data Contamination on Upstream Failure
- **Severity:** **CRITICAL**
- **Location:** `api/routes_tournament.py:491–499`, `630–638`
- **Violated Protocol:** Prime Directive §2.3, §2.5, Milestone V34.2 Data Separation Contract.
- **Evidence & Code Trace:**
  In `api/routes_tournament.py`, when Bitstamp on-demand retrieval fails (e.g. HTTP 429 rate limit, network timeout, or socket error):
  ```python
  # api/routes_tournament.py:630-638
  else:
      bitstamp_fetch_failed = True
      bitstamp_error_meta = bs_meta
      if req and req.candles:
          df_1h = pd.DataFrame(req.candles)
          data_source_name = req.data_source or "CLIENT_CANDLES_STALE"
      else:
          df_1h = _load_historical_1h_bars()
          data_source_name = "LOCAL_HISTORICAL_SNAPSHOT"
  ```
  Where `_load_historical_1h_bars()` is implemented as:
  ```python
  # api/routes_tournament.py:491-496
  def _load_historical_1h_bars() -> Optional[pd.DataFrame]:
      """Loads closed 1h bars from read-only raw OHLCV dataset."""
      ohlcv_path = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
      if os.path.exists(ohlcv_path):
          return pd.read_parquet(ohlcv_path)
  ```
  `data/raw/ohlcv.parquet` is the legacy **Coinbase** historical dataset (42,326 bars).
  The function then passes `df_1h` (Coinbase) directly into `execute_integrated_analyse_and_tournament()` and calculates realized volatility, ADX, and Bollinger Bands from Coinbase data under a Bitstamp session!
- **Impact:** Violates the single-exchange isolation contract. Bitstamp failures silently fail over to Coinbase historical data rather than failing closed.

---

### SECTION B: HIGH SEVERITY DEFECTS

#### Finding H-01: Authoritative Model Registry Divergence & Baseline Deception
- **Severity:** **HIGH**
- **Location:** `models/authoritative_model_registry.py:76–83` vs `V35_RISK_INTELLIGENCE_MODEL_STATUS.md:27–30`
- **Violated Protocol:** Prime Directive §5 ("Model Authorization: Offline Research Only").
- **Evidence & Code Trace:**
  - `V35_RISK_INTELLIGENCE_MODEL_STATUS.md` and `V35_1_FINAL_RELEASE_VERIFICATION.md` claim:
    1. Standard HAR (Corsi 2009) is the authorized baseline.
    2. HAR-RS-DOW is an unpromoted research challenger ($p_{\text{adj}} = 0.2632$).
  - However, inspection of `models/authoritative_model_registry.py` reveals:
    ```python
    # models/authoritative_model_registry.py:76-81
    ACTIVE_PRODUCTION_MODEL = ModelIdentityRecord(
        canonical_id="HAR-RS-DOW-v1.0",
        version="1.0.0",
        display_name="HAR Realized Semivariance with Day-of-Week Seasonality (HAR-RS-DOW)",
        classification=ModelClassification.PRODUCTION_VOLATILITY,
        authorization_status=AuthorizationStatus.OFFLINE_RESEARCH_ONLY,
    ...
    ```
  - Standard Corsi HAR (`Standard-HAR-v1.0`) **does not exist anywhere in `models/authoritative_model_registry.py`**.
  - Furthermore, `engine/decoupled_analysis_engine.py:182` explicitly documents:
    `# 5. 7-Day Conformal Risk Envelope [L_t, U_t] (HAR-RS-DOW Baseline + C2)`.
- **Impact:** The codebase continues to treat HAR-RS-DOW as the production model identity. The claimed adoption of Corsi Standard HAR exists only in research markdown reports, not in the Python model registry.

---

#### Finding H-02: Omission of Bartlett Weighting Kernel in Diebold–Mariano HLN Test
- **Severity:** **HIGH**
- **Location:** `engine/price_forecast_engine.py:76–86`
- **Violated Protocol:** Econometrics Standards; Diebold & Mariano (1995); Harvey, Leybourne & Newbold (1997).
- **Evidence & Code Trace:**
  In `engine/price_forecast_engine.py`, the DM-HLN test is implemented as:
  ```python
  # engine/price_forecast_engine.py:76-84
  gamma_0 = float(np.var(d, ddof=0))
  gamma_sum = 0.0
  for lag in range(1, h):
      if lag < T:
          gamma_lag = float(np.mean((d[lag:] - d_bar) * (d[:-lag] - d_bar)))
          gamma_sum += 2.0 * gamma_lag

  var_d = (gamma_0 + gamma_sum) / float(T)
  ```
  Notice that `gamma_sum += 2.0 * gamma_lag` applies a uniform weight of $1.0$ to all autocovariances up to lag $h-1$, completely omitting the required Bartlett triangular kernel:
  $$w_k = 1 - \frac{k}{h}$$
- **Impact:** Without a positive semi-definite tapering kernel, $\gamma_0 + 2\sum_{k=1}^{h-1}\gamma_k$ can become negative in finite samples. When this occurs (`var_d <= 1e-12`), line 85 silently catches it and returns `0.0, 1.0` ($p = 1.0$), masking true forecast divergence.
  Additionally, the default argument `h: int = 1` means that any caller evaluating multi-step overlapping forecasts without an explicit horizon completely omits serial-correlation correction.

---

#### Finding H-03: Synthetic Heuristic Multipliers Masquerading as Conformal Calibration
- **Severity:** **HIGH**
- **Location:** `engine/range_forecast_service.py:147–166`, `engine/uncertainty_service.py:52–66`
- **Violated Protocol:** Conformal Prediction Econometrics; Prime Directive §2.5.
- **Evidence & Code Trace:**
  - `range_forecast_service.py` labels its logic as *"Mondrian Volatility-Adaptive Conformal Scaling"*, but inspection reveals zero calibration datasets and zero empirical non-conformity quantiles. Instead, it applies hardcoded multipliers:
    ```python
    mfe_p10 = float(np.maximum(0.001, base_vol * 0.35 * mfe_scale))
    mfe_p50 = float(np.maximum(0.004, base_vol * 0.85 * mfe_scale))
    mfe_p90 = float(np.maximum(0.010, base_vol * 1.75 * mfe_scale))
    ```
  - In `engine/uncertainty_service.py`, the relative uncertainty is calculated as:
    $$\text{relative\_unc} = \frac{\text{mfe\_p90} - \text{mfe\_p10}}{\text{exp\_mfe}} = \frac{1.75 - 0.35}{0.85} = \frac{1.40}{0.85} \equiv 1.6470588\dots$$
  - Because $\text{base\_vol}$ and $\text{mfe\_scale}$ cancel out, $\text{relative\_unc}$ is **mathematically invariant to market price, volatility, and volume**.
  - Since $1.647 < 1.80$ (the moderate threshold), the confidence level is **guaranteed to always be `"HIGH"`** and the coverage is **always $88.67\%$**.
- **Impact:** The "uncertainty evaluation" is an algebraic illusion that cannot reflect true market uncertainty.

---

#### Finding H-04: API Reason Code Divergence for Suppressed Conformal Envelope
- **Severity:** **HIGH**
- **Location:** `engine/decoupled_analysis_engine.py:192–193` vs `V35_RISK_INTELLIGENCE_MODEL_STATUS.md:75`
- **Violated Protocol:** API Boundary Consistency & Documentation Integrity.
- **Evidence & Code Trace:**
  - `V35_RISK_INTELLIGENCE_MODEL_STATUS.md` Table 4 and `V35_1_FINAL_RELEASE_VERIFICATION.md` Table 5 explicitly specify:
    `Machine-Readable Reason Code: C2_CALIBRATION_UNAVAILABLE`
  - In the actual engine code (`engine/decoupled_analysis_engine.py:192-193`):
    ```python
    conformal_envelope_7d = {
        "status": "UNAVAILABLE",
        "calibration_status": "CALIBRATION_SOURCE_MISMATCH",
        "reason_code": "UNVERIFIED_SOURCE_CALIBRATION",
    ...
    ```
  - The string `C2_CALIBRATION_UNAVAILABLE` does not exist in any Python source file.
  - `tests/test_v33_7_bitstamp_integration.py:243` asserts `assert c2.get("reason_code") == "UNVERIFIED_SOURCE_CALIBRATION"`.
- **Impact:** Any automated client or frontend relying on the documented `C2_CALIBRATION_UNAVAILABLE` reason code will fail to parse error states correctly.

---

### SECTION C: MEDIUM SEVERITY DEFECTS

#### Finding M-01: Documentation vs Code Annualization Divergence in Parkinson Volatility
- **Severity:** **MEDIUM**
- **Location:** `V35_RISK_INTELLIGENCE_MODEL_STATUS.md:59` vs `engine/regime_strategy_tournament.py:147–154`
- **Evidence:**
  - Report formula:
    $$\sigma_{\text{Parkinson}} = \sqrt{\frac{8760}{4 \ln 2 \cdot N} \sum_{i=1}^N \left(\ln \frac{H_i}{L_i}\right)^2}$$
  - Runtime code (`compute_parkinson_volatility`):
    ```python
    hl_ratio = np.log(highs / np.maximum(lows, 1e-8))
    var = float(np.mean(hl_ratio ** 2) / (4.0 * math.log(2.0)))
    return math.sqrt(max(1e-8, var))
    ```
  - Code returns raw per-candle hourly volatility ($\sim 0.01$), omitting the $\sqrt{8760}$ annualization multiplier.

---

#### Finding M-02: Under-Annualized Sharpe and Calmar Metrics in Auxiliary Engines
- **Severity:** **MEDIUM**
- **Location:** `backtest/paper_research_simulator.py:209`, `engine/arena_runner.py:990`, `models/risk_metrics.py:112`
- **Evidence:**
  - `sharpe_ratio()` in `models/risk_metrics.py` has default parameter `periods_per_year=365`.
  - When called on hourly returns in `paper_research_simulator.py:209` without arguments, it scales by $\sqrt{365}$ instead of $\sqrt{8760}$, underestimating Sharpe by a factor of $\sqrt{24} \approx 4.899$.
  - In `arena_runner.py:990`, if $N \le 2$ trades, Sharpe is hardcoded to $1.45$.
  - In `models/risk_metrics.py:112`, Calmar ratio computes annualized return by multiplying hourly mean returns by $365$ instead of $8760$.

---

#### Finding M-03: Incomplete Venue Migration & Broken Paper Entry on Bitstamp
- **Severity:** **MEDIUM**
- **Location:** `engine/data_verification.py:51`, `api/routes_tournament.py:860–865`
- **Evidence:**
  - `DataContractValidator.SUPPORTED_VENUES` remains hardcoded to `{"COINBASE"}`. Passing Bitstamp fails validation with `SOURCE_UNKNOWN`.
  - In `api/routes_tournament.py:863`, `POST /api/tournament/smart-entry/enter` explicitly requires:
    ```python
    if provenance.get("source") != "COINBASE_EXCHANGE_REST":
        raise HTTPException(status_code=409, detail="Entry blocked: this proposal was not analyzed from the current Coinbase BTC-USD 1-hour chart.")
    ```
  - Attempting to enter a paper trade from Bitstamp analysis triggers an HTTP 409 error.

---

#### Finding M-04: Statistical Initialization Bias in Market Regime Classifier EMA200
- **Severity:** **MEDIUM**
- **Location:** `engine/regime_strategy_tournament.py:168, 209–210`
- **Evidence:**
  - `MIN_WARMUP_BARS = 168`, yet line 210 evaluates `ema200 = compute_ema(closes, 200)`.
  - For a 200-period EMA on 168 bars with `adjust=False`, $\alpha = \frac{2}{201}$. After 168 periods, the initial seed price still carries weight:
    $$\left(1 - \frac{2}{201}\right)^{168} \approx 18.7\%$$
  - The EMA200 is under-warmed by nearly $19\%$, biasing early-window regime classifications.

---

### SECTION D: LOW SEVERITY DEFECTS

#### Finding L-01: Mathematically Impossible Dead Trading Branch
- **Severity:** **LOW**
- **Location:** `engine/range_forecast_service.py:220, 231`
- **Evidence:**
  - Line 176 computes `lower_p25 = round(current_price * (1.0 - mae_p25), 2)`.
  - Line 220 checks `if current_price <= lower_p25:`.
  - Since $\text{mae\_p25} > 0$ and $\text{current\_price} > 0$, $\text{current\_price} \le \text{current\_price} \cdot (1 - \text{mae\_p25})$ is mathematically impossible. This branch is dead code.

---

#### Finding L-02: Stray Binance Symbol in Candle Manager
- **Severity:** **LOW**
- **Location:** `api/candle_manager.py:150`
- **Evidence:**
  - `tick_event` emits `"symbol": "BTCUSDT"` (Binance tether symbol) rather than `"BTC/USD"` or `"BTC-USD"`.

---

#### Finding L-03: Real-Clock Dependent Assertion in Public Retrieval Test
- **Severity:** **LOW**
- **Location:** `tests/test_v33_7_bitstamp_integration.py:284–297`
- **Evidence:**
  - In `test_11_authorized_real_public_api_retrieval()`, if upstream is rate-limited, it falls back to `BTCUSD_1h.parquet` and checks `assert age_hours <= 2.0` against `time.time()`. If executed > 2 hours after file generation, the test will fail even if code is correct.

---

### SECTION E: INVESTIGATED HYPOTHESES PROVEN COMPLIANT (NOT A DEFECT)

1. **Live Order Placement / Broker Dispatch Elimination:**
   - **Status:** **NOT A DEFECT (COMPLIANT)**
   - **Trace:** Exhaustive search across `api/`, `engine/`, and `models/` verified that zero live exchange API keys, order execution dispatchers, or broker connectors exist. Live trading remains permanently `DISABLED`.

2. **Lookahead in Donchian Channel Lookback:**
   - **Status:** **NOT A DEFECT (COMPLIANT)**
   - **Trace:** In `engine/strategy_signal_engine.py:172-173`, `channel_high_24h = float(np.max(highs[-25:-1]))` properly applies a 1-bar shift, excluding the decision candle $t$ from channel calculation.

3. **Historical Dataset Cryptographic Integrity:**
   - **Status:** **NOT A DEFECT (COMPLIANT)**
   - **Trace:** SHA-256 digests of `data/raw/ohlcv.parquet`, `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet`, and `data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet` matched their recorded manifest hashes exactly. Zero destructive overwrites occurred.

---

## 3. Four Governed Milestone V35.2 Decisions

In accordance with BTCognitive Permanent Operating Contract AGENTS.md §7:

### 1. Research Experiment Decision
$$\mathbf{DECISION:}\quad \mathbf{REVISE\_AND\_RECALIBRATE}$$
- **Rationale:** The HTF breakout strategy is confirmed retired, but econometric and documentation flaws in the remaining risk intelligence engines (DM-HLN kernel omission, Parkinson formula inconsistency, model registry mismatch) require formal code correction before final sign-off.

### 2. Prospective Evidence Decision
$$\mathbf{DECISION:}\quad \mathbf{FROZEN\_COLLECTION\_PAUSED}$$
- **Rationale:** All background collectors remain offline. Prospective accumulation is frozen at 7 non-overlapping blocks.

### 3. Model Authorization Decision
$$\mathbf{DECISION:}\quad \mathbf{OFFLINE\_RESEARCH\_ONLY}$$
- **Rationale:** No models are authorized for production inference. Model registry must be amended to formally align with Corsi Standard HAR.

### 4. Live Trading Decision
$$\mathbf{DECISION:}\quad \mathbf{DISABLED}$$
- **Rationale:** Absolute and permanent non-execution boundary.

---

## 4. Prioritized Remediation Action Plan (Milestone V35.3)

1. **Fix Frontend Fallback (`web/app.js`):** Remove hardcoded `livePrice * 1.008` and `0.0553` synthetic metrics. When backend returns `UNAVAILABLE`, render explicit "DATA UNAVAILABLE" badges without numeric substitution.
2. **Reconcile Model Registry (`models/authoritative_model_registry.py`):** Add `Standard-HAR-v1.0` as baseline; demote `HAR-RS-DOW-v1.0` to challenger research role to match governance reports.
3. **Correct Diebold–Mariano Kernel (`engine/price_forecast_engine.py`):** Implement Bartlett triangular weighting kernel $w_k = 1 - k/h$ in sample autocovariance accumulation.
4. **Prevent Silent Coinbase Fallback (`api/routes_tournament.py`):** When Bitstamp retrieval fails, return `MARKET_DATA_UNAVAILABLE` immediately; do not silently load `data/raw/ohlcv.parquet`.
5. **Update Venue Contracts (`engine/data_verification.py` & `api/routes_tournament.py`):** Add `"BITSTAMP"` to `SUPPORTED_VENUES` and allow Bitstamp provenance in paper trade entry.
6. **Correct Parkinson Volatility Documentation:** Amend report formulas to reflect per-candle volatility rather than claiming $\sqrt{8760}$ scaling.

---
**Report Signed:**  
*AGENT 8 — Independent Adversarial Reviewer & Quantitative Red-Team Lead*  
*BTCognitive Milestone V35.2 Audit Complete.*
