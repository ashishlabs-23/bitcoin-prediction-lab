# V32.77 — Volatility-Adaptive Barrier Experiment Design

**Workstream:** Agent 2 — Barrier Research Specialist  
**Milestone:** BTCognitive V32.77 — Volatility-Adaptive Entry Research  
**Date:** 2026-10-30  
**Evaluator:** Barrier Research Specialist (Agent 2)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Experimental Specification Authority Record  

---

## 1. Executive Summary & Design Scope

In response to the Product Manager's mandate, this document specifies a bounded, pre-registered experiment comparing fixed horizontal barriers against volatility-adaptive (ATR-scaled) barriers across BTCUSD:

- **Baseline:** Fixed 24h barrier: $\text{TP} = +1.50\%$, $\text{SL} = -0.75\%$ (Ratio 2:1).
- **Adaptive Parameter Grid:** 14-period Wilder's ATR normalized by closing price ($\text{NATR}_{14} = \text{ATR}_{14} / \text{Close}$).
- **Multipliers Tested ($k_{\text{TP}}, k_{\text{SL}}$):**
  - Tight: $(1.5, 0.75)$
  - Moderate: $(2.0, 1.00)$
  - Wide: $(3.0, 1.50)$
  - Very Wide: $(4.0, 2.00)$ to $(6.0, 3.00)$ for extended horizons.
- **Constraint:** We do **not** assume $k \ge 2.0$ is optimal. The trade-off between reduced stop-outs and larger dollar losses per stopped trade is evaluated explicitly.

---

## 2. Mathematical Barrier Formulations

### 2.1 Fixed Barriers (The Legacy Contract)
For an entry at price $P_{\text{entry}}$ at bar $t$:
$$\text{Long: } P_{\text{TP}} = P_{\text{entry}} \times (1 + 0.015), \quad P_{\text{SL}} = P_{\text{entry}} \times (1 - 0.0075)$$
$$\text{Short: } P_{\text{TP}} = P_{\text{entry}} \times (1 - 0.015), \quad P_{\text{SL}} = P_{\text{entry}} \times (1 + 0.0075)$$

### 2.2 Volatility-Adaptive Barriers (The ATR Contract)
Let $\text{ATR}_{14, t}$ be the Wilder's moving average of True Range up to closed bar $t$:
$$\text{TR}_t = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$
$$\text{NATR}_{14, t} = \frac{\text{ATR}_{14, t}}{C_t}$$

For a pre-specified reward-risk ratio $\theta = k_{\text{TP}} / k_{\text{SL}} = 2.0$:
$$\text{Long: } P_{\text{TP}} = P_{\text{entry}} \times (1 + k_{\text{TP}} \cdot \text{NATR}_t), \quad P_{\text{SL}} = P_{\text{entry}} \times (1 - k_{\text{SL}} \cdot \text{NATR}_t)$$
$$\text{Short: } P_{\text{TP}} = P_{\text{entry}} \times (1 - k_{\text{TP}} \cdot \text{NATR}_t), \quad P_{\text{SL}} = P_{\text{entry}} \times (1 + k_{\text{SL}} \cdot \text{NATR}_t)$$

---

## 3. Ambiguity Resolution & Path Invariants

1. **Conservative Intrabar Resolution:** If in a single 1-hour candle both the High touches $P_{\text{TP}}$ and the Low touches $P_{\text{SL}}$, the outcome is **strictly resolved as `SL_FIRST`**. Favorable intra-candle fill ordering is never assumed.
2. **Point-in-Time Fill:** Fill occurs at the close of the decision candle $t$ (or open of candle $t+1$). $\text{NATR}_t$ is computed strictly from candles $t-13$ to $t$.
3. **Time-Expiry Resolution:** If neither barrier is touched within the maximum holding horizon $H$ (24h, 72h, or 168h), the trade is resolved as `EXPIRED`, and return is marked-to-market at the closing price of bar $t + H$.

---

## 4. Pre-Registered Barrier Configurations Table

| Config Name | Type | Target $k_{\text{TP}}$ or $\%$ | Stop $k_{\text{SL}}$ or $\%$ | Nominal Ratio | Median Target USD | Median Stop USD |
|---|---|---|---|---|---|---|
| `FIXED_24H` | Fixed | +1.50% | -0.75% | 2.0 : 1 | \$1,200 | \$600 |
| `ATR_24H_TIGHT` | ATR-Scaled | $1.5 \times \text{NATR}$ | $0.75 \times \text{NATR}$ | 2.0 : 1 | \$700 | \$350 |
| `ATR_24H_MODERATE` | ATR-Scaled | $2.0 \times \text{NATR}$ | $1.00 \times \text{NATR}$ | 2.0 : 1 | \$933 | \$466 |
| `ATR_24H_WIDE` | ATR-Scaled | $3.0 \times \text{NATR}$ | $1.50 \times \text{NATR}$ | 2.0 : 1 | \$1,400 | \$700 |
| `ATR_72H_MODERATE` | ATR-Scaled | $3.0 \times \text{NATR}$ | $1.50 \times \text{NATR}$ | 2.0 : 1 | \$1,400 | \$700 |
| `ATR_72H_WIDE` | ATR-Scaled | $4.0 \times \text{NATR}$ | $2.00 \times \text{NATR}$ | 2.0 : 1 | \$1,866 | \$933 |
| `ATR_168H_WIDE` | ATR-Scaled | $5.0 \times \text{NATR}$ | $2.50 \times \text{NATR}$ | 2.0 : 1 | \$2,333 | \$1,166 |
| `ATR_168H_MAX` | ATR-Scaled | $6.0 \times \text{NATR}$ | $3.00 \times \text{NATR}$ | 2.0 : 1 | \$2,800 | \$1,400 |

*Signed by Specialist Agent 2 (Barrier Research Specialist)*

