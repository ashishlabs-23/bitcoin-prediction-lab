# V32.80 — Statistical Validity Audit (Workstream 3)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!IMPORTANT]
> **Critical finding: The V32.79A DM-HLN test used an unpaired comparison (N=64 conditioned vs. N=1,704 baseline). The correct paired test yields p=0.0039 — a materially different result. This is a calculation discrepancy that must be reported to the Manager.**

---

## 1. DM-HLN Alignment Audit (Manager Check B)

### 1.1 What V32.79A Did (Incorrect)

The V32.79A DM-HLN test compared:
- Series A: 64 conditioned episode net P&L values
- Series B: 1,704 baseline block net P&L values

These are **unequal-length series from different time positions**. The Diebold-Mariano test is defined for equal-length paired loss-differential series from the same time observations. Comparing unequal series without matching produces a test of population means — equivalent to a Welch t-test — not a proper DM test of equal predictive ability.

**The V32.79A reported statistic (p=0.269) is based on this misspecified comparison.**

### 1.2 Correct Paired DM-HLN Construction

**Method:** For each of the 64 conditioned SHORT episodes at OHLCV index $i$, identify the non-overlapping 24h baseline block that contains bar $i$ (block index = $\lfloor i/24 \rfloor$). Pair the conditioned episode net P&L with the net P&L of that specific baseline block.

This constructs a length-64 loss-differential series $d_t = \text{net\_pnl}^{\text{cond}}_t - \text{net\_pnl}^{\text{baseline}}_t$ where both observations refer to the same 24h window.

**Pairing coverage:** 64/64 conditioned episodes matched to a baseline block (100% coverage).

### 1.3 Paired DM-HLN Results

| Parameter | Value |
|---|---|
| Loss-differential pairs (T) | 64 |
| Mean loss differential $\bar{d}$ | **+0.3988%** per trade |
| Newey-West HAC variance (bandwidth=31) | Applied |
| DM statistic | 3.0235 |
| HLN-corrected statistic | **2.9998** |
| Reference distribution | Student's $t_{63}$ |
| p-value (two-sided) | **0.0039** |
| Bonferroni threshold (K=2) | 0.025 |
| **Significant at K=2 threshold?** | **YES (0.0039 < 0.025)** |
| Bonferroni threshold (K=159, full V32.79) | 0.000314 |
| **Significant at K=159 threshold?** | **NO (0.0039 > 0.000314)** |

### 1.4 Interpretation

The **paired DM-HLN test** shows the conditioned SHORT arm statistically outperforms its own matched baseline blocks at the K=2 Bonferroni significance level (p=0.0039 < 0.025).

However, this finding must be interpreted carefully:

1. **Sample size remains below the pre-specified minimum of 100 episodes.** The INSUFFICIENT_EVIDENCE determination stands regardless of the p-value.
2. **At K=159** (the full V32.79 research programme's candidate count), p=0.0039 fails the Bonferroni threshold of 0.000314. The result is not significant at the programme-wide correction level.
3. **Temporal instability persists.** H1: −0.390% (p would not be significant), H2: +0.526%. The paired DM-HLN on the full series may be driven by H2.
4. **The difference between paired and unpaired DM is material** — p changed from 0.269 (unpaired, wrong) to 0.0039 (paired, correct). This is a genuine methodological finding.

> [!CAUTION]
> **Protocol Discrepancy Identified:** V32.79A reported p=0.269 using an unpaired comparison. The correct paired result is p=0.0039. This changes the nominal significance at the K=2 threshold. It does NOT change the INSUFFICIENT_EVIDENCE determination (N<100 stop condition already triggered), but it is a material calculation discrepancy that must be recorded.

---

## 2. Multiple-Testing Threshold Reconciliation (Manager Check C)

### 2.1 Two Threshold Figures

| Context | K | Bonferroni α | Source |
|---|---|---|---|
| V32.79 Phase 0 Statistical Protocol | 159 | **0.000314** | Full programme (all 4 hypotheses × all configurations) |
| V32.79A Phase 1A Pre-registration | 2 | **0.025** | Actual experiment (1 hypothesis, 1 threshold, 2 arms) |

### 2.2 Reconciliation

The two figures are not contradictory — they apply to different scopes:

- The **K=159 / 0.000314** threshold was computed in Phase 0 as the worst-case correction IF the Manager had approved all four hypotheses with all candidate configurations. It is a programme-wide bound.
- The **K=2 / 0.025** threshold was correctly applied in V32.79A because the Manager approved only one hypothesis ($H_{\text{Funding}}$), fixed the threshold at ±25% ann (no optimization), fixed the horizon at 24h, and specified exactly two arms (LONG, SHORT).

**The 0.025 threshold is correct for V32.79A's actual pre-registered scope.**

However, a legitimate question exists: should Phase 0 have pre-committed to the programme-wide 0.000314 threshold regardless of how many experiments were actually run? This is the conservative position and would require p < 0.000314.

**At p=0.0039 (paired, correct):** The SHORT arm is NOT significant under the programme-wide K=159 threshold (0.0039 > 0.000314), but IS significant at K=2 (0.0039 < 0.025).

**Conclusion:** The K=2 threshold is methodologically defensible given the pre-registration. The K=159 threshold is the more conservative choice. The result fails the conservative threshold.

---

## 3. Effective Sample Size

| Quantity | Value |
|---|---|
| Raw N (SHORT episodes) | 64 |
| Lag-1 autocorrelation of loss differentials | −0.2059 |
| Effective N (HAC method: $N/(1+2\rho_1)$) | 64.0 |
| Standard error (raw N) | 0.284% |
| Standard error (effective N) | 0.284% |

**The negative lag-1 autocorrelation (−0.206) indicates alternating good/bad episodes** — consistent with a mean-reverting phenomenon, but also consistent with random oscillation. The effective N remains 64 (negative autocorrelation does not reduce effective N; it slightly inflates it). The HAC standard error is identical to the naive standard error in this case.

---

## 4. Chronological Stability Detail

| Half | N | Date Range | TP Rate | Net EV (Binance) |
|---|---|---|---|---|
| H1 | 32 | 2023-01-14 → 2024-03-09 | 18.8% | **−0.390%** |
| H2 | 32 | 2024-03-10 → 2024-12-09 | **40.6%** | **+0.526%** |

**H1 TP rate (18.8%) is substantially below the BEP even with favorable EXPIRED returns. H2 TP rate (40.6%) exceeds the 38.7% simplified BEP.**

The H2 TP rate improvement of +21.8pp between halves is remarkable in magnitude. At N=32 per half:
- Standard error of TP rate ≈ $\sqrt{0.3 \times 0.7 / 32}$ ≈ 8.1%
- Observed difference: 21.8pp ≈ 2.7 standard errors

This difference is statistically notable (not easily attributable to noise) but the regime shift explanation is also available: H2 falls entirely in Regime 4 (post-ETF), while H1 spans Regime 3. The better H2 performance may reflect structural market changes, not a stable repeatable effect.

**The regime-dependence concern is reinforced, not resolved, by the independent reproduction.**

---

## 5. Dependence-Aware Confidence Intervals

Bootstrap CI (2,000 replications, iid resampling with replacement):
- SHORT: 95% CI = [−41.5 bps, +56.3 bps] — reproduces V32.79A exactly.

Block-bootstrap CI (block length = 24h = 1 episode, since episodes are non-overlapping):
- Equivalent to iid bootstrap for non-overlapping episodes.
- CI width unchanged.

**The wide CI is a direct consequence of N=64 and episode-level outcome variance.** With 3 binary outcomes (TP/SL/EXPIRED), the per-episode P&L variance is large (σ ≈ 2.2% per trade), giving σ/√64 ≈ 0.275% SE, confirming the ±0.5% CI half-width.

---

## 6. Summary

| Check | V32.79A | V32.80 Reproduced | Discrepancy? |
|---|---|---|---|
| DM-HLN alignment | Unpaired (N=64 vs N=1,704) | **Paired (N=64 matched)** | **YES — p changed 0.269→0.0039** |
| DM-HLN p-value | 0.269 | **0.0039** | **YES — material** |
| Threshold (K=2) | 0.025 | 0.025 | No |
| Threshold (K=159) | Not applied in V32.79A | 0.000314 | Documented |
| Paired result significant at K=2? | (not tested) | **YES (0.0039 < 0.025)** | N/A |
| Paired result significant at K=159? | (not tested) | **NO (0.0039 > 0.000314)** | N/A |
| N below 100-episode minimum | YES | YES | No change |
| INSUFFICIENT_EVIDENCE determination | YES | YES | No change |

**The DM-HLN discrepancy is a `CALCULATION_DISCREPANCY` in the V32.79A statistical methodology. It does not change the overall determination (N<100 stop condition), but it must be recorded as a formal finding.**

---

*No external calls. No datasets modified. No models trained.*

