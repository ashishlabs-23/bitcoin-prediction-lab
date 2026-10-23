# BTCognitive V7 — Independent Red-Team Audit, Input Freshness, Statistical Reproduction & Prospective Evidence Integrity

**Document Version:** 1.0.0  
**Audit Date:** 17 October 2026  
**Auditor / Lead Orchestrator:** Antigravity Research Orchestrator  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Base Commit SHA:** `01f87cad6d189eb4b4c70c0a52e4e759ed8d8eba`  
**Governed Release Verdict:** `V7_VERIFIED_WITHIN_DECLARED_SCOPE`  

---

## 1. Executive Summary & Final Governed Decisions

This independent red-team audit was conducted across the actual BTCognitive workspace following V6. In accordance with Section 1 and Section 2 of `AGENTS.md`, this is strictly an **audit-and-correct task, not a strategy-expansion task**. Generated labels, previous agent claims, and passing tests were independently challenged, reproduced from first principles, and tested on live running software.

### Four Authoritative Governed Decisions:
1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` (Challenger models remain offline; meta-label models show zero statistical edge over prevalence baselines).
2. **Prospective Evidence:** `COLLECTING` (1 strictly non-overlapping clean block resolved, 4 pending 168h blocks; hurdle requires $\ge 100$ clean blocks).
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY` (Restricted volatility serving authorized only for `HAR-RS-DOW-v1.0` 168h variance risk).
4. **Live Trading:** `DISABLED` (Permanent fail-closed invariant across all code, API routes, and interfaces).

---

## 2. Prime Directive & Epistemic Boundary Checks

| Invariant | PRD / AGENTS.md Rule | Workspace Ground Truth | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Strict Non-Execution** | No broker execution, order placement, or live capital. | **DISABLED** across all routes and configs. | `tests/test_forecast_activation_and_readiness.py::test_live_trading_prohibitions_fail_closed` PASSED |
| **Directional Gating** | 90% hit rate is an unproven research hypothesis; abstain on unconditional returns. | **ABSTAIN** permanently enforced on all live UI and API endpoints. | `desktop_live_view_1792232557054.png` (Action: `ABSTAIN`) |
| **Target Separation** | 24h realized variance (`rv24h_var_ann`) is distinct from 168h (`rv7d_var_ann`). | Segregated feature sets, distinct model targets, and separate ledger entries. | `tests/test_canonical_metric_contracts.py` PASSED |
| **No Synthetic Data** | Missing feeds must never be forward-filled or fabricated. | Strict gap preservation via `ContinuityTimeSeriesEngine`. | `tests/test_phase2_market_data_and_pit.py` PASSED |
| **Scheduler Compliance** | Do not register Windows Task Scheduler without explicit user sign-off. | **NOT REGISTERED** (`schtasks /Query` returns system cannot find specified file). | CLI execution: exit code 1 |

---

## 3. P0 — Audit of Scenario Planner Input Freshness & Contract (Agent A)

### Freshness Policy Specification:
- **Baseline Invariant:** Hourly closed candles are finalized once per hour.
- **Maximum Staleness Threshold:** $10,800.0\text{ seconds}$ (3.0 hours). This accommodates 1 hour for candle close plus a conservative 2-hour buffer for exchange network retrieval and batch processing.
- **Rejection Behavior:** Any market quote or volatility observation older than $10,800.0\text{s}$ relative to evaluation time ($t_{\text{as\_of}}$) triggers an explicit typed rejection:
  ```json
  {
    "status": "UNAVAILABLE",
    "rejection_code": "MARKET_DATA_STALE",
    "rejection_narrative": "Market data timestamp (...) is ...s old, exceeding conservative maximum allowable staleness threshold of 10800.0s (3.0 hours)."
  }
  ```
- **Provenance Metadata Exposed on API & UI:**
  - `source`: `"Coinbase Spot"`
  - `instrument`: `"BTC/USD"`
  - `source_timeframe`: `"1h"`
  - `reference_price_timestamp_utc` and `reference_price_age_seconds`
  - `latest_volatility_candle_timestamp_utc` and `volatility_data_age_seconds`
  - `volatility_lookback_start_utc`, `volatility_lookback_end_utc`, and `volatility_observation_count` (24 bars)
  - `continuity_segment_id`: `"seg_0"`
  - `volatility_units`: `"LOG_RETURN_STANDARD_DEVIATION"`
  - `horizon_scaling_method`: `"SQUARE_ROOT_OF_TIME_APPROXIMATION"`
  - `horizon_scaling_notice`: Explicit Brownian increment caveat.

### Formula Verification:
The mathematical formulas compute exact log-return volatility brackets:
$$\text{LONG: } \text{TP} = P \cdot e^{+k_{\text{tp}}\sigma_H}, \quad \text{SL} = P \cdot e^{-k_{\text{sl}}\sigma_H}$$
$$\text{SHORT: } \text{TP} = P \cdot e^{-k_{\text{tp}}\sigma_H}, \quad \text{SL} = P \cdot e^{+k_{\text{sl}}\sigma_H}$$
Where $\sigma_H = \sigma_{1\text{h}} \sqrt{H}$, $k_{\text{tp}} = 1.5$, $k_{\text{sl}} = 1.0$.
- Known-Answer Verification: At $P = 80,000.00$, $\sigma_{1\text{h}} = 0.01$, $H = 4$:
  - $\text{LONG: } \text{TP} = 82,436.36$, $\text{SL} = 78,415.89$, $\text{Gross R:R} = 1.54$.
  - $\text{SHORT: } \text{TP} = 77,635.64$, $\text{SL} = 81,616.11$, $\text{Gross R:R} = 1.46$.
  - Invariants strictly confirmed: $\text{SL} < \text{Entry} < \text{TP}$ (LONG) and $\text{TP} < \text{Entry} < \text{SL}$ (SHORT).

### Horizon & Rejection Coverage:
- Supported: `1h`, `4h`, `24h` compute successfully.
- Sub-hourly (`15m`, `5m`, `30m`): Explicitly rejected with `DATA_FREQUENCY_UNSUPPORTED`.
- Invalid custom entries ($0$, negative, NaN, Inf): Explicitly rejected with `INVALID_CUSTOM_ENTRY_PRICE`.
- Data gaps / insufficient history ($<25$ bars): Explicitly rejected with `INSUFFICIENT_CONTINUOUS_HISTORY`.
- UI Integration: In `web/app.js`, the `15m` button is visibly styled with a warning badge `15m (UNSUPPORTED)` and dashed border. When clicked, it renders the typed rejection notice without leaving stale numerical levels in the UI.

---

## 4. P0 — Independent Statistical Inference Reproduction (Agent B)

### Audit & Reproduction of V6 Inference Artifact:
Executed from first principles via [run_v7_statistical_reproduction.py](file:///c:/Projects/BTCognitive/BTCognitive/research/run_v7_statistical_reproduction.py) on `data/raw/ohlcv.parquet` (41,267 closed hourly bars).

#### 1. Paired Meta-Label Loss Differentials (Sign Convention: $\text{Challenger Loss} - \text{Baseline Loss}$):
- **15 bps Economic Target (`CAND-3A`):**
  - Model Brier Score: $0.246420$ | Baseline Prevalence Brier Score: $0.246089$
  - Mean Paired Difference: $+0.000331$ (Positive favors baseline).
  - V5 Naive IID 95% CI: $[+0.000050, +0.000614]$ (Artificially narrow, SE = $0.000141$).
  - V7 Stationary Bootstrap 95% CI ($L=24$): $[-0.000551, +0.001274]$ (SE = $0.000458$, Expansion Factor = $3.25\times$).
  - Sensitivity across $L \in \{12, 24, 48\}$:
    - $L=12$: $[-0.000490, +0.001146]$
    - $L=24$: $[-0.000551, +0.001274]$
    - $L=48$: $[-0.000573, +0.001307]$
  - Statistical Verdict: `INCONCLUSIVE_INTERVAL_CROSSES_ZERO` (Zero statistical superiority over constant prevalence).
- **87 bps Economic Target (`CAND-3B`):**
  - Model Brier Score: $0.2057$ | Baseline Prevalence: $0.2061$
  - Mean Paired Difference: $-0.000447$
  - V7 Stationary Bootstrap 95% CI ($L=24$): $[-0.001346, +0.000454]$
  - Statistical Verdict: `INCONCLUSIVE_INTERVAL_CROSSES_ZERO`.

#### 2. Candidate 1 Momentum Net Expectancy:
- **Coinbase Spot (87.0 bps two-sided friction):**
  - Point Estimate: $-78.09\text{ bps}$
  - 95% CI ($L=24$): $[-96.42, -57.98]\text{ bps}$
  - Statistical Verdict: `FAIL_DECISIVELY_NEGATIVE` (Strictly below zero across all block lengths).
- **Binance Hypothetical (15.0 bps friction):**
  - Point Estimate: $-6.09\text{ bps}$
  - 95% CI ($L=24$): $[-24.42, +14.02]\text{ bps}$
  - Statistical Verdict: `INCONCLUSIVE_INTERVAL_CROSSES_ZERO`.

#### 3. Investigation of the Discrepancy:
- **Observed Discrepancy:** Prompt inquired about the shift from IID $[0.000234, 0.000621]$ to conjectured $[-0.0182, +0.0241]$.
- **Root-Cause Finding:** The actual V6 artifact on disk (`v6_statistical_inference_audit.json:80`) contained $[-0.000490, +0.001244]$. The value $-0.0182$ was the empirical lag-1 return autocorrelation ($\rho_1 = -0.01824$, documented in `research/reports/application_necessity_and_accuracy_improvement_plan.md:32`). An earlier summary text confounded return autocorrelation with the Brier metric. Under both evaluations, the point estimate is positive ($+0.000331$, favoring baseline) and the interval crosses zero under dependence-aware resampling.

#### 4. Synthetic AR(1) Validation:
Tested a null process with $\phi = 0.7$ and $N = 2,000$. Theoretical SE inflation is $\sqrt{\frac{1+\phi}{1-\phi}} = 2.38\times$. Observed stationary bootstrap expansion factor was $1.97\times$, successfully capturing serial dependence and yielding a 95% CI that correctly covered zero.

---

## 5. P0 — Prospective Evidence Ledger Integrity & Operational Truthfulness (Agent C)

### Ledger Classification Breakdown:
Audit of `data/prospective_forecast_ledger.jsonl` (9 total records):
1. **`prospective-seed-001`:** `rv24h_var_ann`, issued 2026-08-31T06:00 UTC. **Status: SEEDED_HISTORICAL**. Excluded from confirmatory gate count.
2. **`b1203745-8d96-429c-973e-f35d1a49b843`:** `rv24h_var_ann`, issued 2026-10-15T17:00 UTC, matured 2026-10-16T17:00 UTC. **Status: RESOLVED**. Genuine prospective clean block 1.
3. **`3b3a58d9-f9ff-4425-a32d-a9c9c8d692a7`:** `rv7d_var_ann` (168h), issued 2026-10-15T17:00 UTC, matures 2026-10-22T17:00 UTC. **Status: PENDING**.
4. **`f5996bf2-c686-4ea2-8df7-583540187525`:** `rv24h_var_ann`, issued 2026-10-16T03:00 UTC, matured 2026-10-17T03:00 UTC. **Status: RESOLVED**. (Overlaps Record 2).
5. **`5657414d-2c9f-490f-bdf2-90de26e50f6c`:** `rv7d_var_ann` (168h), issued 2026-10-16T03:00 UTC, matures 2026-10-23T03:00 UTC. **Status: PENDING**.
6. **`0e4cfe1a-25af-464a-9a0c-c599308eb367`:** `rv24h_var_ann`, issued 2026-10-16T08:00 UTC, matured 2026-10-17T08:00 UTC. **Status: RESOLVED**. (Overlaps Record 2 & 4).
7. **`46b2e851-b1bb-4520-97a3-b2b437d3796b`:** `rv7d_var_ann` (168h), issued 2026-10-16T08:00 UTC, matures 2026-10-23T08:00 UTC. **Status: PENDING**.
8. **`382df521-c835-49d6-a3d5-65e39ac5d825`:** `rv24h_var_ann`, issued 2026-10-16T09:00 UTC, matured 2026-10-17T09:00 UTC. **Status: RESOLVED**. (Overlaps previous 24h windows).
9. **`5200cda4-1d8b-41cf-bdd1-09769ccc8c80`:** `rv7d_var_ann` (168h), issued 2026-10-16T09:00 UTC, matures 2026-10-23T09:00 UTC. **Status: PENDING**.

### Summary Reconciliation:
- Total Logged Records: **9**
- Matured Resolved: **5** (1 seed + 4 24h prospective)
- Pending Maturation: **4** (All four 168h forecasts)
- Strictly Non-Overlapping Resolved 24h Blocks: **1 block**
- Confirmatory Gate Hurdle: **100 clean non-overlapping blocks**
- Gate Progress: `1 / 100` clean blocks (`is_sufficient_for_confirmatory = false`).
- Operational State: `STANDALONE_CLI_SCHEDULED`.
- Windows Task Scheduler: **NOT CONFIGURED** (confirmed via `schtasks /Query`).

---

## 6. P1 — Browser Subagent End-to-End Red-Team Audit (Agent E)

The dedicated `/browser` subagent conducted independent tests of the live web application at `http://127.0.0.1:8000/#/live`.

| Test Inspection | Desktop (`1440 × 900`) | Mobile (`390 × 844`) | Status | Evidence Path |
| :--- | :--- | :--- | :--- | :--- |
| **Top Signal Banner** | `Action: ABSTAIN`, `Trading: DISABLED` | `Action: ABSTAIN`, `Trading: DISABLED` | `PASS` | `desktop_live_view_1792232557054.png` |
| **Scenario Badge** | `NON-ACTIONABLE RESEARCH` | `NON-ACTIONABLE RESEARCH` | `PASS` | `desktop_live_view_1792232557054.png` |
| **Header Ribbon** | Verified Source: `Coinbase Spot`, Pair: `BTC/USD`, Vol: `18.570%`, Segment: `seg_0` | Re-wrapped cleanly, readable font | `PASS` | `desktop_live_view_1792232557054.png` |
| **Horizon Switching** | `4h` and `1h` updated levels dynamically ($\sigma_H$ changed from 18.570% to 7.581% to 3.791%) | Horizon pills responsive | `PASS` | Browser subagent log |
| **Unsupported `15m`** | Clicked `15m (UNSUPPORTED)`; table disappeared and `DATA_FREQUENCY_UNSUPPORTED` alert appeared | Rejection banner fits mobile viewport | `PASS` | Browser subagent log |
| **Custom Entry** | Input `95000` -> applied `[USER CUSTOM ANCHOR]` with levels around $95,000 -> clicked Reset | Form inputs accessible and functional | `PASS` | Browser subagent log |
| **Signal Invariance** | Active signal remained strictly `ABSTAIN` throughout all interactions | Active signal unchanged | `PASS` | `desktop_live_view_1792232557054.png` |

---

## 7. P1 — Full Regression Suite & Verification Counts (Agent F)

Core test execution command:
```powershell
.\.venv_win\Scripts\python.exe -m pytest tests/test_scenario_freshness_and_contract_v7.py tests/test_scenario_planner_and_inference_v6.py tests/test_prospective_worker_and_resilience.py tests/test_experiment_freeze_and_statistical_integrity_v5.py tests/test_phase_24h_qlike_and_prospective.py tests/test_signal_integrity_and_risk_engine.py tests/test_forecast_activation_and_readiness.py -v
```

### Verified Test Outcome:
- **Total Tests Executed:** 82
- **Passed:** 82
- **Failed:** 0
- **Skipped:** 0
- **Warnings:** 1 (benign Starlette testclient deprecation warning)
- **Exit Code:** `0`
- **Execution Time:** 53.58 seconds

---

## 8. File-by-File Diff Summary

1. `engine/scenario_contract_engine.py`:
   - Added conservative 3.0-hour (`10,800.0s`) staleness policy rejecting stale data with `MARKET_DATA_STALE`.
   - Exposes full input provenance metadata: source, pair, timestamps, ages, continuity segment, units, scaling method, and explicit Brownian increment notice.
2. `web/app.js`:
   - Updated Scenario Planner horizon buttons to style `15m` visibly as `15m (UNSUPPORTED)` with dashed warning border.
   - Enhanced subheader context ribbon to display data age, segment ID, and pair.
   - Hardened rejection box rendering for all typed rejections.
3. `tests/test_scenario_freshness_and_contract_v7.py`:
   - Created comprehensive test suite covering mathematical verification, 1h/4h/24h supported horizons, custom entry anchors, sub-hourly rejections, stale data rejection, gap preservation, and signal gate non-interference. (9/9 passed).
4. `research/run_v7_statistical_reproduction.py`:
   - Independent script reproducing candidate expectancy, paired Brier and log-loss differences across $L \in \{12, 24, 48\}$, synthetic AR(1) control checks, and discrepancy investigation.
5. `experiments/results/research_improvement/v7_statistical_inference_audit.json`:
   - Versioned numerical audit artifact recording reproduced metrics and governance interpretations.
6. `experiments/results/research_improvement/v7_evidence_manifest.json`:
   - Machine-readable evidence manifest capturing all source hashes, test results, and browser artifacts.
7. `docs/PROSPECTIVE_WORKER_RUNBOOK.md`:
   - Updated operational runbook with audited 9-record ledger classification, dry-run procedures, and confirmation that the Windows Task Scheduler is NOT registered.
8. `docs/BTCognitive_PRD_Traceability_Matrix.md`:
   - Reconciled PRD traceability matrix to version 2.2.0, adding PRD-PLN-23, PRD-BST-24, PRD-PRP-25, and PRD-AUD-26 (21 verified, 2 partial, 1 blocked research gate, 1 deferred, 1 obsolete).
9. `tests/test_experiment_freeze_and_statistical_integrity_v5.py`:
   - Repaired rigid `len(records) == 5` assertion to `>= 5` to preserve append-only monotonicity.

---

## 9. Final Release Verdict

```text
================================================================================
FINAL GOVERNED VERDICT: V7_VERIFIED_WITHIN_DECLARED_SCOPE
================================================================================
- Directional Signals: Gated / OFFLINE_RESEARCH_ONLY (Action: ABSTAIN).
- Live Trading / Broker Execution: Permanently DISABLED.
- Scenario Planner: Verified non-actionable hypothetical tool with 3.0h freshness guard.
- Statistical Inference: Independently reproduced; zero meta-label superiority confirmed.
- Prospective Evidence: COLLECTING (1/100 clean blocks; Scheduler NOT registered).
- Full Core Regression: 82 passed, 0 failed (Exit code 0).
- Live Browser Verification: Confirmed on Desktop (1440x900) and Mobile (390x844).
================================================================================
```
