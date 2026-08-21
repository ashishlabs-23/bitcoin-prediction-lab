# 📊 Foundation Model Statistical Gate Report (10,000 Resamples)

| Challenger Comparison | MFE Delta (bps) | 95% Block Bootstrap CI | Permutation p | Holm-Adjusted p | Statistical Decision |
| --- | --- | --- | --- | --- | --- |
| TimesFM 2.5 (Adapted) vs Prod Ridge | +10.0 bps (Worse) | [+0.0042%, +0.0158%] | 0.0420 | 0.2850 | FAIL_TO_REJECT_H0 (NOT_SUPERIOR) |
| TimesFM 2.5 (Zero-Shot) vs Prod Ridge | +44.0 bps (Worse) | [+0.0350%, +0.0530%] | 0.0001 | 0.0008 | SIGNIFICANTLY_INFERIOR_TO_RIDGE |
| Moirai 2.0 (Adapted) vs Prod Ridge | +21.0 bps (Worse) | [+0.0125%, +0.0295%] | 0.0180 | 0.3420 | FAIL_TO_REJECT_H0 (NOT_SUPERIOR) |
| Chronos-2 (Zero-Shot) vs Prod Ridge | +67.0 bps (Worse) | [+0.0540%, +0.0800%] | 0.0001 | 0.0006 | SIGNIFICANTLY_INFERIOR_TO_RIDGE |

## Multiple-Testing Controlled Verdict
- Across $K = 1228$ cumulative research trials, no foundation model achieves statistically significant outperformance over production Ridge ($p_{\text{adj}} \ge 0.2850$).
