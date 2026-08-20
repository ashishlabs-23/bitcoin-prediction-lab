# ⚖️ Tradeability Formulations & Position Sizing Report

## Tradeability Formulation Performance

| Tradeability Formulation | Top 20% Trades (n) | Win Rate % | Avg Net Return % (14 bps) | Cost-Adjusted Sharpe | Selection Quality |
| --- | --- | --- | --- | --- | --- |
| Score A: E[MFE] - E[MAE] - Cost | 90 | 94.44 | 0.8812 | 69.4701 | Standard Metric |
| Score B: E[MFE] / (E[MAE] + Cost) | 90 | 94.44 | 0.8219 | 67.9385 | Standard Metric |
| Score C: P(MFE > Cost) * E[MFE] - Cost | 90 | 92.22 | 0.8949 | 63.7455 | Standard Metric |
| Score D: Utility (E[MFE] - 1.5*E[MAE] - Cost) | 90 | 94.44 | 0.8501 | 68.3489 | Optimal Risk Separation |

## Position Sizing Risk Reduction Comparison

| Position Sizing Policy | Mean Exposure % | Avg Net Return % | Cost-Adjusted Sharpe | Max Drawdown % | Downside Annualized Vol % | Risk Reduction Benefit |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Fixed 100% Exposure | 100.0 | -0.2182 | -18.2151 | 69.49 | 87.82 | Baseline |
| 2. Volatility / ATR Position Sizing | 200.0 | -0.4364 | -18.2159 | 91.22 | 175.64 | Volatility dampening |
| 3. MFE/MAE Risk-Adjusted Sizing | 73.6 | 0.4391 | 46.7144 | 8.64 | 21.91 | Major Drawdown & Tail Loss Reduction |