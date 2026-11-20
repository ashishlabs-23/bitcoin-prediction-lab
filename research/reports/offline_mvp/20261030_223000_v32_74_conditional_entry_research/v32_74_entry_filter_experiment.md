# V32.74 — Conditional Entry Filter Experiment Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Date:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY | Empirical Research  
**Dataset:** `data/raw/ohlcv_backfilled.parquet` (42,177 continuous 1H bars, 2022-01-01 to 2026-10-24)  
**Evaluation Scope:** Chronological Out-of-Sample (OOS) Test Set (10,521 bars; indices 31,632 to 42,153)

---

> [!IMPORTANT]
> **Scientific Integrity & Risk Boundary:**
> 1. All results reflect **retrospective backtest replay** on development data.
> 2. **EQR (Excursion Quality Ratio) is NOT a win probability.** It is a geometric ratio of favorable-to-adverse path excursion ($\text{MFE} / \text{MAE}$).
> 3. Fill prices strictly enforce causal execution: **OPEN of bar $t+1$** (next-bar fill). Signals use only information available at the close of bar $t$.
> 4. All experiments are conducted strictly under `OFFLINE_RESEARCH_ONLY`. Live trading is `DISABLED`.

---

## 1. Experimental Design & Pre-Specified Filters

### 1.1 Barrier Specifications
- **Horizon ($H$):** 24 hours.
- **Take-Profit Barrier ($\text{TP}$):** +1.50% from fill price.
- **Stop-Loss Barrier ($\text{SL}$):** -0.75% from fill price.
- **Asymmetry Ratio:** 2.0 : 1.0 (TP requires a 2x price excursion relative to SL).
- **Labels:**
  - $\text{TP\_FIRST} (+1)$: High $\ge \text{TP}$ (long) or Low $\le \text{TP}$ (short) before SL or expiry.
  - $\text{SL\_FIRST} (-1)$: Low $\le \text{SL}$ (long) or High $\ge \text{SL}$ (short) before TP or expiry.
  - $\text{EXPIRED} (0)$: Neither barrier reached within 24 hours. Settled at bar 24 close.
  - $\text{AMBIGUOUS}$: Both barriers breached in same 1-hour bar or timestamp gap. Quarantined from statistics.

### 1.2 Five Pre-Specified Causal Filters
All indicators computed using data strictly up to bar $t$:
1. **`UNIFORM_BASELINE` (Unconditional):** Systematic sampling every 24 bars (no filtering).
2. **`TREND_FOLLOWING_BASELINE`:**
   - Long: $\text{Close}_t > \text{EMA}_{48}(t)$ AND $\text{EMA}_{24}(t) > \text{EMA}_{168}(t)$
   - Short: $\text{Close}_t < \text{EMA}_{48}(t)$ AND $\text{EMA}_{24}(t) < \text{EMA}_{168}(t)$
3. **`VOLATILITY_FILTERED_BASELINE`:**
   - Long: Rolling 24h Realized Volatility $\sigma_{24} < 33\text{rd percentile}$ (low-vol compression)
   - Short: Rolling 24h Realized Volatility $\sigma_{24} > 66\text{th percentile}$ (high-vol expansion)
4. **`CANDIDATE_A_TREND_PULLBACK`:**
   - Long: $\text{EMA}_{24}(t) > \text{EMA}_{168}(t)$ (uptrend) AND $\text{RSI}_{14}(t) < 45$ (oversold pullback)
   - Short: $\text{EMA}_{24}(t) < \text{EMA}_{168}(t)$ (downtrend) AND $\text{RSI}_{14}(t) > 55$ (relief bounce)
5. **`CANDIDATE_B_DONCHIAN_BREAKOUT`:**
   - Long: $\text{Close}_t > \max_{1 \le k \le 24}(\text{High}_{t-k})$ AND $\text{Volume}_t > \overline{\text{Volume}}_{24}(t)$
   - Short: $\text{Close}_t < \min_{1 \le k \le 24}(\text{Low}_{t-k})$ AND $\text{Volume}_t > \overline{\text{Volume}}_{24}(t)$

---

## 2. Out-of-Sample Empirical Results — LONG Entries

| Filter Name | Valid $N$ | TP Rate (95% Wilson CI) | SL Rate | Expired Rate | Median TTP / TTL | Gross EV | 95% Bootstrap CI | Binance VIP0 Net EV |
|---|---|---|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | 110 | 29.09% (21.4%–38.2%) | 60.00% | 10.91% | 5.0h / 3.0h | +0.0255% | [-0.174%, +0.228%] | **-0.2145%** |
| `TREND_FOLLOWING_BASELINE` | 3,461 | 29.53% (28.0%–31.1%) | 57.41% | 13.06% | 6.0h / 4.0h | +0.0523% | [+0.015%, +0.090%] | **-0.1877%** |
| `VOLATILITY_FILTERED_BASELINE` | 4,286 | 25.20% (23.9%–26.5%) | 53.36% | 21.44% | 8.0h / 6.0h | +0.0493% | [+0.019%, +0.080%] | **-0.1907%** |
| `CANDIDATE_A_TREND_PULLBACK` | 1,085 | 21.94% (19.5%–24.5%) | 59.17% | 18.89% | 7.0h / 4.0h | -0.0404% | [-0.103%, +0.023%] | **-0.2804%** |
| `CANDIDATE_B_DONCHIAN_BREAKOUT` | 390 | 25.38% (21.3%–29.9%) | 65.38% | 9.23% | 4.0h / 2.0h | -0.0728% | [-0.173%, +0.029%] | **-0.3128%** |

### Key Findings (LONG):
1. **Negative Net Expected Value Across All Filters:**
   - Under standard retail exchange conditions (Binance VIP 0: 24 bps round trip fee), **every single long filter produces negative net EV**.
   - Net EV ranges from **-0.1877%** (`TREND_FOLLOWING_BASELINE`) to **-0.3128%** (`CANDIDATE_B_DONCHIAN_BREAKOUT`).
2. **Failure of Candidate Filters:**
   - `CANDIDATE_A_TREND_PULLBACK` degrades TP hit rate to **21.94%** (compared to 29.09% uniform baseline). In BTCUSD, RSI pullbacks during an uptrend frequently precede deeper cascade liquidations that trigger the tight 0.75% stop-loss.
   - `CANDIDATE_B_DONCHIAN_BREAKOUT` triggers stop-loss in **65.38%** of entries, with a median time to stop of only **2.0 hours**. Breakouts on 1H BTCUSD suffer severe mean-reverting false breakouts.
3. **Volatility Filter Dynamics:**
   - Low-volatility compression entries double the expired rate (21.44% vs 10.91%), and push median time to barrier to 8 hours. However, the TP rate drops to 25.20%, yielding negative net returns after fees.

---

## 3. Out-of-Sample Empirical Results — SHORT Entries

| Filter Name | Valid $N$ | TP Rate (95% Wilson CI) | SL Rate | Expired Rate | Median TTP / TTL | Gross EV | 95% Bootstrap CI | Binance VIP0 Net EV |
|---|---|---|---|---|---|---|---|---|
| `UNIFORM_BASELINE` | 110 | 25.45% (18.2%–34.4%) | 60.00% | 14.55% | 7.0h / 3.0h | -0.0536% | [-0.252%, +0.145%] | **-0.2936%** |
| `TREND_FOLLOWING_BASELINE` | 3,978 | 31.35% (29.9%–32.8%) | 57.69% | 10.96% | 5.0h / 3.0h | +0.0433% | [+0.007%, +0.079%] | **-0.1967%** |
| `VOLATILITY_FILTERED_BASELINE` | 2,396 | 31.18% (29.3%–33.1%) | 61.64% | 7.18% | 4.0h / 2.0h | +0.0154% | [-0.030%, +0.061%] | **-0.2246%** |
| `CANDIDATE_A_TREND_PULLBACK` | 1,231 | 30.87% (28.3%–33.5%) | 59.63% | 9.50% | 5.0h / 3.0h | +0.0493% | [-0.011%, +0.111%] | **-0.1907%** |
| `CANDIDATE_B_DONCHIAN_BREAKOUT` | 398 | 34.42% (29.9%–39.2%) | 60.05% | 5.53% | 4.0h / 2.0h | +0.0762% | [-0.033%, +0.183%] | **-0.1638%** |

### Key Findings (SHORT):
1. **Slightly Higher Gross Return for Downward Breakouts:**
   - `CANDIDATE_B_DONCHIAN_BREAKOUT` on the short side achieved the highest TP rate (**34.42%**) and a gross EV of **+0.0762%**.
   - Downward momentum in BTC tends to exhibit higher velocity than upward grinds (liquidation cascades).
2. **Economic Hurdle Remains Unsurpassed:**
   - After subtracting Binance VIP 0 transaction costs (0.24%), even the best short candidate filter yields **-0.1638% Net EV**.
   - Under Coinbase Advanced (0.87% round trip), Net EV is **-0.7938%**.
   - The 95% bootstrap confidence interval on net return spans `[-0.273%, -0.057%]`, which is strictly negative.

---

## 4. Path Excursion Metrics (MFE, MAE & EQR)

| Filter / Direction | Mean MFE | Median MFE | Mean MAE | Median MAE | Mean EQR | Median EQR |
|---|---|---|---|---|---|---|
| `UNIFORM_BASELINE` (Long) | 1.83% | 1.48% | 1.87% | 1.15% | 7.42 | 1.34 |
| `TREND_FOLLOWING` (Long) | 1.86% | 1.51% | 1.77% | 1.09% | 8.84 | 1.41 |
| `CANDIDATE_A` (Long) | 1.63% | 1.35% | 1.83% | 1.14% | 5.32 | 1.20 |
| `CANDIDATE_B` (Long) | 1.72% | 1.40% | 1.95% | 1.23% | 4.96 | 1.17 |
| `UNIFORM_BASELINE` (Short) | 1.69% | 1.38% | 2.02% | 1.30% | 4.88 | 1.07 |
| `TREND_FOLLOWING` (Short) | 1.88% | 1.54% | 1.79% | 1.10% | 7.91 | 1.38 |
| `CANDIDATE_A` (Short) | 1.85% | 1.52% | 1.80% | 1.11% | 7.64 | 1.36 |
| `CANDIDATE_B` (Short) | 1.95% | 1.58% | 1.74% | 1.08% | 8.12 | 1.44 |

> [!WARNING]
> Notice the extreme divergence between Mean EQR (4.9–8.8) and Median EQR (1.1–1.4).
> This occurs because when $\text{MAE} \to 0$ (e.g. bar moves straight to target without hesitation), EQR explodes to $> 100$.
> **Mean EQR is heavily distorted by tail outliers.** Median EQR (1.07–1.44) reflects the true central tendency: entries experience roughly 1.1x to 1.4x favorable excursion relative to adverse excursion.
> This modest geometric advantage is insufficient to overcome the 2:1 barrier asymmetry (TP=1.5% vs SL=0.75%) after transaction friction.

---

## 5. Formal Experimental Conclusion

1. **Hypothesis Rejected:** Causal entry filters do NOT produce positive net expected value in chronological out-of-sample BTCUSD data under verified execution friction.
2. **Economic Cause:** The 24-hour horizon with a tight 0.75% stop-loss suffers from rapid noise-stopouts (median TTL = 2 to 4 hours) in BTC's continuous volatility.
3. **Research Decision:** In accordance with Product Manager instructions, **all candidate filters are rejected rather than curve-fitted with additional indicators**.

---

*End of Conditional Entry Filter Experiment Report.*

