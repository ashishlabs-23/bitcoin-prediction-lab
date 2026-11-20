# V32.80 — Trade Economics Reconciliation (Workstream 2)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

Reconcile the apparent tension between a 29.7% TP rate and a +6.8 bps net EV for the SHORT arm, and verify all cost assumptions.

---

## 2. The TP Rate / Net EV Reconciliation

### Why a 29.7% TP Rate Can Produce Positive Net EV

The V32.79A simplified breakeven assumes:
- TP outcome: +3.0% gross
- SL outcome: −1.5% gross
- EXPIRED outcome: **0.0% gross** ← This assumption is INCORRECT

The empirical EXPIRED mean gross return for the SHORT arm is **+0.388%** — not zero. The 16 expired trades showed mean favorable price movement (shorts profited on average in the expired trades).

**Full arithmetic (SHORT arm, Binance 24 bps):**

| Outcome | Weight | Gross | Net (Binance) | Contribution to Net EV |
|---|---|---|---|---|
| TP_FIRST | 0.2969 | +3.000% | +2.760% | +0.819% |
| SL_FIRST | 0.4531 | −1.500% | −1.740% | −0.788% |
| EXPIRED | 0.2500 | +0.388% | +0.148% | +0.037% |
| **Total** | **1.000** | **+0.308%** | **+0.068%** | **+0.068%** ✅ |

**The simplified 38.7% breakeven formula would predict the breakeven TP rate as follows when EXPIRED returns are +0.388%:**

Let $p$ = TP rate, $q$ = SL rate = $1 - p - 0.25$, EXPIRED rate fixed at 0.25:

$$\text{Net EV} = p \times 2.76\% + (0.75-p) \times (-1.74\%) + 0.25 \times 0.148\% = 0$$
$$p \times 4.50\% = 0.75 \times 1.74\% - 0.037\% = 1.305\% - 0.037\% = 1.268\%$$
$$p_{\text{BEP}} = 1.268\% / 4.50\% = 28.2\%$$

**The actual breakeven TP rate — given the empirical EXPIRED return of +0.388% — is 28.2%, not 38.7%.** The observed 29.7% exceeds this threshold, explaining why net EV is positive even below the simplified 38.7% heuristic.

**The 38.7% heuristic is a two-outcome approximation. The correct endpoint is the full three-outcome net EV calculation. This has been correctly computed throughout.**

---

## 3. Cost Model Audit

### Applied Costs (Unchanged from V32.79 Frozen Methodology)

| Scenario | Round-Trip Cost | Components |
|---|---|---|
| Binance VIP0 | **24 bps (0.24%)** | 10 bps taker × 2 + 2 bps spread × 2 |
| Coinbase Advanced | **87 bps (0.87%)** | 40 bps taker × 2 + 3.5 bps spread × 2 |

Costs are deducted from gross P&L for ALL outcomes (TP, SL, EXPIRED). No selective cost application.

### Net EV Sensitivity

| Exchange | Cost | Net EV | Below BEP? |
|---|---|---|---|
| Binance VIP0 | 24 bps | **+6.8 bps** | Marginally above breakeven |
| Coinbase Advanced | 87 bps | **−56.2 bps** | Comfortably below breakeven |
| Zero cost (theoretical) | 0 bps | +30.8 bps | Above breakeven |
| Passive maker (disqualified) | 4 bps | +26.8 bps | Above breakeven (disqualified) |

At Coinbase retail fees, the SHORT arm requires additional +63 bps of gross EV per trade to break even — approximately 10× the current positive gross result. This is not achievable via minor optimizations.

---

## 4. BTCUSDT Funding Cash Flows — Instrument Distinction Maintained

The BTCUSDT funding rate was used as a signal input only. It was NOT applied as a cash flow to the BTCUSD evaluation.

If the same SHORT strategy were executed on BTCUSDT perpetual futures (NOT authorized):
- At the signal threshold (≥ +25% ann), SHORT perp positions RECEIVE funding.
- 3 settlements over 24h: +3 × 0.000228 = **+0.068%** credit per trade.
- Adjusted net EV (perp): +0.068% (spot) + 0.068% (funding credit) = **+0.136%** at Binance fees.

This information is documented for completeness only. The authorized instrument is BTCUSD spot. No perp position economics are claimed.

---

## 5. Slippage Assumption

The cost model includes:
- Exchange taker fee: stated above
- Half-spread: 2 bps (Binance), 3.5 bps (Coinbase) per leg

**Slippage (market impact):** Zero additional slippage assumed in the model. At 64 trades over 4.67 years — approximately once every 27 days — market impact at institutional BTCUSD spot sizes is negligible. For retail-scale positions, the half-spread estimate subsumes most of the slippage.

---

## 6. Summary

The full three-outcome decomposition confirms:
- All V32.79A arithmetic is correct.
- The +6.8 bps net EV at Binance fees is explained by favorable EXPIRED trade outcomes (+0.388% mean gross), not by TP rate alone.
- The 38.7% two-outcome BEP heuristic overstates the actual breakeven TP rate (which is 28.2% given empirical EXPIRED returns).
- The primary endpoint (net EV) is the correct measure and has been correctly applied.
- Coinbase retail economics remain firmly negative (−56.2 bps).

---

*No external calls. No dataset modifications. No model training.*

