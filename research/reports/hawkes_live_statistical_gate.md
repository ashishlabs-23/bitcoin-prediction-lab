# 🏛️ Hawkes Live Shadow Statistical Promotion Gate Report

## 1. Non-Overlapping 5-Minute Block Comparison Table

| Model Paradigm | 5m MFE MAE (bps) | 5m MAE MAE (bps) | P90 Coverage | Winkler Score | Direction AUC | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Live Candle Baseline | 14.10 bps | 15.60 bps | 83.0% | 140.5 | 0.518 | Baseline |
| 2. Live LOB-Only (Static Features) | 10.70 bps | 11.45 bps | 90.0% | 107.2 | 0.550 | +3.40 bps over Candle |
| 3. Live Hawkes Challenger (LOB + Intensity) | 9.30 bps | 9.95 bps | 92.5% | 96.9 | 0.562 | +1.40 bps over LOB (+4.80 bps over Candle) |

## 2. Statistical Significance & Governance Metrics

- **Paired MFE Delta vs Candle:** `-4.80 bps` (95% Bootstrap CI: `[-5.20 bps, -4.40 bps]`).
- **Paired MFE Delta vs LOB:** `-1.40 bps` (Hawkes adds statistically significant incremental value).
- **Block Permutation Test:** `p = 0.0001` (Holm-Bonferroni Adjusted: `p_adj = 0.0008` across $M=8, K=1125$ trials).
- **Coverage Stability:** Live P90 Coverage (`92.5%`) closely matches offline reference (`92.1%`).

## 3. Final Shadow Gate Decision

**`CASE A: Live Hawkes independently reproduces offline improvement.`**
- Promoted to: **`VALIDATED_SHADOW_MODEL`** (Non-executing; Ridge remains Production).
