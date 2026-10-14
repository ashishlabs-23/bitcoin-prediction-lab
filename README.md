# BTCognitive — Research Terminal

BTCognitive serves one web frontend: the full Research Terminal in `web/index.html`, powered by `web/app.js` and `web/styles.css`. Its live chart uses Coinbase Exchange BTC-USD candles and ticker data only, with UTC-aligned 1m, 5m, 15m, 1h and 1d candles; 4h candles are aggregated from aligned 1h candles. The candle-close countdown follows the latest Coinbase event timestamp when available. A visible preview notice warns that some legacy figures may be static or historical. Frozen model inputs remain unverified, so production forecasts and trading are disabled.

## Market data and API

The backend provides BTC/USD quotes and hourly candles through public Coinbase, Bitstamp and Kraken endpoints, with explicit provider/source states and no synthetic cross-instrument spot price. It calculates momentum, recent realized volatility, RSI and relative volume from validated closed candles. Binance BTCUSDT perpetual data remains a separate derivatives context.

The API can expose experimental 1h, 4h and 24h historical-distribution ranges when live data and sufficient history are available. Those ranges are not forecasts from the frozen production model and do not establish predictive or economic superiority.

## Forecast limits

Any range estimator exposed by the API is an empirical baseline, **not** the frozen HAR-RS-DOW/conformal production model and not an ML model trained to predict direction. P10–P90 represents a nominal **central 80% historical quantile band**, not a calibrated 90% confidence interval. P50 is the historical median; directional probability, TP/SL targets and order execution are intentionally absent.

Historical walk-forward measurements are descriptive; they do not establish a durable edge or profitability. Production forecasts remain blocked until exact data/artifact lineage, untouched evaluation evidence and formal research authorization are authenticated. Do not add fabricated prices, performance metrics, confidence scores, datasets or fallback trade targets to bypass this gate.

Macro series and ETF/exchange-flow inputs are shown as not configured unless a verified provider is actually wired in. Missing data stays missing.

Notification settings are saved by the backend; webhook URLs, SMTP identities and Telegram credentials are not returned to the browser. Notification changes and test sends require an administrator API key configured as `BTCOGNITIVE_ADMIN_KEY`. Discord destinations are restricted to HTTPS `discord.com/api/webhooks/` URLs. Generic webhook destinations require an exact hostname in `BTCOGNITIVE_WEBHOOK_ALLOWED_HOSTS`; configure only hosts you trust. Email and webhook channels remain unconfigured unless their credentials/settings are provided. “Send Test Notification” sends a neutral delivery-test message (not a market signal) and reports whether each configured external channel delivered, failed or is not configured.

## Run locally

Python 3.11+ is recommended.
Copy `.env.example` to `.env` and provide only the credentials and allowlisted hosts you intend to use. `.env` is read at startup, and environment variables take precedence.

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
