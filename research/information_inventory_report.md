# 📋 BTCognitive Information Inventory & Redundancy Audit

## Executive Summary
Comprehensive forensic inventory of all 32 existing features across 6 active categories. Identifies structural collinearity and missing information layers.

## Information Group Distribution

| Information Group | Feature Count |
| --- | --- |
| TECHNICAL | 13 |
| PRICE | 6 |
| ORDER FLOW | 4 |
| SENTIMENT | 4 |
| DERIVATIVES | 3 |
| VOLUME | 2 |

## Complete 32-Feature Inventory

| name | group | lookback | transform | pit_safe | source | missing_rate |
| --- | --- | --- | --- | --- | --- | --- |
| ret_1h | PRICE | 1h | log(p/p_lag) | True | OHLCV | 2.471882338400692e-05 |
| ret_4h | PRICE | 4h | log(p/p_lag) | True | OHLCV | 9.887529353602768e-05 |
| ret_24h | PRICE | 24h | log(p/p_lag) | True | OHLCV | 0.0005932517612161661 |
| vol_24h | PRICE | 24h | rolling_std(ret_1h) | True | OHLCV | 0.0 |
| high_low_ratio | PRICE | 1h | log(high/low) | True | OHLCV | 0.0 |
| close_open_ratio | PRICE | 1h | log(close/open) | True | OHLCV | 0.0 |
| rsi_14 | TECHNICAL | 14h | Wilder RSI [0, 100] | True | OHLCV | 0.0003460635273760969 |
| macd_line | TECHNICAL | 26h | EMA(12) - EMA(26) | True | OHLCV | 0.0 |
| macd_signal | TECHNICAL | 9h | EMA(macd_line, 9) | True | OHLCV | 0.0 |
| macd_hist | TECHNICAL | 9h | macd_line - macd_signal | True | OHLCV | 0.0 |
| sma_ratio_20 | TECHNICAL | 20h | close / SMA(20) - 1 | True | OHLCV | 0.0004696576442961315 |
| sma_ratio_50 | TECHNICAL | 50h | close / SMA(50) - 1 | True | OHLCV | 0.0012112223458163392 |
| sma_ratio_200 | TECHNICAL | 200h | close / SMA(200) - 1 | True | OHLCV | 0.0 |
| bb_width_20 | TECHNICAL | 20h | (upper - lower) / mid | True | OHLCV | 0.0 |
| bb_pct_20 | TECHNICAL | 20h | (close - lower)/(upper-lower) | True | OHLCV | 0.0 |
| atr_14 | TECHNICAL | 14h | ATR(14) / close | True | OHLCV | 0.00032134470399209 |
| vwap_ratio | TECHNICAL | 24h | close / VWAP - 1 | True | OHLCV | 0.0 |
| stoch_k | TECHNICAL | 14h | Stochastic %K | True | OHLCV | 0.0 |
| stoch_d | TECHNICAL | 3h | SMA(%K, 3) | True | OHLCV | 0.0 |
| vol_z_24h | VOLUME | 24h | (vol - mean)/std | True | OHLCV | 0.0 |
| vol_ratio_20 | VOLUME | 20h | vol / SMA(vol, 20) | True | OHLCV | 0.0 |
| order_book_imbalance | ORDER FLOW | Point-in-time | (bid_qty - ask_qty)/(bid+ask) | True | OrderBook L2 | 0.0 |
| spread_bps | ORDER FLOW | Point-in-time | (ask - bid)/mid * 10000 | True | OrderBook L2 | 0.0 |
| depth_ratio_1pct | ORDER FLOW | Point-in-time | bid_vol_1pct / ask_vol_1pct | True | OrderBook L2 | 0.0 |
| trade_flow_imbalance | ORDER FLOW | 1h | (buy_vol - sell_vol)/total_vol | True | Trades | 0.0 |
| funding_rate | DERIVATIVES | 8h | funding_rate | True | Perpetual | 0.0 |
| open_interest_change_24h | DERIVATIVES | 24h | OI / OI_lag - 1 | True | Perpetual | 0.0 |
| oi_vol_ratio | DERIVATIVES | 24h | OI / Volume_24h | True | Perpetual | 0.0 |
| sentiment_score | SENTIMENT | Point-in-time | FinBERT Polarity [-1, 1] | True | News/Social | 0.0 |
| sentiment_embed_dim0 | SENTIMENT | Point-in-time | Dense Embedding Dim 0 | True | News/Social | 0.0 |
| sentiment_embed_dim1 | SENTIMENT | Point-in-time | Dense Embedding Dim 1 | True | News/Social | 0.0 |
| sentiment_embed_dim2 | SENTIMENT | Point-in-time | Dense Embedding Dim 2 | True | News/Social | 0.0 |

## High Collinearity & Redundant Feature Pairs (|Spearman ρ| ≥ 0.80)

| Feature A | Feature B | Spearman Correlation | Relationship |
| --- | --- | --- | --- |
| ret_24h | rsi_14 | 0.8472 | High Collinearity |
| ret_24h | sma_ratio_50 | 0.8784 | High Collinearity |
| rsi_14 | sma_ratio_20 | 0.9149 | High Collinearity |
| rsi_14 | sma_ratio_50 | 0.9092 | High Collinearity |
| macd_signal | sma_ratio_50 | 0.8583 | High Collinearity |
| sentiment_score | sentiment_embed_dim0 | 1.0 | Near Duplicate |
| sentiment_score | sentiment_embed_dim1 | 0.9699 | Near Duplicate |
| sentiment_embed_dim0 | sentiment_embed_dim1 | 0.9699 | Near Duplicate |

## Missing Information Layers
1. **Macro / Cross-Asset**: DXY, Nasdaq, S&P 500, Gold, Treasury Yields (10Y/2Y) currently absent.
2. **Microstructure & Order Flow Depth**: Microprice, order-book slope, liquidity asymmetry, aggressive volume delta absent.
3. **Multi-Timeframe Context**: 1m, 5m, 15m, 4h, 12h, 1d point-in-time context not explicitly modeled.
4. **Macroeconomic Event Proximity**: CPI, FOMC, NFP calendars absent.
