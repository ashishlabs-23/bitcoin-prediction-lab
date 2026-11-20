# V32.73 Cost Sensitivity Report — Entry Intelligence Prototype

**Milestone:** V32.73 — Entry Intelligence Prototype  
**Date:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  
**Status:** RETROSPECTIVE ANALYSIS — NOT A PERFORMANCE GUARANTEE  

---

## 1. Overview

This report presents a cost-sensitivity analysis of the triple-barrier labelling framework implemented in V32.73, using empirical barrier outcomes from a batch of 200 sampled bars (step=100, index range 1000–20900) drawn from the production dataset (`ohlcv.parquet`, 42,233 rows). The purpose is to quantify how transaction costs erode gross expected value (EV) under five representative cost scenarios.

**Barrier parameters:**

| Parameter | Value |
|-----------|-------|
| Take-profit (TP) | +1.50% |
| Stop-loss (SL) | -0.75% |
| Horizon | 24 hours |
| Gap-free window | Yes (0 gaps detected in batch) |

---

## 2. Empirical Barrier Outcome Distribution

### 2.1 LONG Direction (n = 200)

| Label | Count | Frequency |
|-------|-------|-----------|
| SL_FIRST | 124 | 62.0% |
| TP_FIRST | 55 | 27.5% |
| EXPIRED | 19 | 9.5% |
| AMBIGUOUS | 2 | 1.0% |

### 2.2 SHORT Direction (n = 200)

| Label | Count | Frequency |
|-------|-------|-----------|
| SL_FIRST | 123 | 61.5% |
| TP_FIRST | 50 | 25.0% |
| EXPIRED | 25 | 12.5% |
| AMBIGUOUS | 2 | 1.0% |

> **Note on AMBIGUOUS labels:** AMBIGUOUS bars (TP and SL touched within the same bar) are treated as no-trade / excluded from EV calculation (weight effectively 0 in the EV formula). The EXPIRED outcome is assigned a P&L of 0% (position closed at horizon with neither barrier touched), which is a conservative approximation.

---

## 3. Gross Expected Value

Gross EV is computed as the probability-weighted outcome across resolved labels. AMBIGUOUS events (1%) are excluded from the EV sum. Weights are re-stated on the full 200-sample denominator.

**EV formula (per direction):**

```
Gross EV = P(TP_FIRST) * TP_return + P(SL_FIRST) * SL_return + P(EXPIRED) * 0
```

### 3.1 LONG Gross EV

```
Gross EV (LONG) = 0.275 * (+1.50%) + 0.620 * (-0.75%) + 0.095 * 0.00%
               = +0.4125% - 0.4650%
               = -0.0525% per trade
```

### 3.2 SHORT Gross EV

```
Gross EV (SHORT) = 0.250 * (+1.50%) + 0.615 * (-0.75%) + 0.125 * 0.00%
                 = +0.3750% - 0.4613%
                 = -0.0863% per trade
```

Both directions show a **negative gross EV** under the empirical label distribution from this retrospective window. This is consistent with the asymmetric TP:SL ratio (2:1) requiring a win rate above 33.3% to break even gross, whereas empirical TP_FIRST rates are 27.5% (LONG) and 25.0% (SHORT).

---

## 4. Cost Scenarios

Five representative round-trip cost scenarios are defined below. Each scenario specifies a one-way taker fee; round-trip cost = 2 * one-way fee.

| Scenario ID | Description | One-Way Fee (bp) | Round-Trip Fee (bp) | Round-Trip Fee (%) | Verified |
|-------------|-------------|-----------------|--------------------|--------------------|----------|
| SCEN_0_FRICTIONLESS | No fees — theoretical ceiling | 0 bp | 0 bp | 0.00% | Yes |
| SCEN_1_BINANCE_VIP0 | Binance VIP0 taker | 7 bp | 14 bp | 0.14% | Yes |
| SCEN_2_COINBASE_ADV | Coinbase Advanced taker | 25 bp | 50 bp | 0.50% | Yes |
| SCEN_3_PASSIVE_MAKER | Passive limit-order maker | 3 bp | 6 bp | 0.06% | **UNVERIFIED** |
| SCEN_4_STRESSED_VOL | Stressed / high-volatility slippage | 40 bp | 80 bp | 0.80% | Yes |

> **SCEN_3_PASSIVE_MAKER — UNVERIFIED:** Fill probability for passive limit orders is not modelled. Adverse selection (limit orders fill preferentially when the market moves against the position) is not accounted for. The 3 bp maker rate represents an exchange-quoted rebate/fee, not an all-in effective cost. Until fill probability and adverse selection mechanics are empirically characterised on BTC order-book data, SCEN_3 results should be treated as a theoretical lower bound only.

---

## 5. Net Expected Value by Scenario

**Net EV = Gross EV - Round-Trip Fee**

### 5.1 LONG Direction (Gross EV = -0.0525%)

| Scenario | Round-Trip Cost (%) | Net EV (%) | Interpretation |
|----------|--------------------|-----------:|----------------|
| SCEN_0_FRICTIONLESS | 0.00% | -0.0525% | Negative even without fees |
| SCEN_1_BINANCE_VIP0 | 0.14% | -0.1925% | Negative |
| SCEN_2_COINBASE_ADV | 0.50% | -0.5525% | Strongly negative |
| SCEN_3_PASSIVE_MAKER | 0.06% | -0.1125% | Negative (**UNVERIFIED fill probability**) |
| SCEN_4_STRESSED_VOL | 0.80% | -0.8525% | Strongly negative |

### 5.2 SHORT Direction (Gross EV = -0.0863%)

| Scenario | Round-Trip Cost (%) | Net EV (%) | Interpretation |
|----------|--------------------|-----------:|----------------|
| SCEN_0_FRICTIONLESS | 0.00% | -0.0863% | Negative even without fees |
| SCEN_1_BINANCE_VIP0 | 0.14% | -0.2263% | Negative |
| SCEN_2_COINBASE_ADV | 0.50% | -0.5863% | Strongly negative |
| SCEN_3_PASSIVE_MAKER | 0.06% | -0.1463% | Negative (**UNVERIFIED fill probability**) |
| SCEN_4_STRESSED_VOL | 0.80% | -0.8863% | Strongly negative |

**Finding:** Net EV is negative across all five cost scenarios and both directions under the unconditional empirical label distribution from this retrospective batch. The primary driver of negative EV is the low TP_FIRST rate relative to the break-even threshold (33.3%), not transaction costs. Transaction costs further reduce EV by 0.06%–0.80% per trade.

---

## 6. Passive Fill Probability and Adverse Selection

When using passive limit orders (SCEN_3), two structural risks must be addressed before treating the maker fee as representative of actual round-trip cost:

1. **Fill probability:** A limit order placed at the TP or entry level will only fill if price reaches and trades through it. In trending markets, partial fills or zero fills reduce realized TP_FIRST frequency below the simulated rate. Any EV calculation assuming 100% fill probability overstates realised returns.

2. **Adverse selection:** Limit orders are more likely to fill when informed order flow is moving against the position (the "winner's curse" in limit-order microstructure). This systematically reduces the realised EV of a passive strategy relative to the simulated barrier outcome, even at zero maker fee. Adverse selection has not been modelled in V32.73.

These effects must be quantified on live or historical Level-2 order-book data before SCEN_3 can be used for prospective EV estimation.

---

## 7. Prospective Evidence Requirements

The batch of 200 samples used in this analysis is a **retrospective development observation** drawn from the research dataset. It does not constitute confirmatory evidence.

Per BTCognitive governance (AGENTS.md, Phase 5):

- A minimum of **100 non-overlapping, clean confirmatory blocks** is required before prospective EV estimates are treated as statistically valid.
- The current prospective evidence status is: **NOT_STARTED**.
- EV estimates in this report are research hypotheses, not production signals.

---

## 8. Risk Disclosures

1. **Retrospective only.** All outcomes reported here are computed from historical data that was available during research development. They represent in-sample or quasi-out-of-sample observations, not prospective confirmatory results.
2. **No performance guarantee.** Historical label distributions do not imply future profitability. BTC market microstructure, liquidity, and volatility regimes change over time.
3. **No live trading.** V32.73 does not authorize any live order execution. Live trading status: **DISABLED**.
4. **Model authorization.** No trained model exists in V32.73. Model authorization: **OFFLINE_RESEARCH_ONLY**.
5. **Fee assumptions.** Exchange fee tiers depend on 30-day trading volume. SCEN_1 and SCEN_2 reflect publicly documented VIP0 / standard taker rates as of research date. Rates may change.
6. **Slippage exclusion.** SCEN_0 through SCEN_3 do not include market-impact slippage beyond the stated fee. SCEN_4 partially proxies stressed conditions but does not fully model liquidity-adjusted execution cost.

---

## 9. Summary Decision Record

| Decision Point | Status |
|----------------|--------|
| Gross EV (LONG, unconditional) | -0.0525% (NEGATIVE) |
| Gross EV (SHORT, unconditional) | -0.0863% (NEGATIVE) |
| Net EV positive under any scenario | NO |
| Prospective evidence gate | NOT_STARTED |
| Model authorization | OFFLINE_RESEARCH_ONLY |
| Live trading | DISABLED |

The unconditional entry strategy does not show positive net EV in this retrospective window. V32.74 will investigate whether conditioning on predictive features (EQR, vol_ratio, trend_persistence) produces sub-populations with positive net EV under SCEN_1_BINANCE_VIP0.

---

*Report generated by BTCognitive Research Orchestrator — V32.73. All findings are retrospective research observations subject to the epistemic boundaries defined in AGENTS.md.*
