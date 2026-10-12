# BTCognitive — BTC/USD Market Monitor

BTCognitive serves one active read-only market-monitor application. It displays source-backed BTC/USD spot observations, closed hourly candles, technical features, optional derivatives context, and an **experimental historical-distribution forecast**. The authenticated production model remains blocked while frozen inputs and evaluation evidence are unverified.

## What the application does

- Retrieves BTC/USD quotes and hourly candles through public Coinbase, Bitstamp and Kraken endpoints. It fails over between providers without blending different instruments into a synthetic spot price.
- Shows quote retrieval time, candle freshness, bid–ask spread, cross-venue quote divergence and source/provider errors.
- Calculates momentum, recent realized volatility, RSI and relative volume from validated closed BTC/USD candles.
- Displays Binance BTCUSDT perpetual funding/open interest as a separate USDT-quoted derivatives context; these values are never substituted for BTC/USD spot.
- Estimates 1h, 4h and 24h P10/P50/P90 prices from non-overlapping historical log returns when enough complete history is available.
- Calculates a rolling-origin historical check against a zero-return baseline when the sample is large enough.

## Forecast limits

The active range estimator is an empirical baseline, **not** the frozen HAR-RS-DOW/conformal production model and not an ML model trained to predict direction. P10–P90 represents a nominal **central 80% historical quantile band**, not a calibrated 90% confidence interval. P50 is the historical median; directional probability, TP/SL targets and order execution are intentionally absent.

Historical walk-forward measurements are descriptive; they do not establish a durable edge or profitability. Production forecasts remain blocked until exact data/artifact lineage, untouched evaluation evidence and formal research authorization are authenticated. Do not add fabricated prices, performance metrics, confidence scores, datasets or fallback trade targets to bypass this gate.

Macro series and ETF/exchange-flow inputs are shown as not configured unless a verified provider is actually wired in. Missing data stays missing.

## Run locally

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. For a hosted service, set `BTCOGNITIVE_HOST=0.0.0.0` and use the platform-provided `PORT`. The default process binding is loopback for local use.

## API

- `GET /api/dashboard?horizon=24h` — quote, candles, drivers, optional context and baseline forecast. Horizons: `1h`, `4h`, `24h`.
- `GET /api/market-drivers` — alias for the unified dashboard payload.
- `GET /prediction/latest?horizon=24h` and `GET /prediction/range?horizon=24h` — compatibility routes returning the same experimental baseline, never a fabricated directional signal.
- `GET /api/research/entry-tp-sl` — explicitly blocked response until evidence is authenticated.
- `GET /health` — monitor health and research authorization state.

## Tests

Focused deterministic tests do not require live exchange/network access:

```bash
python -m pytest -q tests/test_market_drivers.py tests/test_market_monitor_routes.py
```

The repository retains a legacy research suite with historical frozen-data expectations requiring separate provenance repair. Those constraints are not bypassed by the market monitor.

## Security and scope

- Read-only market-data access; no broker/order execution.
- Research authorization and frozen production inference remain disabled.
- No automatic retraining or promotion.
- Provider outages, stale observations and insufficient history must result in explicit unavailable states, never synthetic values.
