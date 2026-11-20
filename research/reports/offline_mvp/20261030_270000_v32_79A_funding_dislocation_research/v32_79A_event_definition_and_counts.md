# V32.79A — Event Definition and Counts (Workstream 2)
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Threshold Conversion

Manager-specified threshold: ±25% annualized funding rate.

$$\text{threshold}_{\text{8h}} = \frac{0.25}{3 \times 365} = \frac{0.25}{1095} = 0.0002283 \text{ per 8h}$$

At the empirical funding-rate distribution (from `binance_funding_2022_2026.parquet`):
- This threshold sits at the **96.7th percentile** of positive funding rates.
- It represents a genuinely rare event: only ~3.3% of positive-funding 8h settlements exceed it.

---

## 2. Raw Qualifying Observations

Over the genuine overlap period (2022-01-01 → 2026-09-01 = 40,897 OHLCV bars, 5,113 funding settlements):

| Arm | Direction | Raw Count | Interpretation |
|---|---|---|---|
| SHORT | `funding_rate ≥ +0.000228` | **144 observations** | Longs crowded → contrarian short entry hypothesis |
| LONG | `funding_rate ≤ −0.000228` | **5 observations** | Shorts crowded → contrarian long entry hypothesis |

**Critical asymmetry:** The BTCUSDT perpetual market was predominantly in positive-funding territory (longs paying shorts) throughout 2022–2026. Negative funding events exceeding the −25% ann threshold occurred only 5 times — far below the 100-episode minimum.

---

## 3. Episode Grouping

**Grouping rule:** Consecutive qualifying observations within 24 hours of an episode start are merged into a single non-overlapping episode. The next distinct episode begins only after the 24-hour evaluation window closes.

| Arm | Raw Observations | Distinct Episodes | Grouping Ratio |
|---|---|---|---|
| SHORT | 144 | **64** | 2.25 obs/episode average |
| LONG | 5 | **3** | 1.67 obs/episode average |

The grouping is appropriate — it prevents a single prolonged funding dislocation event (e.g., a multi-day crowded-long episode) from being counted as many independent trades.

---

## 4. Minimum Sample Assessment

| Arm | Distinct Episodes | Meets 100-Episode Minimum? |
|---|---|---|
| SHORT | 64 | **NO — INSUFFICIENT_EVIDENCE** |
| LONG | 3 | **NO — INSUFFICIENT_EVIDENCE** |

> [!CAUTION]
> **STOP CONDITION TRIGGERED FOR BOTH ARMS**
> 
> Neither arm meets the Manager-specified minimum of 100 distinct qualifying event episodes.
> 
> - SHORT arm: 64 episodes (36 short of minimum).
> - LONG arm: 3 episodes (97 short of minimum).
>
> Per the pre-registered design: "If fewer than 100 qualifying episodes per arm, report INSUFFICIENT_EVIDENCE for that arm."

---

## 5. Episode Timeline (SHORT Arm, Selected)

The 64 SHORT episodes span the full overlap period, concentrated in specific high-volatility sub-periods:

| Period | Approximate episode count | Market context |
|---|---|---|
| 2022 (LUNA/FTX) | High density | Forced deleveraging → extreme funding spikes |
| 2023 | Lower density | Transition / compression regime |
| 2024–2026 | Moderate density | Post-ETF institutional flows |

The temporal clustering is itself a finding: extreme funding events are not uniformly distributed. They cluster during stress events, raising concerns about independence even within the 64 grouped episodes.

---

## 6. Effective Sample Size

Since episodes are constructed to be non-overlapping (24h cooldown), the effective sample size equals the raw episode count in the ideal case.

However, temporal clustering (episodes cluster in stress periods) means even 64 non-overlapping episodes may not represent 64 statistically independent draws from the same data-generating process.

| Arm | Raw episodes | Effective N (optimistic) | Effective N (conservative, accounting for clustering) |
|---|---|---|---|
| SHORT | 64 | 64 | ~30–40 |
| LONG | 3 | 3 | ~3 |

**Conclusion:** Both arms have effective sample sizes well below the 100-episode minimum required for dependence-aware inference at the pre-specified significance threshold.

---

## 7. Why the LONG Arm Has Only 5 Raw Observations

The empirical funding rate distribution from 2022-01-01 to 2026-09-01 shows:
- Minimum rate: −0.001192 (−130% ann)
- Only 5 observations fall at or below −0.000228 (−25% ann)
- These are extremely rare short-squeeze episodes

**Implication:** The −25% annualized threshold is appropriate as a conceptual threshold but is empirically almost never triggered for BTCUSDT funding. A lower threshold (e.g., −10% ann = −0.0000913 per 8h) would capture more events — but this would constitute threshold optimization, which is explicitly prohibited by the Manager.

---

## 8. Formal Determination

**SHORT arm:** `INSUFFICIENT_EVIDENCE` — 64 distinct episodes, minimum required = 100.  
**LONG arm:** `INSUFFICIENT_EVIDENCE` — 3 distinct episodes, minimum required = 100.

Per the pre-registered stop condition, the experiment continues to record all available evidence for reference, but **no promoted research conclusion is valid for either arm**.

---

*No external data fetched. No datasets modified. Protected hashes verified.*

