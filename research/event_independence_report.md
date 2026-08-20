# ⏱️ Event Independence & Cluster Filtering Report

## Raw Bar-Level vs Event-Clustered Granularity

| Granularity Level | Nominal Sample (n) | Effective Sample (n_eff) | Serial Autocorrelation (rho_1) | Win Rate % | Gross Return % | Net Return % | Cost-Adjusted Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. Raw Bar-Level Observations | 178 | 28 | 0.7254 | 42.7 | -0.3323 | -0.4723 | -3.4737 |
| B. Clustered Event Level | 27 | 27 | -0.1284 | 40.74 | -0.5241 | -0.6641 | -7.7552 |
- **Raw Shock Hours**: `178`
- **Discrete Event Clusters**: `27`
- **Average Shock Duration**: `6.59 hours`
- **Overlapping Hours %**: `84.83%`

## Non-Overlapping Cooldown Policy Performance

| Execution Policy | Independent Events (n) | Win Rate % | Avg Gross Return % | Avg Net Return % | Cost-Adjusted Sharpe | Net Expectancy ($10 base) |
| --- | --- | --- | --- | --- | --- | --- |
| Non-Overlapping (12h Cooldown) | 23 | 43.48 | -0.3433 | -0.4833 | -5.7887 | -0.0483 |
| Non-Overlapping (24h Cooldown) | 21 | 42.86 | -0.3416 | -0.4816 | -5.4531 | -0.0482 |
| Non-Overlapping (48h Cooldown) | 19 | 47.37 | -0.3044 | -0.4444 | -4.6618 | -0.0444 |