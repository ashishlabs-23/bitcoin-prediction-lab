# Pre-Registration: Temporal Calibration Audit of Frozen U4 (UNCERTAINTY-02)
**Document Status**: LOCKED PRIOR TO INFERENCE & CONTROLLER TUNING  
**Target File**: `results/uncertainty_02_preregistration.md`  
**Execution Timestamp**: 2026-08-24T20:35:00Z  
**Research Protocol**: Systematic Diagnosis of 2.16% Coverage Deficit in Frozen U4  
**Fixed Point Forecast Baseline**: **HAR-RS-DOW** ($\text{QLIKE} = 0.19300$, Strictly Frozen)  
**Fixed Uncertainty Architecture**: **U4 Adaptive Asymmetric Scale-Aware Conformal**  

---

## 1. Research Question & Rationale

> **Core Scientific Question**:  
> In `UNCERTAINTY-01`, U4 demonstrated superior Winkler sharpness (`0.56691`) and near-perfect tail symmetry ($6.15\%$ upper vs $6.01\%$ lower breaches), but systematically under-covered the nominal $90.0\%$ target at **$87.84\%$** (a $-2.16\%$ deficit).  
> **Can U4 achieve nominal $90.0\% \pm 1.0\%$ empirical coverage without sacrificing its sharpness ($\overline{\text{Winkler}} \le 0.58$) or inflating into uninformative wide intervals, through temporal-dependence-aware calibration?**

---

## 2. Frozen Invariants (No Ad-Hoc Tuning)

1. **Point Forecast Frozen**: HAR-RS-DOW point forecasts $\hat{v}_t$ are strictly immutable.
2. **Conformity Score Formulation Frozen**:
   $$s_t^+ = \max\left(0, \frac{y_t - \hat{v}_t}{\hat{\sigma}_{\epsilon, t}}\right), \quad s_t^- = \max\left(0, \frac{\hat{v}_t - y_t}{\hat{\sigma}_{\epsilon, t}}\right)$$
3. **No Artificial Alpha Modification**: The nominal input remains $\alpha = 0.10$ (90% target).

---

## 3. Pre-Registered Calibration Candidate Ladder (C0 $\rightarrow$ C4)

| Candidate ID | Calibration Mechanism | Hypothesis Tested |
| :--- | :--- | :--- |
| **C0 (Baseline)** | Current U4 ($W_{\text{cal}}=1000\text{h}$, fixed finite-sample quantile) | Baseline reproduction ($87.84\%$ coverage, Winkler `0.56691`) |
| **C1 (Long Memory)** | Expanding / Long Memory Calibration ($W_{\text{cal}}=2000\text{h}$) | Tests if under-coverage stems from small-sample calibration noise |
| **C2 (Block-Adjusted)** | Block-resampled empirical quantile accounting for $L=168\text{h}$ target overlap | Tests if under-coverage stems from multi-step autocorrelation bias |
| **C3 (Pre-Registered ACI Controller)** | Explicit Adaptive Conformal Inference controller with frozen step size $\eta = 0.003$ | Tests if online sequential feedback eliminates the coverage lag |
| **C4 (Regime-Conditional)** | Partitioned conformal calibration pools conditioned on macro regime | Tests if regime transitions cause structural calibration loss |

---

## 4. Multi-Dimensional Evaluation & Stress-Testing Framework

### A. Primary Performance Metrics:
1. **Nominal Coverage Alignment**: Target $1 - \alpha = 90.0\%$ (Admission Gate: **$89.0\% \le \hat{C} \le 91.0\%$**).
2. **Mean Interval Width**: $\overline{W} = \frac{1}{N} \sum (U_t - L_t)$.
3. **Winkler Score (Sharpness)**: Target $\overline{\text{Winkler}} \le 0.580$.
4. **Tail Breach Balance**: $|\alpha_{\text{upper}} - \alpha_{\text{lower}}| \le 0.015$ ($1.5\%$ maximum tail asymmetry).

### B. Mandatory Stress-Testing Panels:
1. **Regime-Conditional Coverage**: Verified across Regimes 2, 3, and 4 (Every regime $\ge 85.0\%$).
2. **Realized Volatility Quintile Coverage**:
   Evaluates coverage conditional on realized variance magnitude:
   * Quintile 1 (Bottom 20% Calm Volatility)
   * Quintile 2 (20%–40%)
   * Quintile 3 (40%–60%)
   * Quintile 4 (60%–80%)
   * Quintile 5 (Top 20% Extreme Volatility Spikes)
   * **Mandatory Gate**: Top Quintile Upper Breach Rate $\le 8.0\%$ (must contain tail bursts).

---

## 5. Execution Sequence

```
Step 0: Lock UNCERTAINTY-02 Pre-Registration [LOCKED]
  │
Step 1: Ingest frozen out-of-sample HAR-RS-DOW point forecasts and residuals (N=32,974)
  │
Step 2: Execute calibration candidates C0, C1, C2, C3, and C4 sequentially
  │
Step 3: Compute Overall Coverage, Mean Width, Winkler Score, and Breach Symmetry
  │
Step 4: Execute Extreme Volatility Quintile Stress-Testing Audit
  │
Step 5: Output Full Comparative Table & Produce results/uncertainty_02_final_report.md
```
