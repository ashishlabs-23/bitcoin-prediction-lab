# BTCognitive — V32.31 Prospective Coinbase L2 Entry-Gating Pre-Registration Protocol

**Version:** V32.31  
**Date:** 2026-10-25  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed; zero live broker/order execution paths)  
**Lead Econometrician:** Agent 2  
**Lead Microstructure Architect:** Agent 3  
**Status:** FROZEN PRE-REGISTRATION PROTOCOL (Committed prior to prospective outcome accumulation)  

---

## 1. Primary Empirical Hypothesis

### Formal Hypothesis ($H_1$)
*In the 168-hour macro trend breakout strategy (`TSMOM_DONCHIAN_168H_336H`), contemporaneous order-flow toxicity at the breakout candle's execution boundary is a primary driver of false breakouts. Conditioning entry execution on positive contemporaneous Order Flow Imbalance ($\text{OFI}_{15\text{m}} > 0$), balanced book depth ($\text{OBI}_{5} > -0.20$), and tight top-of-book spread ($\le 5.0\text{ bps}$) will filter out unprofitable breakouts, improving net-of-cost expectancy ($EV_{\text{net}}$) by at least $+0.20\text{ R}$ under the Active Trader (27 bps) fee scenario.*

### Null Hypothesis ($H_0$)
*Contemporaneous Level-2 order flow features do not provide statistically significant incremental predictive power for 168-hour barrier outcomes after accounting for transaction costs ($EV_{\text{net, gated}} \le EV_{\text{net, ungated}}$).*

---

## 2. Experimental Design & Estimands

### 2.1 The Two Cohorts
1. **Ungated Control Cohort (`CONTROL_168H`):**  
   The frozen `TSMOM_DONCHIAN_168H_336H` macro breakout candidate:
   - Donchian Trigger: 168 completed hourly bars $[t-168, t-1]$ via `.shift(1).rolling(168).max()`.
   - Macro Filter: $P_t > \text{EMA}_{336h}$.
   - Entry: Filled causally at Open of bar $t+1$.
   - Barrier Geometry: $1R = 1.5 \times \sigma_P(168h) \times P_{\text{entry}}$; Target $k_{\text{tp}} = 1.5R$; Stop $k_{\text{sl}} = 1.0R$; Max holding horizon $H = 168$ hours (7 days).
   - In-position gating: Suppresses overlapping trades while a position is open.
2. **L2-Gated Candidate Cohort (`L2_GATED_168H`):**  
   Evaluates the identical entry candidate at decision time $t$, but applies the causal entry filter:
   $$\text{Decision} = \begin{cases} \text{GATE\_ACCEPTED\_SHADOW} & \text{if } \text{Feed\_Sync} = \text{True} \land \text{OFI}_{15\text{m}} > 0.0 \land \text{OBI}_5 > -0.20 \land \text{Spread}_{\text{bps}} \le 5.0 \\ \text{GATE\_REJECTED\_TOXIC\_OFI} & \text{if } \text{OFI}_{15\text{m}} \le 0.0 \\ \text{GATE\_REJECTED\_HEAVY\_ASK} & \text{if } \text{OBI}_5 \le -0.20 \\ \text{GATE\_REJECTED\_WIDE\_SPREAD} & \text{if } \text{Spread}_{\text{bps}} > 5.0 \\ \text{GATE\_ABSTAIN\_L2\_UNAVAILABLE} & \text{if } \text{Feed\_Sync} = \text{False or Stale} \end{cases}$$

### 2.2 Primary Evaluation Estimand
The primary statistical estimand is the **difference in Mean Net Return ($\Delta \mathbb{E}[R_{\text{net}}]$)** under the Active Trader (27 bps) scenario:
$$\Delta \mathbb{E}[R_{\text{net}}] = \mathbb{E}[R_{\text{net, gated}}] - \mathbb{E}[R_{\text{net, ungated}}]$$
Evaluated under paired block bootstrap ($B=2{,}000$ iterations) and Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite-sample correction.

---

## 3. Sample Size & Statistical Power Justification

Why is a target sample of at least **100 non-overlapping prospective trades** statistically necessary?
- Under a $1.5:1$ reward-to-risk ratio ($k_{\text{tp}} = 1.5R, k_{\text{sl}} = -1.0R$), trade return variance is approximately $\sigma^2_R \approx 1.4^2 \approx 2.0$.
- To detect an incremental improvement of $\Delta = +0.25\text{ R}$ with 80% statistical power ($\beta = 0.20$) at the 5% significance level ($\alpha = 0.05$, two-tailed):
  $$N \ge \frac{(z_{1-\alpha/2} + z_{1-\beta})^2 \cdot 2\sigma^2}{\Delta^2} = \frac{(1.96 + 0.84)^2 \cdot 4.0}{0.25^2} \approx \frac{7.84 \cdot 4.0}{0.0625} \approx 50 \text{ trades per arm}$$
- Because trades are strictly non-overlapping (one open trade at a time, each lasting up to 168 hours), a sample of $N \ge 100$ independent closed prospective events guarantees sufficient statistical power while strictly eliminating serial correlation across overlapping positions.

---

## 4. Invariants & Epistemic Guardrails

1. **Strict Non-Execution:** `LIVE_TRADING_ENABLED = False` permanently. Zero live orders, zero broker API calls, zero real capital.
2. **Dedicated Versioned Ledger:** All prospective shadow candidates and outcomes are recorded in [data/research/prospective_l2_gated_ledger_v1.jsonl](file:///C:/Projects/BTCognitive/BTCognitive/data/research/prospective_l2_gated_ledger_v1.jsonl). Existing protected files remain strictly untouched.
3. **No Retrospective Fabrication:** Historical L2 observations cannot be manufactured from OHLCV. Only forward-accumulated, authenticated WebSocket events qualify.
4. **Fail-Closed on Desynchronization:** If the Coinbase WebSocket feed disconnects, drops sequence numbers, or heartbeats exceed 5.0 seconds, the book state is invalidated, features return `is_available = False`, and the gate fails closed with `GATE_ABSTAIN_L2_UNAVAILABLE`.
5. **No Threshold Fishing:** The filter thresholds ($\text{OFI} > 0, \text{OBI}_5 > -0.20, \text{Spread} \le 5\text{ bps}$) are frozen by this protocol and cannot be tuned post-hoc.
