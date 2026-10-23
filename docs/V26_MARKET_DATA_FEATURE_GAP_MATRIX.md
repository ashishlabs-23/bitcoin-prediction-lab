# V26 BTC Market-Data Feature Gap Matrix & Research Roadmap

**Agent:** Agent D (BTC Market-Data Research & Microstructure)  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  
**Governing Rule:** Strict point-in-time causality; no synthetic backfill; explicit `UNAVAILABLE` state for unconfigured sources; retention subject to incremental out-of-sample ablation over frozen baselines.

---

## 1. Feature Family Gap Analysis

| Feature Category | Current Repo State | Real Historical Availability | Point-in-Time Causality Risk | Proposed Provider / Ingestion Path | Research Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Cross-Exchange Spot Quality & Divergence** | Absent (Single feed: Coinbase Spot) | High (Public REST: Binance, Kraken, Coinbase) | LOW (Exact candle close timestamps match) | Free Public APIs (Binance, Kraken, Coinbase) | **P1 (Immediate)** |
| **2. Derivatives Positioning (Funding & Basis)** | Absent (Zero derivatives inputs in Ridge) | High (Binance Futures & Bybit public 8h funding) | LOW (Funding timestamps fixed at 00:00, 08:00, 16:00 UTC) | Binance Futures public archive (`/fapi/v1/fundingRate`) | **P1 (High Alpha Potential)** |
| **3. Open Interest (OI) & OI Changes** | Absent | Moderate (Binance `/fapi/v1/openInterestHist` 30d rolling) | LOW if captured prospectively; backfill requires paid historical data | Binance public API for prospective; Kaiko/Amberdata for deep history | **P1 (Prospective first)** |
| **4. Order Book Microstructure (Imbalance, Spread)** | Absent | LOW historical; snapshots cannot be reconstructed without tick L2 feeds | HIGH (Snapshot reconstruction risks lookahead or stale timestamps) | Prospective WebSocket L2 depth capture (Coinbase Advanced, Binance) | **P2 (Prospective only)** |
| **5. Liquidation & Forced-Flow Volume** | Absent | Very Low (Exchange liquidation feeds are transient / rate-limited) | HIGH (Silently omitted liquidations distort flow) | Binance WebSocket forceOrder streams prospectively | **P2 (Research prototype)** |
| **6. Volatility & Regime Diagnostics** | Partial (HAR-RV in memory; not in Ridge feature schema) | High (Computed directly from existing 1h OHLCV) | ZERO (Point-in-time causal calculation) | Local feature pipeline (`src/features/regime.py`) | **P0 (Zero cost, high value)** |
| **7. Options Implied Volatility (DVOL / Skew)** | Absent | Moderate (Deribit public API has DVOL daily/hourly) | LOW if using official Deribit index snapshots | Deribit public index API (`/api/v2/public/get_volatility_index_data`) | **P2 (Config-dependent)** |
| **8. Macro / Cross-Asset Context (DXY, SPX, Yields)** | Absent | High (FRED / Yahoo Finance) | HIGH (Publication delays, revisions, weekend market closures) | FRED API for weekly macro; explicit holiday/weekend handling | **P3 (Deferred)** |

---

## 2. Detailed Specifications for High-Priority Candidates

### Candidate 1: Cross-Exchange Divergence & Stale Source Detection
- **Hypothesis:** Price divergence between Coinbase (USD fiat) and Binance (USDT stablecoin) indicates localized liquidity shocks, arbitrage friction, or imminent volatility expansion over 1h to 4h horizons.
- **Provider & Cost:** Binance Public Spot REST API (`/api/v3/ticker/price`) + Kraken (`/0/public/Ticker`). Free, no API key required.
- **Update Frequency:** Hourly candle synchronization.
- **Timestamp Semantics:** Matched on strict Unix candle open/close times ($t_{\text{close}}$).
- **Missingness Policy:** If Binance or Kraken is unavailable, metric yields `NaN` and triggers feature abstention; never imputes from Coinbase.
- **Incremental Ablation:** Evaluate whether Ridge + Divergence lowers QLIKE on HAR volatility or improves Clark–West statistic on price.

### Candidate 2: Perpetual Futures Funding Rate & Annualized Basis
- **Hypothesis:** Extreme positive (negative) perpetual funding rates indicate over-leveraged long (short) sentiment, creating asymmetric tail risk and mean-reverting excursion pressure over 4h to 24h horizons.
- **Provider & Cost:** Binance Futures Public API (`GET /fapi/v1/fundingRate`). Historical data available back to 2019 without authentication.
- **Update Frequency:** 8-hour intervals (00:00, 08:00, 16:00 UTC), forward-carried as step function to 1-hour grid.
- **Timestamp Semantics:** Strictly point-in-time: funding rate announced at $t$ cannot be used until timestamp $t$ has elapsed.
- **Ablation Retention Hurdle:** Must demonstrate statistically significant out-of-sample RMSE reduction or interval coverage sharpness improvement over the baseline.

### Candidate 3: Realized Volatility Regime Diagnostics (HAR-RS Components)
- **Hypothesis:** Separating realized variance into continuous and jump components (Barndorff-Nielsen & Shephard, 2004) and realized semi-variances ($RS^+, RS^-$) predicts asymmetric downside risk.
- **Provider & Cost:** Zero external cost; computed purely from existing verified local OHLCV parquet dataset.
- **Update Frequency:** Hourly.
- **Timestamp Semantics:** Exactly causal ($t-1$ backwards).
- **Ablation Retention Hurdle:** Statistically significant QLIKE reduction ($p < 0.05$) via DM-HAC test against benchmark persistence.

---

## 3. Data Governance & Implementation Rules

1. **No Synthetic Backfilling:** If order book or liquidation feeds lack clean historical records, they must NOT be synthetically backfilled. They will be logged prospectively via append-only collectors.
2. **Graceful Degradation:** Any feature depending on an external network endpoint must fail closed to an explicit `UNAVAILABLE` enum state. The forecast engine must support feature abstention rather than silent imputation.
3. **Ablation Gate:** New features are added only if they beat the frozen baseline in an untouched holdout window. If the challenger does not improve out-of-sample metrics, the simpler model is retained.
