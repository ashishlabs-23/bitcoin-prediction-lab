# V37.4-R1 Deterministic QA Report

**Initial QA disposition:** `INCONCLUSIVE` — the initial deterministic run found two implementation defects. Both were fixed and retested; see the dated follow-up below. The initial QA test run itself used no live exchange data.

## Scope and evidence

The QA work added `tests/test_v37_4_r1_*.py` tests and this report. The tests use local Bitstamp-shaped trade messages, a fake WebSocket connection/backoff clock, an in-memory FastAPI lifespan feed, and an API-shaped frontend fixture. No test establishes prospective validation. A separate bounded manager connectivity check later received one real Bitstamp message and passed its in-memory candle snapshot through the existing API route; it is recorded below and in the manager acceptance report.

Coverage includes seconds/microseconds conversion and receipt lag; malformed and non-BTCUSD inputs; duplicate IDs; out-of-order deterministic minute OHLCV and boundaries; missing-minute gap reporting without fill; staleness threshold; no-data/disconnected states; capped exponential reconnect delay; FastAPI start/stop and actual parsed-observation routing; and chart display of API-shaped Bitstamp OHLCV.

## Test results

| Command | Result |
|---|---|
| `.venv_win\Scripts\pytest tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py -q --tb=line` | **12 passed, 2 failed**, 1 existing Pydantic deprecation warning |
| `npm run check --silent` | **Passed** |
| `git diff --check -- api/candle_manager.py engine/market_data_feed.py api/market_monitor_routes.py api/server.py web/app.js` | **Passed** |
| `.venv_win\Scripts\pytest tests\test_market_drivers.py tests\test_market_monitor_routes.py tests\test_frontend_contracts.py -q` (run before these QA additions) | **16 passed, 1 failed**, 1 Pydantic deprecation warning. The failure is the existing frontend-directory assertion: it expects only `app.js`, `index.html`, and `styles.css`, but `web/analysis_contract.js` is present. |

The two initial V37.4-R1 failures were:

1. `test_parser_rejects_nonintegral_trade_ids`: `_handle_raw_message` converts `id=1.5` to integer `1` and accepts the malformed observation. The trade ID must be validated as integral rather than silently truncated.
2. `test_chart_displays_bitstamp_candles_from_api_shaped_observation`: the 1-minute Bitstamp chart displays the correct Bitstamp source and API close, but labels the receipt-time indicator `Coinbase quote:`. This misattributes Bitstamp timing to Coinbase.

## Independent implementation review

- **Ingestion:** fractional trade IDs are accepted through `int(data["id"])` coercion (`engine/market_data_feed.py:579`); the deterministic malformed-ID test reproduces it.
- **API/frontend:** the chart’s exchange-clock display says `Coinbase quote:` (`web/app.js:2858`) while the 1-minute API response supplies the Bitstamp receipt timestamp; the API-shaped display test reproduces the mismatch.

No implementation files were changed by the QA workstream. Its fixtures demonstrated the route and UI contract path. The later manager check verified one real in-memory observation through the API route, but not a full running-app/browser path.

## Governed decisions

1. **Research Experiment:** `INCONCLUSIVE`
2. **Prospective Evidence:** `NOT_STARTED`
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`

## Follow-up — 2026-11-04

The manager fixed both initial findings without weakening the tests:

1. The trade parser now rejects fractional/non-integer trade IDs instead of coercing them with `int()`.
2. The chart now labels the receipt timestamp as a Bitstamp observation when the selected source is Bitstamp, rather than calling it a Coinbase quote.

The corrected focused command was:

```text
.\.venv_win\Scripts\pytest.exe tests\test_v37_4_r1_trade_feed.py tests\test_v37_4_r1_api.py tests\test_v37_4_r1_frontend.py -q --tb=short
```

Result: **15 passed**, with one existing Pydantic deprecation warning. The protected-file test guard reported 1,848 protected files and identical before/after manifest SHA-256 values (`d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`).

A separate bounded, read-only Bitstamp connectivity check received one actual trade, created one in-memory candle, and requested `/api/market/candles?symbol=BTC-USD&interval=1m&limit=20`. The route returned HTTP 200, source `bitstamp`, exchange `Bitstamp`, symbol `BTC/USD`, one candle, and `STALE`. Event time was `2026-11-04T16:11:57.653000Z`; local receipt time was `2026-11-04T16:15:43.729603Z`; measured event-to-receipt delay was **226.076603 seconds**. The API correctly reported `analysis.status=DATA_UNAVAILABLE` and `engine_invoked=false` because stale, insufficient history is not eligible for analysis. The observation was held in memory only and was not used for model validation.

The original two test failures remain documented above as historical evidence. The corrected deterministic suite passes, but the overall integration disposition remains `PARTIAL_PASS`: provider-use rights are unresolved, automatic application startup remains blocked by the existing external-network policy, and a real observation has not been verified in a running browser session.
