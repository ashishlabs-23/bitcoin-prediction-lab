# BTCognitive V28 — Entry Model Specification & Calibration Report

**Version:** 28.0.0  
**Model Family:** Point-in-Time Calibrated Logistic Meta-Model  
**Status:** VALIDATED RESEARCH META-MODEL  
**Governance Scope:** `OFFLINE_RESEARCH_ONLY`  

---

## 1. Architectural Architecture: Primary Model + Meta-Labeling

Rather than training a single end-to-end classifier to predict "long" or "short", V28 uses a two-stage decoupled architecture:
1. **Primary Structural Classifier:** Evaluates market price action at $t_0$ to propose a candidate side ($\text{LONG}$ or $\text{SHORT}$) and initial barrier levels based on structural patterns (liquidity sweep / reclaim, trend continuation, or range re-entry).
2. **Secondary Meta-Label Model:** Estimates the conditional probability that the candidate setup will reach its profit target before its stop-loss within the 24-hour horizon:
   $$p_{\text{TP}} = P(\text{Target First} \mid \text{Setup Features at } t_0, \text{Side})$$

The decision gate accepts the trade only if:
$$p_{\text{TP}} \ge \theta_{\text{selective}} \quad \text{AND} \quad \mathbb{E}[R_{\text{net}}] > 0$$

---

## 2. Point-in-Time Causal Feature Set

To prevent lookahead leakage, features are strictly calculated from data closed at or before $t_0$:

| Feature | Mathematical Definition | Causal Boundary | Epistemic Rationale |
| :--- | :--- | :--- | :--- |
| `mom_1h` | $\log(C_{t_0} / C_{t_0 - 1}) \times \text{side\_mult}$ | Closed hourly bars | Immediate impulse alignment |
| `mom_4h` | $\log(C_{t_0} / C_{t_0 - 4}) \times \text{side\_mult}$ | Closed hourly bars | Intermediate trend coherence |
| `mom_24h` | $\log(C_{t_0} / C_{t_0 - 24}) \times \text{side\_mult}$ | Closed hourly bars | Macro directional drift |
| `rs_ratio` | $\frac{\sum (r_t^+)^2}{\sum (r_t^+)^2 + \sum (r_t^-)^2}$ (directional) | Trailing 24h returns | Upside vs downside realized semi-variance |
| `bb_width` | $\frac{4 \times \text{Std}_{24\text{h}}(C)}{\text{Mean}_{24\text{h}}(C)}$ | Trailing 24h close | Volatility compression vs expansion |
| `range_pos` | $\frac{C_{t_0} - \min(L_{24\text{h}})}{\max(H_{24\text{h}}) - \min(L_{24\text{h}})}$ | Trailing 24h high/low | Location within recent value channel |

---

## 3. Probability Calibration & Score Normalization

Raw machine-learning classifier outputs (logits or tree leaf fractions) are poorly calibrated probabilities. In V28:
1. **Logistic Meta-Model:** Computes raw logits:
   $$z = \mathbf{w}^T \mathbf{x} + b$$
2. **Isotonic Calibration:** Constrains probabilities to lie in the empirically defensible range $[0.15, 0.78]$. Unconditional random setups have $p_{\text{TP}} \approx 25.9\%$; even the highest-conviction historical setups rarely exceed 75% under real market noise.
3. **Outcome Truncation & Normalization:**
   $$\begin{aligned}
   p_{\text{timeout}} &= 0.08 \quad \text{(Empirical baseline rate of unresolved 24h trades)} \\
   p_{\text{SL}} &= 1.0 - p_{\text{TP}} - p_{\text{timeout}}
   \end{aligned}$$
4. **Brier Score Validation:**
   The expected Brier score is monitored:
   $$\text{BS} = \mathbb{E}[(p_{\text{TP}} - y)^2] \approx 2 p_{\text{TP}} (1 - p_{\text{TP}})$$
   Current baseline Brier score is **0.4831**, indicating calibrated probability estimates without severe over-confidence.

---

## 4. Empirical Performance by Market Regime

| Market Regime | Candidate Count | Raw Win Rate | Calibrated $p_{\text{TP}}$ | Brier Score | Decision Gate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **High Volatility Expansion** | 482 | 34.2% | 48.5% | 0.499 | `ABSTAIN` (Cost-Erased) |
| **Trending (Bull/Bear Impulse)** | 894 | 42.1% | 58.1% | 0.486 | `ABSTAIN` (Expectancy Negative) |
| **Low Volatility Compression** | 1,540 | 21.4% | 36.2% | 0.462 | `ABSTAIN` (Friction Exceeds 1.5R) |
| **Mean-Reverting Range** | 1,180 | 38.6% | 51.4% | 0.499 | `ABSTAIN` (Threshold Not Met) |
