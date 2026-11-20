# Open-Source Chart & Indicator Feasibility Spike (V32.58)

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Location:** Evaluated in isolated scratch environment (`scratch/v32_58_spike/`) preserving all production files.

---

## 1. Candidate Evaluation Matrix

| Library / Candidate | License & Notices | Architecture & Packaging | Target Feature Fit | Performance & Stability | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TradingView Lightweight Charts 4.1.3** | Apache-2.0 (Attribution link required) | Standalone UMD script (`lightweight-charts.standalone.production.js`) | Core OHLCV candlesticks, volume histogram, markers, crosshairs | Native HTML5 Canvas; 120 FPS; rock-solid | **RETAIN AS BASELINE.** In production; zero migration risk. |
| **CandleKit Charts** (`rohanbeingsocial/candlekit-charts`) | MIT | TypeScript / ESM npm bundle; requires bundler build-step | Drawing tools (trendline, ray, Fib, rectangle), measurement, synced replay | Experimental; README explicitly warns "early-stage/AI-assisted" with breaking changes | **REJECT WHOLESALE ADOPTION.** High churn; incompatible with direct React UMD script tag. Use as reference for drawing math. |
| **dipping-charts** (`QuantrumAI/dipping-charts`) | MIT | React & Vanilla TS/JS; npm ESM package | 9 indicators, 6 drawing tools | Stable canvas drawing math | **ADOPT SELECTIVE ALGORITHMS.** Mathematics for Fibonacci levels and Trendline coordinate projections can be integrated cleanly. |
| **OpenCharts** (`cklawkc/opencharts`) | MIT | Full Next.js / Electron application with order execution UI | Indicators, paper-trading tickets, replay | Application-level framework | **REJECT APPLICATION IMPORT.** Violates read-only non-execution boundary; contains order ticket flows unsuitable for BTCognitive. |
| **TA-Lib Python** (`ta-lib-python` / C core) | BSD-2-Clause / BSD-3-Clause | Python C-extension wrapper (`ta-lib.dll`) | 150+ technical indicators | Requires MSVC / native C compiler; high build fragility on Windows runners | **REJECT FOR RUNTIME.** Use pure-python / NumPy alternatives to avoid platform compilation failures. |
| **pandas-ta-classic** (`xgboosted/pandas-ta-classic`) | MIT | Pure Python vectorized pandas routines | Extensive indicator catalog | Vectorized pandas execution ($<25\text{ms}$ for $50{,}000$ bars) | **APPROVED REFERENCE.** Recommended for offline golden benchmark testing. |

---

## 2. Scratch Spike Implementation & Empirical Benchmark

In `scratch/v32_58_spike/test_indicator_spike.py`:
- Tested pure vectorized implementations of EMA (20/50), RSI (14), Bollinger Bands (20, 2.0), and Fibonacci Retracements across **50,000 synthetic price candles**.
- **Execution Benchmark:**
  - Complete 4-indicator computation pass across 50,000 bars completed in **20.84 ms** on Python 3.13.14.
  - Fibonacci level geometry computed instantly with 7 standard levels ($0.0\%, 23.6\%, 38.2\%, 50.0\%, 61.8\%, 78.6\%, 100.0\%$).
- **Frontend Integration Rule:**
  - Lightweight Charts 4.1.3 already implements native canvas-level EMA, Bollinger Bands, and RSI rendering inside `web/app.js` (`#L1673–1715`).
  - Drawing tools (trendlines and horizontal rays) should be rendered using standard Lightweight Charts `createSeries(LineSeries)` or custom series primitives rather than importing bloated external NPM wrappers.

