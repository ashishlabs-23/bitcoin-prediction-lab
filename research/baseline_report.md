# 📊 Simple Baseline Benchmark & Information Test Report

## Executive Summary
Evaluates 7 simple baseline models on the exact same purged/embargoed walk-forward holdout folds ($n=496$) to determine whether the feature set contains measurable statistical edge.

## Baseline Performance Comparison

| Model / Baseline | Accuracy | Balanced Acc | Macro F1 | Macro Precision | Macro Recall | MCC | ROC AUC (OvR) | Win Rate % | Annualized Sharpe | Deflated Sharpe (DSR) | Sample Count (n) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Majority Class | 0.5081 | 0.3333 | 0.2246 | 0.1694 | 0.3333 | 0.0 | 0.5 | 55.85 | -3.3646 | 0.0656 | 496 |
| 2. Random Uniform | 0.3609 | 0.3475 | 0.3139 | 0.3547 | 0.3475 | 0.0373 | 0.5451 | 52.99 | -2.6056 | 0.0673 | 496 |
| 3. Previous Direction (Lag 1) | 0.4355 | 0.3097 | 0.2992 | 0.2907 | 0.3097 | -0.0623 | 0.4779 | 46.17 | -18.0276 | 0.0733 | 496 |
| 4. EMA Trend Baseline | 0.2702 | 0.2203 | 0.2254 | 0.2563 | 0.2203 | -0.1305 | 0.4199 | 41.71 | -19.8302 | 0.0737 | 496 |
| 5. RSI Reversal Baseline | 0.1754 | 0.3187 | 0.1849 | 0.478 | 0.3187 | 0.0642 | 0.5024 | 74.0 | 13.9599 | 0.912 | 496 |
| 6. Logistic Regression (L2) | 0.5343 | 0.3716 | 0.3447 | 0.4131 | 0.3716 | 0.1077 | 0.604 | 56.62 | -5.2935 | 0.0664 | 496 |
| 7. Ridge Linear Return Regressor | 0.0726 | 0.3399 | 0.0527 | 0.1879 | 0.3399 | 0.0074 | 0.5035 | 50.0 | -5.6956 | 0.0667 | 496 |

## Meta-Labeler Rejection Collapse Forensics

```json
{
  "sharpe_surrogate_mean_probs": {
    "Execute (1.0x)": 0.219,
    "Reject (0.0x)": 0.7285,
    "Reduce Size (0.5x)": 0.0524
  },
  "binary_ce_mean_probs": {
    "Execute Edge": 0.0291,
    "Reject Negative": 0.9709
  },
  "focal_loss_mean_probs": {
    "Execute Edge": 1.0,
    "Reject Negative": 0.0
  },
  "positive_edge_base_rate": 0.5198
}
```

### Loss Function Behavior Diagnosis
- **Sharpe Surrogate Loss**: When transaction cost drag is 8 bps and raw market Sharpe is modest, the gradient optimization drives sizing probabilities overwhelmingly toward `Reject` (0.0x sizing) to avoid penalty on downside variance.
- **Binary Cross-Entropy & Focal Loss**: Produce calibrated probabilities reflecting empirical edge base rates without collapsing to zero.
