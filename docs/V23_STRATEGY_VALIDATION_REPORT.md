# BTCognitive V23 — Quantitative Strategy Research & Friction Validation Report

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Re-evaluation of offline strategy hypotheses under realistic execution friction and selection-bias controls.  
**Research Status:** `NO_STRATEGY_WINNER_ESTABLISHED`

---

## 1. Executive Summary

This report evaluates whether any active trading strategy hypothesis implemented in BTCognitive demonstrates statistical or economic superiority over a zero-exposure baseline after accounting for realistic retail transaction friction.

### Central Finding:
Under a realistic retail friction scenario of **87 basis points (bps) round-trip** (40 bps taker fee each side + 7 bps conservative spread and slippage), **every active strategy hypothesis experiences severe net losses**. The zero-exposure baseline decisively outperforms all active strategies. Consequently, the project governance status remains firmly: **`NO_STRATEGY_WINNER_ESTABLISHED`**.

---

## 2. Friction Model & Strategy Definitions

### 2.1 Friction Model Assumptions
- **Exchange Venue:** Retail crypto spot exchange (Coinbase Advanced / Kraken standard tier).
- **Entry Fee:** 40 bps (taker).
- **Exit Fee:** 40 bps (taker).
- **Spread & Execution Slippage:** 7 bps round-trip conservative estimate.
- **Total Round-Trip Friction:** **87 bps (0.87%) per executed trade**.
- *Boundary Note:* This is an assumed friction model for quantitative research comparisons, not an individualized fee quote.

### 2.2 Strategy Hypotheses Evaluated
1. **TS_MOM_TREND (Dual SMA Trend Following):**
   - Rules: Fast SMA (24h) crosses Slow SMA (168h). Long when Fast > Slow; Flat/Short when Fast < Slow.
2. **SHORT_HORIZON_MEAN_REVERSION (RSI 30/70):**
   - Rules: 14-period hourly RSI. Buy when RSI < 30; Sell/Exit when RSI > 70.
3. **VOL_COMPRESSION_BREAKOUT:**
   - Rules: 24h Realized Volatility < 15th historical percentile followed by a 2.0-ATR price breakout.
4. **REGIME_ADAPTIVE_ROUTER:**
   - Rules: Router conditioning entry on confirmed volatility regime from HAR-RS-DOW.
5. **NO_TRADE_BENCHMARK:**
   - Rules: Zero market exposure (cash/USDC). Zero fees incurred.

---

## 3. Historical Simulation Results

| Strategy Hypothesis | Trade Count | Gross Return | Friction Loss (at 87 bps) | Net Return | Maximum Drawdown | Economic Conclusion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dual SMA Trend Following** | 506 trades | +7,863.0 bps | -44,022.0 bps | **-36,159.0 bps** | -42.8% | Heavily negative after friction |
| **Regime-Adaptive Router** | 225 trades | +812.0 bps | -19,575.0 bps | **-18,763.0 bps** | -24.5% | Severe underperformance |
| **Volatility Compression Breakout** | 105 trades | +1,024.5 bps | -9,135.0 bps | **-8,110.5 bps** | -16.2% | Negative after friction |
| **RSI Mean Reversion (30/70)** | 35 trades | +331.4 bps | -3,045.0 bps | **-2,713.6 bps** | -8.4% | Negative after friction |
| **Zero-Exposure Benchmark** | 0 trades | 0.0 bps | 0.0 bps | **0.0 bps** | **0.0%** | **Decisive Winner** |

---

## 4. Methodological Safeguards Against Overfitting

Following peer-reviewed econometrics standards (Bailey et al., "The Probability of Backtest Overfitting"):
1. **Selection Bias Prevention:** Selecting the highest in-sample return among multiple backtest parameter iterations generates false optimism. We do not promote the highest in-sample performer.
2. **Target Mismatch:** Strategies relying on hourly directional forecasts attempt to harvest high-frequency predictability that is empirically absent in unconditional spot BTC returns.
3. **Turnover Destruction:** Higher turnover exponentially compounds trading friction, turning moderate gross profits into devastating net drawdowns.

---

## 5. Chart Representation Standards in BTCognitive V23

In V23, strategy rules are strictly separated from live chart signals:
1. **Default Chart:** Completely clean of strategy arrows or trade ticket recommendations.
2. **Optional Research Markers:** When the user clicks `🔬 Research Markers [ON]`, genuine historical research events are rendered with:
   - Rule identification and version.
   - Exact trigger rationale and timestamp.
   - Explicit classification:
     - 🟢 Potential Bullish Setup (rule satisfied)
     - 🔴 Potential Bearish Setup (rule satisfied)
     - ⚪ No Confirmed Setup (abstention)
   - Mandatory Badge: **`OFFLINE RESEARCH ONLY · NOT AN ORDER INSTRUCTION`**.
3. **No Execution Guarantee:** Research events must never be represented as live orders or validated winning trades.
