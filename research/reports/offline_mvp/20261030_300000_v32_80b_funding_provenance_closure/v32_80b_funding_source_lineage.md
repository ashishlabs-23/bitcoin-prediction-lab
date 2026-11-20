# V32.80B — Funding Source Lineage & Pipeline Audit (Workstream 2)

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T17:55:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report audits the code lineage, origin, API endpoint, and data processing history of `data/raw/binance_funding_2022_2026.parquet`.

### Critical Findings:
1. **Source Script Identified:** The dataset was constructed by `research/download_binance_funding_history.py`.
2. **API Endpoint Verified:**
   ```
   https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime={cur_start}&endTime={end_ms}&limit=1000
   ```
   This is the official public REST endpoint for **Binance USDⓈ-M Futures Historical Funding Rate**.
3. **No Local Clipping or Transformation:**
   Inspection of `download_binance_funding_history.py` (lines 80–91) proves that:
   ```python
   df["funding_rate"] = df["fundingRate"].astype(float)
   df["mark_price"] = pd.to_numeric(df.get("markPrice", 0.0), errors="coerce").fillna(0.0)
   ```
   **No clipping (`clip()`), no rounding, no threshold caps, and no clamping logic exist in the pipeline.** The float value stored in the parquet is the raw float parsed directly from the JSON string returned by Binance's endpoint.
4. **Field Semantic Audit:** The endpoint returns fields:
   - `symbol`: contract string (`"BTCUSDT"`)
   - `fundingRate`: string representation of the settled funding rate
   - `fundingTime`: millisecond epoch timestamp
   - `markPrice`: mark price string (often empty or `"0"` in older API versions prior to mid-2023)

---

## 2. Ingestion Pipeline Forensic Inspection

### 2.1 Code Flow
```
[Binance Public REST API]
   |  GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT
   v
[raw JSON response payload]
   |  {"symbol": "BTCUSDT", "fundingRate": "0.00010000", "fundingTime": 1787817600000, "markPrice": "79059.04402900"}
   v
[download_binance_funding_history.py]
   |  df["funding_rate"] = df["fundingRate"].astype(float)
   |  df["timestamp"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
   v
[pyarrow parquet serialization]
   |  File: data/raw/binance_funding_2022_2026.parquet
   |  SHA-256: e90282de4f78ebd...
```

### 2.2 Mark Price Zero Audit
The code converts `markPrice` via `pd.to_numeric(..., errors="coerce").fillna(0.0)`.
In the Binance API, the `markPrice` field in the `/fapi/v1/fundingRate` response was only added in API schema updates in 2023. For historical calls querying 2022 and early 2023, Binance returned either `""` or omitted the field entirely.
This explains why all 1,095 rows in 2022 and 910 rows in 2023 have `mark_price = 0.0`. It is a consequence of Binance's upstream API response schema, not local data corruption.

---

## 3. Discrepancy between Two Local Funding Files

A critical comparison was performed between the two local funding datasets:
1. `data/raw/binance_funding_2022_2026.parquet` ($5,113$ rows, 2022–2026)
2. `data/raw/funding.parquet` ($375$ rows, Jan–May 2026)

### Findings on Overlapping 2026 Observations ($N=375$):
- **Correlation:** $r = 0.0159$ (**VIRTUALLY ZERO CORRELATION**).
- In `binance_funding_2022_2026.parquet`, the maximum 2026 rate is $+0.000100$.
- In `funding.parquet`, the maximum 2026 rate is **$+0.000821$** ($+89.9\%$ annualized), with $113$ rows exceeding $+0.000228$.

### Lineage Implication:
`funding.parquet` was ingested in an earlier milestone from a different source or live stream (it contains an `available_time` column and live microstructure metrics). The fact that `funding.parquet` shows rates up to $+0.000821$ in 2026 while `binance_funding_2022_2026.parquet` shows rates capped at $+0.000100$ in 2026 confirms that **the two files represent different upstream data captures or different contract fields**.

This finding is examined in depth in Workstream 3 and 5.

