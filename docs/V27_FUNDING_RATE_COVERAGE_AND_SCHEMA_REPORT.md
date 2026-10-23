# V27 Perpetual Funding Rate Coverage & Schema Report

**Feature Class:** Derivatives Positioning & Leverage Intelligence  
**Feature Status:** `RESEARCH_FEATURE_EXPLORATORY`  
**Module Implementation:** [engine/funding_rate_research.py](file:///c:/Projects/BTCognitive/BTCognitive/engine/funding_rate_research.py)  
**Append-Only Ledger:** `data/research/funding_rate_research_ledger.jsonl`  

---

## 1. Instrument Specifications & Economic Mechanics

Perpetual futures contracts utilize periodic funding payments between long and short market participants to tether the derivative price to the spot index price without physical settlement:
1. **Binance USDⓈ-M Linear Perpetual (`BTCUSDT`):**
   - Quoted in USDT; collateralized in USDT.
   - PnL is linear in USD terms.
   - Funding payments settled in USDT.
2. **Binance COIN-M Inverse Perpetual (`BTCUSD_PERP`):**
   - Quoted in USD; collateralized in Bitcoin (BTC).
   - PnL is non-linear (convex) with respect to spot USD price.
   - Funding payments settled in BTC.

**Contractual Invariant:** Linear USDT perpetuals and inverse BTC perpetuals must never be merged as identical instruments. Their funding rates reflect distinct balance sheet constraints and funding currencies.

---

## 2. Ingestion Schema & Hypothesis Semantics

### 2.1 Ledger Schema
Each observation logged to `data/research/funding_rate_research_ledger.jsonl` adheres to:
```json
{
  "venue": "BINANCE",
  "instrument": "BTCUSDT",
  "contract_type": "LINEAR_USDT",
  "funding_rate": 0.0001,
  "funding_rate_bps": 1.0,
  "annualized_rate_pct": 10.95,
  "funding_time_utc": "2026-10-19T16:00:00Z",
  "interval_hours": 8,
  "retrieval_time_utc": "2026-10-19T16:02:11.450Z",
  "exploratory_hypothesis": {
    "threshold_rate": 0.0003,
    "is_extreme_leverage_flag": false,
    "scientific_status": "UNVALIDATED_EXPLORATORY_HYPOTHESIS_ONLY"
  },
  "feature_status": "RESEARCH_FEATURE_EXPLORATORY",
  "execution_authorization": "DISABLED"
}
```

### 2.2 Re-Evaluation of the 0.03% per 8h Condition
In earlier research notes, a threshold of `>0.03% per 8h` ($\approx 32.85\%$ annualized) was proposed as an indicator of crowded long positioning.
- **Scientific Reclassification in V27:** This threshold is classified strictly as an **unvalidated exploratory hypothesis**. It is **NOT** a validated market threshold, nor may it be hardcoded as an automated signal or decision trigger.
- **Evaluation Requirement:** Any prospective signal threshold must undergo formal walk-forward evaluation and ablation testing on training data before being promoted to model candidate status.

---

## 3. Data Ingestion & Availability Constraints

- **Public Endpoint:** Binance public REST endpoint `GET /fapi/v1/fundingRate` requires zero API credentials and provides historical funding rates in 1,000-record pages.
- **Survivorship & Timestamps:** Timestamps represent the effective timestamp when the rate was deducted from positions. Funding announced for $t$ is strictly causal for features evaluated at $t_{\text{close}} \ge t$.
- **Trading Invariant:** `EXECUTION: DISABLED — ANALYSIS ONLY`.
