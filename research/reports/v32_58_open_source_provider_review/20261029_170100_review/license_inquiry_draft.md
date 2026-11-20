# BTCognitive — Market-Data Rights Inquiry Draft

**Document ID:** LID-20261029-01  
**Target Vendors:** Bitstamp (`partners@bitstamp.net`), CoinAPI (`sales@coinapi.io`), CoinGecko (`support@coingecko.com`), Twelve Data (`sales@twelvedata.com`)  
**Purpose:** Formal inquiry to secure binding written commercial display, caching, and analytics permissions for BTCognitive.

---

### Inquiry Template

**Subject:** Commercial market-data licensing for BTC/USD charting and research application

Hello,

I am evaluating a market-data provider for BTCognitive, a hosted charting and market-research application focused initially on BTC/USD. The product will display candles and volume, technical indicators, and research-only volatility/uncertainty forecasts. It will not execute orders, connect to user trading accounts, hold funds or provide broker services.

Before integrating your feed, I would appreciate written confirmation of the data rights and plan required for this exact use case.

Please confirm whether the proposed licence permits:
1. Displaying historical and current BTC/USD OHLCV candles, volume, timeframes, tooltips and last-updated/source indicators in a public web application.
2. Using the data to calculate and display technical indicators, volatility summaries, forecast/risk envelopes, alerts and other non-reconstructable derived analytics.
3. Serving a paid or free product to multiple end users, with your required attribution or logo.
4. Server-side caching and retention of historical candles for chart loading, and the retention/deletion policy after termination.
5. Using selected data as inference-time input to an existing research model.
6. Using data for training, fine-tuning, validation, walk-forward backtesting and benchmark evaluation of forecasting models. Please state separately which of these are permitted and which need a separate agreement.
7. Displaying the series in an interactive chart that lets users zoom, inspect individual candle values and export a chart image. We do not intend to offer raw bulk-data downloads or a downstream market-data API unless separately licensed.
8. Sending data to our own hosted application services and approved infrastructure providers for processing.

Please also provide:
- The permitted market/pair identifier (BTC/USD versus BTC/USDT or aggregate BTC/USD), available timeframes and historical depth;
- Refresh/latency guarantees, rate limits, outage/correction policy and any SLA;
- Mandatory attributions and terms that must be shown to end users;
- Pricing for a small initial beta and any limits by number of users, requests, caching duration or displayed symbols;
- Any additional exchange permissions or separate licences required;
- The binding contract or terms clause that grants the above rights.

We will keep data-provider credentials server-side and will not expose your API as a reusable public endpoint unless specifically licensed. If any element above is prohibited under your standard plan, please identify the required commercial licence or alternative permitted architecture.

Thank you,

BTCognitive Project Team

