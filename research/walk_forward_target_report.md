# 📈 Multi-Fold Purged Walk-Forward Target Report

## Cross-Fold Out-of-Sample Performance (5 Folds)

| Target | Fold | Train Span | Test Span | Train n | Test n | Accuracy | Balanced Acc | Macro F1 | MCC | ROC AUC (OvR) | Brier Score | Annualized Sharpe | Max Drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Target B (2.0x TB) | 1 | 2026-04-10 to 2026-05-01 | 2026-05-01 to 2026-05-21 | 486 | 490 | 0.4061 | 0.2678 | 0.2628 | -0.1959 | 0.3852 | 0.8008 | -20.2107 | 0.5579 |
| Target B (2.0x TB) | 2 | 2026-04-10 to 2026-05-21 | 2026-05-21 to 2026-06-11 | 979 | 490 | 0.1245 | 0.2979 | 0.1274 | -0.0244 | 0.4864 | 1.3957 | -18.3264 | 0.3669 |
| Target B (2.0x TB) | 3 | 2026-04-10 to 2026-06-11 | 2026-06-11 to 2026-07-02 | 1442 | 490 | 0.2143 | 0.3448 | 0.2174 | 0.0127 | 0.5497 | 0.9924 | -0.9042 | 0.127 |
| Target B (2.0x TB) | 4 | 2026-04-10 to 2026-07-02 | 2026-07-02 to 2026-07-22 | 1906 | 490 | 0.3857 | 0.4058 | 0.3074 | 0.0119 | 0.564 | 0.6387 | -12.3814 | 0.3487 |
| Target B (2.0x TB) | 5 | 2026-04-10 to 2026-07-22 | 2026-07-22 to 2026-08-12 | 2371 | 494 | 0.5607 | 0.3621 | 0.3424 | 0.159 | 0.5159 | 0.5507 | -2.7577 | 0.1675 |

## Summary Statistics Across Folds

- **Mean AUC**: `0.5002` (Std: `0.0635`)
- **Min / Max AUC**: `0.3852` / `0.5640`
- **Mean Balanced Accuracy**: `0.3357`
- **Mean Annualized Sharpe**: `-10.9161`
