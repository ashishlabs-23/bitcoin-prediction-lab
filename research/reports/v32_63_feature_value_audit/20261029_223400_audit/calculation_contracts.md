# BTCognitive V32.63 — Mathematical Calculation Contracts & Specifications

**Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_63_feature_value_audit/20261029_223400_audit/`  
**Scope:** Canonical mathematical formulas, warm-up policies, boundary conditions, edge cases, and causal assertions for all core indicators and metrics.

---

## 1. Exponential Moving Average (EMA-N)

### Mathematical Definition
For a price series $P = \{p_0, p_1, \dots, p_T\}$ and period $N$:
$$\alpha = \frac{2}{N + 1}$$
$$EMA_0 = p_0$$
$$EMA_t = \alpha \cdot p_t + (1 - \alpha) \cdot EMA_{t-1} \quad \text{for } t \ge 1$$

### Operational Rules in BTCognitive
- **Implemented in:** `engine/feature_pipeline.py:186-198` and `engine/regime_strategy_tournament.py:77-82`.
- **Backend Implementation:** `pd.Series(arr).ewm(span=N, adjust=False).mean()`.
- **Warm-Up Policy:**
  - For $t < N$, the EMA is computed recursively from the available history ($EMA_0 = p_0$).
  - For regime classification, a minimum warm-up window of $T \ge 168$ bars is strictly required. If $T < 168$, classification fails closed with `UNKNOWN_OR_INVALID`.
- **Known-Answer Validation Fixture:**
  - Input: $P = [10.0, 11.0, 12.0, 13.0, 14.0]$, $N = 3 \implies \alpha = 2 / (3 + 1) = 0.5$.
  - $t=0: EMA_0 = 10.0$
  - $t=1: EMA_1 = 0.5 \cdot 11.0 + 0.5 \cdot 10.0 = 10.5$
  - $t=2: EMA_2 = 0.5 \cdot 12.0 + 0.5 \cdot 10.5 = 11.25$
  - $t=3: EMA_3 = 0.5 \cdot 13.0 + 0.5 \cdot 11.25 = 12.125$
  - $t=4: EMA_4 = 0.5 \cdot 14.0 + 0.5 \cdot 12.125 = 13.0625$

---

## 2. Wilder Average True Range (ATR-14)

### Mathematical Definition
For bar $t$ with High $H_t$, Low $L_t$, and Close $C_t$:
$$TR_t = \max\left(H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}|\right)$$
Wilder's modified smoothing ($\alpha_{\text{Wilder}} = \frac{1}{N} = \frac{1}{14}$):
$$ATR_0 = TR_0$$
$$ATR_t = \frac{1}{14} TR_t + \left(1 - \frac{1}{14}\right) ATR_{t-1} = \frac{13 \cdot ATR_{t-1} + TR_t}{14}$$

### Operational Rules in BTCognitive
- **Implemented in:** `engine/regime_strategy_tournament.py:84-99` and `engine/feature_pipeline.py:234-244`.
- **Edge Conditions:**
  - If $T < 2$: returns $H_0 - L_0$.
  - Floor Guard: $ATR = \max(1.0, ATR)$ to prevent zero-division in volatility scaling.

---

## 3. Wilder Directional Movement & ADX (ADX-14)

### Mathematical Definition
For bar $t$:
$$\Delta H_t = H_t - H_{t-1}, \quad \Delta L_t = L_{t-1} - L_t$$
$$+DM_t = \begin{cases} \Delta H_t & \text{if } \Delta H_t > \Delta L_t \text{ and } \Delta H_t > 0 \\ 0 & \text{otherwise} \end{cases}$$
$$-DM_t = \begin{cases} \Delta L_t & \text{if } \Delta L_t > \Delta H_t \text{ and } \Delta L_t > 0 \\ 0 & \text{otherwise} \end{cases}$$
Smoothed with Wilder's technique over period $N = 14$:
$$+DI_t = 100 \cdot \frac{\text{Wilder}(+DM_t, 14)}{\text{Wilder}(TR_t, 14)}$$
$$-DI_t = 100 \cdot \frac{\text{Wilder}(-DM_t, 14)}{\text{Wilder}(TR_t, 14)}$$
Directional Index:
$$DX_t = 100 \cdot \frac{|+DI_t - -DI_t|}{+DI_t + -DI_t + \epsilon}$$
Average Directional Index:
$$ADX_t = \text{Wilder}(DX_t, 14)$$

### Operational Discrepancy & Reconciliation Note
- **`engine/regime_strategy_tournament.py:101-131`:** Correctly implements the second smoothing stage:
  `adx_series = pd.Series(dx).ewm(span=14, adjust=False).mean()`. This returns canonical ADX.
- **`engine/strategy_signal_engine.py:90-134`:** Computes rolling sums of $+DM$, $-DM$, $TR$ over $N$ bars and returns $DX$ directly without the final Wilder smoothing stage (labeled "simplified ADX").
- **Resolution:** The regime classifier strictly uses `regime_strategy_tournament.py`, which is verified and compliant with standard ADX definitions. The difference in `strategy_signal_engine.py` is documented as a known variance.

---

## 4. Donchian 24-Hour Channels (Causal Breakout Bounds)

### Mathematical Definition
For bar $t$ and lookback $N = 24$:
$$Upper_t = \max\left(H_{t-24}, H_{t-23}, \dots, H_{t-1}\right) = \max_{1 \le i \le 24} H_{t-i}$$
$$Lower_t = \min\left(L_{t-24}, L_{t-23}, \dots, L_{t-1}\right) = \min_{1 \le i \le 24} L_{t-i}$$
$$Mid_t = \frac{Upper_t + Lower_t}{2}$$

### Strict Causal Contract
- **Causal Invariant:** $High_t$ and $Low_t$ are **NEVER** included in the calculation of $Upper_t$ and $Lower_t$.
- Code enforces `high.shift(1).rolling(24).max()` and `low.shift(1).rolling(24).min()`.
- **Breakout Condition:**
  - Long Breakout: Emitted at close of bar $t$ if $Close_t > Upper_t$.
  - Execution: Scheduled strictly for Open of bar $t+1$.

---

## 5. 7/10 Preliminary Strategy Screening Screen & Wilson CI

### Preliminary Screening Gate
A candidate strategy is eligible for shortlisting only if it satisfies the empirical preliminary screen:
$$\text{Eligible} \iff \text{Recent } 10 \text{ attempts contain } \ge 7 \text{ SUCCESS\_TP\_HIT outcomes}$$
- Failures: `FAILURE_SL_HIT`, `EXITED_ANOMALY`, and `TIMEOUT_NO_TP` count as non-successes.
- History Requirement: Exactly 10 completed, comparable attempts required. If $N < 10$, screen emits `INSUFFICIENT_EVIDENCE`.

### Analytical Wilson Score 95% Confidence Interval
For $k$ successes in $n$ trials with $z = 1.95996$:
$$\hat{p} = \frac{k}{n}$$
$$\text{Center} = \frac{\hat{p} + \frac{z^2}{2n}}{1 + \frac{z^2}{n}}$$
$$\text{Spread} = \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}$$
$$\text{CI}_{95\%} = \left[\max(0.0, \, \text{Center} - \text{Spread}), \,\, \min(1.0, \, \text{Center} + \text{Spread})\right]$$

### Exact Known Answers
- $k = 7, n = 10 \implies \hat{p} = 0.70 \implies \mathbf{[0.3968, \, 0.8922]}$ (approx 39.7% to 89.2%).
- $k = 8, n = 10 \implies \hat{p} = 0.80 \implies \mathbf{[0.4902, \, 0.9433]}$ (approx 49.0% to 94.3%).
- $k = 6, n = 10 \implies \hat{p} = 0.60 \implies \mathbf{[0.3127, \, 0.8318]}$ (Fails screen).

> [!IMPORTANT]
> **Epistemic Disclosure:** Passing 7/10 is merely an eligibility filter to reject decaying rules. Because the 95% Wilson confidence interval spans down to 39.7%, a 7/10 record **DOES NOT** prove a future 70% win rate or an unconditional trading edge.

---

## 6. Execution Cost & Net-EV Drag Calculations

### Volatility Risk Unit ($1R$)
$$1R_{\text{usd}} = \text{SpotPrice} \cdot k_{sl} \cdot \sigma_{\text{Parkinson}}(24h)$$
where $k_{sl} = 1.0$ and $\sigma_{\text{Parkinson}} = \sqrt{\frac{1}{4 \ln 2 \cdot 24} \sum_{i=0}^{23} \ln\left(\frac{H_i}{L_i}\right)^2}$.

### Roundtrip Friction in Units of $R$
$$\text{Friction}_R = \frac{\text{RoundtripCostBps}}{10,000 \cdot k_{sl} \cdot \sigma_{t0}}$$

### Break-Even Win Rate Formula
For reward multiple $RR = \frac{k_{tp}}{k_{sl}}$:
$$\mathbb{E}[\text{Net } R] = p \cdot RR - (1 - p) \cdot 1.0 - \text{Friction}_R = 0$$
$$p \cdot (RR + 1) = 1.0 + \text{Friction}_R$$
$$\mathbf{p_{\text{breakeven}} = \frac{1.0 + \text{Friction}_R}{RR + 1.0}}$$

### Concrete Benchmark Tiers ($k_{tp} = 1.5, k_{sl} = 1.0, RR = 1.5 \implies RR + 1 = 2.5, \sigma = 0.00837$):
1. **Zero Friction:**
   $$\text{Friction}_R = 0 \implies p_{be} = \frac{1.0}{2.5} = \mathbf{40.00\%}$$
2. **Coinbase India / International Retail (27 bps):**
   $$\text{Friction}_R = \frac{27}{10,000 \cdot 0.00837} = 0.3226R \implies p_{be} = \frac{1.3226}{2.5} = \mathbf{52.90\%}$$
3. **Coinbase Advanced Tier 1 (87 bps):**
   $$\text{Friction}_R = \frac{87}{10,000 \cdot 0.00837} = 1.0394R \implies p_{be} = \frac{2.0394}{2.5} = \mathbf{81.58\%}$$
4. **Coinbase US Retail (187 bps):**
   $$\text{Friction}_R = \frac{187}{10,000 \cdot 0.00837} = 2.2342R \implies p_{be} = \frac{3.2342}{2.5} = \mathbf{129.37\%} \text{ (Unprofitable)}$$

---

## 7. HAR-RS-DOW Variance Forecast Causal Anchoring

### Target Definition ($168\text{h}$ Realized Variance Proxy)
$$\text{rv7d\_var\_ann}(t) = \frac{8,760}{168} \sum_{i=1}^{168} r_{t+i}^2$$

### Causal Ordering Invariant
$$t_{\text{feature}} \le t_{\text{issue}} < t_{\text{maturity}} = t_{\text{issue}} + 168\text{h}$$
- At $t_{\text{issue}}$, regressors use $r_t, r_{t-1}, \dots, r_{t-720}$.
- The forward target $r_{t+1}, \dots, r_{t+168}$ is strictly unknown and cannot be evaluated until maturity.
- No lookahead leakage is tolerated.

