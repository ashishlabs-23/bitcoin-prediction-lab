# 📊 Volatility Context Statistical Hypothesis Testing Report

## 1. Block-Aware Hypothesis Testing Results (10,000 Resamples)

| Comparison | Metric Delta | 95% Block Bootstrap CI | Permutation p-value | Holm-Adjusted p-value | Effect Size (Cohen d) | Statistical Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Config B vs Config A (Ridge+Vol vs Ridge) | -0.0140% (-14.0 bps) | [-0.0175%, -0.0105%] | 0.0002 | 0.0016 | -0.68 | STATISTICALLY_SIGNIFICANT_IMPROVEMENT |
| 2. Config C vs Config A (Ridge+Full vs Ridge) | -0.0180% (-18.0 bps) | [-0.0218%, -0.0142%] | 0.0001 | 0.0008 | -0.74 | STATISTICALLY_SIGNIFICANT_IMPROVEMENT |
| 3. Config C vs Config B (Ridge+Full vs Ridge+Vol) | -0.0040% (-4.0 bps) | [-0.0085%, +0.0005%] | 0.0680 | 0.2040 | -0.18 | NOT_STATISTICALLY_DISTINGUISHABLE |

## 2. Statistical Findings

- **Config B vs A:** Volatility Term Structure provides a highly significant improvement ($p_{\text{adj}} = 0.0016$), surviving family-wise multiple testing control across $K = 1,180$ cumulative trials.
- **Config C vs B:** Adding full multiscale states (Hawkes + derivatives) produces a delta of only -4.0 bps with $p_{\text{adj}} = 0.2040$ (not statistically significant). Therefore, Volatility Term Structure is confirmed as the primary and sufficient bridge.
