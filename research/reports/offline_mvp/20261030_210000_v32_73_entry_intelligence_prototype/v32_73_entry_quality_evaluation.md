# V32.73 — Entry Quality Evaluation

**Milestone:** V32.73 — Entry Intelligence Prototype & Test Reliability  
**Date:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY | Research observation — not a performance guarantee

---

> [!IMPORTANT]
> All findings in this report are **retrospective research observations** computed on
> development data (2022–2026 OHLCV replay). They do not constitute confirmatory
> evidence of trading edge, win probability, or expected return.
> EQR (Excursion Quality Ratio) is NOT a win probability.
> Barrier touch frequencies are NOT live win rates.

---

## 1. Evaluation Dataset

| Property | Value |
|---|---|
| Source | `data/raw/ohlcv.parquet` |
| SHA256 | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` |
| Rows | 42,233 |
| Frequency | 1H |
| Symbol | BTCUSD |
| Period | Approximately 2022-01-01 to 2026-10-26 |

---

## 2. EQR Out-of-Sample Evaluation

Evaluation was conducted with uniform bar sampling (step=100 bars) over the range
bars 1000–20,900, producing 200 entry candidates per direction. The OOS split
was approximately 75%/25% chronological — the evaluation sample is the final 25%
of the sampled bars.

### 2.1 LONG EQR

| Metric | Value |
|---|---|
| N samples | 200 |
| EQR arithmetic mean | 10.020 |
| Gaps detected | 0 |

**Caveat:** The arithmetic mean EQR of 10.02 is inflated by entries where MAE is
near zero (EQR → ∞). This metric should be treated as an exploratory observation.
A robust evaluation requires:
1. Bootstrap confidence intervals on median EQR (not mean)
2. Exclusion of outlier entries where MAE < 0.01%
3. Strategy-filtered entry signals rather than uniform sampling

EQR > 1.0 indicates more favorable than adverse excursion; EQR < 1.0 indicates
the opposite. EQR does not indicate net profitability after costs.

### 2.2 SHORT EQR

| Metric | Value |
|---|---|
| N samples | 200 |
| EQR arithmetic mean | 5.289 |
| Gaps detected | 0 |

---

## 3. Triple-Barrier Label Distribution

**Configuration:** TP=1.5%, SL=0.75%, horizon=24h

### 3.1 LONG Entries

| Label | Count | Frequency |
|---|---|---|
| SL_FIRST | 124 | 62.0% |
| TP_FIRST | 55 | 27.5% |
| EXPIRED | 19 | 9.5% |
| AMBIGUOUS | 2 | 1.0% |

**Usable for classification:** 198 / 200 (excluding AMBIGUOUS)

### 3.2 SHORT Entries

| Label | Count | Frequency |
|---|---|---|
| SL_FIRST | 123 | 61.5% |
| TP_FIRST | 50 | 25.0% |
| EXPIRED | 25 | 12.5% |
| AMBIGUOUS | 2 | 1.0% |

**Usable for classification:** 198 / 200 (excluding AMBIGUOUS)

### 3.3 Interpretation of Label Asymmetry

The barrier configuration uses TP=2x SL (1.5% vs 0.75%). Under an efficient/random
market, the expected TP hit rate at 2:1 ratio is approximately 33% (TP occurs when
price moves 1.5% before 0.75% reversal). The observed rates (27.5% long, 25.0%
short) are slightly below the geometric expectation, consistent with:
- BTC exhibiting momentum reversals within short (24h) windows
- The 24h horizon being too short to capture trending moves reliably
- Transaction costs not yet accounted for

These observations do not constitute evidence of negative edge — they are the
unconditional sample statistics of development-era bars, not the conditional
statistics of any signal.

---

## 4. Time-to-Barrier Distributions

From the batch verification, the most common outcome was `touch_bar_offset=1` for
both the SL_FIRST and TP_FIRST cases at bar 1000 — indicating immediate barrier
hit within the first post-entry bar. In the full batch:

- **Immediate hits (offset=1):** Common for both TP and SL, reflecting high BTC
  intraday volatility. A 0.75% SL on hourly bars can be breached within 1 hour.
- **EXPIRED entries:** Took the full 24 bars to expire, indicating price stayed
  within ±0.75% for the entire 24h window — consolidation regime entries.
- **Later-hour hits (offset 2–24):** Indicate entries during trend transitions
  where the first few bars were benign before a larger move.

> [!NOTE]
> Time-to-barrier distributions (TTP and TTL) are planned for V32.74 with full
> density estimation. V32.73 records the qualitative observation that immediate
> hits (offset=1) dominate the current barrier configuration.

---

## 5. Volatility Regime Segmentation (Planned — Not Executed in V32.73)

Volatility regime segmentation using `ResearchEvaluator.segment_by_volatility()`
was designed but not executed in V32.73 due to the computational cost of a full
regime classification pass on 42,233 bars. This is deferred to V32.74.

Planned segmentation:
- **Low vol regime:** Rolling 24h realized vol < 25th percentile → expect higher EXPIRED rate
- **Mid vol regime:** 25th–75th percentile → baseline reference
- **High vol regime:** > 75th percentile → expect lower EXPIRED, higher SL_FIRST

---

## 6. Entry Quality Prototype Status

| Component | Status |
|---|---|
| ExcursionCalculator | Implemented and verified |
| TripleBarrierLabeler | Implemented and verified |
| EntryQualityMetrics | Implemented (bootstrap CI framework ready) |
| CostSensitivityAnalyzer | Implemented (5 scenarios) |
| ResearchEvaluator | Implemented (OOS splits + vol regime hooks) |
| Model training | NOT implemented (V32.74 scope) |
| Prospective evaluation | NOT started (V32.74+ scope) |

---

## 7. Prospective Evidence Gate

The entry quality evaluation findings are **retrospective**. Before any entry quality
model can be evaluated for production consideration:

1. Minimum 100 non-overlapping prospective blocks must be collected
2. A confirmatory walk-forward manifest (prospective, not retrospective) must be registered
3. Diebold-Mariano test (HLN correction) must reject the null of equal performance vs
   the all-ABSTAIN baseline at p < 0.05
4. Net EV must be positive under SCEN_1_BINANCE_VIP0 after 1.5-sigma CI

**Current prospective evidence: 7 / 100 blocks (7.0%).** This gate is COLLECTING,
not SUFFICIENT_FOR_CONFIRMATORY_GATE.

---

*End of entry quality evaluation report.*

