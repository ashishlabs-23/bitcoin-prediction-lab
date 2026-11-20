# V32.73 — Excursion Calculator Report

**Milestone:** V32.73 — Entry Intelligence Prototype & Test Reliability  
**Date:** 2026-10-30  
**Module:** `research/entry_intelligence/excursion_calculator.py`  
**Classification:** OFFLINE_RESEARCH_ONLY | Research observation — not a performance guarantee

---

> [!NOTE]
> EQR (Excursion Quality Ratio) is a geometric ratio of favorable-to-unfavorable price
> excursion. It is **NOT** a win probability, expected return, or trading edge indicator.
> It is a descriptive research metric for entry quality analysis only.

---

## 1. Implementation Summary

### 1.1 Core Classes

**`ExcursionResult`** (dataclass):
- `entry_idx`: Bar index of the entry signal
- `entry_timestamp`: UTC timestamp string
- `entry_price`: Fill price = OPEN of bar `entry_idx + 1` (causal, next-bar fill)
- `direction`: `"long"` or `"short"`
- `horizon_hours`: Holding period in hours
- `mfe_pct`: Maximum Favorable Excursion as % of entry price (direction-adjusted)
- `mae_pct`: Maximum Adverse Excursion as % of entry price (direction-adjusted)
- `excursion_quality_ratio`: `mfe_pct / mae_pct` if `mae_pct > 0`, else `float('inf')`
- `mfe_price`: Absolute price of the MFE bar
- `mae_price`: Absolute price of the MAE bar
- `mfe_bar_offset`: Bar offset from entry where MFE occurred
- `mae_bar_offset`: Bar offset from entry where MAE occurred
- `has_gap`: True if a timestamp discontinuity was detected in the forward window
- `gap_exclusion_reason`: Description if `has_gap=True`, else None

**`ExcursionCalculator`** class:
- Constructor: `ExcursionCalculator(df: pd.DataFrame)`
  - Accepts DataFrame with columns `['timestamp', 'open', 'high', 'low', 'close', 'volume']`
- `.compute(entry_idx, direction, horizon_hours) -> ExcursionResult`
- `.compute_batch(entry_indices, direction, horizon_hours) -> pd.DataFrame`

### 1.2 Causal Entry Rule

Fill price is **OPEN of bar `entry_idx + 1`** — the next bar after the signal bar.
This is a strict point-in-time causal boundary: the signal fires at bar `t`, and
the fill is executed at the open of bar `t+1`. No intra-bar fill is used.

```
t        t+1           t+horizon
|  signal | OPEN=fill  |  ... window bars ...  |
```

### 1.3 Gap Detection

A timestamp gap is detected when consecutive bars in the forward window have
a timestamp difference exceeding the expected hourly interval (> 90 minutes).
When `has_gap=True`:
- The result is still computed up to the gap boundary.
- `gap_exclusion_reason` is populated with "DISCONTINUOUS_FORWARD_HORIZON_GAP".
- The result should be excluded from evaluation metrics that require continuous
  price paths.

---

## 2. Hand-Calculated Fixture Verification

### 2.1 Bar 1000 — LONG direction, 24h horizon

| Field | Value |
|---|---|
| Entry bar | 1000 |
| Fill bar | 1001 (OPEN price) |
| Direction | LONG |
| Horizon | 24 bars |
| MFE | 0.3347% |
| MAE | 4.3348% |
| EQR | 0.0772 |
| Has gap | False |

**Interpretation:** Bar 1000 was a poor long entry. Adverse excursion (MAE=4.33%)
substantially exceeded favorable excursion (MFE=0.33%), yielding EQR=0.077.
EQR < 1.0 indicates the trade moved against the long direction more than it moved
in the long direction before returning.

### 2.2 Bar 1000 — SHORT direction, 24h horizon

| Field | Value |
|---|---|
| Direction | SHORT |
| MFE | 4.3348% |
| MAE | 0.3347% |
| EQR | 12.9501 |

**Interpretation:** The mirror case — bar 1000 was a good short entry. The price
moved 4.33% favorably (downward for short) before a 0.33% adverse excursion.
EQR = 12.95 >> 1.0. This is consistent: bar 1000 coincided with a price decline.

---

## 3. Batch Verification (200 samples, step=100, bars 1000–20,900)

| Metric | LONG | SHORT |
|---|---|---|
| N samples | 200 | 200 |
| EQR mean | 10.020 | 5.289 |
| EQR mean (excl. gaps) | 10.020 | 5.289 |
| Gaps detected | 0 | 0 |

### 3.1 EQR Mean Caveat

The high mean EQR values (10.0 long, 5.3 short) deserve scrutiny. EQR can be
inflated by outliers when MAE is very small (EQR = MFE/MAE → ∞ as MAE → 0).
A few bars with near-zero adverse excursion will dominate the arithmetic mean.
**Median EQR is a more robust research metric; mean EQR should not be reported
without a distribution.** The implementation computes EQR per-bar; aggregation
choices belong to the caller (`EntryQualityMetrics` uses bootstrap CIs).

> [!WARNING]
> EQR is NOT a win probability. A high mean EQR does not mean entries are profitable.
> It does not account for transaction costs, adverse selection, or execution slippage.
> These findings are retrospective research observations on development data.

---

## 4. Gap Detection Behavior

No gaps were detected in the 1000–20,900 bar window. This is consistent with the
dataset being `ohlcv.parquet` (raw feed, 42,233 rows, ends 2026-10-26) which has
been gap-filled in the production backfill process.

When gaps do occur:
- `has_gap=True` is set on the result
- `gap_exclusion_reason = "DISCONTINUOUS_FORWARD_HORIZON_GAP"`
- The MFE/MAE/EQR are computed up to the first gap bar only
- The caller must exclude gap-flagged results from aggregate statistics

---

## 5. Module Boundary

The `ExcursionCalculator` is a pure research module:
- It reads from a parquet DataFrame passed at construction time
- It performs no I/O, no DB connections, no API calls
- It enforces causal boundaries by design (next-bar fill)
- It carries no model authorization; it is a data transformation utility

---

*End of excursion calculator report.*

