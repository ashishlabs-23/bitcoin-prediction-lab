# BTCognitive V34.5 — Trade-to-Candle Ingestion Pipeline Design & Specification

**Milestone:** BTCognitive V34.5 — Continuous Historical Data & Strategy Viability  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Lead Author:** Agent 2 (Data Ingestion & Integrity Architect)  
**Governed Standard:** Causal Deterministic Trade Aggregation & Immutability Contract

---

## 1. Architectural Overview

To bridge the gap between tick-level trade archives and the multi-timeframe analytical pipelines of BTCognitive, Agent 2 has formulated the strict **Trade-to-Candle Aggregation Architecture**.

This specification governs the causal synthesis of:
1. **5-Minute OHLCV** (Microstructure, volume-weighted excursion analysis).
2. **1-Hour OHLCV** (Primary volatility forecasting and feature extraction lane).
3. **4-Hour OHLCV** (Derived strictly from completed hourly bars for HTF trend/regime classification).

```
Raw Tick Trades (CSV.GZ)
       │
       ▼
[Deduplication & Chronological Sort]
       │
       ├───────────────────────────────────────────┐
       ▼                                           ▼
[5-Minute Aggregator]                      [1-Hour Aggregator]
 (Epoch floor % 300)                        (Epoch floor % 3600)
       │                                           │
       ▼                                           ▼
Parquet 5m Dataset                         Parquet 1h Dataset
                                                   │
                                                   ▼
                                           [4-Hour Aggregator]
                                            (Epoch floor % 14400)
                                            (Strictly 4 closed 1h bars)
                                                   │
                                                   ▼
                                           Parquet 4h Dataset
```

---

## 2. Ingestion Contracts & Data Schema

### A. Raw Trade Ingestion Schema

Every ingested trade record retains full provenance:

| Field Name | Type | Description | Ingestion Requirement |
| :--- | :--- | :--- | :--- |
| **`exchange`** | `str` | Exchange identifier (`bitstamp`) | Constant |
| **`symbol`** | `str` | Trading pair (`BTCUSD`) | Upper-case normalized |
| **`exchange_ts`** | `int64` | Exchange trade timestamp in microseconds ($\mu\text{s}$) | Primary chronological key |
| **`local_ts`** | `int64` | Capture arrival timestamp in microseconds ($\mu\text{s}$) | Microstructure latency audit |
| **`trade_id`** | `str` | Exchange-assigned trade identifier | Deduplication key |
| **`side`** | `str` | Aggressor direction (`buy` / `sell` / `unknown`) | Volume classification |
| **`price`** | `float64` | Execution price | Positive finite float |
| **`amount`** | `float64` | Base currency volume (BTC) | Positive finite float |
| **`source_file_sha256`** | `str` | SHA-256 digest of source daily `.csv.gz` | Cryptographic audit trail |

---

## 3. Aggregation Mathematics & Boundary Rules

### A. 5-Minute Candle Synthesis ($T=300\text{s}$)
$$\text{bucket\_start} = \left\lfloor \frac{\text{exchange\_ts\_sec}}{300} \right\rfloor \times 300$$
$$\text{open} = \text{price}_{\text{first}(\text{bucket})}, \quad \text{high} = \max(\text{price}), \quad \text{low} = \min(\text{price}), \quad \text{close} = \text{price}_{\text{last}(\text{bucket})}$$
$$\text{volume} = \sum \text{amount}, \quad \text{trade\_count} = N_{\text{bucket}}, \quad \text{vwap} = \frac{\sum (\text{price} \times \text{amount})}{\sum \text{amount}}$$

### B. 1-Hour Candle Synthesis ($T=3600\text{s}$)
$$\text{bucket\_start} = \left\lfloor \frac{\text{exchange\_ts\_sec}}{3600} \right\rfloor \times 3600$$
Identical formulation evaluated across all trades where $\text{bucket\_start} \le \text{exchange\_ts} < \text{bucket\_start} + 3600$.

### C. 4-Hour Candle Synthesis ($T=14400\text{s}$)
$$\text{bucket\_start} = \left\lfloor \frac{\text{bucket\_start}_{1\text{h}}}{14400} \right\rfloor \times 14400$$
- **Causal Invariance Rule:** 4-hour candles must be synthesized **strictly from completed 1-hour candles**, never directly from trades.
- A 4-hour candle is valid if and only if **all 4 constituent 1-hour bars are fully closed**.

---

## 4. Edge Case Handling & Epistemic Guardrails

1. **Duplicate Trades:**
   - De-duplicated on compound key `(trade_id, exchange_ts, price, amount)`. If `trade_id` is blank, de-duplicated on `(exchange_ts, price, amount, side)`.
2. **Out-of-Order Timestamps:**
   - Stable sort applied to all daily records: primary key `exchange_ts ASC`, secondary key `trade_id ASC`.
3. **Zero-Volume & Missing Intervals (Exchange Downtime):**
   - If no trades occur in an interval (e.g., Bitstamp scheduled maintenance or zero-trade illiquidity):
     - The interval is emitted with: `volume = 0.0`, `trade_count = 0`, `open = high = low = close = close_{t-1}`.
     - An explicit boolean flag `is_synthetic_flat: True` is attached.
     - **NEVER interpolate missing prices linearly or spline-wise.**
4. **Incomplete Current Periods:**
   - Any candle currently in progress at ingestion time is truncated and excluded from the immutable Parquet output until closed.
5. **Protection of Existing Historical Datasets:**
   - Existing datasets (`BTCUSD_1h_v34_2_multiyear.parquet` and `BTCUSD_1h_v34_expanded.parquet`) remain write-protected and quarantined.
   - New continuous ingestions write strictly to versioned paths: `data/providers/bitstamp/BTCUSD_continuous_v35.parquet`.

---

## 5. Implementation Readiness

The ingestion engine will be packaged into `engine/data_ingestion/tardis_trade_aggregator.py` upon user authorization of historical data retrieval. All aggregation algorithms adhere strictly to zero-lookahead causal streaming.

