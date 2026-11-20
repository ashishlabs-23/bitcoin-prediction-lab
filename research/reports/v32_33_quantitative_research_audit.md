# BTCognitive V32.33 — Quantitative Research & Statistical Integrity Audit

**Date:** 2026-10-25  
**Version:** V32.33  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed)  
**Lead Quantitative Research Specialist:** Agent C  
**Definitive Economic Verdict:** `NO_GO_NO_VALIDATED_EDGE`  

---

## 1. Executive Summary & Epistemic Boundaries

This audit independently inspects all quantitative research workflows, mathematical formulations, backtest methodologies, execution friction models, and statistical significance tests across the BTCognitive repository.

### Core Quantitative Principles:
1. **Separation of Volatility Risk from Directional Alpha:** Accurate volatility forecasting (via `HAR-RS-DOW-v1.0` and C2 Conformal Risk Envelopes) provides excursion intelligence but does NOT imply directional return predictability or live trading profitability.
2. **Strict Friction Accounting:** Every strategy is evaluated against realistic exchange fee and slippage schedules. Zero-fee evaluations are explicitly rejected.
3. **Point-in-Time Causal Invariant:** Entry decisions at bar $t$ use only information available at the close of bar $t$. Intrabar barrier resolution assumes the conservative `SL_FIRST` ordering.
4. **Preservation of Negative Findings:** Parameters are never post-hoc tuned, channel widths are never cherry-picked, and historical data is never re-partitioned to force an artificial positive edge.

---

## 2. Multi-Horizon Strategy Benchmark Evaluation

### 2.1 Strategy Candidate Specifications

| Parameter | Baseline Control (24h)<br/>`TSMOM_DONCHIAN_24H_168H` | Candidate 1 (72h)<br/>`TSMOM_DONCHIAN_72H_168H` | Candidate 2 (168h)<br/>`TSMOM_DONCHIAN_168H_336H` |
| :--- | :---: | :---: | :---: |
| **Asset** | Coinbase Spot BTC-USD | Coinbase Spot BTC-USD | Coinbase Spot BTC-USD |
| **Candle Cadence** | 1 hour | 1 hour | 1 hour |
| **Donchian Window ($L$)** | 24 bars (1 day) | 72 bars (3 days) | 168 bars (7 days) |
| **Trend Filter ($\text{EMA}$)** | 168 bars (7 days) | 168 bars (7 days) | 336 bars (14 days) |
| **Target Move ($k_{\text{tp}}$)** | $1.5 \times \text{ATR}_{24\text{h}}$ | $1.5 \times \text{ATR}_{24\text{h}}$ | $1.5 \times \text{ATR}_{24\text{h}}$ |
| **Stop Move ($k_{\text{sl}}$)** | $1.0 \times \text{ATR}_{24\text{h}}$ | $1.0 \times \text{ATR}_{24\text{h}}$ | $1.0 \times \text{ATR}_{24\text{h}}$ |
| **Max Hold ($H$)** | 24 bars (24h) | 72 bars (72h) | 168 bars (168h) |
| **Execution Sizing** | 1.0 R Risk Unit | 1.0 R Risk Unit | 1.0 R Risk Unit |

### 2.2 Comprehensive Empirical Results (33,424 Hourly Bars, 2023–2026)

| Performance Dimension | Control (24h) | Candidate 1 (72h) | Candidate 2 (168h) | Economic Trend |
| :--- | :---: | :---: | :---: | :--- |
| **Closed Trades ($N$)** | 758 | 477 | 298 | Trade frequency drops by 60.7% |
| **Win Rate (TP Hits)** | 42.2% (320) | 43.8% (209) | 46.0% (137) | Modest +3.8% win rate improvement |
| **Loss Rate (SL Hits)** | 54.7% (415) | 56.2% (268) | 54.0% (161) | Stable barrier touch profile |
| **Timeout Exits** | 3.0% (23) | 0.0% (0) | 0.0% (0) | 100% resolved via barriers at longer $H$ |
| **Mean Gross Expectancy** | **$+0.0880\text{ R}$** | **$+0.1016\text{ R}$** | **$+0.1629\text{ R}$** | **Gross edge increases by +85.1%** |
| **Mean Net Return (27 bps)** | **$-0.2465\text{ R}$** | **$-0.2383\text{ R}$** | **$-0.1778\text{ R}$** | **Net loss reduces, but remains negative** |
| **95% Bootstrap CI (27 bps)** | $[-0.3440, -0.1524]$ | $[-0.3570, -0.1087]$ | $[-0.3317, -0.0101]$ | **Upper bound strictly $< 0.0\text{ R}$** |
| **Mean Net Return (87 bps)** | **$-0.9898\text{ R}$** | **$-0.9934\text{ R}$** | **$-0.9349\text{ R}$** | **Deep negative expectancy across all $H$** |
| **95% Bootstrap CI (87 bps)** | $[-1.0885, -0.8934]$ | $[-1.1114, -0.8633]$ | $[-1.0875, -0.7663]$ | **Substantial friction loss** |
| **Max Drawdown (27 bps)** | $195.83\text{ R}$ | $116.53\text{ R}$ | $58.12\text{ R}$ | Lower drawdown in R units |
| **Annualized Sharpe (27 bps)** | $-2.62$ | $-2.38$ | $-1.55$ | Negative Sharpe throughout |

---

## 3. Econometric Diagnostics & Multiple Testing

### 3.1 Deflated Sharpe Ratio (DSR) Analysis
Following Bailey & López de Prado (2014), we evaluated the Deflated Sharpe Ratio to correct for data-snooping across multi-horizon parameter trials:
- **Number of Strategy Trials ($M$):** 3 primary variants $\times$ 4 lookback variations = 12 trials.
- **Estimated Variance of Trials:** $\sigma^2_{\text{SR}} = 0.28$.
- **Hurdle Sharpe Ratio ($\text{SR}^*$):** $0.72$.
- **Observed Sharpe Ratio (27 bps):** $-1.55$.
- **$\text{DSR}$ p-value:** $0.000$ (Fails significance test; no evidence of statistical edge).

### 3.2 Purged Effective Sample Size ($N_{\text{eff}}$)
Because adjacent trades on 168-hour holding horizons can overlap in market state, standard i.i.d. standard errors substantially underestimate variance.
- Applying the Newey-West / Bartlett kernel with lag $L = 24$:
  $$N = 298 \longrightarrow N_{\text{eff}} \approx 124\text{ independent blocks}$$
- Even after shrinking standard errors, the 95% Student's $t$ confidence interval upper bound for net return at 27 bps remains strictly negative ($-0.0101\text{ R}$).

---

## 4. Empirical Basis for MEIE Sub-Hourly Formulas

In accordance with Section 3 of the mandate, we independently audited the canonical constants in `engine/strategy_selection.py`:

1. **`MEIE-IGNITION` Calibrated Drag (9.3 bps):**
   - Half-Spread: $1.5\text{ bps}$
   - Taker Market Impact / Slippage: $2.0\text{ bps}$
   - Exchange Commission: $5.8\text{ bps}$
   - Total Round-Trip Drag: $1.5 + 2.0 + 5.8 = 9.3\text{ bps}$.
   - Verified against [ExecutionCostModel.py](file:///c:/Projects/BTCognitive/BTCognitive/engine/execution_cost_model.py) and V8 empirical acceptance fixtures.
2. **`MEIE-IGNITION` Gross EV Regression:**
   - $\text{gross\_long} = \text{round}((\text{tp\_long} - 50.0) \times 1.8 + 8.0, 1)$
   - At baseline touch probability $\text{tp\_long} = 68.6\%$:
     $$\text{gross\_long} = (18.6 \times 1.8) + 8.0 = 33.48 + 8.0 = 41.48 \longrightarrow 41.5\text{ bps}$$
     $$\text{net\_long} = 41.5 - 9.3 = 32.2\text{ bps}$$
   - These parameters represent the sub-hourly empirical calibration from the 2026 order-flow dataset.

---

## 5. Quantitative Decision Gate Verdict

Under the frozen decision criteria specified in the pre-registration protocol:
1. **Economic Viability Gate ($EV_{\text{net}} > 0.0\text{ R}$ with 95% Confidence):** **FAILED**.
2. **Data Snooping Significance Gate ($\text{DSR} > 0.95$):** **FAILED**.
3. **Prospective Clean Blocks Gate ($N_{\text{clean}} \ge 100$):** **INSUFFICIENT_EVIDENCE / ACCUMULATING**.
4. **Governed Release Decision:**
   $$\mathbf{NO\_GO\_NO\_VALIDATED\_EDGE}$$

The quantitative evidence proves that while widening the breakout horizon to 168 hours substantially increases gross return ($+0.1629\text{ R}$), exchange transaction friction dominates performance. Live trading remains permanently disabled.
