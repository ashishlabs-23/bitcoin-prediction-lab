# BTCognitive V28 — Cost Expectancy & Risk Analysis Report

**Version:** 28.0.0  
**Status:** COMPLETED ECONOMETRIC COST ANALYSIS  
**Contract Version:** `COST_ACCOUNTING_V28`  

---

## 1. Microstructure Cost Breakdown

Backtest models that ignore friction generate fictional profits. In cryptocurrency spot and derivatives markets, execution costs consist of four distinct components:

| Friction Component | Base Scenario | Stressed Conservative Scenario | Rationale |
| :--- | :--- | :--- | :--- |
| **Exchange Taker Fee (Entry)** | 40.0 bps (0.40%) | 60.0 bps (0.60%) | Retail/Pro spot taker fee tier |
| **Exchange Taker Fee (Exit)** | 40.0 bps (0.40%) | 60.0 bps (0.60%) | Emergency market stop execution |
| **Bid-Ask Half-Spread** | 1.5 bps (0.015%) | 3.0 bps (0.030%) | Observed top-of-book spread |
| **Execution Slippage** | 2.0 bps (0.020%) | 7.5 bps (0.075%) | Adverse fill on market order impact |
| **Total Round-Trip Friction** | **87.0 bps (0.87%)** | **130.5 bps (1.305%)** | Total unavoidable cost |

---

## 2. Mathematical Conversion: Basis Points to R-Multiples

The critical insight of V28 is that transaction friction is not a constant deduction in R-space; it varies inversely with market volatility:

Let:
- $P_{\text{entry}}$ be the fill price.
- $\sigma$ be trailing realized volatility.
- $k_{\text{SL}}$ be the stop multiple.
- $F$ be the round-trip friction rate ($F = 0.0087$ for 87 bps).

Then:
$$\text{Risk Unit (1R in USD)} = P_{\text{entry}} \times k_{\text{SL}} \sigma$$
$$\text{Friction (in USD)} = P_{\text{entry}} \times F$$
$$\text{Friction in R-Multiples} = \frac{\text{Friction USD}}{\text{Risk Unit USD}} = \frac{F}{k_{\text{SL}} \sigma}$$

### Volatility-Friction Sensitivity Table ($k_{\text{SL}} = 1.0$, $F = 87$ bps):
| Trailing Volatility ($\sigma$) | Stop Distance (USD @ $80k) | Round-Trip Cost (USD) | Friction in R | Required Win Rate for Breakeven ($k_{\text{TP}}=1.5$) |
| :--- | :--- | :--- | :--- | :--- |
| **0.50% (Low Vol Compression)** | $400.00 | $696.00 | **1.740 R** | **109.6% (Mathematically Infeasible)** |
| **0.80% (Current Market State)** | $640.00 | $696.00 | **1.088 R** | **83.5% (Aspirational / Unachievable)** |
| **1.00% (Normal Range)** | $800.00 | $696.00 | **0.870 R** | **74.8%** |
| **1.50% (Active Expansion)** | $1,200.00 | $696.00 | **0.580 R** | **63.2%** |
| **2.50% (High Vol Breakdown)** | $2,000.00 | $696.00 | **0.348 R** | **53.9%** |

### Proof of Cost Erasure:
When Bitcoin enters volatility compression ($\sigma \le 0.8\%$), round-trip friction exceeds $1.0R$. Under these conditions, a trade that stops out loses $-2.088R$, while a trade that hits its $1.5\sigma$ target only gains $+0.412R$. The required breakeven win rate exceeds $83\%$. Because real BTC directional hit rates rarely exceed $55\%-65\%$, **the edge is completely erased by market friction**.

---

## 3. Net Expectancy Formula & Gating Logic

The expected net return $\mathbb{E}[R_{\text{net}}]$ is computed for every setup:
$$\mathbb{E}[R_{\text{net}}] = p_{\text{TP}} \left(\frac{k_{\text{TP}}}{k_{\text{SL}}}\right) - p_{\text{SL}} (1.0) + p_{\text{timeout}} (-0.10) - \left(\frac{F}{k_{\text{SL}} \sigma}\right)$$

The decision gate enforces:
$$\text{Action} = \begin{cases}
\text{ACCEPTED\_RESEARCH\_CANDIDATE} & \text{if } \mathbb{E}[R_{\text{net}}] > 0 \text{ AND } p_{\text{TP}} \ge \theta_{\text{selective}} \\
\text{ABSTAIN} & \text{otherwise}
\end{cases}$$

At current market levels ($\sigma \approx 0.00837$, $k_{\text{TP}}=1.5, k_{\text{SL}}=1.0$):
$$\begin{aligned}
\mathbb{E}[R_{\text{gross}}] &= (0.592 \times 1.5) - (0.328 \times 1.0) - (0.08 \times 0.10) = +0.5520 R \\
\text{Friction}_R &= 1.0877 R \\
\mathbb{E}[R_{\text{net}}] &= +0.5520 - 1.0877 = \mathbf{-0.5357 R} \implies \text{ABSTAIN}
\end{aligned}$$
