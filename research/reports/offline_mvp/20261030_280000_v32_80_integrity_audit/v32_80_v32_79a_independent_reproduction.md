# V32.80 — V32.79A Independent Reproduction (Workstream 1)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30  
**Source:** Raw local datasets only — `v32_79A_results_raw.json` NOT consulted  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Reproduction Method

All calculations were executed independently from:
- `data/raw/ohlcv_checkpoint_42233_bars.parquet` (hash verified: `f5c15cb11b9d51cf...` — MATCH)
- `data/raw/binance_funding_2022_2026.parquet` (hash recorded)

The V32.79A raw JSON output was **not read** during reproduction. Every figure below is a fresh calculation.

---

## 2. Count Verification

| Quantity | V32.79A Reported | V32.80 Reproduced | Match |
|---|---|---|---|
| OHLCV overlap bars | 40,897 | **40,897** | ✅ |
| Funding rows (BTCUSDT) | 5,113 | **5,113** | ✅ |
| Threshold (per 8h) | 0.0002283 | **0.00022831** | ✅ |
| Threshold percentile | 96.7th | **96.67th** | ✅ |
| SHORT raw observations | 144 | **144** | ✅ |
| LONG raw observations | 5 | **5** | ✅ |
| SHORT distinct episodes | 64 | **64** | ✅ |
| LONG distinct episodes | 3 | **3** | ✅ |

All counts reproduce exactly.

---

## 3. Manager Check A — Full Outcome Decomposition

### SHORT Arm (N=64)

| Outcome | Count | Frequency | Mean Gross P&L | Mean Net P&L (Binance 24 bps) |
|---|---|---|---|---|
| TP_FIRST | 19 | **29.69%** | +3.0000% | +2.7600% |
| SL_FIRST | 29 | **45.31%** | −1.5000% | −1.7400% |
| EXPIRED | 16 | **25.00%** | **+0.3884%** | +0.1484% |
| **All** | **64** | 100% | **+0.3080%** | **+0.0680%** |

**Arithmetic verification of net EV (Binance):**

$$\text{Net EV} = 0.2969 \times 2.76\% + 0.4531 \times (-1.74\%) + 0.2500 \times 0.1484\%$$
$$= 0.8194\% - 0.7884\% + 0.0371\% = \mathbf{+0.0681\%}$$

Matches simulation output (+0.0680%) within rounding. ✅ **Arithmetic verified.**

**Reconciling TP rate vs. net EV:**

The Manager correctly identified that 29.7% TP rate and +6.8 bps net EV are not contradictory. The reason:
- EXPIRED trades have a **mean gross return of +0.388%** (not zero). The price drifted favorably in the 16 expired episodes, contributing +0.0371% to net EV.
- This is why net EV is positive (+6.8 bps) even though the TP rate (29.7%) is well below the simplified two-outcome breakeven (38.7%).
- The simplified breakeven formula assumes EXPIRED trades return exactly zero, which is empirically false.
- **The primary endpoint (net EV = +6.8 bps) is the correct measure. The 38.7% reference is a heuristic only.**

### LONG Arm (N=3 — Statistically Meaningless)

| Outcome | Count | Frequency | Mean Gross P&L | Mean Net P&L (Binance) |
|---|---|---|---|---|
| TP_FIRST | 2 | 66.67% | +3.0000% | +2.7600% |
| SL_FIRST | 1 | 33.33% | −1.5000% | −1.7400% |
| EXPIRED | 0 | 0.00% | N/A | N/A |
| **All** | **3** | 100% | **+1.5000%** | **+1.2600%** |

N=3 — no reliable inference possible.

### Baseline Decompositions (N=1,704 each)

| Baseline | TP Rate | SL Rate | EXPIRED Rate | EXPIRED Mean Gross | Net EV (Binance) |
|---|---|---|---|---|---|
| BASELINE_SHORT | 17.19% | 43.08% | 39.73% | +0.4425% | −0.1945% |
| BASELINE_LONG | 16.61% | 44.42% | 38.97% | +0.4705% | −0.2248% |

Arithmetic verification: confirmed for both baselines. ✅

---

## 4. Episode Timeline Detail

The first SHORT episode entry bar is **2023-01-14 09:00 UTC** — not 2022 as might be assumed from the dataset start. This is because:
1. The funding dataset begins 2022-01-01, but extreme positive-funding events (≥ 96.7th percentile) were absent during the 2022 bear market period in the first year of the dataset.
2. The first extreme positive-funding settlement above the +25% ann threshold did not occur until January 2023.

Chronological split boundary: **2024-03-10** (episode 33 of 64).

| Period | Episodes | Date Range | TP Rate | Net EV (Binance) |
|---|---|---|---|---|
| H1 (first 32) | 32 | 2023-01-14 → 2024-03-09 | 18.8% | **−0.390%** |
| H2 (last 32) | 32 | 2024-03-10 → 2024-12-09 | **40.6%** | **+0.526%** |

**H2 TP rate (40.6%) exceeds the Binance breakeven (38.7%). H1 TP rate (18.8%) is far below it.**

The regime shift is notable: H2 spans the post-ETF approval period (Jan 2024 onwards), which is entirely within Regime 4. H1 spans the 2023 transition/compression regime.

---

## 5. Reproduction Conclusion

All V32.79A count and summary figures reproduce exactly from raw data. The arithmetic of net EV from outcome decomposition is verified. The one significant methodological issue — the DM-HLN alignment — is addressed in Workstream 3.

**Reproduction verdict: CONFIRMED — counts and summary statistics match.**

---

*Raw datasets only. No external calls. No modifications.*

