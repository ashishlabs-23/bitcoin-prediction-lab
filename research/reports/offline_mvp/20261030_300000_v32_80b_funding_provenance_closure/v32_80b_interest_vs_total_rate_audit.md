# V32.80B — Interest Rate vs. Total Funding Rate Audit (Workstream 3)

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T18:00:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Official Binance Funding Rate Settlement Mechanics

Per Binance's official documentation ([Binance Support FAQ 360033525031](https://www.binance.com/en/support/faq/detail/360033525031)):

### 1.1 Mathematical Formulation
The settled Funding Rate ($F$) is calculated every 8 hours as:
$$F = P + \text{clamp}(I - P, -0.05\%, +0.05\%)$$

Where:
- $P$ is the **Premium Index**, calculated from the difference between the Perpetual Contract Price and the Spot Mark Price.
- $I$ is the **Interest Rate Component**, fixed by Binance at **$0.01\%$ per 8 hours ($+0.000100$)** for major contracts including BTCUSDT.
- The $\text{clamp}(x, -0.05\%, +0.05\%)$ function constrains $(I - P)$ within $[-0.000500, +0.000500]$.

### 1.2 Behavior in Different Market Regimes:
1. **Regime 1: Mild Premium ($|P - I| \le 0.05\%$)**
   When the premium index is close to the interest rate (i.e., $-0.04\% \le P \le 0.06\%$):
   $$F = P + (I - P) = I = \mathbf{+0.000100}$$
   **In a balanced or quiet market, the funding rate is clamped exactly to $+0.000100$ ($10\text{ bps}$).**
2. **Regime 2: Heavy Contango / Bullish Euphoria ($P > 0.06\%$)**
   When contract price trades at a substantial premium to spot:
   $$I - P < -0.05\% \implies \text{clamp} = -0.05\%$$
   $$F = P - 0.05\%$$
   The rate unclamps and can rise up to the contract cap ($+0.375\%$ or $+0.75\%$ depending on margin bracket).
3. **Regime 3: Backwardation / Bearish Discount ($P < -0.04\%$)**
   When contract price trades below spot:
   $$I - P > +0.05\% \implies \text{clamp} = +0.05\%$$
   $$F = P + 0.05\%$$
   The rate unclamps downward and can become negative (shorts pay longs).

---

## 2. Evaluation of the Local Dataset against Binance Mechanics

### 2.1 The Critical Observation
In `binance_funding_2022_2026.parquet`:
- In **2023** and **2024**, Regime 2 was triggered frequently: $282$ settlements unclamped upward, reaching $+0.000881$ ($88.1\text{ bps}$).
- In **2022**, **2025**, and **2026**, **no settlement unclamped upward above $+0.000100$**.

### 2.2 Could Upstream Field Substitution Have Occurred?
The Manager asked: *Did the pipeline capture the interest-rate component separately rather than the full funding rate?*

**Audit Proof:**
1. The endpoint called was `/fapi/v1/fundingRate`.
2. This endpoint **only returns the final settled funding rate (`fundingRate`)**. Binance does not publish the standalone interest rate component on this endpoint (the interest rate is fixed at $0.000100$ by contract rule).
3. Furthermore, in 2025, there are $874$ unique values, and in 2026 there are $670$ unique values, including negative rates (down to $-0.000152$) and fractional positive rates ($0.000042$, $0.000056$, etc.).
4. If the pipeline had captured the interest rate component, every row would be identically $0.000100$.

Therefore, **field substitution did NOT occur**. The stored values are genuine responses from `/fapi/v1/fundingRate`.

---

## 3. Why Did Rates Never Unclamp Above $+0.000100$ in 2025–2026?

Two competing explanations:

### Hypothesis 1: Real Market Compression (Subdued Premium)
During 2025 and 2026, institutional basis trading, automated carry arbitrage, and ETF hedging compressed the basis between Binance perpetuals and spot, keeping $|P - I| \le 0.05\%$ on almost all 8-hour settlements. Under this regime, Binance's formula clamps the rate to $+0.000100$.

### Hypothesis 2: Endpoint / Data Provider Anomaly (Historical API Clipping)
In `data/raw/funding.parquet` (the contemporaneous 2026 capture), 2026 rates **did** unclamp up to $+0.000821$ ($113$ settlements $\ge +0.000228$).
The correlation between `funding.parquet` and `binance_funding_2022_2026.parquet` for the same 2026 timestamps is **$r = 0.0159$**.

This massive discrepancy between two local files for the exact same contract in the exact same year proves that:
- Either `funding.parquet` sampled a different contract/source, OR
- The historical `/fapi/v1/fundingRate` REST API query returned post-processed, smoothed, or clamped historical settlements for 2025–2026.

**Conclusion:** We cannot resolve with $100\%$ certainty whether the 2025–2026 lack of spikes is a true market regime or an upstream API artifact without contacting external networks (which is prohibited). Thus, **the provenance of 2025–2026 data must be classified as `SOURCE_LINEAGE_UNRESOLVED`**.

