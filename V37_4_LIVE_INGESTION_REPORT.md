# BTCognitive V37.4 — Live Ingestion Report

**Disposition:** `PARTIAL_PASS` for an external public Bitstamp socket smoke; `NOT_VERIFIED` for an application-integrated continuous ingestion service.

## Bounded public Bitstamp smoke

One public connection was opened to `wss://ws.bitstamp.net` and subscribed to `live_trades_btcusd`. No credentials or private/account endpoints were used. No data was written to a repository dataset, research ledger, or persistent application store.

- Started: `2026-11-04T15:23:26.838073Z`
- Last received message: `2026-11-04T15:23:30.201901Z`
- Subscription acknowledgement: `bts:subscription_succeeded`, channel `live_trades_btcusd`
- Messages: 4 (one acknowledgement and three trade messages)
- Trade JSON parse/field validation: 3 parsed, 0 parse errors
- Reconnects: 0 (the smoke ended after three trades)
- Exchange event field observed: `microtimestamp` (integer, 16-digit microsecond epoch interpretation)
- Received fields: `id`, `price`, `amount`, `type`

| Trade ID | Exchange event timestamp (UTC, interpreted from `microtimestamp`) | Receive time (UTC) | Price (USD/BTC) | Quantity (BTC) | Raw side code |
|---:|---|---|---:|---:|---:|
| 667265617 | 2026-11-04T15:19:42.235000Z | 2026-11-04T15:23:28.313652Z | 80678.06 | 0.002 | 1 |
| 667265626 | 2026-11-04T15:19:43.101000Z | 2026-11-04T15:23:29.179104Z | 80686.53 | 0.1 | 1 |
| 667265637 | 2026-11-04T15:19:44.120000Z | 2026-11-04T15:23:30.201901Z | 80684.54 | 0.00962355 | 1 |

**Critical freshness result:** the three exchange timestamps were approximately **226.08 seconds older** than their corresponding receive times. The connection and subscription succeeded, but these observations do not establish a fresh live feed. The channel's official timestamp semantics could not be independently retrieved, so the unit conversion is explicit and the precise cause of delay is unknown. Raw `type=1` is retained as a code; its buy/sell interpretation was not verified from an official reference.

## Acceptance boundary

The bounded check demonstrates protocol reachability and real Bitstamp message parsing only. It does **not** demonstrate:

- A persistent application-owned WebSocket lifecycle, heartbeat monitoring, reconnect behavior, or shutdown.
- A canonical stored observation with duplicate/out-of-order decisions.
- Reproducible candle aggregation, gap/stale detection, or same-provider historical recovery.
- API availability/status constructed from the feed.
- Engine integration or frontend rendering of those trades/candles.
- Rights to persist, redistribute, or use these data for model research.

A separate 30-minute soak was started but stopped before its 30-minute completion. The process exited without writing its summary file, so no soak metrics or acceptance are claimed. Only the bounded smoke above is evidence.

## Implementation disposition

No ingestion code was changed. The repo has candle adapters and an existing Coinbase L2 collector, but no verified Bitstamp trade-stream-to-FastAPI path. The current candle manager is coupled to inference and has reported out-of-order/gap behavior that should not be reused without correction. The actual Bitstamp freshness anomaly and unavailable official feed/terms documentation prevent claiming operational readiness.

Next implementation should first confirm Bitstamp event-time semantics and terms, then adapt through the existing observation contract, retain per-source identity, aggregate only that venue's trades, and surface stale status rather than feeding stale values into analysis.
