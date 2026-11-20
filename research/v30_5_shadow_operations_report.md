# BTCognitive V30.5 — Shadow Operations, Cost Reconciliation & Statistical Gate Audit

**Date:** October 23, 2026  
**HEAD:** `24092a1`  
**Strategy Under Shadow Evaluation:** `HTF_RANGE_EXPANSION_BREAKOUT` (Spec Hash: `e1a3436a18ff992d`)  
**Protocol:** PROTOCOL-SHADOW-V1.1 + V30.5 Amendments  
**Final Status:** `SHADOW OPERATIONS READY — MANUAL START REQUIRED`

---

## 1. Executive Summary

V30.5 advances the BTCognitive shadow collection infrastructure from V30.4's single-shot operational readiness to a hardened, continuously-operable system with deterministic risk accounting, process-level concurrency control, and honest operational status reporting.

**No autonomous shadow collection is currently running.** The system has been verified and is ready for user-initiated manual collection via CLI.

---

## 2. Deliverables Completed

### 2.1 R-Multiple & Risk Geometry Hardening

| Change | File | Status |
| :--- | :--- | :---: |
| Added `risk_unit_usd`, `gross_r`, `net_r_by_scenario` to `ShadowOutcomeRecord` | `engine/prospective_shadow_collector.py` | ✅ |
| Replaced silent fallback with `ValueError` for zero/negative risk geometry | `engine/prospective_shadow_collector.py` | ✅ |
| Computed `net_r = [(exit - entry) - friction_usd] / risk_usd` per cost scenario | `engine/prospective_shadow_collector.py` | ✅ |
| Added `test_resolver_zero_or_negative_risk_rejected` | `tests/test_prospective_shadow_collector.py` | ✅ |
| Added gross_r / net_r assertions to stop-loss and horizon-timeout tests | `tests/test_prospective_shadow_collector.py` | ✅ |

**Hand-verified arithmetic:**
- Stop-loss case: Entry $80,200, Stop $78,000, Exit $78,000 → `risk_unit_usd = 2200.0`, `gross_r = -1.0`, `net_r(87bps) = (-2200 - 697.74) / 2200 = -1.3172 R` ✅
- Horizon-timeout case: Entry $80,200, Exit $80,800 → `gross_r = 600/2200 = 0.2727 R`, `net_r(87bps) = (600 - 697.74) / 2200 = -0.0444 R` ✅

### 2.2 Runner Single-Instance Lock

| Component | Description |
| :--- | :--- |
| Lock file | `data/.prospective_shadow_runner.lock` |
| Format | JSON: `{pid, acquired_utc, runner}` |
| Stale recovery | Checks PID liveness via `psutil` → `ctypes.OpenProcess` → `os.kill(pid, 0)` |
| Release | `finally` block ensures release on graceful exit or exception |

### 2.3 CLI Operational Controls

```
python -m engine.shadow_feed_runner --once              # Single cycle
python -m engine.shadow_feed_runner --loop --interval 3600  # Continuous (1h)
python -m engine.shadow_feed_runner --status            # Lock + telemetry
python -m engine.shadow_feed_runner --check-freshness   # Data age diagnostic
python -m engine.shadow_feed_runner --once --dry-run     # Read-only evaluation
Ctrl+C                                                  # Graceful loop shutdown
```

### 2.4 Stale Feed Detection

Pre-cycle freshness check at `STALE_FEED_THRESHOLD_SECONDS = 7200` (2 hours). If latest closed candle exceeds threshold, emits `WARNING` but proceeds — never fabricates synthetic data.

---

## 3. Cost Reconciliation Audit

### 3.1 Primary Cost Scenario: COINBASE_RETAIL_87BPS

| Component | Per-Side (bps) | Round-Trip (bps) |
| :--- | :---: | :---: |
| Taker Commission | 40.0 | 80.0 |
| Half Spread | 1.5 | 3.0 |
| Slippage Estimate | 2.0 | 4.0 |
| **Total** | **43.5** | **87.0** |

**Provenance:** Coinbase Advanced Tier 1 (<$10k 30d volume) taker fee schedule.

### 3.2 Bps vs R-Multiple Separation

- **Bps** measures return relative to entry price: `gross_return_bps = ((exit - entry) / entry) × 10000`
- **R-multiple** measures return relative to risk unit: `gross_r = (exit - entry) / (entry - stop)`
- **Net R** deducts friction in dollar terms, then divides by risk unit: `net_r = ((exit - entry) - friction_usd) / risk_usd`
- These are **dimensionally independent** and must never be arithmetically combined

### 3.3 Secondary Sensitivity Scenarios

| Scenario | RT bps | Purpose |
| :--- | :---: | :--- |
| `COINBASE_INSTITUTIONAL_18BPS` | 18.6 | High-volume institutional benchmark |
| `BINANCE_PERP_15BPS` | 15.0 | Perpetual futures sensitivity |
| `ADVERSE_STRESS_120BPS` | 120.0 | Adverse liquidity stress test |

**Rule:** Secondary scenarios inform sensitivity analysis only. All primary stopping rules and confidence intervals use `COINBASE_RETAIL_87BPS` exclusively.

---

## 4. Statistical Gate Alignment

| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| Sampling unit | 1 candidate trade setup (up to 18 × 4h bars = 72 hours) | Non-overlapping in-position gating eliminates return overlap |
| Bootstrap block length | $E[L] = 5$ trade observations (~15-20 calendar days) | Captures volatility regime clustering without extreme undersampling |
| Early stopping threshold | 50 observations | Pause if net expectancy < 0 bps OR max drawdown > 35% |
| Confirmatory gate | 100 non-overlapping blocks | Lower 95% bootstrap CI on net expectancy > 0 bps AND max DD < 20% |
| Paired comparison test | Diebold–Mariano with HLN (1997) correction | Paired vs Buy & Hold, $t_{T-1}$ reference distribution |
| Primary metric | Net Expectancy (bps) under `COINBASE_RETAIL_87BPS` | Net R reported as secondary normalized metric |

---

## 5. Test Suite Results

```
31 passed in 1.45s
```

| Test File | Tests | Status |
| :--- | :---: | :---: |
| `tests/test_entry_contracts_and_resolver.py` | 13 | ✅ All Pass |
| `tests/test_prospective_shadow_collector.py` | 12 | ✅ All Pass |
| `tests/test_shadow_feed_runner.py` | 6 | ✅ All Pass |

Key test coverage:
- `test_resolver_zero_or_negative_risk_rejected` — confirms `ValueError` on zero risk geometry
- `test_resolver_stop_loss_hit` — validates `risk_unit_usd`, `gross_r = -1.0`, `net_r = -1.3172`
- `test_resolver_horizon_timeout` — validates `gross_r = 0.2727`, `net_r = -0.0444`
- `test_cross_process_file_lock_synchronization` — verifies ledger-level `FileLock`
- `test_dry_run_does_not_mutate_ledger` — confirms `--dry-run` is non-destructive
- `test_existing_prospective_ledger_untouched` — confirms `prospective_entry_ledger.jsonl` is never modified

---

## 6. Ledger Integrity Verification

| Ledger | Lines | SHA-256 | Status |
| :--- | :---: | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | ✅ Untouched |
| `data/prospective_shadow_v1.jsonl` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | ✅ Empty (awaiting first prospective candidate) |

---

## 7. Operational Status

| Dimension | Status |
| :--- | :--- |
| Shadow runner daemon | **NOT RUNNING** — no active PID, no scheduled task |
| Runner lock | `INACTIVE` — no `.prospective_shadow_runner.lock` file |
| Shadow ledger records | 0 candidates, 0 outcomes |
| Prospective entry ledger | Intact (5 lines, SHA-256 verified) |
| Live trading | `DISABLED — ANALYSIS ONLY` |
| Governance | `OFFLINE_RESEARCH_ONLY` |
| Model authorization | `OFFLINE_RESEARCH_ONLY` |

---

## 8. User Operations Guide

### Start shadow collection (single cycle)
```powershell
cd C:\Projects\BTCognitive\BTCognitive
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --once
```

### Start continuous shadow collection
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --loop --interval 3600
```

### Check status
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status
```

### Check feed freshness
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --check-freshness
```

### Stop continuous collection
Press `Ctrl+C` — completes current cycle, releases lock, exits cleanly.

### Recovery from stale lock
If the runner was killed without cleanup:
```powershell
.venv_win\Scripts\python.exe -m engine.shadow_feed_runner --status
# If lock is stale (PID not running), next --loop invocation will auto-clear it
```

---

## 9. Governance Decisions

| Decision | Verdict |
| :--- | :--- |
| Research Experiment | `COLLECTING — NOT YET EVALUABLE` |
| Prospective Evidence | `NOT_STARTED` (0 shadow candidates collected) |
| Model Authorization | `OFFLINE_RESEARCH_ONLY` |
| Live Trading | `DISABLED` |

---

## 10. Files Modified in V30.5

| File | Change |
| :--- | :--- |
| `engine/prospective_shadow_collector.py` | Added `risk_unit_usd`, `gross_r`, `net_r_by_scenario` to `ShadowOutcomeRecord`; replaced zero-risk fallback with `ValueError` |
| `engine/shadow_feed_runner.py` | Added `_pid_is_running`, single-instance lock (`acquire_lock`/`release_lock`/`is_locked`), `check_freshness`, `--loop`/`--interval`/`--check-freshness` CLI, graceful SIGINT, stale-feed warning; version bump to V30.5 |
| `tests/test_prospective_shadow_collector.py` | Added `test_resolver_zero_or_negative_risk_rejected`; added `gross_r`, `net_r_by_scenario`, `risk_unit_usd` assertions |
| `tests/test_shadow_feed_runner.py` | Updated version assertion to V30.5 |
| `research/protocol_v1_1.md` | Added §5 V30.5 Amendments (R-multiple definitions, lock, CLI, staleness) |

**No files deleted. No existing APIs broken. No destructive Git operations performed.**
