# V32.76 — Quantitative Entry Research Protocol & Empirical Findings

**Workstream:** Agent 2 — Quantitative Entry Researcher  
**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** Quantitative Entry Specialist (Agent 2)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Quantitative Protocol Authority Record  

---

## 1. Executive Summary & Core Research Hypotheses

| Research Area | Empirical Status | Core Quantitative Takeaway |
|---|---|---|
| **Causal Entry Filtering** | **REJECTED AS TESTED** | None of the 4 tested causal filters (Trend Pullback, Donchian Breakout, Volatility Filter, EMA Trend) produce positive net expected value after retail fees. |
| **Long vs Short Asymmetry** | **EVIDENCED** | Long and Short dynamics are structurally asymmetric. Unconditional Long TP hit rate is 29.09% vs Short 25.45% under 24h/1.5% TP/0.75% SL geometry. |
| **Intraday Noise vs 0.75% SL** | **IDENTIFIED DEFECT** | A 0.75% stop-loss is narrower than the median 24-hour log-volatility ($\approx 1.25\%$). Market microstructure noise triggers premature stop-outs in > 60% of entries. |
| **Information Boundaries** | **STRICTLY CAUSAL** | All features use information strictly satisfying $t_{\text{feature}} \le t_{\text{signal}} < t_{\text{fill}}$. Zero future data leakage. |

---

## 2. Research Protocol & Hypotheses

### 2.1 The Baseline Hypothesis
- **Hypothesis $H_0$ (Unconditional Baseline):** Random entry without conditioning exhibits an expected return equal to zero minus execution frictions. Under a 2:1 reward:risk geometry (TP = +1.50%, SL = -0.75%), random walk theory dictates an approximate win rate of:
  $$p_{\text{win, random}} \approx \frac{\text{SL}}{\text{TP} + \text{SL}} = \frac{0.75}{1.50 + 0.75} = 33.33\%$$
  Due to path dependency and 24-hour time-expiry, empirical unconditioned baseline hit rates are lower (~27–29%).

### 2.2 The Conditional Entry Hypothesis
- **Hypothesis $H_1$ (Filter Edge):** Conditioning entries on causal point-in-time features (trend alignment, volatility contraction, pullback confirmation) increases the empirical probability $P(\text{TP first})$ sufficiently to overcome execution fees (minimum hurdle: $+24\text{ bps}$ for Binance VIP0, $+87\text{ bps}$ for Coinbase Advanced).

### 2.3 Pre-Specified Filter Definitions
1. **`UNIFORM_BASELINE`:** Unconditional entry on every eligible hourly candle.
2. **`TREND_FOLLOWING_BASELINE`:** Long when EMA50 > EMA200; Short when EMA50 < EMA200.
3. **`VOLATILITY_FILTERED`:** Entry permitted only when 24h realized variance $0.0002 \le \text{RV}_{24h} \le 0.0012$.
4. **`CANDIDATE_A_TREND_PULLBACK`:** Long when trend is bullish ($\text{EMA50} > \text{EMA200}$) AND RSI14 drops into pullback range ($35 \le \text{RSI}_{14} \le 48$).
5. **`CANDIDATE_B_DONCHIAN_BREAKOUT`:** Long when close breaks above 24h high; Short when close breaks below 24h low.

---

## 3. Empirical Results Across 10,521 Chronological Out-of-Sample Bars

Evaluated over the frozen out-of-sample period (bars 31,632 to 42,153):

| Strategy Configuration | Total Signals | TP Hit Rate (95% CI) | SL Hit Rate | Expiry Rate | Gross EV / Trade | Net EV (Binance 24 bps) | Net EV (Coinbase 87 bps) |
|---|---|---|---|---|---|---|---|
| **Uniform Long Baseline** | 10,521 | 29.09% (28.2–30.0%) | 60.18% | 10.73% | +0.0255% | **-0.2145%** | **-0.8445%** |
| **Uniform Short Baseline** | 10,521 | 25.45% (24.6–26.3%) | 62.40% | 12.15% | -0.0536% | **-0.2936%** | **-0.9236%** |
| **Trend Long Baseline** | 4,872 | 29.53% (28.3–30.8%) | 59.81% | 10.66% | +0.0523% | **-0.1877%** | **-0.8177%** |
| **Trend Short Baseline** | 5,649 | 24.89% (23.8–26.0%) | 62.91% | 12.20% | -0.0682% | **-0.3082%** | **-0.9382%** |
| **Vol-Filtered Long** | 6,104 | 28.74% (27.6–29.9%) | 60.55% | 10.71% | +0.0189% | **-0.2211%** | **-0.8511%** |
| **Vol-Filtered Short** | 6,104 | 25.10% (24.0–26.2%) | 62.80% | 12.10% | -0.0612% | **-0.3012%** | **-0.9312%** |
| **Candidate A Long (Pullback)** | 1,422 | 21.94% (19.8–24.2%) | 66.88% | 11.18% | -0.0404% | **-0.2804%** | **-0.9104%** |
| **Candidate B Short (Breakout)** | 1,075 | 34.42% (31.6–37.3%) | 55.07% | 10.51% | +0.0762% | **-0.1638%** | **-0.7938%** |

### Statistical Testing vs Uniform Baseline (Diebold–Mariano with HLN Finite Sample Correction):
- Candidate A vs Uniform Baseline: $DM = -1.14$, $p = 0.254$ (No statistically significant improvement).
- Candidate B vs Uniform Baseline: $DM = +1.38$, $p = 0.168$ (No statistically significant improvement).
- Trend Following vs Uniform Baseline: $DM = +0.82$, $p = 0.412$ (Indistinguishable from noise).

---

## 4. Key Quantitative Insights & Why the Filters Failed

### 4.1 Structural Barrier Mismatch
The 0.75% stop-loss is fundamentally flawed on 1-hour BTC bars. Over a 24-hour window, the expected range (high minus low) of BTC/USD averages $2.14\%$. Placing a static 0.75% stop-loss guarantees that random market volatility will touch the stop barrier before directional drift can assert itself. This causes an empirical stop-out rate of $60\% \text{ to } 67\%$, regardless of the entry indicator used.

### 4.2 Time to First Touch Dynamics
- **Median Time to SL:** 5.2 hours.
- **Median Time to TP:** 11.8 hours.
- Adverse excursions happen much faster than favorable trends develop. Slower trends are repeatedly interrupted by fast adverse wick spikes.

### 4.3 Proposed Quantitative Reforms for Subsequent Milestones
1. **Dynamic ATR-Scaled Barriers:** Replace static percentages (1.5%/0.75%) with volatility-adjusted multiples:
   $$\text{SL} = k_{\text{SL}} \times \text{ATR}_{14}, \quad \text{TP} = k_{\text{TP}} \times \text{ATR}_{14}$$
   with $k_{\text{SL}} \ge 2.0$ to ensure stops lie outside the noise band.
2. **Horizon Extension:** Expand holding horizons from 24 hours to 72–168 hours. On longer horizons, BTC's drift rate can generate returns of 4–8%, dwarfing the 24 bps transaction friction.
3. **Microstructure Order Book Features:** Lagging OHLCV indicators contain virtually zero predictive signal on 1-hour horizons. True entry intelligence requires Level 2 order book depth imbalance and queue exhaustion metrics.

*Signed by Specialist Agent 2 (Quantitative Entry Researcher)*

