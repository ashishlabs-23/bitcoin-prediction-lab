# V32.79A — Funding Signal Results (Workstream 3)
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Generated:** 2026-10-30  
**Status: INSUFFICIENT_EVIDENCE — results reported for reference only, no conclusion promoted**  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!WARNING]
> Both arms have fewer than 100 distinct qualifying episodes. No result below is statistically reliable at the pre-specified significance threshold. This section is reported for completeness and to enable auditable record-keeping, not as evidence of any trading edge.

---

## 1. Execution Parameters

| Parameter | Value |
|---|---|
| OHLCV dataset | `ohlcv_checkpoint_42233_bars.parquet` (42,233 bars — hash MATCH) |
| Overlap restriction | 2022-01-01 → 2026-09-01 (40,897 bars) |
| Funding threshold | ±0.000228 per-8h (±25% annualized) |
| Barrier | 3.0% TP / 1.5% SL (asymmetric) |
| Horizon | 24 bars (hourly) |
| Same-bar tie-break | SL_FIRST (conservative) |
| Causal lag | +1 hour after funding settlement |

---

## 2. SHORT Arm Results (N = 64 episodes — BELOW MINIMUM)

**Signal:** Funding rate ≥ +25% ann → contrarian SHORT entry.  
**Hypothesis:** Crowded longs will mean-revert; price will decline.

### Outcome Distribution

| Outcome | Count | Rate |
|---|---|---|
| TP_FIRST (short hits −3%) | 19 | **29.7%** |
| SL_FIRST (short hits +1.5%) | 29 | **45.3%** |
| EXPIRED (neither within 24h) | 16 | **25.0%** |

### Return Statistics

| Metric | Value |
|---|---|
| Gross EV | **+0.308%** |
| Net EV (Binance 24 bps) | **+0.068%** |
| 95% Bootstrap CI (Binance) | [−0.415%, +0.563%] — **CI straddles zero** |
| Net EV (Coinbase 87 bps) | **−0.562%** |
| MFE mean (favorable excursion) | +1.876% |
| MAE mean (adverse excursion) | −1.300% |

### Chronological Stability

| Period | Net EV (Binance) |
|---|---|
| First half (episodes 1–32) | **−0.390%** |
| Second half (episodes 33–64) | **+0.526%** |

The **sign reversal between first and second half** is a strong warning sign of temporal instability. The strategy would have lost money in the first half and recovered in the second half — with no pre-registered explanation for this pattern.

### Breakeven Assessment

| Exchange | Actual TP Rate | Required TP Rate | Sufficient? |
|---|---|---|---|
| Binance VIP0 | 29.7% | 38.7% | **NO — 9pp below breakeven** |
| Coinbase Advanced | 29.7% | 52.7% | **NO — 23pp below breakeven** |

---

## 3. LONG Arm Results (N = 3 episodes — CRITICALLY BELOW MINIMUM)

**Signal:** Funding rate ≤ −25% ann → contrarian LONG entry.  
**Hypothesis:** Crowded shorts will mean-revert; price will rise.

> [!CAUTION]
> N=3 is statistically meaningless. These results are recorded for completeness only. No inference can be drawn.

| Outcome | Count | Rate |
|---|---|---|
| TP_FIRST | 2 | 66.7% |
| SL_FIRST | 1 | 33.3% |
| EXPIRED | 0 | 0.0% |

| Metric | Value |
|---|---|
| Gross EV | +1.500% |
| Net EV (Binance) | +1.260% |
| 95% Bootstrap CI | [−1.740%, +2.760%] — extremely wide, N=3 |
| Net EV (Coinbase) | +0.630% |

**The LONG arm shows apparently positive results, but with N=3 this is meaningless.** A single SL hit from a different sample would reverse the conclusion. The CI width of 4.5pp confirms that no reliable inference is possible.

---

## 4. Unconditional Baseline

| Baseline arm | N | TP Rate | Net EV (Binance) | 95% CI |
|---|---|---|---|---|
| BASELINE_LONG | 1,704 | 16.6% | −0.225% | [−0.305%, −0.145%] |
| BASELINE_SHORT | 1,704 | 17.2% | −0.194% | [−0.275%, −0.111%] |

Both baseline arms have negative net EV at Binance fees — confirming the prior V32.74–V32.78 finding that unconditional entries are not profitable after costs. The baseline is established on the same 40,897-bar overlap period with non-overlapping 24h blocks.

---

## 5. Conditioned vs. Baseline Comparison

| Arm | Conditioned Net EV | Baseline Net EV | Delta |
|---|---|---|---|
| SHORT | +0.068% | −0.194% | **+0.262% relative improvement** |
| LONG | +1.260% | −0.225% | (+1.485% — statistically meaningless at N=3) |

The SHORT arm shows a meaningful improvement over the unconditional baseline in gross terms (+0.262pp). However:
1. The conditioned result is still only +0.068% net, far from the unconditional profitability standard.
2. The 95% CI includes zero (−0.415%, +0.563%).
3. The DM-HLN test is not significant (p = 0.269, threshold = 0.025).
4. The chronological instability (H1 = −0.39%, H2 = +0.53%) means the improvement may be spurious.

---

## 6. Key Empirical Observations

1. **The market is almost never in a negative-funding state above the −25% ann threshold.** Only 5 raw observations in 4+ years. This is a practical ceiling on any LONG-arm research.

2. **The SHORT arm does outperform the unconditional baseline in expected value.** But the outperformance is statistically inconclusive (N=64, p=0.269) and temporally unstable (sign reversal between halves).

3. **The SHORT arm TP rate of 29.7% is below the 38.7% Binance breakeven.** Even without the N constraint, this experiment would not meet the economic acceptance criterion at Binance fees.

4. **At Coinbase fees (87 bps), the SHORT arm is comfortably loss-making** (−0.562% net EV).

5. **The 96.7th percentile threshold is selectively achieved during stress events.** Using a lower threshold would capture more events, but the Manager has prohibited threshold optimization. This is a fundamental tension between economic intuition and statistical power at this dataset's scale.

---

*Results recorded for auditability. INSUFFICIENT_EVIDENCE — no conclusion promoted.*

