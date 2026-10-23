# BTCognitive V24 — Strategy Research & Backtest Forensic Audit

**Specialist Role:** Agent C (Quantitative Strategy Reviewer)  
**Date:** 19 October 2026  
**Status:** Canonical Reproduction Complete — `NO_STRATEGY_WINNER_ESTABLISHED`  
**Dataset:** `data/raw/ohlcv.parquet` (41,273 hourly bars, SHA-256 `43c8881b...`)  
**Evaluation Window:** 9,975 out-of-sample hourly bars (415.6 calendar days)  

---

## 1. Executive Summary & Core Conclusion

An independent quantitative backtest was conducted to reproduce the offline rule-based strategy experiments under the documented retail transaction friction scenario (87 basis points round-trip).

### Definitive Finding:
1. **Zero Active Strategy Winners:** After deducting realistic retail transaction friction (87 bps round-trip, or 43.5 bps per one-way exposure transition), **every active strategy generated catastrophic negative net returns**, with net drawdowns exceeding 67% to 99%.
2. **Turnover Drag as the Primary Destroyer of Value:** Gross returns for momentum or breakout models (+1,500 to +2,600 bps) are completely erased by frequent turnover (100 to 1,011 trades).
3. **Decisive Baseline Victory:** The zero-exposure benchmark (0.0 bps return, 0.0% max drawdown) decisively outperformed all active strategy candidates.
4. **Governed Decision:** The status `NO_STRATEGY_WINNER_ESTABLISHED` is reaffirmed. No strategy is authorized for execution or live deployment.

---

## 2. Friction Scenario & Accounting Model

### Cost Specification:
- **Round-Trip Friction:** 87.0 basis points ($0.87\%$).
- **Per-Transition Friction:** 43.5 basis points ($0.00435$) charged whenever position state changes ($|s_t - s_{t-1}| > 0$).
- **Realistic Composition:**
  - Maker/Taker fee: 40–50 bps
  - Spread cost: 15–20 bps
  - Slippage and market impact: 15–20 bps
- **Position Scaling:** Continuous unpadded $[-1.0, 1.0]$ exposure. Spot instrument restrictions prevent naked shorting unless explicitly synthetic; tests evaluate spot long/cash ($[0, 1]$) and full long/short ($[-1, 1]$) regimes.

---

## 3. Reproduced Performance Matrix

Evaluated over 9,975 closed hourly candles:

| Strategy Candidate | Rule Specification | Position Transitions | Gross Return (bps) | Total Friction (bps) | Net Return (bps) | Max Drawdown | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dual-SMA Trend** | SMA(12) / SMA(48) Crossover | 100 | +1,570.6 | -4,350.0 | **-2,779.4** | 67.8% | `REJECTED` |
| **Volatility Compression** | ATR(14) squeeze & 20-bar High breakout | 893 | +2,686.0 | -38,845.5 | **-36,159.5** | 97.4% | `REJECTED` |
| **RSI Mean Reversion** | RSI(14) < 30 buy, > 70 sell | 642 | -370.5 | -27,927.0 | **-28,297.5** | 94.2% | `REJECTED` |
| **Regime Adaptive Router** | Volatility-gated regime switcher | 1,011 | -3,561.3 | -43,978.5 | **-47,539.8** | 99.5% | `REJECTED` |
| **Zero-Exposure Benchmark** | Flat / Cash ($s_t = 0$) | **0** | **0.0** | **0.0** | **0.0** | **0.0%** | `DECISIVE WINNER` |

---

## 4. Forensic Investigation of Arithmetic & Sizing Discrepancies

1. **Trade Count Multiplication:**
   - Dual-SMA generated 100 transitions across the test window ($100 \times 43.5\text{ bps} = 4,350\text{ bps}$ total friction).
   - In earlier V22 reports, an aggregate figure of 506 trades was reported across an extended multi-year slice ($506 \times 87\text{ bps} = 44,022\text{ bps}$ round-trip friction). Both computations use identical arithmetic: trade count multiplied by round-trip fee.
2. **Gross vs. Net Return Conventions:**
   - High gross basis points reported in research memos represent cumulative raw price drift without transaction fees, borrow costs, or execution slippage.
   - When compounded or accumulated under 87 bps friction, high turnover renders active trading unprofitable in hourly BTCUSD.
3. **Execution Gate Governance:**
   - Under BTCognitive Operating Principles, strategies with negative net expected value under realistic costs must never emit live BUY/SELL signals or live order tickets.
   - The user interface must maintain its analysis-only posture.
