# Frequently Asked Questions (FAQ)

### 1. What machine learning architecture is used for predictions?
BTCognitive employs an **Adaptive Regime Ensemble** combining Random Forest classifiers and XGBoost quantile regressors trained under Purged Walk-Forward Cross-Validation.

### 2. How are risk buffers (Take-Profit & Stop-Loss) determined?
Dynamic barriers are calculated per bar based on the 14-period Average True Range (ATR) normalized by price, rather than fixed percentage targets.

### 3. What is the Deflated Sharpe Ratio (DSR)?
The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) is a statistical metric that penalizes backtest Sharpe ratios for selection bias and multi-trial testing over $N$ strategy variants.

### 4. Can this run client-side in the browser?
The frontend provides real-time streaming charts and visual heuristics directly via WebSockets. Full ensemble ML inference, SHAP decomposition, and regime clustering execute securely on the Python backend.
