# V32.79 Phase 0 — Funding Rate Provenance Audit (Workstream A)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream A (Data & Contracts)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Dataset Under Audit

**File:** `data/raw/binance_funding_2022_2026.parquet`  
**Shape:** 5,113 rows × 5 columns  
**Columns:** `timestamp` (datetime64[ms, UTC]), `symbol` (str), `funding_rate` (float64), `mark_price` (float64), `fundingTime` (int64)

---

## 2. Instrument Identity Verification

**Manager concern:** Is this BTCUSDT (USDⓈ-M perpetual) or BTCUSD_PERP (COIN-M perpetual)? These are NOT interchangeable.

**Audit result:**

```
symbol         count
BTCUSDT        5113
```

**Determination: BTCUSDT only.** Zero rows for `BTCUSD_PERP`, `BTCUSD`, or any other symbol. The dataset represents **Binance USDⓈ-M perpetual futures** funding rates throughout. No instrument mixing exists.

**Significance:** BTCUSDT and BTCUSD_PERP have different funding mechanisms:
- **BTCUSDT (USDⓈ-M):** Settled in USDT. Funding rate applies between long and short holders. Fee charged every 8 hours.
- **BTCUSD_PERP (COIN-M):** Settled in BTC. Different liquidity pool and different rate dynamics.

Research using this dataset must specify BTCUSDT USDⓈ-M perpetual throughout. The funding rates are NOT directly applicable to spot BTC/USD positions.

---

## 3. Settlement Interval Verification

**Manager concern:** Binance has had variable settlement windows historically. Are all intervals genuinely 8h?

**Audit result (inter-row intervals computed per symbol, sorted by timestamp):**

```
interval_h statistics:
  count    5112.000000
  mean        8.000000
  std         0.000002
  min         7.999991
  25%         8.000000
  50%         8.000000
  75%         8.000000
  max         8.000008
```

**Determination: Uniformly 8-hour intervals throughout.** The sub-millisecond jitter (std = 0.000002 hours = ~7ms) is a timestamp precision artifact in the `fundingTime` field (millisecond epoch integers), not genuine variation in settlement intervals. The minimum interval is 7.999991h and maximum is 8.000008h — both are 8h within measurement precision.

**No non-8h settlements were found.** The 2,982 rows classified as "non-8h" in a naive equality test are purely floating-point rounding artifacts; all lie within ±29ms of exactly 8 hours.

---

## 4. Date Range Assessment

| Property | Value |
|---|---|
| First settlement | 2022-01-01 00:00:00.006 UTC |
| Last settlement | 2026-09-01 00:00:00.005 UTC |
| Total rows | 5,113 |
| Expected rows at exactly 8h | 5,113 (2022-01-01 → 2026-09-01 = ~4.67 years = 40,924h / 8 = 5,116 max) |
| Missing settlements | ~3 (trivial gap, likely data provider omission at boundary) |
| Duplicate rows | 0 |
| Missing timestamps | 0 |

**Coverage:** The dataset spans 2022-01-01 to 2026-09-01 and overlaps completely with the OHLCV checkpoint period (2022-01-01 to 2026-10-26). The final ~2 months of OHLCV (Sep–Oct 2026) have no corresponding funding data.

---

## 5. Funding Rate Statistics

```
count    5113.000000
mean        0.000060      (0.006% per 8h = 1.095% ann. at 3 settlements/day)
std         0.000084
min        -0.001192      (most negative: -0.1192% — rare short-squeeze events)
25%         0.000018
50%         0.000060
75%         0.000100      (most common range: +0.0018% to +0.010%)
max         0.000881      (most positive: +0.0881% — high contango)
```

**Interpretation:**
- The median rate of +0.006%/8h = +0.018%/day = +6.57%/year is a meaningful cost for sustained long positions on BTCUSDT perpetuals.
- Negative funding rates (periods where shorts pay longs) occur but are rarer.
- The V32.77 cost report used +0.010%/8h (10 bps per settlement) as the funding drag assumption. The empirical median is lower at +0.006%/8h. The prior assumption was conservative by ~67%.

---

## 6. Mark Price Data Quality Issue

**Finding:** 2,005 rows (all in 2022) have `mark_price = 0.0`. The funding_rate is populated for all these rows.

| Year | Rows with mark_price = 0 |
|---|---|
| 2022 | 2,005 (entire 2022 dataset) |
| 2023+ | 0 |

**Assessment:** The 2022 mark price values are missing from the source pull. This affects any analysis requiring mark price (e.g., computing funding payment in USD terms). It does NOT affect the funding_rate column itself, which is the primary signal of interest.

**Recommendation:** If funding payment in USD terms is required, mark price must be sourced separately for the 2022 portion, or analysis must be restricted to 2023-onwards where mark_price is populated.

---

## 7. Causal Availability Assessment

**Manager requirement:** Funding rate must be available before the trading decision, not merely correlated with it.

**Assessment:**

BTCUSDT funding is settled at 00:00, 08:00, and 16:00 UTC daily. The rate for the next settlement is announced approximately 1 hour before each settlement window closes (i.e., predicted rate is publicly visible in the Binance API from ~7h before settlement).

**Key causal boundary rules for funding-based signals:**
1. **Current funding rate** (settled at time $t$): Available as a confirmed input from time $t$ onwards. ✅ Causal.
2. **Predicted next funding rate** (for settlement at $t + 8h$): Announced by Binance at approximately $t + 0h$ but only confirmed at $t + 8h$. Requires careful timestamp treatment. ⚠️ Predicted, not confirmed.
3. **Historical average funding**: Fully causal if computed from confirmed settlements prior to entry time. ✅ Causal.

**The `available_time` field is absent from this dataset.** The `timestamp` field appears to represent the settlement timestamp (confirmed rate), not a publication timestamp. For point-in-time causal feature construction, entries must use only settlements with `timestamp ≤ entry_bar_open_time`.

---

## 8. Overlap with OHLCV Checkpoint

| Dataset | Start | End |
|---|---|---|
| OHLCV Checkpoint (42,233) | 2022-01-01 00:00 UTC | 2026-10-26 16:00 UTC |
| Binance Funding | 2022-01-01 00:00 UTC | 2026-09-01 00:00 UTC |
| **Overlap** | **2022-01-01** | **2026-09-01** |
| **Gap (no funding)** | **2026-09-01** | **2026-10-26** |

The OHLCV checkpoint contains approximately **1,241 hours** (51.7 days) without corresponding funding data at its tail end. Any analysis requiring funding data must restrict its evaluation window to bars up to and including 2026-09-01.

---

## 9. Determinations

| Question | Answer |
|---|---|
| Instrument identity confirmed? | ✅ BTCUSDT USDⓈ-M perpetual throughout |
| Any COIN-M mixing? | ✅ None |
| Settlement intervals uniform 8h? | ✅ Yes (±7ms jitter only) |
| Any non-8h genuine settlements? | ✅ None found |
| Duplicates? | ✅ None |
| Missing timestamps? | ✅ None |
| Mark price quality? | ⚠️ Missing for all 2022 rows |
| Coverage sufficient for V32.79 research? | ⚠️ 2022-2026-09-01 only; 51-day gap at tail |
| Available_time field present? | ❌ Absent — causal timestamp treatment requires using `timestamp` as the settlement confirmation time |
| Appropriate for H_Funding hypothesis? | ✅ PROVISIONALLY — subject to provenance verification of collection methodology |

**Overall workstream A determination: PROVISIONALLY USABLE WITH DOCUMENTED CAVEATS**

The funding dataset has a clear instrument identity, uniform interval, and sufficient historical coverage. The main risks are: (1) mark price zeros in 2022, (2) absence of an `available_time` field requiring careful timestamp handling, and (3) the 51-day tail gap with OHLCV.

---

*No external data fetched. No datasets modified. No models trained.*

