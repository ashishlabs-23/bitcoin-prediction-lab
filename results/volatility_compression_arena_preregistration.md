# Pre-Registration: Non-Directional Volatility-Compression Arena Strategy (STRAT-VOLCOMP-01)
**Document Status**: LOCKED & IMMUTABLE PRIOR TO ARENA INFERENCE  
**Target File**: `results/volatility_compression_arena_preregistration.md`  
**Execution Timestamp**: 2026-08-24T19:48:00Z  
**Research Protocol**: Rigorous Dual-Window Simulated Arena Admission Trial  
**Audit Ledger**: SHA-256 State-Chained Virtual Ledger (`market_memory.db`)  

---

## 1. Context & Architectural Rationale

### A. The Zero Automatic Retraining Invariant
Automated model retraining on recent live predictions is permanently prohibited in this system for three structural reasons:
1. **Silent Regime Overfitting**: A rolling auto-retraining model mistakes transient low-volatility regimes for persistent structural state changes, creating catastrophic failure modes during sudden liquidation cascades (e.g., August 5, 2024).
2. **Calibration Drift Masking**: Automated retraining absorbs systemic calibration errors into updated weights, silently concealing predictive degradation rather than triggering alerts.
3. **Loss of Fixed Baseline**: Multi-hypothesis corrections (FDR, FWER) and frozen effective sample size ($N_{\text{eff}}$) benchmarks require an immutable, stationary reference model.

### B. Core Arena Premise: Honest Non-Directional Strategy
Given that directional classifiers in this repository remain unadmitted (AUC $\approx 0.50$), the Arena does **not** permit unvalidated directional betting. Instead, this first pre-registered strategy operates strictly on the **conformal excursion envelope** ($\hat{y}_{\text{MFE}}, \hat{y}_{\text{MAE}}$)—exploiting the empirically validated property of volatility compression and expansion without taking directional risk.

---

## 2. Primary Hypothesis & Statistical Formulation

> **Hypothesis $H_1$ (Volatility-Compression Economic Viability)**:  
> When the 24-hour conformal excursion envelope width $W_t = \hat{y}_{\text{MFE}, 24h}^{\text{P90}}(t) + \hat{y}_{\text{MAE}, 24h}^{\text{P90}}(t)$ compresses below its rolling 168-hour 10th percentile ($\text{CompressionRatio}_t \le 0.10$), simulated delta-neutral / symmetric range-boundary positions capture mean-reverting volatility expansion with **statistically significant positive net economic yield ($\text{Sharpe}_{\text{net}} \ge 1.0, p < 0.05$) after full taker fees, square-root volume-scaled modeled slippage, and 150ms simulated execution latency**.
>
> **Null Hypothesis $H_0$ (Execution Drag & Spread Decay)**:  
> Any gross volatility-expansion edge is entirely consumed by market microstructure frictions (taker fees, modeled depth/volume slippage, execution latency, and spread decay), resulting in $\text{Sharpe}_{\text{net}} \le 0$ or non-significant returns under stationary block-bootstrap testing ($B=24\text{h}$).

---

## 3. Exact Strategy & Feature Specifications

### A. Predictor Signal & Provenance Invariant
* **Signal Variable**: $W_t = \hat{y}_{\text{MFE}, 24h}^{\text{P90}}(t) + \hat{y}_{\text{MAE}, 24h}^{\text{P90}}(t)$
* **Data Source Invariant**: Computed strictly from the full multi-regime dataset (`data/processed/multi_regime_features.parquet`, $N = 20,978$ rows across 2022–2026) or raw un-truncated OHLCV series (`data/raw/ohlcv.parquet`, $N = 40,455$ rows). **Strictly prohibited from reading the 28-day truncated `features.parquet` ($N=672$).**
* **Rolling Percentile Context**:
  $$\text{CompressionPercentile}_{168h}(W_t) = \text{PercentileRank}_{\tau \in (t-168h, t]}(W_t)$$
* **Entry Trigger**:
  $$\text{Trigger}(t) = \begin{cases} 
  1 & \text{if } \text{CompressionPercentile}_{168h}(W_t) \le 0.10 \text{ (extreme compression)} \\
  0 & \text{otherwise}
  \end{cases}$$
* **Causal Invariant**: Strict point-in-time calculation. Envelope width and 168-hour rolling percentile are computed using only data available at close of bar $t$.

### B. Position Construction & Payoff Model
* **Structure**: Symmetric delta-neutral simulated synthetic straddle / range boundary position.
* **Holding Horizon**: Fixed 24 hours ($H = 24$ bars) or dynamic exit upon band expansion to median ($\text{CompressionPercentile}_{168h}(W_{t+k}) \ge 0.50$).
* **Gross P&L Calculation**:
  $$\text{PnL}_{\text{gross}}(t, t+h) = \frac{|P_{t+h} - P_t|}{P_t} - \text{CarryCost}$$

---

## 4. Execution Simulation & Slippage Methodology

### A. Backtest Windows (2023 & 2024): Modeled Microstructure Approximation
Because historical archives prior to live deployment do not contain recorded top-20 Level-2 order book snapshots, historical backtest slippage is implemented via an **econometric square-root volume-impact model** (Almgren-Chriss / Kyle proxy) and explicitly labeled as a **modeled approximation**:
$$\text{Slippage}_{\text{hist}}(Q, t) = 2.0 \times \text{Spread}_{\text{base}} + \kappa \cdot \sigma_{24h}(t) \cdot \sqrt{\frac{Q}{V_{1h}(t)}}$$
* $\text{Spread}_{\text{base}} = 1.0\text{ bps}$ ($0.01\%$) baseline bid-ask spread.
* $\sigma_{24h}(t) = \text{realized volatility over trailing 24h}$.
* $Q = \$1,000.00$ simulated position size.
* $V_{1h}(t) = \text{hourly traded volume (USD)}$ from authenticated OHLCV.
* $\kappa = 0.10$ market impact parameter.

### B. Live / Forward Arena Streaming: Real Depth Snapshots
In live/forward execution, slippage transitions to **empirical top-20 order book depth** from `engine/data_engine.py`:
$$\text{Slippage}_{\text{live}}(Q, t) = 2.0 \times \text{Spread}_{t} + \kappa \left(\frac{Q}{\text{Depth}_{20}(t)}\right)^{\alpha}$$

### C. Universal Execution Frictions Table

| Friction Parameter | Specification | Value / Modeling Rule |
| :--- | :--- | :--- |
| **Fee Structure** | Full Taker Fee (No maker-rebate optimism) | **5.0 bps ($0.05\%$) per leg** ($10.0$ bps round-trip) |
| **Execution Latency** | Simulated API & matching delay | **150 ms** forward price-fill displacement |
| **Historical Slippage** | Square-root volume impact approximation | $\text{Slippage}_{\text{hist}}(Q, t)$ as defined in 4.A |
| **Live Slippage** | Empirical top-20 order book depth | Depth snapshot curve as defined in 4.B |
| **Partial Fill Rule** | Liquidity ceiling per bar | Max position fill $\le 5\%$ of bar traded volume / top-20 depth |
| **Capital Base** | Realistically scaled virtual balance | **$\$1,000.00$** (1.0x sizing, fractionally scaled) |

### D. Structural Slippage Regime Invariant & Downstream Reporting Rule
> ⚠️ **STANDING REPORTING CAVEAT (Slippage Regime Divergence)**:  
> Historical backtest Sharpe and net return metrics are computed under an **econometric square-root volume slippage approximation** ($S_{\text{hist}}$), whereas live forward Arena execution will operate under **empirical top-20 limit order book depth fills** ($S_{\text{live}}$). Because these two mechanisms possess distinct functional sensitivities to volatility, book density, and execution cadence, **historical backtest Sharpe and live Arena Sharpe are not directly comparable without re-validation**. Any report citing Gate 1's economic performance must explicitly state this caveat:  
> *"Historical Sharpe was computed under a modeled slippage approximation; live Sharpe will use empirical order-book fills and is not directly comparable without re-validation."*

---

## 5. Dual-Window Evaluation Design & $N_{\text{eff}}$ Baseline Reference

### A. Dual Evaluation Windows

| Dimension | Window 1: High-Vol Shock & Jump Window | Window 2: Low-Vol Tranquil Control Window |
| :--- | :--- | :--- |
| **Date Range** | **2024-06-01 00:00 to 2024-08-15 23:59 UTC** | **2023-06-01 00:00 to 2023-08-15 23:59 UTC** |
| **Duration** | 76 Days (1,824 Hourly Bars) | 76 Days (1,824 Hourly Bars) |
| **Regime Dynamics** | Pre-shock tension, violent liquidation cascades (Aug 5) | Range-bound compression, low realized volatility |
| **Window Sub-Test $N_{\text{eff}}$** | $N_{\text{eff}} \approx 248.83$ (Newey-West Bartlett adjustment) | $N_{\text{eff}} \approx 267.87$ (Newey-West Bartlett adjustment) |

### B. Baseline $N_{\text{eff}}$ Reference Resolution
* **Full Multi-Regime Canonical Baseline**: Grounded against `experiments/results/baseline_neff_manifest.json` and `data/processed/multi_regime_features.parquet` ($N = 20,978$ non-truncated observations, $N_{\text{eff}} = \mathbf{2,036.56}$, $\text{SE} = 0.0222$, $\text{MDE Gate} = \mathbf{+0.0444}$).
* **Stale Baseline Rejection**: Rejects the previous synthetic baseline ($N_{\text{eff}}=601.54$), the single-slice $N=276$ ($N_{\text{eff}}=15$), and the 28-day truncated $N=649$ ($N_{\text{eff}}=107.97$). All previous artifacts are formally marked SUPERSEDED.

---

## 6. Pre-Registered Decision Rules & Admission Gates

For strategy `STRAT-VOLCOMP-01` to achieve formal promotion status in the Arena, all four gates must be satisfied simultaneously:

### Gate 1: Statistically Significant Net Economic Edge
* **Net Sharpe Ratio**: $\text{Sharpe}_{\text{net}} \ge 1.00$ on combined out-of-sample data.
* **Block Bootstrap Significance**: $p < 0.05$ with lower $95\%$ bootstrap confidence interval of net P&L $> 0$ (Stationary Block Bootstrap with block length $B = 24$ hours, $10,000$ resamples).

### Gate 2: Maximum Drawdown & Ruin Probability
* **Max Drawdown**: $\text{MDD} \le 15.0\%$ across both evaluation windows.
* **Calmar Ratio**: $\text{Annualized Return} / \text{MDD} \ge 1.50$.

### Gate 3: Live Transfer Degradation Haircut Test
* **Required Stress Haircut**: Reported results must maintain $\text{PnL}_{\text{net}} > 0$ after applying an explicit **$30\%$ external transfer penalty** (simulating unmodeled latency jitter, extreme adverse selection, and exchange downtime).

### Gate 4: Multi-Testing Discipline (FWER / FDR Family Tracking)
* This strategy counts as **Trial $K = 1,229$** in the repository's cumulative multi-testing ledger.
* Significance values must clear Benjamini-Hochberg False Discovery Rate (FDR) control at $q = 0.05$ across all concurrent Arena strategy candidates.

---

## 7. Audit & Provenance Protocol

* **Ledger Destination**: `results/arena_strategy_ledger.json` and SQLite table `arena_virtual_trades` in `market_memory.db`.
* **State Hash**: Every simulated fill generates a SHA-256 digest chaining the preceding state hash, execution timestamp, fill price, estimated slippage, fee deduction, and resulting virtual portfolio balance.
* **Modification Policy**: Zero hyperparameter tweaking (e.g. altering $\gamma_{\text{compress}} = 0.10$ or lookback $168\text{h}$) is permitted post-execution. Any variation constitutes a distinct trial in the $K$-family.
