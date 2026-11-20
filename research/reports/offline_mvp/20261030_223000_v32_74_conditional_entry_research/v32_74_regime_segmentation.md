# V32.74 — Market Regime Segmentation Report

**Milestone:** V32.74 — Conditional Entry Quality Research  
**Date:** 2026-10-30  
**Classification:** Macro-Microstructure Analysis | OFFLINE_RESEARCH_ONLY  
**Dataset:** `data/raw/ohlcv_backfilled.parquet` — Chronological OOS Window (10,521 bars)

---

## 1. Executive Summary

Milestone V32.74 evaluated whether entry quality and barrier touch distributions vary systematically across **volatility regimes** (Low, Medium, High) and **trend regimes** (Bullish, Bearish, Ranging).

**Key Findings:**
1. **Volatility Regime Impact:**
   - **Low Volatility:** Expired rate nearly doubles to **19.72%** (Long) and **13.33%** (Short). Stop-out rate declines from 63% to 55%. However, Net EV remains negative (**-0.116%** to **-0.143%**) because the market fails to reach the 1.5% take-profit target within 24 hours.
   - **High Volatility:** Expired rate drops to **6.8%–7.4%**, but Stop-out rate surges to **61.9%–63.9%**. Immediate stop-out risk increases due to intraday noise.
2. **Trend Regime Impact:**
   - In **Bullish Trends**, Long TP rate improves to **28.22%** (vs 26.32% in Bearish), but SL rate remains stubbornly high (**57.67%**).
   - In **Bearish Trends**, Short TP rate reaches **30.87%** (vs 27.08% in Bullish).
   - In **Ranging Markets**, Expired outcomes peak at **17.39%** (Long), while directional TP rates collapse.
3. **Sample Size & Validity:**
   - All evaluated segments have sample sizes between **184 and 366 observations**. Zero segments are undersized ($N < 30$).
   - Net expected value is **strictly negative across all 12 segmented sub-populations** after Binance VIP 0 transaction costs.

---

## 2. Volatility Regime Breakdown

Regimes defined by 33rd and 66th quantiles of 24-hour rolling realized volatility:
- **`LOW_VOLATILITY`:** $\sigma_{24} \le 0.018$ (Annualized $\approx 38\%$)
- **`MEDIUM_VOLATILITY`:** $0.018 < \sigma_{24} \le 0.034$ (Annualized $\approx 55\%$)
- **`HIGH_VOLATILITY`:** $\sigma_{24} > 0.034$ (Annualized $\approx 92\%$)

| Volatility Regime | Direction | Valid $N$ | Undersized ($N < 30$) | TP_FIRST Rate | SL_FIRST Rate | EXPIRED Rate | Gross EV | Net EV (Binance VIP0) |
|---|---|---|---|---|---|---|---|---|
| **`LOW_VOLATILITY`** | LONG | 360 | False | 25.00% | 55.28% | **19.72%** | +0.0237% | **-0.1163%** |
| **`LOW_VOLATILITY`** | SHORT | 360 | False | 28.06% | 58.61% | **13.33%** | -0.0025% | **-0.1425%** |
| **`MEDIUM_VOLATILITY`** | LONG | 322 | False | 25.78% | 63.66% | 10.56% | -0.0599% | **-0.1999%** |
| **`MEDIUM_VOLATILITY`** | SHORT | 324 | False | 31.17% | 60.80% | 8.02% | +0.0250% | **-0.1150%** |
| **`HIGH_VOLATILITY`** | LONG | 189 | False | 30.69% | 61.90% | **7.41%** | +0.0100% | **-0.1300%** |
| **`HIGH_VOLATILITY`** | SHORT | 191 | False | 29.32% | 63.87% | **6.81%** | -0.0330% | **-0.1730%** |

### Observations:
- **Low Volatility Trap:** Many retail traders attempt to trade breakouts or tight ranges in low-volatility regimes. However, because Bitcoin's range compresses, 20% of trades time out at 24 hours without hitting either barrier. The resulting exit near open yields essentially zero gross profit, while paying full trading fees.
- **High Volatility Whip:** In high volatility, barriers are breached rapidly (median time to barrier < 3 hours). The stop-out frequency exceeds 61% in both directions.

---

## 3. Trend Regime Breakdown

Regimes defined by exponential moving average spread:
$\Delta_{\text{EMA}} = \frac{\text{EMA}_{24} - \text{EMA}_{168}}{\text{EMA}_{168}} \times 100\%$
- **`BULLISH_TREND`:** $\Delta_{\text{EMA}} > +0.50\%$
- **`BEARISH_TREND`:** $\Delta_{\text{EMA}} < -0.50\%$
- **`RANGING_MARKET`:** $|\Delta_{\text{EMA}}| \le 0.50\%$

| Trend Regime | Direction | Valid $N$ | Undersized ($N < 30$) | TP_FIRST Rate | SL_FIRST Rate | EXPIRED Rate | Gross EV | Net EV (Binance VIP0) |
|---|---|---|---|---|---|---|---|---|
| **`BULLISH_TREND`** | LONG | 326 | False | **28.22%** | 57.67% | 14.11% | +0.0360% | **-0.1040%** |
| **`BULLISH_TREND`** | SHORT | 325 | False | 27.08% | 61.85% | 11.08% | -0.0347% | **-0.1747%** |
| **`BEARISH_TREND`** | LONG | 361 | False | 26.32% | 62.33% | 11.36% | -0.0465% | **-0.1865%** |
| **`BEARISH_TREND`** | SHORT | 366 | False | **30.87%** | 60.66% | 8.47% | +0.0170% | **-0.1230%** |
| **`RANGING_MARKET`** | LONG | 184 | False | 23.91% | 58.70% | **17.39%** | -0.0209% | **-0.1609%** |
| **`RANGING_MARKET`** | SHORT | 184 | False | 30.98% | 58.15% | 10.87% | +0.0323% | **-0.1077%** |

### Observations:
- **Trend Asymmetry Exists but is Economically Sub-Hurdle:**
  - Aligning with the trend regime provides an empirical boost to take-profit rates:
    - Long TP rate rises from 26.32% in Bearish to 28.22% in Bullish (+1.90%).
    - Short TP rate rises from 27.08% in Bullish to 30.87% in Bearish (+3.79%).
  - However, in neither case does the boost push Gross EV beyond +0.036%, which remains far below the round-trip fee hurdle of +0.14% to +0.24%.
- **Ranging Market Chop:** In ranging markets, Long entries suffer the lowest TP rate across the entire study (**23.91%**), with 17.39% expiring unfulfilled.

---

## 4. Regime Conditioning vs Unconditional Baseline

```mermaid
graph TD
    A[Unconditional Baseline: Net EV -0.214%] --> B{Condition on Trend}
    B -->|Bullish Long| C[Net EV -0.104% (Improved +11 bps)]
    B -->|Bearish Long| D[Net EV -0.186%]
    A --> E{Condition on Volatility}
    E -->|Low Vol Long| F[Net EV -0.116% (Improved +10 bps)]
    E -->|High Vol Long| G[Net EV -0.130%]
```

While conditioning on favorable regimes (Bullish for Long, Bearish for Short, Low Vol for both) improves Net EV by **10 to 11 basis points** compared to the unconditional random entry baseline, **the net result remains strictly underwater**.

---

## 5. Statistical Rigor Summary

- **Sample Size Sufficiency:** The smallest segment evaluated contained $N = 184$ independent valid observations, well above the $N \ge 30$ threshold for asymptotic normality under the Central Limit Theorem.
- **Empirical Verdict:** Macro-regime classification shifts the barrier probabilities in the expected theoretical direction, but the magnitude of the shift is insufficient to generate positive economic expectancy under a 24-hour fixed 2:1 barrier configuration.

---

*End of Regime Segmentation Report.*

