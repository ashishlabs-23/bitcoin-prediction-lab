# BTCognitive — Multi-Horizon Strategy Research Pre-Registration (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Econometrician:** Agent 2  
**Protocol Status:** FROZEN PRE-REGISTRATION (Committed before calculating returns)  

---

## 1. Research Motivation & Core Question

In the V32.28 and V32.29 baseline evaluations, the primary 24-hour Donchian trend strategy (`TSMOM_DONCHIAN_24H_168H`) achieved positive gross returns ($+0.0880\text{ R}$) across 33,424 hourly bars due to its $1.5:1$ reward-to-risk geometry, but suffered negative net returns after exchange transaction costs:
- **Active Trader Scenario (27 bps):** Mean Net Return = **$-0.2465\text{ R}$** ($95\%$ CI: $[-0.3433, -0.1508]$).
- **Retail Scenario (87 bps):** Mean Net Return = **$-0.9898\text{ R}$** ($95\%$ CI: $[-1.0883, -0.8921]$).

**Core Quantitative Question:**  
*Does expanding the holding horizon to multi-day swing horizons (72 hours / 3 days) or macro trend horizons (168 hours / 7 days) generate sufficiently larger price excursions to overcome fixed exchange friction (27–87 bps), or does the lower trade frequency and extended market exposure introduce offsetting adverse variance and drawdowns?*

---

## 2. Pre-Registered Strategy Candidate Matrix

To eliminate data-snooping and backtest overfitting (PBO; Bailey et al. 2016), we pre-register exactly **three strategy specifications** with fixed, non-tunable parameters:

| Strategy ID | Role | Donchian Trigger Window ($L_{\text{don}}$) | Macro Trend Filter | Holding Horizon ($H$) | Standardized Risk Unit ($1R$) | Target Distance ($k_{\text{tp}}$) | Stop Distance ($k_{\text{sl}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`TSMOM_DONCHIAN_24H_168H`** | **Control** | 24 bars (prior $[t-24, t-1]$) | $P_t > \text{EMA}_{168h}$ | 24 bars (1 day) | $1.5 \times \sigma_{\text{Parkinson}}(24h) \times P_{\text{entry}}$ | $1.5 R$ ($1.5:1$) | $1.0 R$ |
| **`TSMOM_DONCHIAN_72H_168H`** | **Candidate 1** | 72 bars (prior $[t-72, t-1]$) | $P_t > \text{EMA}_{168h}$ | 72 bars (3 days) | $1.5 \times \sigma_{\text{Parkinson}}(72h) \times P_{\text{entry}}$ | $1.5 R$ ($1.5:1$) | $1.0 R$ |
| **`TSMOM_DONCHIAN_168H_336H`** | **Candidate 2** | 168 bars (prior $[t-168, t-1]$) | $P_t > \text{EMA}_{336h}$ | 168 bars (7 days) | $1.5 \times \sigma_{\text{Parkinson}}(168h) \times P_{\text{entry}}$ | $1.5 R$ ($1.5:1$) | $1.0 R$ |

---

## 3. Strict Causal & Deterministic Evaluation Rules

1. **Point-in-Time Causality:**
   - Donchian High and Low are computed strictly on completed bars prior to signal candle $t$ using `.shift(1).rolling(L).max()` and `.shift(1).rolling(L).min()`. Signal bar $t$ is strictly excluded.
   - Signal is emitted at Close of bar $t$.
   - Entry is filled strictly at Open of bar $t+1$ ($P_{\text{entry}} = O_{t+1}$). Future prices are never accessed for entry.
2. **Spot Long-Only Restriction:**
   - Coinbase Spot `BTC-USD` does not support margin shorting without separate borrow facilities. Short breakout signals are mapped strictly to `CASH` / `SPOT_SHORT_INELIGIBLE` and excluded from trading P&L.
3. **Deterministic Barrier Resolution:**
   - Executed via [DeterministicBarrierResolver](file:///C:/Projects/BTCognitive/BTCognitive/engine/barrier_resolver.py).
   - **Conservative Intrabar Collision:** If both TP and SL are breached in the same bar, the resolver resolves strictly as `SL_FIRST` (`is_ambiguous_touch = True`).
   - **Opening Gap Execution:** If a bar opens beyond a barrier, it is executed at the actual bar Open price, capturing true market gap slippage.
   - **Timeout Resolution:** If neither barrier is touched before bar $t + 1 + H$, the position exits at the Open of bar $t + 1 + H$ with actual signed return:
     $$R_{\text{TO}} = \frac{O_{t + 1 + H} - P_{\text{entry}}}{1R}$$
4. **Non-Overlapping Trade Execution:**
   - In-position gating is strictly enforced: while a trade is open, all subsequent signals are suppressed until the current trade resolves. This guarantees independent, non-overlapping outcome samples without synthetic position scaling.
5. **Assumed Transaction Cost Scenarios:**
   - **Active Trader Scenario (27.0 bps round-trip):** Taker 10 bps/side, spread 1.5 bps/side, slippage 2.0 bps/side.
   - **Retail Scenario (87.0 bps round-trip):** Taker 40 bps/side, spread 1.5 bps/side, slippage 2.0 bps/side.
   - Friction converted to R units: $C_R = \frac{\text{Round-Trip Friction (bps)} / 10{,}000}{|P_{\text{entry}} - P_{\text{stop}}| / P_{\text{entry}}}$.
6. **Data Gap Sensitivity Rule:**
   - The Coinbase archive contains 3 documented outages (13 missing hours). Any trade whose holding horizon spans an outage gap is flagged. Sensitivity analysis will compare full sample vs. gap-purged sample. Zero synthetic interpolation will be performed.

---

## 4. Pre-Registered Decision Criteria

1. **Superiority Gate:** Candidate must achieve a statistically significant higher Mean Net Return than the Control under the Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction ($p < 0.05$).
2. **Economic Viability Gate:** Candidate must achieve Mean Net Return $EV_{\text{net}} > 0.0\text{ R}$ and a $95\%$ bootstrap confidence interval lower bound $> 0.0\text{ R}$ under the Active Trader (27 bps) scenario.
3. **Fail-Closed Terminal Rule:** If neither candidate achieves $EV_{\text{net}} > 0.0\text{ R}$ after costs, the scientific verdict remains **`NO_GO_NO_VALIDATED_EDGE`**. No parameter tuning or threshold searching is authorized.
