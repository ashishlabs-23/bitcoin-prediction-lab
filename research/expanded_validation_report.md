# 📊 Expanded Historical Data Audit & 3-Stage Split Report

## Historical Dataset Audit

| Audit Metric | Value |
| --- | --- |
| Exchange / Source | Binance BTC/USDT Perpetual & Spot |
| Sampling Frequency | 1 Hour (1h OHLCV) |
| First Timestamp | 2026-04-10 16:00:00+00:00 |
| Last Timestamp | 2026-08-13 15:00:00+00:00 |
| Total Hourly Bars | 3000 |
| Total Calendar Days | 124.96 days |
| Total Calendar Months | 4.11 months |
| Duplicate Bars Count | 0 |
| Missing Bars Count | 0 |

## Strict 3-Stage Chronological Split Structure

- **Train Partition (70%)**: `0` to `2100` bars (2026-04-10 16:00:00+00:00 to 2026-07-07 04:00:00+00:00)
- **Validation Partition (15%)**: `2100` to `2550` bars (2026-07-07 04:00:00+00:00 to 2026-07-25 22:00:00+00:00)
- **Untouched Final Confirmation (15%)**: `2550` to `3000` bars (2026-07-25 22:00:00+00:00 to 2026-08-13 15:00:00+00:00)
