# 🎯 BTCUSD Prediction Target & Horizon Forensics Report

## Executive Summary
This report evaluates multiple BTCUSD directional and continuous prediction targets across 1h, 3h, 6h, 12h, and 24h horizons, as well as ATR-normalized event-based Triple Barrier labels (0.5x, 1.0x, 1.5x, 2.0x ATR).

## Target Comparison Table

| Target Type | Horizon (Bars) | Total Samples | BUY Count | SELL Count | HOLD Count | BUY Pct | SELL Pct | HOLD Pct | Majority Baseline | Class Entropy (bits) | Overlap Rate | Avg Abs Return % | Net Return (8bps) % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed Horizon 1h | 1 | 2999 | 1309 | 1328 | 362 | 43.65 | 44.28 | 12.07 | 0.4428 | 1.4106 | 0.0 | 0.2654 | 0.1854 |
| Fixed Horizon 3h | 3 | 2997 | 1319 | 1362 | 316 | 44.01 | 45.45 | 10.54 | 0.4545 | 1.3804 | 1.0 | 0.4623 | 0.3823 |
| Fixed Horizon 6h | 6 | 2994 | 1347 | 1285 | 362 | 44.99 | 42.92 | 12.09 | 0.4499 | 1.4107 | 1.0 | 0.6451 | 0.5651 |
| Fixed Horizon 12h | 12 | 2988 | 1380 | 1315 | 293 | 46.18 | 44.01 | 9.81 | 0.4618 | 1.3644 | 1.0 | 0.917 | 0.837 |
| Fixed Horizon 24h | 24 | 2976 | 1366 | 1335 | 275 | 45.9 | 44.86 | 9.24 | 0.459 | 1.352 | 1.0 | 1.352 | 1.272 |
| Triple Barrier 0.5x ATR | 24 | 2976 | 1486 | 1486 | 4 | 49.93 | 49.93 | 0.13 | 0.4993 | 1.0134 | 0.478 | 0.4275 | 0.3475 |
| Triple Barrier 1.0x ATR | 24 | 2976 | 1460 | 1504 | 12 | 49.06 | 50.54 | 0.4 | 0.5054 | 1.0337 | 0.7425 | 0.6232 | 0.5432 |
| Triple Barrier 1.5x ATR | 24 | 2976 | 1475 | 1415 | 86 | 49.56 | 47.55 | 2.89 | 0.4956 | 1.1596 | 0.8666 | 0.8039 | 0.7239 |
| Triple Barrier 2.0x ATR | 24 | 2976 | 1385 | 1300 | 291 | 46.54 | 43.68 | 9.78 | 0.4654 | 1.3635 | 0.9261 | 0.9376 | 0.8576 |

## Key Findings
1. **1-Hour Directional Target**: Features high noise and low average return (0.265% gross, 0.185% net 8bps). Overlap rate is 0.00.
2. **24-Hour Fixed Horizon**: Exhibits significantly higher net return (1.272%) with robust class entropy (1.352 bits).
3. **Triple Barrier Labels (1.5x - 2.0x ATR)**: Balances event-driven profit capture with reasonable holding periods and non-degenerate class distribution.
