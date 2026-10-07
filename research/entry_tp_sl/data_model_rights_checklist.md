# Data and Model Rights Checklist — Entry/TP/SL Track

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Date:** 2026-10-07  
**Gate:** `G0 Foundation Integrity`  

---

## 1. Dataset Rights Inventory

| Source | Intended/observed use | Available provenance / license claim | Current Rights Status |
|---|---|---|---|
| **Kaggle `mczielinski/bitcoin-historical-data` (v745)** | 1-minute Bitstamp BTC/USD spot OHLCV for path resolution | Declared CC BY-SA 4.0; 393,952,273 bytes; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`. User formally approved CC BY-SA 4.0 license and placed file at `data/raw/btcusd_1-min_data.csv`. | **`APPROVED_FOR_RESEARCH`** |
| **Local Snapshot** (`data/raw/btcusd_1-min_data.csv`) | 1-minute sub-path barrier resolution & label generation | Local immutable file verified byte-exact against Kaggle v745 metadata; 7,766,111 rows (2012-01-01 to 2026-10-07). | **`APPROVED_FOR_RESEARCH`** |
| **Google Drive** | Optional secondary cloud mirror | Local snapshot verified; cloud upload can be mirrored if needed. | `OPTIONAL_MIRROR` |
| **Binance public endpoints / CCXT** | Current repository's live fallback ingestion | Public exchange endpoints; separate from historical path dataset. | `UNVERIFIED` for this track |
| **Deribit 7-day IV (`iv7d`)** | Existing legacy HAR research input only | Explicitly excluded from Entry/TP/SL features and dataset lineage. | **`EXCLUDED`** |
| **Google TimesFM 3.0 / Amazon Chronos-2 / Datadog Toto 2.0 / Kronos** | Future feature challengers only | No checkpoint fetched; must create `model_verification.json` prior to any evaluation in Phase 6. | `UNVERIFIED`, not downloaded |

---

## 2. G0 Clearance Sign-Off

- **License:** CC BY-SA 4.0 formally acknowledged by user for research exploration.
- **Lineage:** Kaggle Bitstamp v745, file `btcusd_1-min_data.csv`.
- **SHA-256:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`.
- **Integrity:** 7,766,111 rows, 0 nulls, strictly monotonic timestamps, clean price boundaries.
