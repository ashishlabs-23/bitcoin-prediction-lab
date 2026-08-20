# 🔬 Feature Information & Incremental Ablation Report

## Executive Summary
Measures the information capacity of 8 feature families and tests controlled incremental additions (Order Flow, News/Sentiment) against baseline technicals.

## Controlled Model Ablations

| Configuration | Features Used | Accuracy | Balanced Acc | Delta Balanced Acc | Macro F1 | MCC | ROC AUC (OvR) | Delta AUC | Brier Score | Annualized Sharpe | Sample Count (n) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Model A (Baseline Technicals 1-21) | 21 | 0.496 | 0.3687 | 0.0 | 0.3242 | 0.0406 | 0.6216 | 0.0 | 0.5589 | -3.7752 | 496 |
| Model B (Baseline + Order Flow 1-25) | 25 | 0.5242 | 0.3548 | -0.0139 | 0.3183 | 0.0825 | 0.6 | -0.0216 | 0.562 | -6.6952 | 496 |
| Model C (Baseline + News/Sentiment 1-21 + 29-32) | 25 | 0.496 | 0.3687 | 0.0 | 0.3242 | 0.0406 | 0.6218 | 0.0002 | 0.5588 | -3.7752 | 496 |
| Model D (Full Multimodal Stack 1-32) | 32 | 0.5343 | 0.3716 | 0.0029 | 0.3447 | 0.1077 | 0.6043 | -0.0173 | 0.5606 | -5.2935 | 496 |

## Top Predictive Features by Mutual Information & Correlation

| Feature Name | Family | Correlation with Return | Mutual Information | Univariate AUC |
| --- | --- | --- | --- | --- |
| bid_ask_spread | Microstructure & Orderbook Depth | 0.1348 | 0.5101 | 0.5322 |
| plus_minus_di_spread | Volume & Directional Flow | 0.0634 | 0.4925 | 0.5112 |
| norm_close_ret | Price Action / OHLCV | -0.0347 | 0.1335 | 0.5279 |
| macd_hist | Momentum Oscillators | -0.048 | 0.1307 | 0.5709 |
| norm_high | Price Action / OHLCV | -0.0343 | 0.111 | 0.5298 |
| norm_low | Price Action / OHLCV | -0.0331 | 0.1 | 0.5245 |
| norm_open | Price Action / OHLCV | -0.0333 | 0.0996 | 0.5266 |
| order_book_imbalance | Microstructure & Orderbook Depth | 0.0386 | 0.0978 | 0.5246 |
| depth_liquidity_score | Microstructure & Orderbook Depth | -0.0006 | 0.0937 | 0.5171 |
| bollinger_width | Volatility & Bands | -0.0821 | 0.0436 | 0.5801 |
| roc_10 | Moving Averages / Trend | 0.0707 | 0.0393 | 0.5088 |
| rsi_14 | Momentum Oscillators | 0.0668 | 0.0348 | 0.5184 |
| sentiment_embed_dim1 | News Sentiment & Embeddings | 0.0 | 0.0298 | 0.5 |
| norm_volume | Price Action / OHLCV | -0.0082 | 0.0211 | 0.5442 |
| macd_signal | Momentum Oscillators | 0.0546 | 0.0178 | 0.5156 |

## Regime-Conditional Performance

| Regime | Sample Count (n) | BUY Count | SELL Count | HOLD Count | Majority Baseline | Momentum Accuracy | Balanced Acc | Avg Future Return % | Strategy Net Return % | Regime Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sideways | 187 | 88 | 78 | 21 | 0.4706 | 0.4011 | 0.3011 | 0.0303 | -0.186 | -16.1377 |
| Accumulation | 341 | 161 | 156 | 24 | 0.4721 | 0.4282 | 0.3077 | 0.0302 | -0.188 | -17.2002 |
| Distribution | 2230 | 982 | 945 | 303 | 0.4404 | 0.426 | 0.3287 | -0.0363 | -0.0939 | -7.498 |
| Capitulation | 218 | 97 | 99 | 22 | 0.4541 | 0.4495 | 0.3333 | 0.0182 | -0.1598 | -12.7956 |