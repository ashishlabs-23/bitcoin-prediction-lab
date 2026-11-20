# BTCognitive Prospective Shadow Evaluation Protocol V1.1

**Protocol ID:** PROTOCOL-SHADOW-V1.1  
**Supersedes:** Protocol V1.0 (V30.3)  
**Effective Date:** October 23, 2026  
**Governance Tier:** `OFFLINE_RESEARCH_ONLY`  
**Execution Authorization:** `DISABLED — ANALYSIS ONLY`  
**Target Strategy:** `HTF_RANGE_EXPANSION_BREAKOUT` (alias `STRATEGY_D_HTF_EXPANSION_V1`)  
**Specification Hash:** `e1a3436a18ff992d`  

---

## 1. Amendments & Rationale Over Protocol V1.0

| Issue Identified in V1.0 Audit | Protocol V1.1 Amendment | Epistemic Rationale |
| :--- | :--- | :--- |
| **Concurrency Hazard** | Replaced in-memory `threading.Lock()` with kernel-level cross-process `filelock.FileLock` (`data/.prospective_shadow_v1.jsonl.lock`). | Prevents simultaneous process execution (e.g. CLI runner + background task) from corrupting append-only jsonl records. |
| **Overlapping Trade Contamination** | Implemented strict in-position gating in `HTFShadowCollector`. Subsequent breakout signals while a position is open are suppressed. | Eliminates overlapping outcome windows, portfolio margin conflicts, and multi-candidate return dependence. |
| **Sampling Unit Ambiguity** | Clarified that **1 observation = 1 candidate trade setup** spanning up to 18 4h bars (72 hours). Underlying feed uses 1-hour candles. | Resolves confusion between 1-hour candle counts and 4-hour evaluation bars. |
| **Autocorrelation Block Length** | Adjusted stationary bootstrap block length to $E[L] = 5$ trade observations (~15–20 calendar days). | Trade observations are non-overlapping in time but subject to broader market volatility regime clustering. |
| **Metric Independence** | Primary metric is strictly **Net Expectancy in basis points** (`net_expectancy_bps`) under `COINBASE_RETAIL_87BPS`. Net R-multiple is reported strictly as a secondary normalized risk metric. | Eliminates mixing or arithmetic addition of basis points and R-multiples. |
| **Early Stopping vs Confirmatory Gate** | Clarified the 50-trade threshold as an **early research stop/pause rule** (if net expectancy $< 0$ or drawdown $> 35\%$). The 100-block hurdle remains the **confirmatory evidence gate**. | Distinctly separates risk mitigation from confirmatory hypothesis testing. |

---

## 2. Frozen Strategy Specification

- **Strategy Identifier:** `HTF_RANGE_EXPANSION_BREAKOUT`
- **Specification Hash:** `e1a3436a18ff992d`
- **Primary Instrument:** `BTC-USD` Spot on Coinbase Advanced
- **Timeframe:** 4-hour resampled from completed Coinbase 1-hour candles (`closed='left', label='left'`)
- **Lookback Window:** 20 closed 4-hour candles
- **Indicator Formulas:**
  - Range High: $\text{RangeHigh}_{20}(t) = \max_{k=1}^{20} \{ \text{High}_{t-k} \}$ (strictly `.shift(1).rolling(20).max()`)
  - Range Low: $\text{RangeLow}_{20}(t) = \min_{k=1}^{20} \{ \text{Low}_{t-k} \}$ (strictly `.shift(1).rolling(20).min()`)
- **Breakout Trigger:** $\text{Close}_{4h}(t_0) > \text{RangeHigh}_{20}(t_0)$ evaluated at candle close $t_0$.
- **Simulated Execution:** Earliest possible fill at next 1-hour candle open: $P_{\text{entry}} = \text{Open}_{1h}(t_{\text{fill}})$.
- **Stop Loss Level:** Frozen at decision time $t_0$ as $\text{RangeLow}_{20}(t_0)$.
- **Take Profit Level:** None (open excursion trend-follower).
- **Maximum Holding Horizon:** 18 4-hour candles (72 hours).
- **Exit Conditions:**
  - **Stop Loss Trigger:** If $\text{Low}_{4h} \le \text{StopLoss}$, exit at $\min(\text{StopLoss}, \text{Open}_{4h})$ (capturing opening gap slippage).
  - **Horizon Timeout:** If $\text{bars\_held} \ge 18$, exit at $\text{Close}_{4h}$.
- **Direction:** Long only. Short direction is disabled in Strategy D.

---

## 3. Cost Scenario Registry

| Scenario ID | Instrument | Venue | Round-Trip Friction (bps) | Breakdown (Entry/Exit Comm + Spread + Slip + Fund) | Role |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **`COINBASE_RETAIL_87BPS`** | BTC-USD Spot | Coinbase Advanced | **87.0** | 40.0 + 40.0 comm + 3.0 spread + 4.0 slippage | **Primary Pre-Registered Benchmark** |
| **`COINBASE_INSTITUTIONAL_18BPS`** | BTC-USD Spot | Coinbase Institutional | **18.6** | 8.0 + 8.0 comm + 1.0 spread + 1.6 slippage | Sensitivity Analysis Only |
| **`BINANCE_PERP_15BPS`** | BTCUSDT Perpetual | Binance USDT-M | **15.0** | 5.0 + 5.0 comm + 1.0 spread + 2.0 slip + 2.0 fund | Sensitivity Analysis Only |
| **`ADVERSE_STRESS_120BPS`** | BTC-USD Spot | Coinbase Advanced | **120.0** | 50.0 + 50.0 comm + 8.0 spread + 12.0 slippage | Stress Hurdle |

*Constraint:* All primary decisions, confidence intervals, and stopping rules are governed strictly by `COINBASE_RETAIL_87BPS`.

---

## 4. Feed & Ingestion Integrity Policies

1. **Closed-Candle Rule:** The candle currently forming ($\text{bar\_time} \ge \lfloor \text{now} / 3600 \rfloor \times 3600$) is strictly discarded. Only closed hourly bars enter feature pipelines.
2. **OHLC Integrity:** Any bar where $\text{Low} > \min(\text{Open}, \text{Close})$ or $\text{High} < \max(\text{Open}, \text{Close})$ or $\text{Volume} < 0$ is rejected as corrupt.
3. **Gap & Staleness Policy:** If the elapsed time between consecutive candles exceeds 3 hours, any candidate active during that gap is marked `data_quality_status = "GAP_EXCLUDED"` and disqualified from confirmatory metrics.
4. **Controlled Activation:** The collector runs only when explicitly invoked via manual CLI execution (`--once`) or a scheduled background loop (`--loop`). All loop modes enforce single-instance process locks with stale-PID recovery.

---

## 5. V30.5 Amendments — R-Multiple Accounting & Operational Hardening

**Amendment Date:** October 23, 2026  
**Supersedes:** Protocol V1.1 §4 item 4 (controlled activation)

### 5.1 R-Multiple & Risk Unit Definitions

Each `SHADOW_OUTCOME` record now carries three additional fields:

| Field | Definition | Formula |
| :--- | :--- | :--- |
| `risk_unit_usd` | Dollar risk per share/unit at entry | $1R = P_{\text{entry}} - P_{\text{stop}}$ (must be > 0) |
| `gross_r` | Gross R-multiple before friction | $(P_{\text{exit}} - P_{\text{entry}}) / 1R$ |
| `net_r_by_scenario` | Net R-multiple after scenario friction | $[(P_{\text{exit}} - P_{\text{entry}}) - \text{Friction}_{\text{USD}}] / 1R$ |

Where $\text{Friction}_{\text{USD}} = P_{\text{entry}} \times (\text{round\_trip\_bps} / 10{,}000)$.

**Strict separation rule:** Basis points and R-multiples must never be arithmetically combined. Net expectancy is reported in bps; net risk-adjusted return is reported in R-multiples. They are complementary but dimensionally independent metrics.

**Zero/negative risk rejection:** Candidates where $P_{\text{entry}} \le P_{\text{stop}}$ (zero or negative $1R$) now raise `ValueError` and are excluded from all ledger records. The prior fallback (`risk_usd = entry * 0.01`) has been permanently removed.

### 5.2 Runner Single-Instance Lock

The `ShadowFeedRunner` now enforces a process-level lock at `data/.prospective_shadow_runner.lock`:
- Contains PID and acquisition timestamp as JSON.
- `acquire_lock()` checks if the holding PID is still alive; clears stale locks automatically.
- `release_lock()` is called in a `finally` block on loop exit.
- `--loop` mode is prohibited without acquiring the lock first.

### 5.3 CLI Operational Controls

| Command | Behavior |
| :--- | :--- |
| `--once` | Single evaluation cycle, no lock required |
| `--loop --interval N` | Continuous loop every N seconds with single-instance lock |
| `--status` | Print runner lock state + last cycle telemetry |
| `--check-freshness` | Report OHLCV data age vs 2-hour staleness threshold |
| `--dry-run` | Evaluate without appending to ledger |
| `Ctrl+C` | Graceful shutdown: completes current cycle, releases lock |

### 5.4 Stale Feed Detection

Pre-cycle freshness check warns if the latest closed candle in `data/raw/ohlcv.parquet` is older than 7200 seconds (2 hours). This does not halt collection — it emits a `WARNING` log and proceeds. Feed outages do not fabricate synthetic data.
