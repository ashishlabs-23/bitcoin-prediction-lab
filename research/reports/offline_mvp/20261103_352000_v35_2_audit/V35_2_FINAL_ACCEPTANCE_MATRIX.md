# BTCognitive Milestone V35.2 — Final Acceptance Matrix

**Audit Date:** 2026-11-03  
**Auditor:** Senior Engineering Manager, Quantitative Research Lead & Independent Quality Auditor  
**Operating Boundary:** Phase 0–7 Comprehensive System Audit | Strict Non-Execution  
**Git Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  

---

## 1. Governed 24-Point Acceptance Evaluation Matrix

| ID | Evaluation Requirement | Verdict | Empirical Evidence & Forensic Findings | Mandated Action / Status |
| :---: | :--- | :---: | :--- | :--- |
| **A01** | **Bitstamp Source Integrity** | **PASS** | Validated across 6,000 bars (1,000 live, 4,000 expanded, 1,000 multiyear). Zero timestamp gaps, zero duplicates, zero negative volume, zero OHLC geometric breaches. | Compliant. |
| **A02** | **Current-Market Freshness** | **PASS** | Strict 2.0-hour policy threshold enforced. Stale data triggers fail-closed `MARKET_DATA_STALE` warning and suppresses trade geometry. Verified via live CDP browser test (age 0.98h). | Compliant. |
| **A03** | **Correct Return Calculation** | **PASS** | Evaluates logarithmic returns $r_t = \ln(C_t / C_{t-1})$ across consecutive closed hourly candles. Causal boundary $t_{\text{avail}} \ge t_{\text{close}}$ strictly maintained. | Compliant. |
| **A04** | **Correct Realized-Volatility Construction** | **PASS** | $\text{RV}_W = \sqrt{\frac{1}{W}\sum r_i^2} \times \sqrt{8760} \times 100\%$ correctly implements uncentered high-frequency variance estimator across 1h, 4h, 24h, 7d, 30d windows. | Compliant. |
| **A05** | **Correct Annualization & Units** | **FAIL** | 1. `compute_parkinson_volatility` computes per-candle hourly volatility ($\sim 0.01$) without $\sqrt{8760}$ scaling, contradicting documentation claiming annualized percent.<br>2. `models/risk_metrics.py:sharpe_ratio` defaults to $\sqrt{365}$ instead of $\sqrt{8760}$, under-annualizing hourly Sharpe by $4.9\times$. | Remediate in V35.3. |
| **A06** | **Correct Term Structure** | **PASS** | Term structure ratio $\rho = RV_{1h} / RV_{24h}$ dynamically classifies market into `CONTANGO_COMPRESSION` ($\rho < 0.85$, 68%), `FLAT` (14%), and `INVERTED_EXPANSION` ($\rho > 1.25$, 18%). | Compliant. |
| **A07** | **Standard HAR Benchmark Reproducibility** | **PASS** | Corsi (2009) Standard Log-HAR fully reproduced. Wins 7-day horizon with lowest holdout QLIKE ($0.02571$), outperforming complex variants. | Baseline established. |
| **A08** | **QLIKE-HAR Challenger Reproducibility** | **PASS** | Lineage of QLIKE values ($0.3874 \to 0.3951 \to 0.3976$) mathematically resolved and reproduced (log vs linear regressors, 30d vs 22d memory, L2 penalty, sample truncation). | Lineage resolved. |
| **A09** | **Dependence-Aware Forecast Comparison** | **FAIL** | `engine/price_forecast_engine.py:76–86` implements DM-HLN without the required Bartlett triangular kernel ($w_k = 1 - k/h$), causing unweighted autocovariances and negative variance clipping. Default $h=1$ ignores overlap. | Remediate in V35.3. |
| **A10** | **Chronological Holdout Integrity** | **PASS** | Causal temporal splits preserved. No forward data leakage into training matrices. Strict separation between training ($t < t_{\text{split}}$) and holdout ($t \ge t_{\text{split}}$). | Compliant. |
| **A11** | **Regime Classification Stability** | **PASS** | 3-candle persistence hysteresis reduces boundary switching chatter by **44.80%**. Mean dwell times extend from 7–9h to 14–18h. Transition matrix exhibits $> 90\%$ 1-hour diagonal persistence. | Compliant. |
| **A12** | **Regime Predictive Usefulness** | **PASS** | Statistically significant explanatory power in nested regressions ($F = 26.69, p = 3.8 \times 10^{-22}$), but incremental variance explained is tiny ($+0.19\text{ pp}$). Economically validated as discrete risk gating, not alpha generation. | Compliant. |
| **A13** | **C2 Calibration Integrity** | **FAIL** | 1. Empirical causal coverage drops to **84.89%** overall and crashes to **64.79%** in extreme volatility due to the 168h feedback maturity barrier.<br>2. `research/risk_envelope.py` hardcodes unverified "91.3% Validated" claims.<br>3. Reason code divergence (`UNVERIFIED_SOURCE_CALIBRATION` vs `C2_CALIBRATION_UNAVAILABLE`). | Keep UNAVAILABLE. Remediate in V35.3. |
| **A14** | **Historical Excursion Measurement** | **FAIL** | 1. Downside MAE in `research/risk_envelope.py:27–28` is synthetically fabricated by multiplying upside MFE by fixed scalars (`1.32x`, `1.90x`).<br>2. MFE regression models exhibit negative Spearman rank correlation ($\text{IC} = -0.2378$ to $+0.0192$) across 4 of 5 folds. | Remediate in V35.3. |
| **A15** | **Strategy Deprecation Across Endpoints** | **PASS** | HTF breakout strategy is strictly marked `DEPRECATED_RESEARCH_ONLY` across strategy registry, setup detector, API endpoints, and UI headers. Smart entry action permanently returns `ABSTAIN`. Zero live recommendations. | Compliant. |
| **A16** | **Historical Evidence Preservation** | **PASS** | All 17 causal backtest trades from Milestone V34.5 preserved bit-for-bit in `data/research/v34_5_htf_trade_events.jsonl` (-102.9 bps gross, -172.9 bps net, 17.6% win rate, 0.12 profit factor). | Compliant. |
| **A17** | **API & Browser Consistency** | **FAIL** | `web/app.js:6511–6598` contains hardcoded fallback mock data substituting synthetic price levels (`livePrice * 1.008`), fake touch probabilities (`5.53%`, `9.11%`), and dummy Sharpe metrics when backend returns null. | Remediate in V35.3. |
| **A18** | **Provider Failure Handling** | **FAIL** | When Bitstamp retrieval fails, `api/routes_tournament.py:630–638` silently loads legacy Coinbase data (`data/raw/ohlcv.parquet`) to calculate baseline indicators rather than failing closed. | Remediate in V35.3. |
| **A19** | **Application Restart Behavior** | **PASS** | Validated via failure injection Mode 11. SQLite WAL journaling and atomic parquet replacements preserve state across abrupt process restarts. | Compliant. |
| **A20** | **Data & Model Provenance** | **FAIL** | 1. `models/authoritative_model_registry.py` still lists `HAR-RS-DOW-v1.0` as `ACTIVE_PRODUCTION_MODEL` while governance reports designate Standard HAR.<br>2. `DataContractValidator.SUPPORTED_VENUES` only accepts `"COINBASE"`. | Remediate in V35.3. |
| **A21** | **Live Trading Disabled** | **PASS** | `EXECUTION_STATUS_CONSTANT = "DISABLED — ANALYSIS ONLY"`. Exhaustive code scan confirms zero exchange API keys, zero order dispatchers, and zero live broker hooks. | Compliant. |
| **A22** | **Prospective Collector Inactive** | **PASS** | All background shadow runners and forward collectors remain offline and locked. Prospective ledger frozen at 7 blocks. | Compliant. |
| **A23** | **Full Regression Suite** | **FAIL** | Milestone V35.1 sign-off claimed 128 tests represented the regression suite "in its entirety", whereas the repository contains 362 test files (350 test files were omitted from execution). | Remediate in V35.3. |
| **A24** | **Git Integrity** | **PASS** | Verified clean worktree on `main` (`25d483f4c3646661b57311de9d0b53d2be881adb`). Zero destructive git commands invoked. All user modifications preserved. | Compliant. |

---

## 2. Quantitative Summary Statistics

- **Total Criteria Evaluated:** 24
- **PASS Criteria:** **16 (66.7%)**
- **FAIL Criteria:** **8 (33.3%)**
- **NOT APPLICABLE:** 0
- **NOT VERIFIED:** 0

### Categorical Breakdown:
- **Core Market Data & Pipeline (A01–A04, A06, A10):** 6 / 6 PASS (100%)
- **Strategy & Governance Invariants (A15, A16, A21, A22, A24):** 5 / 5 PASS (100%)
- **Econometric Forecasting & Calibration (A05, A07–A09, A11–A14):** 4 / 8 PASS (50.0%) — *Failures in Parkinson scaling, DM kernel, C2 delayed feedback, and synthetic MFE/MAE multipliers.*
- **System Integration & Presentation (A17–A20, A23):** 1 / 5 PASS (20.0%) — *Failures in frontend mock fallbacks, silent Coinbase failover, model registry divergence, and selective test suite reporting.*

---

## 3. Master Decision Determination

$$\mathbf{FINAL\ GOVERNANCE\ DECISION:}\quad \mathbf{APPLICATION\_DEFECTS\_FOUND}$$

### Governing Rationale:
BTCognitive has successfully established high-integrity market data ingestion on Bitstamp, causal regime tracking, and permanent strategy deprecation of negative-expectancy breakout trading. However, **the application cannot be certified as fully release-ready** due to 8 verified defects spanning frontend synthetic data substitution, omitted test suites, silent cross-exchange fallback, model registry divergence, and Bartlett kernel omission in statistical tests. 

Milestone V35.3 must prioritize remediation of these 8 items before production sign-off.

