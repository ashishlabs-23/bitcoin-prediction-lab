# Local Windows Run Guide

## Start the application

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1
```

The launcher uses `.venv_win\Scripts\python.exe`, starts the existing FastAPI
application with one Uvicorn worker, and serves the existing `web` frontend
through FastAPI's root `StaticFiles(..., html=True)` mount. It binds only to
`127.0.0.1`; the default URL is `http://127.0.0.1:8765/`.

The launcher fails rather than stopping or reusing another process if the
requested port is occupied. To select a different free port, use
`-Port 8770`. Add `-OpenBrowser` to open the URL after the static page and
fixture-only health contract pass startup checks. Ctrl+C stops the server
started by this launcher. Per-run stdout and stderr logs are written under
`logs\local-run\`.

## Data and capability limits

This command explicitly sets `DATA_MODE=fixture`, `BTC_DATA_MODE=fixture`, and
`BTC_LOCAL_FIXTURE_FEED=1`. The opt-in fixture candle endpoint is only used
when health confirms fixture mode and the flag is enabled. Its deterministic
bars are test fixtures held in memory; they are not market observations. If
the fixture is absent or not enabled, the UI leaves candle data unavailable
instead of substituting values or switching to a provider. The fixture lane
must not read protected market datasets or make external market-data requests.

When fixture mode is active, the UI labels the data exactly:

> LOCAL TEST FIXTURE ONLY — NOT MARKET DATA

Treat every displayed value and dependent output as test-only, not validated
research or market evidence. Standard HAR is unavailable; Entry/TP/SL analysis
is blocked; C2 is unavailable; journal functions, terminal analysis, and
research evidence are unavailable or unvalidated in this fixture-only run.
Existing routes and screens remain present, but their presence does not mean
their outputs are supported. Live trading and order submission remain
disabled. This launcher does not authorize or enable trading.

The frontend currently references some browser libraries and fonts from CDNs;
those presentation assets may require browser internet access. This is not a
market-data provider configuration, and the launcher does not enable one.
