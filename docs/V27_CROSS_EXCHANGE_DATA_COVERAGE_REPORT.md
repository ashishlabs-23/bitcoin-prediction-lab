# V27 Cross-Exchange Spot-Price Data Coverage & Dislocation Report

**Feature Class:** Cross-Venue Microstructure & Dislocation Intelligence  
**Feature Status:** `CROSS_VENUE_PRICE_DIVERGENCE_RESEARCH_ONLY`  
**Module Implementation:** [engine/cross_venue_divergence.py](file:///c:/Projects/BTCognitive/BTCognitive/engine/cross_venue_divergence.py)  
**Append-Only Ledger:** `data/research/cross_venue_divergence_ledger.jsonl`  

---

## 1. Instrument Disambiguation & Quote Normalization

### 1.1 Resolution of V26 Roadmap Mismatch
The V26 roadmap listed Binance and Kraken as target venues, but stated a divergence formula using Coinbase and Binance. This conflated two distinct economic instruments:
1. **Coinbase BTC-USD:** Quoted in US Dollars (fiat USD).
2. **Kraken BTC-USD:** Quoted in US Dollars (fiat USD).
3. **Binance BTC-USDT:** Quoted in Tether USD (USDT stablecoin).

Treating BTC-USD and BTC-USDT as interchangeable assumes a 1:1 fixed dollar peg for Tether ($1.00\text{ USDT} \equiv \$1.00\text{ USD}$), which ignores Tether peg deviations, redeemability haircuts, and exchange-specific banking friction.

### 1.2 Canonical Pairwise Dislocation Specifications

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Pairwise Dislocation Architecture                     │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│ Metric                  │ Instrument Pair         │ Economic Character      │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ 1. Pure Fiat Spread     │ Coinbase USD vs Kraken  │ True inter-venue        │
│                         │ USD (Fiat vs Fiat)      │ liquidity dislocation   │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ 2. Tether Stablecoin    │ Coinbase USD vs Binance │ Combined exchange       │
│    Basis                │ USDT (USD vs USDT)      │ spread + USDT peg basis │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

#### Formulation:
$$\Delta_{\text{Fiat}}(t) = \ln\left(\frac{P_{\text{Coinbase, USD}}(t)}{P_{\text{Kraken, USD}}(t)}\right) \times 10,000\text{ bps}$$
$$\Delta_{\text{USDT}}(t) = \ln\left(\frac{P_{\text{Coinbase, USD}}(t)}{P_{\text{Binance, USDT}}(t)}\right) \times 10,000\text{ bps}$$

---

## 2. Data Schema & Ingestion Semantics

Each record logged to `data/research/cross_venue_divergence_ledger.jsonl` preserves the following schema:
```json
{
  "timestamp_utc": "2026-10-19T22:00:00Z",
  "receipt_time_utc": "2026-10-19T22:00:02.148Z",
  "coinbase_usd": 65420.50,
  "kraken_usd": 65415.00,
  "binance_usdt": 65480.00,
  "fiat_spread_cb_kr_bps": 0.84,
  "tether_basis_cb_bn_bps": -9.09,
  "usd_fiat_metrics": {
    "pair": "COINBASE_USD_vs_KRAKEN_USD",
    "is_quote_normalized": true,
    "currency_risk_flag": "NONE"
  },
  "usdt_basis_metrics": {
    "pair": "COINBASE_USD_vs_BINANCE_USDT",
    "is_quote_normalized": false,
    "currency_risk_flag": "STABLECOIN_PEG_BASIS"
  },
  "feature_status": "CROSS_VENUE_PRICE_DIVERGENCE_RESEARCH_ONLY"
}
```

---

## 3. Epistemic Safeguards

1. **No Synthetic Backfilling:** Historical periods with missing Kraken or Binance hourly candles are logged as `UNAVAILABLE` or `NaN`. No synthetic interpolation is permitted.
2. **No Arbitrage Execution:** Dislocation features serve purely to detect market stress and liquidity drying. No order placement or trading is enabled.
