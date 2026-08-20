# 💰 Multi-Task & Cost-Aware Economic Targets Report

## Multi-Task Prediction Decomposition

| Target Task | Metric Type | OOS Performance | Interpretation |
| --- | --- | --- | --- |
| Task 1: Expected Return Sign P(up) | ROC AUC | 0.5015 | Directional noise-dominated |
| Task 2: Expected Magnitude |r_24h| | Spearman IC | 0.1785 | Statistically meaningful volatility predictability |
| Task 3: Hurdle Probability (|r| > 14 bps) | ROC AUC | 0.5452 | Volatility expansion detection |
| Task 4: Maximum Favorable Excursion (MFE) | Spearman IC | 0.2366 | Predictable upper tail boundary |
| Task 5: Maximum Adverse Excursion (MAE) | Spearman IC | -0.1541 | Predictable risk/downside boundary |