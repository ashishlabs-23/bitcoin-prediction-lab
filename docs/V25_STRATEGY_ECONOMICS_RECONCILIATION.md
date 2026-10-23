# BTCognitive V25 — Strategy Economics & Cost-Model Reconciliation Audit

**Specialist Role:** Agent A (Quantitative Strategy Reviewer)  
**Date:** 19 October 2026  
**Status:** Economics Reconciled — Standardized Accounting Established  
**Canonical Manifest:** `experiments/results/v25_canonical_strategy_manifest.json`  
**Dataset:** `data/raw/ohlcv.parquet` (41,273 rows, SHA-256 `43c8881b57431759f68fcb7036d78432449d079b11bcaea45f0d0ecfa287e2f6`)  
**Evaluation Window:** 9,975 out-of-sample hourly bars (415.6 calendar days)  

---

## 1. Executive Summary & Root-Cause Forensic Resolution

A primary mandate of V25 was to resolve cross-version discrepancies in strategy trade counts, transition accounting, and friction multiplication:
1. **The Arithmetic Discrepancy:** In V24, friction was reported as $\text{transition count} \times 43.5\text{ bps}$. For Dual-SMA, this produced $100 \times 43.5 = 4,350.0\text{ bps}$.
2. **The Forensic Finding:** In position state space $s_t \in \{-1, 0, 1\}$, a transition event occurs whenever $s_t \neq s_{t-1}$. However, transitions are **not** all equal in execution cost:
   - **One-Step Transition (Entry or Exit):** $|s_t - s_{t-1}| = 1$ unit of exposure change. E.g., Flat to Long ($0 \to 1$) or Long to Flat ($1 \to 0$). Cost $= 43.5\text{ bps}$. Two one-step transitions form 1 complete round trip ($87.0\text{ bps}$).
   - **Reversal Transition (Long to Short or Short to Long):** $|s_t - s_{t-1}| = 2$ units of exposure change. E.g., $+1 \to -1$. A reversal requires closing the long (1 unit) AND opening the short (1 unit). This equals **2 one-way executions** and incurs a full round trip of friction ($2 \times 43.5 = 87.0\text{ bps}$) in a single bar!
3. **The Dual-SMA Breakdown:**
   - In Dual-SMA, out of 100 transition events, **99 were reversals** ($+1 \to -1$ or $-1 \to +1$) and only 1 was an initial entry ($0 \to 1$).
   - The true turnover volume was $1 + (99 \times 2) = \mathbf{199.0\text{ turnover units}}$, which equals $99.5$ completed round trips!
   - Correct friction $= 199.0 \times 43.5\text{ bps} = \mathbf{8,656.5\text{ bps}}$ (twice the simplistic event-count multiplication).
   - This reconciles the bar-level compounding equity curve (which penalized 2 units for reversals) with the summary table.
4. **Historical Trade Count Reconciliation (V18/V22 506 trades vs V24 100 events):**
   - The 506-trade figure in earlier memos evaluated an extended historical window or alternate fast/slow spans ($SMA(12)/SMA(48)$ across 41,273 bars).
   - On the standardized out-of-sample test window of 9,975 bars, the exact candidate rules generate 100 events (199 turnover units).
   - In both cases, the qualitative and quantitative conclusion is identical: **retail friction completely destroys gross returns**.

---

## 2. Standardized Offline Backtesting Protocol

To prevent future accounting ambiguities, BTCognitive adopts an authoritative 8-tier simulation contract:

$$\begin{aligned}
\text{Signal Event } E_t &= \mathbb{I}(s_t \neq s_{t-1}) \\
\text{Turnover Units } \Delta s_t &= |s_t - s_{t-1}| \in \{0, 1, 2\} \\
\text{Completed Round Trips } RT &= \frac{1}{2} \sum_{t=1}^T \Delta s_t \\
\text{Friction Drag } C_t &= \Delta s_t \times \left( \frac{\text{Cost}_{\text{round-trip}}}{2} \right) \\
\text{Gross Bar Return } r_{g, t} &= s_{t-1} \cdot \ln(P_t / P_{t-1}) \\
\text{Net Bar Return } r_{n, t} &= r_{g, t} - \left( \Delta s_t \times \frac{\text{Cost}_{\text{round-trip}}}{20000} \right)
\end{aligned}$$

---

## 3. Reconciled Performance Matrix (Retail 87 bps Scenario)

Evaluated over 9,975 continuous out-of-sample hourly candles (415.6 calendar days):

| Strategy Hypothesis | Signal Events ($E$) | Reversals ($\Delta s = 2$) | Turnover Units ($U$) | Completed Round Trips ($RT$) | Gross Return (bps) | Friction Drag (bps) | Net Return (bps) | Max Drawdown | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Zero-Exposure Benchmark** | **0** | **0** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0%** | `DECISIVE WINNER` |
| **Dual-SMA Trend (24h/168h)** | 100 | 99 | 199.0 | 99.5 | +1,570.6 | -8,656.5 | **-7,085.9** | 79.4% | `REJECTED` |
| **RSI Mean Reversion (14h)** | 642 | 0 | 642.0 | 321.0 | -370.5 | -27,927.0 | **-28,297.5** | 94.2% | `REJECTED` |
| **Volatility Breakout (24h)** | 893 | 3 | 896.0 | 448.0 | +2,686.0 | -38,976.0 | **-36,290.0** | 97.4% | `REJECTED` |
| **Regime-Adaptive Router** | 1,011 | 105 | 1,116.0 | 558.0 | -3,561.3 | -48,546.0 | **-52,107.3** | 99.6% | `REJECTED` |

---

## 4. Governed Release Conclusion

1. **Turnover Drag Decimates Active Returns:** Even for momentum strategies that achieve positive gross price drift (+1,570 to +2,686 bps), turnover friction under realistic retail conditions (87 bps round-trip) produces deep, irreversible capital destruction.
2. **Decisive Victory of Zero Exposure:** The zero-exposure baseline decisively outperforms all active strategies across return, volatility, Sharpe ratio, and drawdown.
3. **Official Governance State:** **`NO_STRATEGY_WINNER_ESTABLISHED`** is reaffirmed without reservation.
4. **Non-Execution Commitment:** No strategy will be promoted, authorized, or connected to live execution.
