# Provider-rights release gates and staging QA plan

## P0 gates

1. Executed provider agreement or current published licence expressly covers public display, commercial use, derived indicators/analytics, caching/retention/backups, and required model use. A sales contact or API key is not clearance.
2. The source identity is explicit: provider, venue, spot/perpetual type, pair, quote currency, interval, source timestamp, fetch timestamp, revision and rights status.
3. Adapter staging probe passes UTC/order/duplicate/OHLCV/gap/staleness/open-bar validation without protected-data writes.
4. No direct browser request reaches an unapproved provider. No raw candle export, user candle API, or reusable response is exposed unless licensed.
5. `OFFLINE_RESEARCH_ONLY`, `NO_GO_NO_VALIDATED_EDGE`, no broker execution and no order placement remain enforced.

## Real-browser staging checklist — execute only after P0 rights clearance

- Initial chart load shows source/venue/pair/timeframe, data cutoff, fetch time, candle state and attribution.
- Pair/timeframe changes cancel obsolete work; cache keys prevent source/venue/timeframe contamination; zoom/pan preserve correct timestamps.
- Validate EMA/Bollinger/RSI/ATR/ADX against deterministic fixtures; do not use fixtures in normal runtime.
- Exercise OK, STALE, GAP, PARTIAL/OPEN, UNAVAILABLE, malformed candle, empty history, provider outage and retry states.
- Exercise absent/stale/malformed forecast, wrong origin/timeframe, source/model-version mismatch, update race and marker-unanchorable fallback panel. Show only actual contract fields and uncertainty semantics.
- Exercise repeated Analyse, cancellation, timeout, retry, no eligible result and backend failure.
- Test desktop and 375px viewport, keyboard controls and accessible live/status updates.
- Inspect network and download surfaces for raw-data exposure; test authorized response headers and redaction.
- Establish p50/p95 chart-load, interaction, Analyse latency and bounded concurrent-user baseline with provider rate-limit behavior.

## Evidence required to move to external beta

Agreement/rights record; immutable staging manifests; adapter unit/integration results; browser recordings/logs; source comparison discrepancy report; security review of server-held credentials; CI result; rollback/outage procedure. Until these exist, public data route is **BLOCKED** and browser QA is **NOT EXECUTED**.
