# V32.74 — Baseline Comparison & Statistical Significance Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Date:** 2026-10-30  
**Classification:** Quantitative Econometrics | OFFLINE_RESEARCH_ONLY  
**Benchmarked Against:** `UNIFORM_BASELINE` (Periodic 24h Sampling) and Simple Moving Average Baseline

---

## 1. Executive Summary

A critical requirement of Milestone V32.74 is to determine whether proposed causal entry filters provide a statistically significant and economically meaningful improvement over:
1. **Unconditional Uniform Sampling** (periodic baseline across all bars).
2. **Simple Trend-Following Baseline** ($\text{Close} > \text{EMA}_{48}$ and $\text{EMA}_{24} > \text{EMA}_{168}$).
3. **Simple Volatility Baseline** (realized volatility quantile filtering).

**Result:** While `TREND_FOLLOWING_BASELINE` and `CANDIDATE_B_DONCHIAN_BREAKOUT` (Short) achieve minor gross improvements in TP hit rate (+2.3% to +8.9% over uniform baseline), **no filter achieves a statistically significant improvement in Net Expected Value after transaction friction** (Diebold–Mariano $p > 0.15$ in all paired comparisons).

---

## 2. Head-to-Head Comparison Matrix (OOS Test Set)

### 2.1 LONG Direction

| Strategy / Filter | $N$ | TP Rate | Delta vs Uniform | Gross EV | Net EV (Binance) | Net EV (Coinbase) | DM Test vs Uniform ($p$-value) | Verdict |
|---|---|---|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | 110 | 29.09% | 0.00% | +0.0255% | -0.2145% | -0.8445% | Reference | Baseline |
| `TREND_FOLLOWING` | 3,461 | 29.53% | +0.44% | +0.0523% | -0.1877% | -0.8177% | $p = 0.412$ (Not Sig) | No Meaningful Delta |
| `VOLATILITY_FILTERED` | 4,286 | 25.20% | -3.89% | +0.0493% | -0.1907% | -0.8207% | $p = 0.389$ (Not Sig) | Inferior TP Hit Rate |
| `CANDIDATE_A` (Pullback) | 1,085 | 21.94% | -7.15% | -0.0404% | -0.2804% | -0.9104% | $p = 0.181$ (Inferior) | Rejection |
| `CANDIDATE_B` (Breakout) | 390 | 25.38% | -3.71% | -0.0728% | -0.3128% | -0.9428% | $p = 0.224$ (Inferior) | Rejection |

### 2.2 SHORT Direction

| Strategy / Filter | $N$ | TP Rate | Delta vs Uniform | Gross EV | Net EV (Binance) | Net EV (Coinbase) | DM Test vs Uniform ($p$-value) | Verdict |
|---|---|---|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | 110 | 25.45% | 0.00% | -0.0536% | -0.2936% | -0.9236% | Reference | Baseline |
| `TREND_FOLLOWING` | 3,978 | 31.35% | +5.90% | +0.0433% | -0.1967% | -0.8267% | $p = 0.287$ (Not Sig) | Inconclusive |
| `VOLATILITY_FILTERED` | 2,396 | 31.18% | +5.73% | +0.0154% | -0.2246% | -0.8546% | $p = 0.341$ (Not Sig) | Inconclusive |
| `CANDIDATE_A` (Pullback) | 1,231 | 30.87% | +5.42% | +0.0493% | -0.1907% | -0.8207% | $p = 0.295$ (Not Sig) | Inconclusive |
| `CANDIDATE_B` (Breakout) | 398 | 34.42% | +8.97% | +0.0762% | -0.1638% | -0.7938% | $p = 0.164$ (Not Sig) | Rejection (Negative Net) |

---

## 3. Diebold–Mariano Hypothesis Testing (HLN Corrected)

Per the BTCognitive Governance Protocol (Phase 5), paired predictive comparisons must use the **Diebold–Mariano (1995)** statistic with the **Harvey–Leybourne–Newbold (1997)** finite-sample correction:
$$S^* = S \times \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$$
with reference distribution Student's $t_{T-1}$, evaluating loss differential series $d_t = L(\hat{y}_{1,t}, y_t) - L(\hat{y}_{0,t}, y_t)$ where $L$ is negative net realized return.

### 3.1 Long Results:
- For `TREND_FOLLOWING` vs `UNIFORM_BASELINE`: $t = 0.82$, $p = 0.412$. Cannot reject the null hypothesis of equal economic loss.
- For `CANDIDATE_A` vs `UNIFORM_BASELINE`: $t = -1.34$, $p = 0.181$. Shows weaker performance than uniform sampling, driven by premature stop-outs during pullback entry.
- For `CANDIDATE_B` vs `UNIFORM_BASELINE`: $t = -1.22$, $p = 0.224$. Shows inferior performance due to high false breakout rate on 1H charts.

### 3.2 Short Results:
- For `CANDIDATE_B` (Short Donchian Breakout) vs `UNIFORM_BASELINE`: $t = 1.39$, $p = 0.164$. Although the TP rate increased from 25.45% to 34.42%, the variance of trade returns is high, and the difference is not statistically significant at the pre-registered $\alpha = 0.05$ threshold.
- Crucially, even with an 8.97% boost in TP rate, net return remains **negative (-0.1638%)** under Binance VIP 0 fees.

---

## 4. Why Causal Technical Indicators Fail to Overcome the Hurdle

1. **High Intrinsic BTC Noise at 1H Horizon:**
   - Over a 24-hour horizon, Bitcoin's median 1H ATR is approximately 0.65%–0.90%.
   - Placing a stop-loss at 0.75% places the stop boundary directly inside 1 standard deviation of 1-hour noise.
   - Consequently, in over 57%–65% of all bars, price breaches the stop before establishing a 1.50% directional trend, regardless of moving average alignment or RSI status.

2. **Winner's Curse on Breakouts:**
   - Donchian breakouts trigger only after price has already traveled 24-hour highs/lows.
   - In crypto spot markets, breakout bars are often local exhaustion points where liquidity providers absorb momentum and mean-revert into range equilibrium.

3. **Transaction Cost Drag:**
   - At a 24-hour frequency, trading multiple signals per day accumulates round-trip turnover fees that overwhelm gross edge.
   - A gross edge of 5 to 7 basis points cannot survive a retail fee structure of 24 to 87 basis points.

---

## 5. Decision & Governance Verdict

- **Experiment Result:** `FAIL` / `NO_GO_NO_VALIDATED_EDGE`.
- **Baseline Challenger:** Retain `OFFLINE_RESEARCH_ONLY`.
- **Recommendation:** Do not promote any candidate filter. Do not autorun further indicator tweaks without altering fundamental horizon and barrier parameters.

---

*End of Baseline Comparison Report.*

