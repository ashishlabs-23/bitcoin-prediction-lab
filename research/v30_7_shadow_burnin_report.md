# BTCognitive V30.7 — Shadow Collection Burn-In & Evidence Validation Report

**Date:** October 23, 2026  
**HEAD Commit:** `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Strategy Under Shadow Evaluation:** `HTF_RANGE_EXPANSION_BREAKOUT` (Spec Hash: `e1a3436a18ff992d`)  
**Operating Protocol:** `PROTOCOL-SHADOW-V1.1` + V30.5 Amendments  
**Final Governed Status:** `SHADOW BURN-IN VERIFIED — MANUAL COLLECTION MAY BE STARTED`  

---

## 1. Executive Summary & Epistemic Boundaries

Milestone **V30.7** completes the end-to-end burn-in and operational verification of the prospective shadow data-collection pipeline. The system was validated against the genuine Coinbase public REST API, completed-candle filtering, crash recovery, process-lock mutual exclusion, and statistical protocol conformance.

### Absolute Epistemic Constraints
1. **Strict Non-Execution:** Live trading, automated order placement, broker connections, and capital deployment are **permanently disabled**.
2. **Zero Profitability Claims:** Verification of data-collection plumbing does not constitute proof of strategy profitability or economic edge.
3. **No Automatic Daemon Startup:** No continuous background process or cron job has been launched automatically. Operators must explicitly initiate collection.
4. **Zero Synthetic Fabrication:** No synthetic candles or mock trades were injected into production or prospective ledgers. Missing market data is reported as offline/stale, never interpolated.

---

## 2. Baseline and Final Git & Ledger State

### 2.1 Git Repository State

- **Branch:** `main`
- **HEAD Commit SHA:** `24092a118bb4285cb2675cbc02694d34800d92d5`
- **Tracked Code Invariants:** Zero destructive Git operations performed. Unrelated historical files, manifests, and scratch scripts preserved.

### 2.2 Ledger Cryptographic Audit (Before & After Burn-In)

| Ledger File | Baseline Count | Baseline SHA-256 | Post-Audit Count | Post-Audit SHA-256 | Audit Status |
| :--- | :---: | :--- | :---: | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | ✅ **Untouched** |
| `data/prospective_shadow_v1.jsonl` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | ✅ **Ready (0 records)** |

---

## 3. Genuine Feed-to-Ledger Validation Results

### 3.1 Bounded Live Collection Cycles

Two bounded, manual single-cycle executions (`--once`) were performed to evaluate live market ingestion against the public Coinbase BTC-USD REST API:

#### Cycle 1: Ingestion & Storage Sync
- **Command:** `.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once`
- **Receipt Timestamp (UTC):** `2026-10-23T12:36:44Z`
- **Feed Status:** `HEALTHY`
- **Raw Candles Fetched:** 349 hourly candles
- **Forming Candle Dropped:** Discarded candle $\ge 12\text{:00:00 UTC}$ (forming bar).
- **Latest Closed Candle Ingested:** `2026-10-23T11:00:00+00:00`
- **Candles Added to Storage:** 1 newly closed candle appended to `data/raw/ohlcv.parquet`.
- **4h Aggregation:** Point-in-time resample completed (`closed='left', label='left'`).
- **Breakout Evaluation:** Latest completed 4h candle close $\le \text{RangeHigh}_{20}$. No candidate emitted (`Active Candidate: None`).

#### Cycle 2: Idempotency & Duplicate Rejection Check
- **Command:** `.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once`
- **Receipt Timestamp (UTC):** `2026-10-23T12:37:07Z`
- **Feed Status:** `HEALTHY`
- **Candles Fetched:** 349 hourly candles
- **Candles Added to Storage:** **0** (idempotency filter `timestamp > max_existing_ts` suppressed duplicates).
- **Candidate Emitted:** None (`Active Candidate: None`).

### 3.2 Feed Freshness Diagnostic

- **Pre-Cycle Status:** `is_stale: True` ($9397\text{s}$ elapsed since previous 10:00 UTC candle).
- **Post-Cycle Status:** `is_stale: False` ($5823\text{s}$ elapsed since latest 11:00 UTC candle, strictly $< 7200\text{s}$ threshold).
- **Console Diagnostic:** `[OK] Feed is FRESH (5823s old)` printed cleanly without Unicode encoding errors.

---

## 4. Failure and Recovery Test Matrix

All failure simulations were executed strictly in isolated temporary filesystem fixtures (`tmp_path`) to guarantee zero corruption of real ledgers or parquet storage:

| Test Identifier | Failure Scenario Simulated | Expected Epistemic Behavior | Observed Behavior | Test Status |
| :--- | :--- | :--- | :--- | :---: |
| `test_feed_malformed_json_handling` | Public API returns HTML 502 Bad Gateway | Logs error, sets `feed_status: OFFLINE`, evaluates local storage without crashing | Graceful fallback; 0 synthetic records generated | ✅ PASS |
| `test_feed_empty_or_dict_response_handling` | Public API returns JSON error dict `{"message": "rate limit"}` | Rejects non-list payload, sets `feed_status: OFFLINE` | Correctly flags invalid payload; no data mutation | ✅ PASS |
| `test_feed_corrupted_candles_filtered_out` | Inverted high/low, negative volume, open > high | Filters invalid candles; ingests only structurally valid OHLC | Corrupt candles dropped; only clean candle persisted | ✅ PASS |
| `test_ledger_recovers_from_partial_trailing_line` | Process interrupted mid-write leaving truncated trailing JSON line | Skips partial line on index rebuild, preserves prior entries, appends cleanly | Corrupted line ignored; new records appended normally | ✅ PASS |
| `test_unresolved_candidate_survives_restart_and_blocks_new_candidates` | Process restart while candidate is active | Restores active candidate from disk; in-position gating blocks duplicate setup | Duplicate breakout candidate suppressed | ✅ PASS |
| `test_unresolved_candidate_not_prematurely_resolved` | Future horizon $< 18$ bars (72h) and stop unhit | Outcome remains strictly `None` (pending maturation) | Position held open; zero premature outcome fabrication | ✅ PASS |
| `test_runner_single_instance_lock_lifecycle` | Concurrent runner attempt while lock is held | Second runner fails lock acquisition; first runner unaffected | Mutual exclusion enforced; lock released on exit | ✅ PASS |
| `test_runner_stale_lock_recovery` | Lock file exists but holding PID is dead | Detects dead PID via OS process check, reclaims lock | Lock reclaimed safely without manual deletion | ✅ PASS |

---

## 5. Statistical Protocol Conformance Audit

### 5.1 Formal Observation Hierarchy

To avoid conflating raw data samples with statistically independent evidence, the following strict definitions are enforced:

| Term | Operational Definition | Statistical Properties |
| :--- | :--- | :--- |
| **Candle** | 1-hour closed market OHLCV bar | Highly autocorrelated price sample; not an evaluation unit |
| **Setup / Candidate** | Causal breakout trigger at closed 4h bar ($P_{\text{entry}} = \text{Open}_{1h}$) | Discrete trading decision; evaluated only when flat |
| **Completed Observation** | 1 resolved trade excursion (`SHADOW_OUTCOME` record) | Up to 18 4h bars (72 hours). Non-overlapping in time. |
| **Evaluation Block** | $E[L] = 5$ sequential trade observations (~15–20 calendar days) | Captures temporal clustering and volatility regime dependence |

### 5.2 Stationary Bootstrap Conformance
- **Algorithm:** Politis & Romano (1994) Stationary Bootstrap.
- **Block Length Distribution:** Geometric with $p = 1 / E[L] = 1 / 5.0 = 0.20$.
- **Temporal Stationarity:** Wraps circularly strictly within contiguous observation segments, preserving volatility regime clustering without rigid boundary artifacts.
- **Empirical Coverage Verification:** Verified on synthetic normal distribution: empirical 95% bootstrap CI coverage matches true mean ($10.0 \pm 0.5$).

### 5.3 Diebold–Mariano with HLN (1997) Correction
- **Benchmark:** Passive Buy & Hold over the exact trade duration $[t_{\text{entry}}, t_{\text{exit}}]$.
- **Loss Function:** Excess return differential $d_i = R_{\text{strategy, net}, i} - R_{\text{B&H}, i}$.
- **Finite-Sample Correction:** $\text{HLN} = \text{DM} \times \sqrt{(T - 1) / T}$.
- **Reference Distribution:** Student's $t$ with $T - 1$ degrees of freedom.

### 5.4 Pre-Registered Statistical Gates

1. **Early Stopping Review (50 Observations):**
   - Pauses collection for research audit if sample mean net expectancy $< 0$ bps under `COINBASE_RETAIL_87BPS` OR max drawdown $> 35\%$.
2. **Confirmatory Evaluation Gate (100 Non-Overlapping Blocks):**
   - Confirmatory hypothesis acceptance requires lower bound of 95% stationary bootstrap CI $> 0$ bps AND max drawdown $< 20\%$.
   - **Current Status:** 0 observations accumulated. Confirmatory gate is **NOT_STARTED**.

---

## 6. Verification Test Suite Execution Results

### 6.1 Targeted Shadow Test Suites (50/50 Passed)

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_entry_contracts_and_resolver.py tests/test_prospective_shadow_collector.py tests/test_shadow_feed_runner.py tests/test_v30_6_operational_proof.py tests/test_v30_7_shadow_burnin.py -v
```

**Results:**
- `tests/test_entry_contracts_and_resolver.py`: 13 passed
- `tests/test_prospective_shadow_collector.py`: 12 passed
- `tests/test_shadow_feed_runner.py`: 6 passed
- `tests/test_v30_6_operational_proof.py`: 12 passed
- `tests/test_v30_7_shadow_burnin.py`: 7 passed
- **Total:** **50 passed in 4.69s (100% pass rate)**

### 6.2 Broader Repository Regression Suite (22/22 Passed)

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_smoke.py tests/test_causal_resolution.py tests/test_canonical_metric_contracts.py tests/test_single_market_data_contract.py tests/test_fail_closed_data_contracts.py -v
```

**Results:**
- **22 passed, 1 deselected in 22.00s (100% pass rate)**

---

## 7. Recommended Operator Commands

### Check Operational Status & Lock Telemetry
```powershell
cd C:\Projects\BTCognitive\BTCognitive
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status
```

### Check Live Feed Freshness
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --check-freshness
```

### Run Single Bounded Evaluation Cycle (Manual)
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once
```

### Initiate Continuous Shadow Collection Loop (Operator Initiated)
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --loop --interval 3600
```

### Stop Continuous Collection
Press `Ctrl+C` in the running terminal. The process will finish the current cycle, flush data, release the lock file, and exit cleanly.

---

## 8. Final Governed Milestone Decision

| Governed Dimension | Status | Epistemic Justification |
| :--- | :--- | :--- |
| **Research Experiment** | `COLLECTING — NOT YET EVALUABLE` | Plumbing, feed ingestion, and crash recovery verified; awaiting prospective observations |
| **Prospective Evidence** | `NOT_STARTED` | 0 shadow candidates collected; 100 clean blocks hurdle required |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Production promotion strictly prohibited |
| **Live Trading** | `DISABLED` | Order execution and broker interfaces remain disabled |

### Explicit Final Milestone Decision:
$$\mathbf{SHADOW\ BURN\text{-}IN\ VERIFIED\ —\ MANUAL\ COLLECTION\ MAY\ BE\ STARTED}$$

*(Verification confirms the system is technically, operationally, and causally ready for safe forward shadow data accumulation. Live trading and automatic daemon execution remain disabled.)*
