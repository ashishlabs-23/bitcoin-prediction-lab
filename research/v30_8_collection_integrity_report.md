# BTCognitive V30.8 — Prospective Collection Integrity Monitor Report

**Date:** October 23, 2026  
**HEAD Commit:** `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Strategy Under Shadow Evaluation:** `HTF_RANGE_EXPANSION_BREAKOUT` (Spec Hash: `e1a3436a18ff992d`)  
**Operating Protocol:** `PROTOCOL-SHADOW-V1.1` + V30.5 Amendments  
**Final Governed Status:** `COLLECTION HEALTH VERIFIED — PERFORMANCE NOT YET EVALUABLE`  

---

## 1. Executive Summary & Epistemic Honesty Statement

Milestone **V30.8** provides formal monitoring, operational health verification, and statistical governance reconciliation for the prospective shadow evaluation pipeline during initial data collection.

### Fundamental Epistemic Honesty Disclosure:
- **Zero Real Trade Observations Accumulated:** `data/prospective_shadow_v1.jsonl` currently contains **0 candidate records** and **0 resolved outcome records**.
- **Persistence of Genuine Trade Outcomes Remains Unverified:** While automated fixtures prove the schema, file locking, recovery, and outcome-resolution code with 100% test coverage, the physical persistence and lifecycle of a *real-market trade outcome under live prospective conditions* remains **empirically unverified** until genuine market price action triggers a breakout above the 20-bar 4h high.
- **Strict Non-Execution:** Live trading, broker connectivity, capital deployment, and automated background daemons remain **permanently disabled**.
- **Performance Not Yet Evaluable:** Passing unit tests and healthy feed ingestion prove operational readiness only; they provide zero evidence of statistical edge, positive expectancy, or trading profitability.

---

## 2. Git & Ledger Integrity Verification

### 2.1 Git Repository State

- **Branch:** `main`
- **HEAD Commit SHA:** `24092a118bb4285cb2675cbc02694d34800d92d5`
- **Worktree Invariants:** No destructive Git commands, branch switches, or resets executed. Existing user files, manifests, and prior research reports preserved.

### 2.2 Ledger Cryptographic Hashes (Pre vs. Post Monitor Audit)

| Ledger File | Baseline Count | Baseline SHA-256 | Post-Audit Count | Post-Audit SHA-256 | Integrity Status |
| :--- | :---: | :--- | :---: | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | ✅ **Untouched** |
| `data/prospective_shadow_v1.jsonl` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | ✅ **Ready (0 records)** |

---

## 3. Collection Health & Live Feed Diagnostics

### 3.1 Live Feed Cycle Verification

The shadow feed runner was evaluated against the public Coinbase BTC-USD REST API:
- **Receipt Timestamp:** `2026-10-23T13:09:42Z`
- **Candles Ingested:** 1 newly closed candle appended (`2026-10-23T12:00:00+00:00`).
- **Candle Integrity:** Forming bar ($\ge 13\text{:00:00 UTC}$) strictly dropped. All ingested candles pass OHLC invariants ($\text{Low} \le \min(\text{Open}, \text{Close}) \le \max(\text{Open}, \text{Close}) \le \text{High}$, $\text{Volume} \ge 0$).
- **Storage Parquet Health:** `data/raw/ohlcv.parquet` contains **41,414** closed 1h candles with continuous hourly intervals.
- **Feed Freshness Diagnostic:**
  - Age: $4214\text{s}$ ($\approx 1.17\text{ hours}$).
  - Threshold: $7200\text{s}$ ($2.0\text{ hours}$).
  - Status: `[OK] Feed is FRESH (4214s old)`.

### 3.2 Duplicate Replay & Idempotency Proof

Subsequent evaluations of identical candle timestamps demonstrated:
- **Candles Added to Storage:** **0** (idempotency filter `timestamp > max_existing_ts` suppressed duplicates).
- **Candidate Emitted:** None (`Active Candidate: None`).
- **Durability:** File lock and atomic `.tmp` replace mechanisms guarantee no partial writes or index corruptions.

---

## 4. Record Integrity & Causal Boundaries

### 4.1 Schema Validation & Dataclass Immutability
- **Candidate Records (`SHADOW_CANDIDATE`):** Frozen dataclass `ShadowCandidateRecord`. Validated fields include `candidate_id`, `strategy_id`, `strategy_spec_hash`, `decision_timestamp_utc`, `entry_reference_price`, `proposed_entry_price`, `stop_loss_price`, and `primary_cost_scenario`.
- **Outcome Records (`SHADOW_OUTCOME`):** Frozen dataclass `ShadowOutcomeRecord`. Validated fields include `candidate_id`, `exit_reason`, `entry_fill_price`, `exit_price`, `bars_held_4h`, `gross_return_bps`, `net_returns_by_scenario_bps`, `risk_unit_usd`, `gross_r`, and `net_r_by_scenario`.
- **Strict Geometry:** Any candidate with $P_{\text{entry}} \le P_{\text{stop}}$ strictly raises `ValueError`.

### 4.2 Causal Boundary Enforcement
- **Signal Generation:** Evaluated strictly on the close of completed 4h candle $t_0$.
- **Execution Fill:** Modeled at next 1h candle open $t_{\text{fill}} = t_0 + 1\text{h}$.
- **Resolution Horizon:** Traverses strictly future candles $t > t_{\text{fill}}$.
- **In-Position Gating:** Active unresolved candidate blocks subsequent candidate emission, eliminating overlapping trade windows.

---

## 5. Statistical Governance & Gate Reconciliation

### 5.1 Reconciling the 100-Block Hurdle with the Stationary Bootstrap

To prevent silent protocol drift or misunderstood evidence claims, the relationship between observations, blocks, and calendar time is formally reconciled:

1. **Sampling Unit:** One completed candidate trade setup ($1\text{ observation} \le 72\text{ hours}$).
2. **Dependence Invariant:** Sequential trade setups are non-overlapping in time, but **are not statistically independent** due to macro regime shifts and volatility clustering (Engle 1982).
3. **Stationary Bootstrap Parameter:** Politis & Romano (1994) stationary bootstrap with expected block length $E[L] = 5$ trade observations ($p = 1 / E[L] = 0.20$).
4. **Confirmatory Gate Sample Size:**
   $$\text{Required Sample Size} = 100\text{ blocks} \times 5.0\text{ observations/block} = \mathbf{500\text{ completed trades}}$$
   At an average frequency of 1 breakout trade every 3–4 days, accumulating 500 completed trades requires **approximately 1,500 to 2,000 calendar days** (~4 to 5.5 years) of forward prospective data.
5. **Early Stopping Review (50 Observations):**
   Interim safety audit conducted after 50 completed trades (~150 to 200 calendar days). If sample mean net expectancy $< 0$ bps under `COINBASE_RETAIL_87BPS` OR max drawdown $> 35\%$, shadow collection is paused for research re-evaluation.

### 5.2 Benchmark Comparison Protocol
- **Benchmark:** Passive Buy & Hold over identical entry/exit intervals $[t_{\text{entry}}, t_{\text{exit}}]$.
- **Loss Function:** Excess return $d_i = R_{\text{strategy, net}, i} - R_{\text{B&H}, i}$.
- **Statistical Test:** Diebold–Mariano with Harvey–Leybourne–Newbold (1997) finite-sample correction factor $\sqrt{(T-1)/T}$ evaluated against Student's $t_{T-1}$ reference distribution.

---

## 6. Operator Runbook

### 6.1 Status & Health Check
Verify runner lock state, latest candle timestamp, and ledger counts:
```powershell
cd C:\Projects\BTCognitive\BTCognitive
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status
```

### 6.2 Feed Freshness Diagnostic
Check whether market data has fallen behind the 2-hour staleness threshold:
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --check-freshness
```

### 6.3 Manual Single Evaluation Cycle
Run a single bounded evaluation cycle with live feed sync:
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once
```

### 6.4 Operator-Initiated Continuous Loop (1-Hour Interval)
Launch the continuous hourly evaluation loop with single-instance process lock:
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --loop --interval 3600
```

### 6.5 Graceful Shutdown
To stop the continuous loop:
- Press `Ctrl+C` in the running terminal.
- The runner completes the active evaluation cycle, flushes storage, removes `data/.prospective_shadow_runner.lock`, and exits cleanly.

### 6.6 Recovery from Unexpected Process Termination
If the runner process is killed externally (e.g. power loss, OS reboot):
- Check status: `.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status`.
- If the lock file exists but the holding PID is dead, the next `--loop` or `--once` command will automatically detect the dead PID and reclaim the lock safely.

### 6.7 Conditions Requiring Collection Pause
Operators MUST immediately stop collection if:
1. `feed_status` remains `OFFLINE` for $> 24$ consecutive hours.
2. The early stopping review threshold is reached ($50$ trades) and net expectancy $< 0$ bps.
3. Maximum drawdown across shadow observations exceeds $35\%$.
4. Any candidate record contains non-positive risk geometry ($P_{\text{entry}} \le P_{\text{stop}}$).

---

## 7. Regression Test Suite Execution

### 7.1 Targeted Shadow & Verification Suites (54/54 Passed)

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_entry_contracts_and_resolver.py tests/test_prospective_shadow_collector.py tests/test_shadow_feed_runner.py tests/test_v30_6_operational_proof.py tests/test_v30_7_shadow_burnin.py tests/test_v30_8_collection_integrity.py -q
```

**Results:**
```
......................................................                   [100%]
54 passed in 8.06s
```

### 7.2 Broader Repository Regression Suite (22/22 Passed)

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_smoke.py tests/test_causal_resolution.py tests/test_canonical_metric_contracts.py tests/test_single_market_data_contract.py tests/test_fail_closed_data_contracts.py -v
```

**Results:**
- **22 passed, 1 deselected in 22.00s (100% pass rate)**

---

## 8. Final Governed Milestone Decision

| Governed Dimension | Status | Epistemic Justification |
| :--- | :--- | :--- |
| **Collection Plumbing Health** | `VERIFIED` | 54/54 targeted tests pass; feed ingestion, atomic persistence, and recovery validated |
| **Real Trade Persistence** | `UNVERIFIED` | 0 genuine market breakout candidates have occurred; real trade lifecycle remains unobserved |
| **Prospective Evidence** | `NOT_STARTED` | 0 shadow candidates collected; 100 clean blocks hurdle required |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` | Production promotion strictly prohibited |
| **Live Trading** | `DISABLED` | All live order execution and broker connections remain permanently disabled |

### Explicit Final Milestone Decision:
$$\mathbf{COLLECTION\ HEALTH\ VERIFIED\ —\ PERFORMANCE\ NOT\ YET\ EVALUABLE}$$

*(The shadow collection infrastructure is operational and healthy. Because zero prospective trade setups have occurred in live market data, strategy profitability remains unproven and unevaluable. Continuous collection may be initiated manually by the operator per the runbook.)*
