# BTCognitive — Multi-Horizon Strategy Research Results (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Econometrician:** Agent 2  
**Dataset:** Authenticated Coinbase Spot BTC-USD Hourly Archive (33,424 bars, 2023-01-01 to 2026-10-25)  
**Trade Logs:** `research/runs/v32_30/*_trades.jsonl`  
**Summary Artifact:** `research/runs/v32_30/horizon_study_summary.json`  

---

## 1. Executive Summary & Core Findings

Following the pre-registered protocol committed in [v32_30_horizon_research_preregistration.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_30_horizon_research_preregistration.md), we evaluated whether expanding the holding horizon from 24h to 72h (3 days) or 168h (7 days) could overcome spot transaction costs (27 bps Active Trader vs. 87 bps Retail):

### Master Comparative Horizon Matrix (Full 33,424-Bar History)

| Metric | Control (24h)<br/>`TSMOM_DONCHIAN_24H_168H` | Candidate 1 (72h)<br/>`TSMOM_DONCHIAN_72H_168H` | Candidate 2 (168h)<br/>`TSMOM_DONCHIAN_168H_336H` | Empirical Progression |
| :--- | :---: | :---: | :---: | :--- |
| **Donchian Window ($L$)** | 24 bars | 72 bars | 168 bars | Slower breakout trigger |
| **Trend Filter ($\text{EMA}$)** | 168h (7-day) | 168h (7-day) | 336h (14-day) | Longer macro baseline |
| **Max Holding Horizon ($H$)** | 24 bars (1 day) | 72 bars (3 days) | 168 bars (7 days) | $7\times$ longer exposure window |
| **Closed Trades ($N$)** | **758** | **477** | **298** | Trade frequency decreases by 60.7% |
| **Take-Profit Hits (TP)** | 320 (42.2%) | 209 (43.8%) | 137 (46.0%) | Win rate increases by +3.8% |
| **Stop-Loss Hits (SL)** | 415 (54.7%) | 268 (56.2%) | 161 (54.0%) | Consistent barrier exit profile |
| **Timeout Exits (TO)** | 23 (3.0%) | 0 (0.0%) | 0 (0.0%) | 100% resolved via barriers at longer $H$ |
| **Mean Gross Return ($R$)** | **$+0.0880\text{ R}$** | **$+0.1016\text{ R}$** | **$+0.1629\text{ R}$** | **Gross edge nearly doubles (+85.1%)** |
| **Mean Net Return (27 bps)** | **$-0.2465\text{ R}$** | **$-0.2383\text{ R}$** | **$-0.1778\text{ R}$** | **Net loss reduces but remains negative** |
| **95% Bootstrap CI (27 bps)** | $[-0.3440, -0.1524]$ | $[-0.3570, -0.1087]$ | $[-0.3317, -0.0101]$ | **Upper bound remains strictly $< 0.0$** |
| **Mean Net Return (87 bps)** | **$-0.9898\text{ R}$** | **$-0.9934\text{ R}$** | **$-0.9349\text{ R}$** | **Substantial friction loss across all $H$** |
| **95% Bootstrap CI (87 bps)** | $[-1.0885, -0.8934]$ | $[-1.1114, -0.8633]$ | $[-1.0875, -0.7663]$ | **Negative across entire support** |
| **Max Drawdown (27 bps)** | $195.83\text{ R}$ | $116.53\text{ R}$ | $58.12\text{ R}$ | Drawdown in R units decreases |
| **Annualized Sharpe (27 bps)** | $-2.62$ | $-2.38$ | $-1.55$ | Negative Sharpe throughout |

---

## 2. 2026 Holdout Evaluation

To evaluate temporal stability out of sample, we isolated the trades initiated in 2026:

| Metric | Control (24h) | Candidate 1 (72h) | Candidate 2 (168h) |
| :--- | :---: | :---: | :---: |
| **2026 Trade Count** | 149 | 90 | 52 |
| **Gross Mean Return** | $+0.0772\text{ R}$ | $+0.0076\text{ R}$ | $+0.2591\text{ R}$ |
| **Net Mean Return (27 bps)** | **$-0.2640\text{ R}$** | **$-0.3372\text{ R}$** | **$-0.0911\text{ R}$** |
| **Net Mean Return (87 bps)** | **$-1.0223\text{ R}$** | **$-1.1034\text{ R}$** | **$-0.8694\text{ R}$** |

---

## 3. Gap Sensitivity Analysis

Out of the 33,424 hourly candles, 3 documented exchange outages occurred (13 missing hours total). We evaluated whether trades intersecting these outage windows distorted performance:
- For `TSMOM_DONCHIAN_168H_336H`, 5 trades intersected an outage gap.
- **Purged Sample (293 trades):**
  - Net Mean Return (27 bps): **$-0.1804\text{ R}$** (vs $-0.1778\text{ R}$ full sample).
  - Net Mean Return (87 bps): **$-0.9376\text{ R}$** (vs $-0.9349\text{ R}$ full sample).
- **Conclusion:** Outage gaps have negligible impact on performance; results are structurally robust to missing intervals.

---

## 4. Econometric Interpretation & Decision Gate Verdict

1. **Gross vs. Net Divergence:**  
   The empirical evidence demonstrates that Bitcoin momentum breakouts have positive raw gross expectancy across all three horizons ($+0.0880\text{ R}$ at 24h, $+0.1016\text{ R}$ at 72h, $+0.1629\text{ R}$ at 168h). This confirms the theoretical hypothesis that wider channels capture more substantial directional swings.
2. **Transaction Cost Dominance:**  
   Even with the 168h macro horizon where the average target move is larger ($1R \approx 3.8\%$), round-trip friction of 27 bps (Active Trader) or 87 bps (Retail) consumes the entire gross edge. At 27 bps, $EV_{\text{net}} = -0.1778\text{ R}$ with a 95% CI upper bound of $-0.0101\text{ R}$. At 87 bps, $EV_{\text{net}} = -0.9349\text{ R}$.
3. **Pre-Registered Gate Verdict:**  
   Under the frozen decision criteria in Section 4 of the pre-registration:
   - **Economic Viability Gate ($EV_{\text{net}} > 0.0\text{ R}$):** **FAILS** for all three candidates.
   - **Pre-Registered Terminal Decision:** **`NO_GO_NO_VALIDATED_EDGE`**.

In accordance with BTCognitive operating rules, we do not tune channel multipliers, search for post-hoc entry filters, or cherry-pick sub-periods to force a positive number. The negative net return is preserved as an authoritative scientific finding.
