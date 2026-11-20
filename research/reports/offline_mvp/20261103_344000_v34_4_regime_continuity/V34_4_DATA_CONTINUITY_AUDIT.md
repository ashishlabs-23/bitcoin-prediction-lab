# BTCognitive V34.4 — Data Continuity, Lineage, and WAF Boundary Audit

**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Authors:** Agent 1 (Data Acquisition & WAF Specialist) & Agent 2 (Dataset Lineage & Gap Reconciler)  
**Governed Assessment:** `HISTORICAL_COVERAGE_INSUFFICIENT`

---

## 1. Executive Summary

Milestone V34.4 investigated the feasibility of assembling a contiguous, multi-year hourly Bitstamp BTC/USD dataset using unauthenticated public REST endpoints, resolved the dataset consumption discrepancies between V34.2 and V34.3, and mathematically characterized the discontinuity between the 2024 and 2026 data segments.

### Key Audit Findings
1. **Public REST WAF Boundary:** Bitstamp routes public API requests through Imperva Incapsula DDoS protection (`107.154.131.13`). Rapid sequential pagination over unauthenticated REST triggers TLS termination (`Recv failure: Connection was reset`) and HTTP 403 `Incident ID` blocks.
2. **Access Control & Safety Compliance:** In strict adherence to BTCognitive Epistemic Principles and AGENTS.md Prime Directives, no attempt was made to evade, spoof, or bypass Bitstamp's access controls. The limitation is acknowledged and governed honestly.
3. **Lineage Discrepancy Reconciliation:** V34.2's reported "multi-year" results actually consumed the 4,000-bar dataset (`BTCUSD_1h_v34_expanded.parquet`) because the multi-year pagination script halted at Page 1 (1,000 bars) when encountering rate limits. V34.3 correctly diagnosed this and audited both files.
4. **Discontinuous Historical Gap:** The two available Bitstamp segments are separated by an unbridgeable gap of **828.5 days (19,883 missing hourly bars, ~2.27 calendar years)**.

---

## 2. Dataset Cryptographic Fingerprints & Boundaries

| Attribute | Segment 1 (2024 Slice) | Segment 2 (2026 Slice) |
| :--- | :--- | :--- |
| **Workspace Path** | `data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet` | `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet` |
| **SHA-256 Digest** | `811c9704629d3b735643c0d931ad1998cf0604e9dd96b9790aaf1241ee807436` | `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` |
| **Row Count** | 1,000 hourly bars | 4,000 hourly bars |
| **Earliest Bar (UTC)** | `2024-01-01 00:00:00+00:00` | `2026-05-20 02:00:00+00:00` |
| **Latest Bar (UTC)** | `2024-02-11 15:00:00+00:00` | `2026-11-02 17:00:00+00:00` |
| **Span (Days / Hours)** | 41.6 days (1,000 hours) | 166.6 days (4,000 hours) |
| **Hourly Continuity** | 100% contiguous (0 missing intervals) | 100% contiguous (0 missing intervals) |
| **Duplicates** | 0 duplicate timestamps | 0 duplicate timestamps |
| **Incomplete Bar** | Bar 1,000 truncated to closed bar | Bar 4,000 truncated to closed bar |

---

## 3. Discontinuous Historical Gap Characterization

```
+-----------------------------+                           +-----------------------------+
|    Segment 1 (2024 Slice)   |    828.5-Day Gap (19,883h) |    Segment 2 (2026 Slice)   |
|   2024-01-01 -> 2024-02-11  | ------------------------> |   2026-05-20 -> 2026-11-02  |
|      1,000 Hourly Bars      |    NO CONTINUOUS DATA    |      4,000 Hourly Bars      |
+-----------------------------+                           +-----------------------------+
```

- **Gap Start:** `2024-02-11 15:00:00 UTC`
- **Gap End:** `2026-05-20 02:00:00 UTC`
- **Missing Duration:** 19,883 hours = 828.46 days = 2.27 calendar years.
- **Epistemic Mandate:** Under no circumstances may indicators (EMA, ATR, HAR realized variance, C2 conformal quantiles) be computed across this gap. Any attempt to concatenate these segments into a unified series without resetting warmups introduces fatal lookahead/lookbehind distortions.

---

## 4. Bitstamp API Bounded Pagination & WAF Behavior

The Bitstamp OHLCV endpoint documentation states:
- Parameter `step`: `3600` for 1-hour candles.
- Parameter `limit`: Maximum 1,000 candles per query.
- Parameter precedence: When both `start` and `end` are provided, `end` takes precedence, returning up to `limit` candles *prior* to `end`.

### Empirical Test Protocol
During V34.4, Agent 1 executed bounded test queries using `end`-only pagination stepping backward from `2026-05-20 02:00:00 UTC`.
- **Query 1 (Single request):** Successfully returned 1,000 candles with clean JSON boundaries.
- **Query 2 (Rapid subsequent request):** Bitstamp returned connection termination:
  ```
  curl: (35) Recv failure: Connection was reset
  ```
- **Analysis:** Imperva Incapsula blocks high-frequency pagination sweeps on the unauthenticated public endpoint.

---

## 5. Viable Data Acquisition Routes

To acquire continuous multi-year Bitstamp data without violating terms of service or encountering WAF barriers:
1. **Official Data Archive / Export:** Download official daily trade archives provided by Bitstamp or approved market data vendors (e.g., Kaiko, Tardis.dev, CoinAPI).
2. **Authenticated REST / WebSocket:** Use authenticated API keys with institutional rate limits.
3. **External Licensed Provider:** Utilize enterprise market data repositories (e.g., Databento, LOBSTER, Coin Metrics).

---

## 6. Governed Recommendation & Next Steps

1. **Retain Dual-Segment Separation:** Maintain `BTCUSD_1h_v34_2_multiyear.parquet` and `BTCUSD_1h_v34_expanded.parquet` as isolated, non-concatenated research segments.
2. **Governed Decision:** `HISTORICAL_COVERAGE_INSUFFICIENT`.
3. **Production Status:** Live trading strictly `DISABLED`. System authorization remains `OFFLINE_RESEARCH_ONLY`.

