# V32.77 — Statistical Protocol & Multiple-Testing Pre-Registration

**Workstream:** Agent 4 — Statistical Validation Specialist  
**Milestone:** BTCognitive V32.77 — Volatility-Adaptive Entry Research  
**Date:** 2026-10-30  
**Evaluator:** Statistical Validation Specialist (Agent 4)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Statistical Validation Protocol Record  

---

## 1. Executive Summary & Pre-Registered Criteria

To eliminate p-hacking, threshold optimization, and backtest overfitting, this protocol **pre-registers the evaluation grid and acceptance hurdles before experimental conclusions are finalized**:

| Validation Dimension | Governed Requirement | Formal Mathematical Hurdle |
|---|---|---|
| **Evaluation Window** | Bars 31,632 to 42,153 (10,521 continuous chronological OOS hourly bars). | Fixed chronological split. Zero random shuffling. |
| **Label Independence** | Strictly non-overlapping 24-hour evaluation blocks ($N_{\text{blocks}} = 432$). | $N_{\text{eff}} \ge 100$ independent blocks minimum. |
| **Statistical Testing** | Diebold-Mariano test with Harvey-Leybourne-Newbold (HLN 1997) finite sample correction. | $p < 0.05$ against the uniform fixed-barrier baseline using Student's $t_{T-1}$. |
| **Multiple-Testing Adjustment** | Deflated Sharpe Ratio (DSR - Bailey & López de Prado 2014) across all evaluated configurations. | $\text{DSR} > 0.95$ accounting for total trial count $K = 24$. |
| **Economic Hurdle** | Net Expected Value after verified retail transaction costs. | $\text{EV}_{\text{net, Binance}} > 0$ and $\text{EV}_{\text{net, Coinbase}} > 0$. |

---

## 2. Statistical Leakage Controls & Embargo

1. **Information Horizon Purging:** For an evaluation at bar $t$ over horizon $H$, all market information up to $t$ is partitioned into features. Bars $t+1$ to $t+H$ constitute the outcome label window.
2. **Split Boundary Embargo:** When validating across split boundaries, an embargo period equal to the maximum horizon ($H_{\max} = 168\text{ hours}$) is inserted between train/validation and validation/test splits to eliminate autoregressive serial memory leakage.
3. **Non-Overlapping Sampling ($N_{\text{eff}}$):**
   - In continuous hourly sampling (10,521 observations), consecutive 24h labels share 23 hours of price movement.
   - To provide an unbiased, statistically rigorous benchmark, our primary empirical tests evaluate **strictly non-overlapping blocks spaced by $H$ hours** (432 blocks for 24h, 144 blocks for 72h, 61 blocks for 168h).

---

## 3. Multiple-Testing Formulation: The DSR Framework

With $K = 24$ strategy configurations evaluated across the grid (12 configurations $\times$ 2 directions):
$$\text{Expected Maximum Null Sharpe} \approx \sqrt{\text{Var}(\{\widehat{\text{SR}}_k\})} \left( (1 - \gamma) \Phi^{-1}\left(1 - \frac{1}{K}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right)$$
where $\gamma \approx 0.5772$.
- If an investigator tests 24 configurations and picks the one with the highest Sharpe ratio, a raw Sharpe of $\approx 1.5$ is expected purely by chance.
- The Deflated Sharpe Ratio requires that the candidate's observed Sharpe exceeds this expected maximum hurdle with 95% statistical confidence.

---

## 4. Pre-Registered Decision Rule

A configuration is declared **`POTENTIALLY_VIABLE`** if and only if:
1. $p_{\text{DM, HLN}} < 0.05$ relative to `FIXED_24H_BASELINE`.
2. $\text{Mean Net EV} > 0$ under `SCEN_1_BINANCE_VIP0` (24 bps).
3. 95% Wilson confidence lower bound on TP hit rate exceeds the zero-drift random walk rate.

If zero configurations satisfy all three conditions, the hypothesis is formally declared **`REJECTED_BY_EMPIRICAL_EVIDENCE`**.

*Signed by Specialist Agent 4 (Statistical Validation Specialist)*

