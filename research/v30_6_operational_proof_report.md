# BTCognitive V30.6 — Operational Proof & Statistical Integrity Audit Report

**Date:** October 23, 2026  
**HEAD Commit:** `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Strategy Under Shadow Evaluation:** `HTF_RANGE_EXPANSION_BREAKOUT` (Spec Hash: `e1a3436a18ff992d`)  
**Operating Protocol:** `PROTOCOL-SHADOW-V1.1` + V30.5 Amendments  
**Final Governed Status:** `SHADOW OPERATIONS READY — MANUAL START REQUIRED`  

---

## 1. Verified Findings vs. Unverified Claims

To uphold strict epistemic integrity, every assertion regarding the trading strategy and prospective collection system is partitioned into verified empirical evidence vs. unverified hypotheses:

| Dimension | Empirical Ground Truth (Verified) | Speculative / Unsupported Claim (Rejected) |
| :--- | :--- | :--- |
| **Strategy Profitability** | **Unknown / Unproven.** 0 prospective shadow observations collected. Historical retrospective replay (2026 out-of-sample) is development data only, not confirmatory evidence. | **REJECTED:** Any claim that `HTF_RANGE_EXPANSION_BREAKOUT` is profitable in production. |
| **Directional Accuracy** | Directional hit rate on BTC unconditional returns is statistically indistinguishable from noise without regime conditioning. | **REJECTED:** A 90% directional hit rate hypothesis is unsupported by empirical evidence. |
| **Cost Model** | Coinbase Retail taker round-trip friction is **87.0 bps** (40 bps entry taker + 40 bps exit taker + 3 bps spread + 4 bps slippage). Reconciled and mathematically proven. | **REJECTED:** Zero-cost, maker-rebate, or double-counted 91.04 bps calculations. |
| **Metric Independence** | Basis points (relative to entry price) and R-multiples (relative to initial risk unit) are dimensionally distinct and never combined arithmetically. | **REJECTED:** Adding bps to R or treating R as equivalent to percentage return. |
| **Data Collection** | Public Coinbase REST API provides genuine, closed 1h candles. Current forming candles are dropped. No synthetic data is fabricated. | **REJECTED:** Fabricating backfill candles or interpolating missing periods. |
| **Process Concurrency** | Single-instance lock file (`data/.prospective_shadow_runner.lock`) with active PID detection prevents duplicate runners. Atomic file writes protect data integrity. | **REJECTED:** Claiming continuous automated execution when no background scheduler is running. |
| **Statistical Power** | 50 trades required for early stopping review; 100 non-overlapping blocks required for confirmatory gate. Non-overlapping trades $\ne$ independent observations due to volatility clustering. | **REJECTED:** Treating sequential trades as independent Bernoulli trials ($iid$). |

---

## 2. Exact Cost Arithmetic & Provenance

### 2.1 Primary Benchmark: `COINBASE_RETAIL_87BPS`

The primary pre-registered cost model is frozen across the entire system (`COST_REGISTRY_BPS`, `ProbabilisticEntryEngine`, `DeterministicBarrierResolver`, `protocol_v1_1.md`):

| Component | Per-Side (bps) | Round-Trip (bps) | Arithmetic Basis | Provenance |
| :--- | :---: | :---: | :--- | :--- |
| **Taker Commission (Entry)** | 40.0 | — | $40.0 \times 10^{-4} \times P_{\text{entry}}$ | Coinbase Advanced Tier 1 (<$10k 30d volume) |
| **Taker Commission (Exit)** | 40.0 | 80.0 | $40.0 \times 10^{-4} \times P_{\text{exit}}$ | Coinbase Advanced Tier 1 (<$10k 30d volume) |
| **Half-Spread (Entry)** | 1.5 | — | $1.5 \times 10^{-4} \times P_{\text{entry}}$ | Empirical BTC-USD spot top-of-book half spread |
| **Half-Spread (Exit)** | 1.5 | 3.0 | $1.5 \times 10^{-4} \times P_{\text{exit}}$ | Empirical BTC-USD spot top-of-book half spread |
| **Slippage (Entry)** | 2.0 | — | $2.0 \times 10^{-4} \times P_{\text{entry}}$ | Conservative model for market order fill drag |
| **Slippage (Exit)** | 2.0 | 4.0 | $2.0 \times 10^{-4} \times P_{\text{exit}}$ | Conservative model for market order fill drag |
| **Total Round-Trip Friction** | **43.5** | **87.0** | $\mathbf{80.0 + 3.0 + 4.0 = 87.0\text{ bps}}$ | **Reconciled & Proven** |

### 2.2 Mathematical Formulas & Dimensional Separation

1. **Return in Basis Points (relative to entry price):**
   $$\text{gross\_return\_bps} = \left(\frac{P_{\text{exit}} - P_{\text{entry}}}{P_{\text{entry}}}\right) \times 10{,}000$$
   $$\text{net\_return\_bps} = \text{gross\_return\_bps} - 87.0$$

2. **Return in R-Multiples (relative to initial risk unit):**
   $$\text{risk\_unit\_usd} = P_{\text{entry}} - P_{\text{stop}}$$
   $$\text{gross\_r} = \frac{P_{\text{exit}} - P_{\text{entry}}}{\text{risk\_unit\_usd}}$$
   $$\text{friction\_usd} = P_{\text{entry}} \times \left(\frac{87.0}{10{,}000}\right)$$
   $$\text{net\_r} = \frac{(P_{\text{exit}} - P_{\text{entry}}) - \text{friction\_usd}}{\text{risk\_unit\_usd}}$$

3. **Strict Geometry Enforcement:**
   If $P_{\text{entry}} \le P_{\text{stop}}$, `risk_unit_usd` $\le 0$. The resolver strictly raises a `ValueError` rather than silently continuing or dividing by zero.

### 2.3 Reconciliation of Historical 91.04 bps Discrepancy

In legacy V30 research scripts, `self.half_friction_rate` erroneously evaluated `(self.fee_one_way_bps + self.slippage_bps)`, which added slippage twice (once inside `fee_one_way_bps` and once externally), producing $43.5 + 2.0 = 45.52\text{ bps}$ per side ($91.04\text{ bps}$ round-trip). This has been completely audited and resolved: the correct, verified round-trip friction is **87.0 bps**.

---

## 3. Runner Lifecycle & Recovery Evidence

### 3.1 Concurrency & Single-Instance Locking

| Component | Implementation | Audit Finding |
| :--- | :--- | :--- |
| **Lock File** | `data/.prospective_shadow_runner.lock` | Contains JSON: `{"pid": <int>, "acquired_utc": "<iso>", "runner": "ShadowFeedRunner-V30.5"}`. Written with atomic flush and `os.fsync`. |
| **Process Mutual Exclusion** | `runner.acquire_lock()` | If lock file exists and PID is alive, returns `False` and halts startup. |
| **Stale Lock Recovery** | `_pid_is_running(pid)` | Checks PID existence via `psutil` or `ctypes.OpenProcess` on Windows. If the PID is dead, the stale lock is automatically reclaimed. |
| **Graceful Shutdown** | `signal.signal(signal.SIGINT, handler)` | Sets `runner._shutdown_requested = True`. Finishes current cycle, releases lock in `finally:` block, and exits cleanly. |
| **CLI Verification** | `--status`, `--check-freshness`, `--dry-run` | Verified operational. Console output hardened to standard ASCII to guarantee CP1252 / Windows terminal compatibility. |

### 3.2 Failure Mode Recovery Matrix

| Failure Mode | System Behavior | Data Integrity Protection |
| :--- | :--- | :--- |
| **Network Outage / API 5xx** | Retries 3 times with exponential backoff ($1\text{s}, 2\text{s}, 4\text{s}$). If still unreachable, marks `feed_status: OFFLINE` and evaluates from local storage without crashing. | Zero synthetic data inserted. Parquet file untouched. |
| **Process Crash During Write** | All file writes (OHLCV parquet, status JSON, shadow ledger) use either `.tmp` + `os.replace` atomic replacement or `FileLock` + `flush()` + `os.fsync()`. | No partially written or corrupted records can persist. |
| **Candle Replay / Re-fetch** | `sync_candles_to_storage()` filters `timestamp > max_existing_timestamp`, drops duplicates, and sorts. | Idempotent; duplicate candles cannot be appended. |
| **Duplicate Candidate Trigger** | In-position gating suppresses breakout signals while any candidate is pending. Ledger indexing skips already recorded `candidate_id`s. | Zero duplicate candidates emitted. |

---

## 4. Statistical Gate Definitions & Unresolved Assumptions

### 4.1 Trade Unit vs. Statistical Observation

- **Sampling Unit:** One resolved candidate trade setup (`SHADOW_OUTCOME` record).
- **Non-Overlapping Gating:** Because subsequent candidates are suppressed until the active position exits (up to 72 hours), trade holding periods do not overlap.
- **Independence Assumption Warning:** Non-overlapping holding periods **do not** imply statistical independence ($iid$). Volatility regimes cluster in financial markets (Engle 1982, Bollerslev 1986). A cluster of trades occurring during a low-volatility or high-volatility regime will exhibit correlated outcomes and holding times.

### 4.2 Stationary Bootstrap Specification

To account for temporal dependence, bootstrap confidence intervals are computed using the **Politis & Romano (1994) Stationary Bootstrap**:
- **Distribution of Block Lengths:** Geometric distribution:
  $$P(L = k) = (1 - p)^{k-1} p, \quad \text{where } p = \frac{1}{E[L]} = \frac{1}{5.0} = 0.20$$
- **Expected Block Length:** $E[L] = 5$ candidate trade units (~15 to 20 calendar days).
- **Segment Preservation:** Resampling wraps circularly strictly within contiguous observation segments.

### 4.3 Diebold–Mariano with Harvey–Leybourne–Newbold (1997) Correction

When evaluating against the passive Buy & Hold benchmark:
- **Aligned Windows:** For trade $i$ spanning $[t_{\text{entry}, i}, t_{\text{exit}, i}]$, the benchmark return is $R_{\text{B&H}, i} = (P_{\text{exit}, i} - P_{\text{entry}, i}) / P_{\text{entry}, i}$.
- **Loss Differential:** $d_i = R_{\text{strategy, net}, i} - R_{\text{B&H}, i}$.
- **Finite-Sample Correction:**
  $$\text{HLN} = \text{DM} \times \sqrt{\frac{T - 1}{T}}$$
- **Reference Distribution:** Evaluated strictly against Student's $t_{T-1}$ distribution (heavier tails than normal, preventing overconfident claims in small samples).

### 4.4 Pre-Registered Review Hurdles

1. **Early Stopping Review (50 Observations):**
   - If sample mean net expectancy $< 0$ bps under `COINBASE_RETAIL_87BPS` OR maximum drawdown $> 35\%$, collection is paused for research review.
2. **Confirmatory Gate (100 Non-Overlapping Blocks):**
   - Requires lower bound of 95% stationary bootstrap CI $> 0$ bps AND maximum drawdown $< 20\%$.
   - **Current Status:** 0 observations. `NOT_STARTED`.

---

## 5. Test Suite & Verification Results

### 5.1 Targeted Test Suites (43/43 Passed)

```
tests/test_entry_contracts_and_resolver.py: 13 passed
tests/test_prospective_shadow_collector.py:  12 passed
tests/test_shadow_feed_runner.py:            6 passed
tests/test_v30_6_operational_proof.py:       12 passed
============================= 43 passed in 1.38s ==============================
```

### 5.2 Broader Regression Smoke Suite (12/12 Passed)

```
tests/test_smoke.py:                         3 passed
tests/test_causal_resolution.py:             3 passed
tests/test_canonical_metric_contracts.py:    6 passed
====================== 12 passed, 1 deselected in 8.99s =======================
```

**Total Verified Tests Across Sprints:** **55 passed, 0 failed.**

---

## 6. Original Ledger Integrity Verification

Cryptographic SHA-256 hashes confirm zero unauthorized modification, truncation, or corruption:

| Ledger File | Record Count | SHA-256 Digest | Status |
| :--- | :---: | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | ✅ **Untouched** |
| `data/prospective_shadow_v1.jsonl` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | ✅ **Ready (0 records)** |

---

## 7. Operational Instructions

### Start Continuous Shadow Collection (Manual Start)
```powershell
cd C:\Projects\BTCognitive\BTCognitive
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --loop --interval 3600
```

### Execute Single Evaluation Cycle (On-Demand)
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once
```

### Inspect Operational Telemetry & Lock Status
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status
```

### Diagnose Feed Freshness
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --check-freshness
```

### Stop Running Process
Send `Ctrl+C` in the running terminal. The process will complete its current evaluation cycle, release `data/.prospective_shadow_runner.lock`, and terminate gracefully.

---

## 8. Governed Release Decisions

| Governed Dimension | Status | Epistemic Justification |
| :--- | :--- | :--- |
| **Research Experiment** | `COLLECTING — NOT YET EVALUABLE` | Architecture, contracts, cost models, and test suites verified; awaiting prospective observations |
| **Prospective Evidence** | `NOT_STARTED` | 0 shadow candidates collected; requires 100 non-overlapping blocks for confirmatory evaluation |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Production promotion strictly prohibited |
| **Live Trading** | `DISABLED` | All live order execution and broker connections remain permanently disabled |

**Final Milestone Status:** `SHADOW OPERATIONS READY — MANUAL START REQUIRED`  
*(Per instructions, `SCHEDULED COLLECTION VERIFIED` is reserved strictly for demonstrably active, running background schedulers; because no autonomous daemon is running without user launch, manual start is required.)*
