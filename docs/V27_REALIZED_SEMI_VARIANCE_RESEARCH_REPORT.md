# V27 Hourly-Sampled Realized Semi-Variance Research Report

**Feature Class:** Volatility Asymmetry & Downside Risk Intelligence  
**Feature Status:** `HOURLY_SAMPLED_RESEARCH_FEATURE`  
**Module Implementation:** [engine/realized_semi_variance.py](file:///c:/Projects/BTCognitive/BTCognitive/engine/realized_semi_variance.py)  
**Verification Test:** [tests/test_v27_metric_repair_and_features.py](file:///c:/Projects/BTCognitive/BTCognitive/tests/test_v27_metric_repair_and_features.py)  

---

## 1. Scientific Background & Mathematical Formulation

Following Barndorff-Nielsen, Kinnebrock, and Shephard (2010) and Patton & Sheppard (2015), total realized variance can be decomposed into positive (upside) and negative (downside) semi-variances. In Bitcoin markets, downside return variance often carries distinct risk-premium and volatility-feedback dynamics compared to upside price momentum.

### 1.1 Definitions
Given closed hourly candles with log returns:
$$r_t = \ln\left(\frac{C_t}{C_{t-1}}\right)$$

Across a rolling window of $W$ closed hourly bars ($W=24$ for daily, $W=168$ for weekly):
1. **Total Realized Variance ($RV$):**
   $$RV_{t}(W) = \sum_{i=0}^{W-1} r_{t-i}^2 \times \frac{8760}{W}$$
2. **Upside Realized Semi-Variance ($RS^+$):**
   $$RS^+_{t}(W) = \sum_{i=0}^{W-1} r_{t-i}^2 \cdot \mathbb{I}(r_{t-i} > 0) \times \frac{8760}{W}$$
3. **Downside Realized Semi-Variance ($RS^-$):**
   $$RS^-_{t}(W) = \sum_{i=0}^{W-1} r_{t-i}^2 \cdot \mathbb{I}(r_{t-i} < 0) \times \frac{8760}{W}$$
4. **Asymmetry Ratio ($A$):**
   $$A_t(W) = \frac{RS^+_t(W) - RS^-_t(W)}{RS^+_t(W) + RS^-_t(W) + \epsilon}$$
   where $\epsilon = 10^{-12}$ prevents division-by-zero during flat regimes.

### 1.2 Exact Algebraic Identity
By construction, because every return is either positive, negative, or zero:
$$r_t^2 = r_t^2 \cdot \mathbb{I}(r_t > 0) + r_t^2 \cdot \mathbb{I}(r_t < 0)$$
Therefore:
$$RV_t(W) \equiv RS^+_t(W) + RS^-_t(W)$$
This identity is enforced and verified to machine precision ($\Delta < 10^{-12}$) in unit tests.

---

## 2. Research Guardrails & Limitations

1. **Hourly Sampling Limitation:**
   - This feature is an **hourly-sampled proxy** constructed from 1-hour closed candles.
   - It must **NEVER** be conflated with high-frequency 5-minute bipower variation ($BV$) or jump-diffusion decomposition ($J_t = \max(0, RV_t - BV_t)$). True continuous/jump decomposition requires sub-hourly tick/trade sampling.
2. **Model Authorization Invariant:**
   - Realized semi-variance components are deployed under the explicit status **`HOURLY_SAMPLED_RESEARCH_FEATURE`**.
   - They do **NOT** modify or retrain the authorized production volatility model `HAR-RS-DOW-v1.0`. Any model incorporation requires pre-registered ablation over untouched data.
3. **Execution Guardrail:**
   - Non-execution analysis only (`EXECUTION: DISABLED`).
