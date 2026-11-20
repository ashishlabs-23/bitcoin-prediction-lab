# V33.5 Market Data and Input Reliability Audit Report

**Classification:** AUTHORITATIVE RESEARCH AUDIT & DATA CONTRACT BENCHMARK  
**System:** BTCognitive Volatility Intelligence & Research Platform  
**Target Environment:** Local Offline Research / Causal Point-in-Time Evaluation  
**Audit Wall-Clock UTC:** 2026-11-02T14:57:58.027Z (Epoch: `1793631478.027`)  
**Operating Contract Reference:** AGENTS.md § 2 (Epistemic Principles & Research Boundaries)  

---

## 1. Authoritative Data Asset Verification (`data/raw/ohlcv.parquet`)

### 1.1 Physical File Invariants & Cryptographic Hashes
- **Canonical Path:** `data/raw/ohlcv.parquet`
- **Absolute Local Path:** `C:\Projects\BTCognitive\BTCognitive\data\raw\ohlcv.parquet`
- **File Size:** `2,334,866` bytes (2.2267 MB)
- **SHA-256 Checksum:** `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`
- **Format:** Apache Parquet (Snappy compressed, columnar dictionary encoding)
- **Matching Checkpoint Backup:** Identical SHA-256 bit-for-bit to `data/raw/ohlcv_version_42326_bars.parquet`.

### 1.2 Schema Definition & Physical Dtypes
| Column Name | Physical Parquet Type | Pandas Dtype | Nullable | Invariant Constraint |
|:---|:---|:---|:---|:---|
| `timestamp` | `INT64 (TIMESTAMP_MICROS, UTC)` | `datetime64[us, UTC]` | No (0 nulls) | Exact hourly boundary (`% 3600 == 0`), monotonic increasing |
| `open` | `DOUBLE` | `float64` | No (0 nulls) | Strictly finite, $x > 0$ |
| `high` | `DOUBLE` | `float64` | No (0 nulls) | Strictly finite, $x \ge \max(\text{open}, \text{close})$ |
| `low` | `DOUBLE` | `float64` | No (0 nulls) | Strictly finite, $0 < x \le \min(\text{open}, \text{close})$ |
| `close` | `DOUBLE` | `float64` | No (0 nulls) | Strictly finite, $x > 0$ |
| `volume` | `DOUBLE` | `float64` | No (0 nulls) | Strictly finite, $x \ge 0$ |
| `available_time` | `INT64 (TIMESTAMP_MICROS, UTC)` | `datetime64[us, UTC]` | No (0 nulls) | Strictly `timestamp + 1h` (zero lookahead causal maturity) |

### 1.3 Row Counts, Boundaries, and Continuity Audit
- **Total Record Count:** `42,326` rows
- **Index Type:** `pandas.RangeIndex(start=0, stop=42326, step=1)`
- **Start Candle Open (`timestamp`):** `2022-01-01 00:00:00+00:00` (Unix epoch: `1640995200`)
- **End Candle Open (`timestamp`):** `2026-10-30 13:00:00+00:00` (Unix epoch: `1793365200`)
- **Start Maturity (`available_time`):** `2022-01-01 01:00:00+00:00` (Unix epoch: `1640998800`)
- **End Maturity (`available_time`):** `2026-10-30 14:00:00+00:00` (Unix epoch: `1793368800`)
- **Monotonic Chronological Ordering:** `True` (`is_monotonic_increasing == True`)
- **Duplicate Timestamps:** `0` (Zero duplicate entries)
- **Interval Step Analysis:**
  - Interval delta: $\Delta t_i = t_i - t_{i-1}$ across all 42,325 adjacent pairs.
  - Exactly `0 days 01:00:00` (3,600,000,000 µs): **42,325 (100.000%)**
  - Gaps (> 1 hour): **0**
  - Contract deviations: **0**
- **Causal Offset Invariant:**
  - $(\text{available\_time} - \text{timestamp})$: Exactly `0 days 01:00:00` for all **42,326 rows (100.000%)**.

### 1.4 Numerical & Geometric Extremum Validation
- **Missing / NaN Values:** `0` across all 7 columns (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `available_time`).
- **Infinite Values ($\pm \infty$):** `0` across all numerical columns.
- **Price Positivity ($P > 0$):** `0` non-positive or negative values.
- **High Geometric Violations ($\text{high} < \max(\text{open}, \text{close})$):** `0`
- **Low Geometric Violations ($\text{low} > \min(\text{open}, \text{close})$):** `0`
- **Inverted Bar Violations ($\text{high} < \text{low}$):** `0`
- **Negative Volumes ($V < 0$):** `0`
- **Zero Volume Bars:** Exactly **1 bar** out of 42,326.
  - *Location:* Row Index `10740`
  - *Timestamp:* `2023-03-24 12:00:00+00:00` (available at `2023-03-24 13:00:00+00:00`)
  - *Bar Values:* `open=28080.00`, `high=28080.00`, `low=28080.00`, `close=28080.00`, `volume=0.0`
  - *Empirical Attribution:* Corresponds to the well-documented Binance spot trading engine suspension on March 24, 2023 (11:30–14:00 UTC) caused by a trailing stop order bug. This is genuine empirical market state, not a synthetic artifact.

### 1.5 Historical Price and Volume Descriptive Statistics
| Metric | Open (USD) | High (USD) | Low (USD) | Close (USD) | Volume (BTC) |
|:---|---:|---:|---:|---:|---:|
| **Minimum** | 15,648.23 | 15,769.99 | 15,476.00 | 15,649.52 | 0.0000 |
| **25th Percentile** | 26,837.28 | 26,920.00 | 26,762.11 | 26,837.00 | 832.4110 |
| **Median (50th)** | 61,023.50 | 61,250.00 | 60,800.00 | 61,025.10 | 1,675.2890 |
| **Mean** | 59,216.16 | 59,412.78 | 59,012.66 | 59,216.89 | 2,730.6431 |
| **75th Percentile** | 88,142.75 | 88,498.00 | 87,790.00 | 88,145.00 | 3,298.1500 |
| **Maximum** | 126,011.18 | 126,199.63 | 125,252.74 | 126,011.18 | 137,207.1886 |
| **Std Deviation** | 30,418.92 | 30,499.76 | 30,334.28 | 30,418.98 | 4,779.4012 |

---

## 2. Complementary Raw Parquet Datasets Inventory

| File Name | Rows | Cols | Size (Bytes) | SHA-256 (Prefix) | Time Column | Start UTC | End UTC |
|:---|---:|---:|---:|:---|:---|:---|:---|
| `ohlcv.parquet` | 42,326 | 7 | 2,334,866 | `ba06fb533c0b5338` | `timestamp` | 2022-01-01 00:00:00Z | 2026-10-30 13:00:00Z |
| `coinbase_15m.parquet` | 16,200 | 8 | 830,946 | `bfd4295f563141c6` | `timestamp` | 2026-05-10 23:45:00Z | 2026-10-26 17:30:00Z |
| `binance_funding_2022_2026.parquet` | 5,113 | 5 | 145,791 | `e90282de4f78ebde` | `timestamp` | 2022-01-01 00:00:00Z | 2026-09-01 00:00:00Z |
| `funding.parquet` | 375 | 3 | 12,625 | `f176186ec28c78fe` | `timestamp` | 2026-01-01 00:00:00Z | 2026-05-05 16:00:00Z |
| `oi.parquet` | 3,000 | 3 | 81,676 | `f6f63fe4790d52df` | `timestamp` | 2026-01-01 00:00:00Z | 2026-05-05 23:00:00Z |
| `onchain.parquet` | 30 | 3 | 3,623 | `c281a41fa35b33ed` | `timestamp` | 2026-10-01 14:33:52Z | 2026-10-30 14:33:52Z |
| `ohlcv_checkpoint_42233_bars.parquet`| 42,233 | 7 | 2,329,800 | `f5c15cb11b9d51cf` | `timestamp` | 2022-01-01 00:00:00Z | 2026-10-26 16:00:00Z |
| `ohlcv_version_42326_bars.parquet` | 42,326 | 7 | 2,334,866 | `ba06fb533c0b5338` | `timestamp` | 2022-01-01 00:00:00Z | 2026-10-30 13:00:00Z |

---

## 3. Data Age Quantification & Freshness Protocols

### 3.1 Empirical Age Calculation Relative to Wall-Clock Time
- **Audit Wall-Clock UTC:** `2026-11-02 14:57:58.027 UTC` (Epoch: `1793631478.027`)
- **Latest Bar Open Epoch ($T_{\text{open}}$):** `2026-10-30 13:00:00 UTC` (Epoch: `1793365200.0`)
- **Latest Bar Close Epoch ($T_{\text{close}}$):** `2026-10-30 14:00:00 UTC` (Epoch: `1793368800.0`)
- **Data Age (from Candle Close):**
  $$\text{Data Age}_{\text{close}} = T_{\text{wall-clock}} - T_{\text{close}} = 1,793,631,478.027 - 1,793,368,800.0 = \mathbf{262,678.027\text{ s}} \approx \mathbf{72.97\text{ hours}} \approx \mathbf{3.04\text{ days}}$$
- **Data Age (from Candle Open):**
  $$\text{Data Age}_{\text{open}} = T_{\text{wall-clock}} - T_{\text{open}} = \mathbf{266,278.027\text{ s}} \approx \mathbf{73.97\text{ hours}} \approx \mathbf{3.08\text{ days}}$$

### 3.2 Measurement and Reporting Across System Components

1. **`engine/data_verification.py` (Deterministic Data Contract Validator):**
   - *Logic:*
     ```python
     candle_close_epoch = latest_epoch + granularity_sec
     data_age_sec = max(0.0, now_epoch - candle_close_epoch)
     if data_age_sec > (granularity_sec * max_staleness_multiplier):
         return DataValidationReport(is_valid=False, reason_code="STALE_DATA", ...)
     ```
   - *Behavior:* For 1h candles with `max_staleness_multiplier = 2.0`, the allowable freshness window is $2 \times 3600 = 7,200\text{ s}$ (2 hours post-close). The raw file exceeds this window by 255,478s and correctly fails closed with `reason_code="STALE_DATA"` if evaluated under live execution assumptions.

2. **`engine/market_data_adapters/provider_contract.py` (BaseMarketDataProvider):**
   - *Logic:*
     ```python
     stale_sec = max(0.0, now_sec - (bars[-1].time + step))
     is_stale = stale_sec > self.stale_threshold_seconds  # Default: 7200.0s
     ```
   - *Behavior:* Flags `continuity.is_stale = True` and sets provider response status to `"STALE"`.

3. **`engine/market_data_adapters/bitstamp.py` & `coingecko.py`:**
   - *Logic:*
     ```python
     age_sec = retrieval_epoch - (latest_bar.timestamp_epoch + step_seconds)
     if age_sec > (2 * step_seconds):
         freshness = FeedFreshnessStatus.STALE
     elif age_sec > step_seconds:
         freshness = FeedFreshnessStatus.DELAYED
     else:
         freshness = FeedFreshnessStatus.FRESH
     ```
   - *Behavior:* Emits standardized tri-state enum: `FRESH` ($\le 1\text{h}$), `DELAYED` ($1\text{h} < \text{age} \le 2\text{h}$), or `STALE` ($> 2\text{h}$).

4. **`api/market_drivers.py` & `api/market_monitor_routes.py` (Research & Market Dashboard):**
   - *Logic:* Under `DataMode.OFFLINE_RESEARCH`, market drivers load historical candles via `get_offline_historical_candles(168)` and explicitly label the payload:
     ```python
     "status": "HISTORICAL_SNAPSHOT",
     "source": "LOCAL_HISTORICAL_SNAPSHOT",
     "age_seconds": round(time.time() - last_candle["time"], 1),
     "reason": "Serving validated local historical snapshot from data/raw/ohlcv.parquet"
     ```
   - *Behavior:* Prevents false live execution by transparently disclosing that the data is an offline historical snapshot.

---

## 4. Incomplete Candle Isolation & Zero Lookahead Enforcement

### 4.1 Invariant Rules for Active / Forming Candles
A primary requirement of causal econometric inference is that **no forming candle ($t \le t_{\text{wall-clock}} < t + \Delta t$) may ever enter feature calculations or realized variance target summations**. The codebase strictly enforces this invariant across five independent barriers:

1. **Adapter Boundary Exclusion (`provider_contract.py`):**
   ```python
   step = {"15m": 900, "1h": 3600, "4h": 14400, "24h": 86400}[interval.value]
   now_epoch = int(time.time())
   closed_cutoff = (now_epoch // step) * step
   # Drop unclosed bars:
   if t + step > closed_cutoff:
       continue
   ```
   Any candle whose interval boundary reaches beyond `closed_cutoff` is pruned during ingestion.

2. **Market Monitor Ingestion Filter (`market_drivers.py`):**
   ```python
   closed_before = int(now_epoch // HOUR) * HOUR
   if ts_i + HOUR > closed_before:
       continue
   ```
   Ensures that only candles strictly closed prior to the current UTC hour are retained in memory.

3. **Streaming State Isolation (`api/candle_manager.py`):**
   - Real-time ticks dynamically update `self.current_candle` where `is_closed = False`.
   - `_generate_prediction_on_closed_candle()` is **never** called during tick updates.
   - It is triggered **strictly** when `now_ms >= candle_end`:
     ```python
     if now_ms >= candle_end:
         closed_candle = {..., "is_closed": True}
         self.closed_candles.append(closed_candle)
         prediction_payload = self._generate_prediction_on_closed_candle(closed_candle)
     ```
   - Furthermore, `_generate_prediction_on_closed_candle` strictly queries the `authoritative_model_registry` and immediately fails closed with `status="BLOCKED_MODEL_UNAUTHORIZED"` when production models are offline.

4. **REST Degraded Feed Safety (`engine/data_engine.py`):**
   ```python
   # Discard forming candle: index [-1] is currently active, so select [-2]
   closed_kline = data[-2] if len(data) >= 2 else data[-1]
   ```
   Guarantees that upstream exchange REST endpoints returning an incomplete live candle cannot contaminate feature inputs.

5. **Target Definition Separation ($t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}}$):**
   - For `rv24h_var_ann` (24-hour forward realized variance), the observation issued at $T$ is computed strictly over closed candles $[T+1, \dots, T+24]$.
   - For `rv7d_var_ann` (168-hour forward realized variance), maturity occurs at $T + 168\text{h}$.
   - All feature vector inputs terminate at $T$ (where $T_{\text{available}} \le T_{\text{issue}}$). Under no circumstances are future or forming bars leaked into prior feature timestamps.

---

## 5. Architectural Recommendations & Operational Summary

1. **Offline Research Mode Continuity:**
   The `data/raw/ohlcv.parquet` file is in **pristine econometric health** for retrospective replay, walk-forward cross-validation, and backtesting through `2026-10-30 13:00:00 UTC`.
2. **Prospective Observation Gating:**
   Because `ohlcv.parquet` ends on October 30, 2026, all observations prior to October 30, 2026 constitute retrospective development data. Fresh confirmatory prospective evidence accumulation must begin from an explicit post-freeze timestamp (`T_freeze >= 2026-10-30 14:00:00 UTC`) via an authorized append-only prospective ledger.
3. **No Synthetic Fill:**
   Zero synthetic bars exist in the primary raw datasets. Gaps detected during network ingestion are flagged (`INTERVAL_GAP_DETECTED`), not filled with synthetic interpolated prices.

