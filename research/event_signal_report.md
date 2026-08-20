# ⚡ Point-in-Time Event Shock Forensics Report

## Executive Summary
Evaluates price, volatility, and volume behavior immediately following 7 point-in-time market shocks.

## Event Shock Performance Table

| Event / Shock Type | Sample Count (n) | Mean Abs Future Move % | Directional Hit Rate % | Gross Expectancy % | Net Expectancy ($10 base) | Cost-Adjusted Sharpe | Assessment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Return Shock (|r_1h| > 2 sigma) | 196 | 1.4526 | 54.08 | 0.0405 | -0.01 | -2.5553 | Negative after 14 bps drag |
| 2. Volatility Shock (ATR / Price Expansion) | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | Insufficient Sample (n < 20) |
| 3. Volume Surge (Vol > 2x Mean) | 270 | 1.558 | 53.7 | 0.0872 | -0.0053 | -1.4735 | Negative after 14 bps drag |
| 4. Funding Spike (|funding| > 2 sigma) | 1077 | 1.3323 | 47.35 | 0.2503 | 0.011 | 6.9243 | Positive Net Expectancy |
| 5. Open Interest Shock (|dOI| > 2 sigma) | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | Insufficient Sample (n < 20) |
| 6. Order Flow Extreme (|OBI| > 0.60) | 166 | 1.4454 | 43.37 | -0.2875 | -0.0427 | -10.515 | Negative after 14 bps drag |
| 7. Macro Event Proximity Window | 105 | 1.2691 | 50.48 | 0.1824 | 0.0042 | 0.8813 | Positive Net Expectancy |