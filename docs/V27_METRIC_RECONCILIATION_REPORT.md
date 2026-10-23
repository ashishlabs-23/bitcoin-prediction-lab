# V27 Metric Reconciliation & Scientific Integrity Report

**Release Version:** 27.0.0  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  
**Audited Artifacts:**
- `experiments/results/v27_canonical_strategy_equity_manifest.json`
- `experiments/results/v27_canonical_forecast_manifest.json`
- `experiments/results/v27_canonical_forecast_origins_summary.json`

---

## 1. Strategy Transition Accounting & Turnover Reconciliation

### 1.1 The Source of the Discrepancy
In the V26 run diagnostic snippet, an engineer executed:
```python
pos_changes = np.abs(np.diff(positions, prepend=positions[0]))
```
For positions taking values in $\{-1, +1\}$, setting `prepend=positions[0]` made the first transition `abs(pos[0] - pos[0]) = 0`. This implicitly assumed the portfolio was already holding an active position prior to the start of the out-of-sample evaluation period ($t=0$). Consequently, that calculation reported 99 events, 99 reversals, and 198 turnover units.

However, the canonical strategy table reported:
- **Signal Events:** 100
- **Reversals:** 99
- **Initial Entries:** 1
- **Turnover Units:** 199.0
- **Completed Round Trips:** 99.5

### 1.2 Mathematical Resolution & Formal Contract
Under sound econometrics and portfolio theory, an evaluation period must assume an initial portfolio state of **FLAT (0 exposure in cash)** at $t=0$:
$$s_{-1} = 0$$
When the strategy enters its first active position ($s_0 = +1$ or $s_0 = -1$), it incurs an entry cost equal to 1 turnover unit:
$$\Delta s_0 = |s_0 - 0| = 1.0\text{ unit}$$
All subsequent position flips between $+1$ and $-1$ are full reversals incurring 2 turnover units:
$$\Delta s_t = |s_t - s_{t-1}| = 2.0\text{ units}$$
Therefore:
$$\mathrm{Turnover\ Units} = \sum_{t=0}^{T-1} |s_t - s_{t-1}| = 1 \times 1.0 + 99 \times 2.0 = 199.0\text{ units}$$
$$\mathrm{Completed\ Round\ Trips} = \frac{199.0}{2} = 99.5\text{ round trips}$$
Total signal events $= 1\text{ (initial entry)} + 99\text{ (reversals)} = 100\text{ events}$.

This behavior is now permanently protected by automated test `test_v27_dual_ema_100_events_reconciliation`.

---

## 2. Return Units: Log Returns vs Compounded Simple Equity

### 2.1 The Critical Defect
Prior reports calculated gross and net returns by summing log returns:
$$\text{Gross Log Return} = \sum_{t=0}^{T-1} s_t \ln\left(\frac{C_{t+1}}{C_t}\right) \times 10,000\text{ bps}$$
$$\text{Net Log Return} = \text{Gross Log Return} - (\text{Turnover Units} \times \text{Half-Fee bps})$$
The report then divided these log-basis-point sums by 100 and labeled them as ordinary percentage returns (e.g., Dual-EMA: $-7,085.9\text{ bps} \to -70.9\%$; Regime Router: $-52,107.3\text{ bps} \to -521.1\%$).

This is mathematically false:
1. Log returns are continuously compounded. Summed log returns cannot be converted to simple percentage returns by dividing by 100.
2. A loss of $-521.1\%$ simple return is physically impossible for an unleveraged cash portfolio, where maximum loss is bounded at $-100\%$.
3. When continuous log return is $r = -0.70859$ ($-7,085.9$ bps), the equivalent simple return is:
   $$R_{\text{simple}} = \exp(r) - 1 = \exp(-0.70859) - 1 = -50.77\%$$
4. When continuous log return is $r = -5.21073$ ($-52,107.3$ bps), the equivalent simple return is:
   $$R_{\text{simple}} = \exp(-5.21073) - 1 = -99.45\%$$

### 2.2 Formal Equity Compounding Model
In V27, we implemented a discrete-time compounded equity simulation where transaction friction is deducted from capital at each rebalancing event:
$$E_0 = 1.0$$
$$E_{t,\text{post-fee}} = E_{t-1} \times (1 - \Delta s_t \cdot f_{\text{half}})$$
$$E_t = E_{t,\text{post-fee}} \times \left(1 + s_t \cdot \frac{C_{t+1} - C_t}{C_t}\right)$$
where $f_{\text{half}} = \frac{\text{cost\_bps}}{20,000}$.

### 2.3 Reconciled Performance Matrix (9,975 Hours Out-of-Sample)

| Strategy ID | Events (Reversals/1-Step) | Turnover Units | Additive Net Log Return (bps) | Implied Simple Return from Log $\exp(r)-1$ | Compounded Simple Equity Return (%) | Compounded Max Drawdown (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NO_TRADE_BENCHMARK** | 0 (0 / 0) | 0.0 | **+0.0 bps** | **+0.00%** | **+0.00%** | **0.00%** |
| **TS_MOM_DUAL_EMA** | 100 (99 / 1) | 199.0 | **-7,085.9 bps** | **-50.77%** | **-56.97%** | **68.76%** |
| **TRUE_DUAL_SMA** | 105 (104 / 1) | 209.0 | **-9,530.2 bps** | **-61.44%** | **-66.38%** | **73.21%** |
| **SHORT_HORIZON_MR** | 642 (0 / 642) | 642.0 | **-28,297.5 bps** | **-94.10%** | **-94.22%** | **94.22%** |
| **VOL_COMPRESSION** | 893 (3 / 890) | 896.0 | **-36,290.0 bps** | **-97.35%** | **-97.40%** | **97.40%** |
| **REGIME_ROUTER** | 1,011 (105 / 906) | 1,116.0 | **-52,107.3 bps** | **-99.45%** | **-99.50%** | **99.51%** |

---

## 3. Forecast Canonical Sample Boundary Contract

### 3.1 Resolving the Boundary Defect
In V26, the evaluation script used:
```python
origins = list(range(20000, 35000 - h, h))
```
Because Python's `range(start, stop)` is exclusive of `stop`, setting `stop = 35000 - h` stopped at index $35000 - h - 1$. This inadvertently omitted the final origin $35000 - h$, whose target is exactly closed candle index $35,000$. Consequently, sample sizes were reduced by 1 ($14,999, 3,749, 624$).

### 3.2 Canonical Boundary Contract
The evaluation window $[20000, 35000]$ includes target index 35,000.
The canonical range formula is:
```python
origins = list(range(20000, 35000 - h + 1, h))
```
This restores the exact canonical sample sizes:
- **1-Hour Horizon ($h=1$):** $N = 15,000$ (Origins: 20,000 to 34,999; Targets: 20,001 to 35,000).
- **4-Hour Horizon ($h=4$):** $N = 3,750$ (Origins: 20,000 to 34,996 step 4; Targets: 20,004 to 35,000).
- **24-Hour Horizon ($h=24$):** $N = 625$ (Origins: 20,000 to 34,976 step 24; Targets: 20,024 to 35,000).

The point-by-point errors, timestamps, and Newey–West HAC statistics are preserved in `experiments/results/v27_canonical_forecast_manifest.json` and `v27_canonical_forecast_origins_summary.json`.

---

## 4. Conformal Coverage Reclassification

In V26, the 24-hour future price forecast reported an empirical interval coverage of 81.25%.
- **Governance Finding:** The nominal coverage specified in the product requirement was $90\%$ ($\alpha = 0.10$).
- **Scientific Ruling:** An empirical coverage of $81.25\%$ against a $90.0\%$ target constitutes **undercoverage ($-8.75\%$ coverage gap)**. Calling this a calibration pass was scientifically invalid.
- **V27 Remediation:** The price forecast interval status is formally updated to **`DEGRADED / UNDERCOVERAGE`**. It will not be authorized for production risk envelopes until conformal calibration evidence on untouched data meets the $90\%$ hurdle.
