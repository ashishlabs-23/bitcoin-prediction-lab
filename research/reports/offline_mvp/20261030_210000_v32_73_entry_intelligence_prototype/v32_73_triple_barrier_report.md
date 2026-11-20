# V32.73 — Triple Barrier Report

**Milestone:** V32.73 — Entry Intelligence Prototype & Test Reliability  
**Date:** 2026-10-30  
**Module:** `research/entry_intelligence/triple_barrier_labeler.py`  
**Classification:** OFFLINE_RESEARCH_ONLY | Research observation — not a performance guarantee

---

> [!NOTE]
> Triple-barrier labels are a retrospective research construct. Label frequencies
> on development data are NOT win rates, fill rates, or performance guarantees.
> AMBIGUOUS labels must be excluded from any classifier training target.

---

## 1. Implementation Summary

### 1.1 Label Definitions

| Label | Integer | Condition |
|---|---|---|
| TP_FIRST | +1 | Price reaches the TP barrier before SL or horizon expiry |
| SL_FIRST | -1 | Price reaches the SL barrier before TP or horizon expiry |
| EXPIRED | 0 | Neither barrier touched within the horizon window |
| AMBIGUOUS | None | Both barriers touched on the same bar, or a gap detected |

### 1.2 Core Classes

**`TripleBarrierLabel`** (dataclass):
- `entry_idx`, `entry_timestamp`, `entry_price`, `direction`
- `tp_pct`, `sl_pct`, `horizon_hours`: Barrier configuration
- `label`: +1, -1, 0, or None
- `label_str`: Human-readable string
- `tp_price`, `sl_price`: Absolute barrier levels
- `touch_bar_offset`: Bar offset of first barrier touch (None if EXPIRED/AMBIGUOUS)
- `touch_timestamp`: UTC timestamp of first touch
- `expiry_return_pct`: Return at horizon expiry bar (direction-adjusted)
- `bars_evaluated`: Number of bars in the forward window
- `hit_dataset_end`: True if window reaches end of dataset
- `has_gap`: True if a discontinuity was detected
- `gap_exclusion_reason`: Description if has_gap=True

**`TripleBarrierLabeler`** class:
- Constructor: `TripleBarrierLabeler(df, tp_pct=1.5, sl_pct=0.75, horizon_hours=24)`
- `.label(entry_idx, direction) -> TripleBarrierLabel`
- `.label_batch(entry_indices, direction) -> pd.DataFrame`

### 1.3 Fill Price and Barrier Calculation

- **Fill price** = OPEN of bar `entry_idx + 1` (same causal convention as ExcursionCalculator)
- **TP price (LONG)** = `entry_price * (1 + tp_pct/100)`
- **SL price (LONG)** = `entry_price * (1 - sl_pct/100)`
- **TP price (SHORT)** = `entry_price * (1 - tp_pct/100)` (price moves down)
- **SL price (SHORT)** = `entry_price * (1 + sl_pct/100)` (price moves up)

Each bar in the forward window is checked: if the bar's HIGH >= TP (LONG) or
LOW <= TP (SHORT), the TP is triggered. If bar's LOW <= SL (LONG) or HIGH >= SL
(SHORT), the SL is triggered.

---

## 2. Boundary Cases

### 2.1 Both Barriers Same Bar → AMBIGUOUS

If in a single bar, both the HIGH triggers TP AND the LOW triggers SL (or vice
versa for SHORT), the label is AMBIGUOUS. The direction of intra-bar movement
cannot be determined from OHLCV data. This is the conservative, scientifically
correct choice — it avoids injecting look-ahead bias into the labeling.

### 2.2 Gap → AMBIGUOUS

If a timestamp discontinuity is detected in the forward window, the label is
AMBIGUOUS with `gap_exclusion_reason="DISCONTINUOUS_FORWARD_HORIZON_GAP"`.
A gap means the assumed continuous price path is invalid, so neither barrier
outcome can be reliably attributed to the entry.

### 2.3 Dataset End

If the forward window reaches the end of the dataset (`hit_dataset_end=True`),
the label is whatever was determined up to the last available bar. If no barrier
was hit by dataset end, the label is EXPIRED. These entries should be excluded
from evaluations that require a full horizon window.

---

## 3. Hand-Calculated Fixture Verification

### 3.1 Bar 1000 — LONG, TP=1.5%, SL=0.75%, horizon=24h

Using `ohlcv.parquet` (42,233 rows):

| Field | Value |
|---|---|
| Entry bar | 1000 |
| Fill price (OPEN bar 1001) | derived from actual data |
| TP level (LONG) | 44,231.58 |
| SL level (LONG) | 43,251.08 |
| Label | **SL_FIRST** |
| Touch bar offset | 1 (first bar after entry) |
| Has gap | False |

**Interpretation:** Within 1 bar of entry, the low of bar 1001 crossed the SL level
(43,251.08). This is consistent with bar 1000 being in a declining period (confirmed
by the LONG MAE=4.33% in the excursion analysis — large adverse move immediately).

### 3.2 Bar 1000 — SHORT, TP=1.5%, SL=0.75%, horizon=24h

| Field | Value |
|---|---|
| TP level (SHORT) | 42,924.24 (target = price moves down) |
| SL level (SHORT) | 43,904.74 (stop = price moves up) |
| Label | **TP_FIRST** |
| Touch bar offset | 1 |

**Interpretation:** Bar 1001's low was below the SHORT TP level within 1 bar.
Consistent with a downward price move at that timestamp.

---

## 4. Batch Label Distribution

**200 samples, step=100, bars 1000–20,900, ohlcv.parquet:**

### 4.1 LONG direction (TP=1.5%, SL=0.75%)

| Label | Count | % |
|---|---|---|
| SL_FIRST | 124 | 62.0% |
| TP_FIRST | 55 | 27.5% |
| EXPIRED | 19 | 9.5% |
| AMBIGUOUS | 2 | 1.0% |
| **Total** | **200** | **100%** |

**Gross EV (LONG, pre-cost):** 0.275 × 1.5% + 0.620 × (-0.75%) + 0.095 × 0% = **-0.053%**

This is a negative gross EV on the retrospective development sample. This does
NOT mean long entries are generally unprofitable — this is a uniform sampling of
development-data bars, not a strategy signal.

### 4.2 SHORT direction (TP=1.5%, SL=0.75%)

| Label | Count | % |
|---|---|---|
| SL_FIRST | 123 | 61.5% |
| TP_FIRST | 50 | 25.0% |
| EXPIRED | 25 | 12.5% |
| AMBIGUOUS | 2 | 1.0% |
| **Total** | **200** | **100%** |

**Gross EV (SHORT, pre-cost):** 0.250 × 1.5% + 0.615 × (-0.75%) + 0.125 × 0% = **-0.086%**

### 4.3 Observations

- AMBIGUOUS rate (1%) is low, indicating few bars with intra-bar gap/ambiguity
- SL hits significantly outnumber TP hits in both directions (asymmetric barrier: TP=2x SL)
- The 2:1 TP/SL ratio (1.5%/0.75%) means TP_FIRST requires a 2x move vs SL_FIRST
- EXPIRED rate (9.5–12.5%) indicates a meaningful fraction of bars where price
  stayed within ±0.75% for 24h — indicative of low-volatility consolidation periods

---

## 5. Gap Exclusion Verification

Zero gaps detected in the 1000–20,900 bar window (consistent with ExcursionCalculator
findings). This confirms the raw OHLCV dataset is largely continuous in this range.

For entries near known gap events (e.g., exchange maintenance windows), the gap
detection mechanism would correctly label them AMBIGUOUS, preventing contaminated
labels from entering training sets.

---

## 6. Research Integrity Notes

> [!CAUTION]
> The label frequencies above are computed on **retrospective development data** using
> **uniform bar sampling** (not a strategy filter). They must not be interpreted as:
> - Win rates for any trading strategy
> - Expected label frequencies under a production signal
> - Statistical evidence of edge

Only label frequencies computed under a confirmed, prospective strategy signal on
confirmatory data (minimum 100 non-overlapping prospective blocks) would constitute
valid performance evidence.

---

*End of triple barrier report.*

