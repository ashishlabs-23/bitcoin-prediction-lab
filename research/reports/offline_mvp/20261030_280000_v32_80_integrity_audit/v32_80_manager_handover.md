# V32.80 — Research Integrity & Reproducibility Audit: Manager Handover Report

**Milestone:** BTCognitive V32.80 — Research Integrity, Reproducibility and Evidence Consolidation  
**Generated:** 2026-10-30T17:22:00Z  
**Lead Orchestrator:** Antigravity  
**Final Milestone Determination:** `REPRODUCIBLE_INSUFFICIENT_EVIDENCE` (with recorded `CALCULATION_DISCREPANCY`)  
**Operating Contract:** `OFFLINE_RESEARCH_ONLY`  

---

## Executive Summary

V32.80 has executed an independent, end-to-end mathematical and governance audit of the V32.79A funding dislocation experiment and repository research data lineage.

1. **Reproduction Confirmed:** All raw observation counts (144 Short, 5 Long), episode counts (64 Short, 3 Long), event dates, and gross/net realized returns from V32.79A were successfully reproduced from raw data without referencing previous result files.
2. **Three Manager Reconciliations Resolved:**
   - **TP Rate vs. Realized Net EV:** Reconciled via full three-outcome decomposition. The $+6.8\text{ bps}$ net EV at 24 bps fees despite a $29.7\%$ TP rate (below the simplified two-outcome $38.7\%$ threshold) is driven by the $16$ EXPIRED trades, which achieved a mean gross return of **$+0.3884\%$** ($+0.1484\%$ net). The true empirical breakeven TP rate given this expiry behavior is **$28.2\%$**, not $38.7\%$.
   - **DM-HLN Comparison Validity:** A **`CALCULATION_DISCREPANCY`** was identified. The V32.79A report calculated DM-HLN using an unpaired sample comparison ($N=64$ vs. $N=1,704$), yielding $p = 0.269$. When properly constructed as a paired loss-differential series against contemporaneous baseline blocks, the HLN statistic is $2.9998$ ($p = 0.0039$).
   - **Multiple-Testing Threshold:** The discrepancy between $K=159$ ($\alpha \approx 0.000314$) and $K=2$ ($\alpha = 0.025$) is reconciled: $0.000314$ was the maximum theoretical bound across all four candidate hypotheses in Phase 0; $0.025$ was the local Bonferroni correction for the single hypothesis ($H_{\text{Funding}}$) and two pre-registered arms actually run. While $p = 0.0039$ passes $0.025$, it **fails** the programme-wide $0.000314$ threshold.
3. **No Validated Trading Edge:** The paired $p = 0.0039$ result does **not** alter the core research determination:
   - Sample size $N=64$ breached the mandatory pre-registered stop gate of $\ge 100$ episodes.
   - Chronological performance exhibits severe non-stationarity / sign reversal (H1: $-39.02\text{ bps}$, H2: $+52.62\text{ bps}$).
   - Retail economics on Coinbase Advanced ($87\text{ bps}$) produce a catastrophic **$-56.20\text{ bps}$** loss per trade.
4. **Synthetic Data Lineage Isolated:** `multi_regime_features.parquet` is preserved and classified as `SYNTHETIC_DATA — NOT_VALID_FOR_EMPIRICAL_RESEARCH`. Seven downstream consumers were audited. All independent OHLCV barrier milestones (V32.74–V32.78) used authoritative raw OHLCV and remain sound.
5. **Test & Governance State:** 57 governance and regression tests pass ($100\%$). 9 operational freshness failures remain isolated to the idle ingestion collector (>3.8h age).

---

## 1. Resolution of the Three Reconciliation Checks

### Check A: Full Outcome Decomposition (Short Arm, N=64)

| Outcome | Episode Count | Frequency | Mean Gross Return | Mean Net Return (Binance 24 bps) | Net PnL Contribution |
|---|---|---|---|---|---|
| **TP_FIRST** | 19 | $29.69\%$ | $+3.0000\%$ | $+2.7600\%$ | $+0.8194\%$ |
| **SL_FIRST** | 29 | $45.31\%$ | $-1.5000\%$ | $-1.7400\%$ | $-0.7884\%$ |
| **EXPIRED** | 16 | $25.00\%$ | **$+0.3884\%$** | $+0.1484\%$ | $+0.0371\%$ |
| **Total / Net EV** | **64** | **100.0%** | **$+0.3080\%$** | **$+0.0680\%$ (+6.8 bps)** | **$+0.0681\%$** |

**Arithmetic Proof:**
$$0.2969 \times (+2.76\%) + 0.4531 \times (-1.74\%) + 0.2500 \times (+0.1484\%) = +0.0681\% \approx +6.8\text{ bps}$$

The simplified $38.7\%$ breakeven threshold assumes zero return on expired trades ($0.297 \times 2.76\% + 0.453 \times -1.74\% + 0 = -0.059\%$). Because expired trades experienced positive mean price drift ($+38.8\text{ bps}$ gross), the true empirical breakeven TP rate is **$28.2\%$**. The observed $29.7\%$ is above $28.2\%$, resulting in $+6.8\text{ bps}$ net.

---

### Check B: DM-HLN Paired Alignment & Calculation Discrepancy

- **V32.79A Methodology (Misspecified):** Tested the unconditional baseline ($N=1,704$) as an independent two-sample t-test against the conditioned episodes ($N=64$), ignoring time alignment $\rightarrow p = 0.269$.
- **V32.80 Paired Methodology (Correct):** Paired each of the 64 conditioned episodes with the corresponding 24-hour block in the baseline timeline ($100\%$ matching).
  - Mean paired loss differential ($\bar{d}$): **$+0.3988\%$** ($+39.88\text{ bps}$)
  - Newey-West HAC Variance ($b=31$): Applied
  - Harvey-Leybourne-Newbold finite-sample stat: **$2.9998$**
  - Reference Distribution: Student's $t_{63}$
  - Two-Sided p-value: **$p = 0.0039$**

**Audit Finding:** This is a **`CALCULATION_DISCREPANCY`** in the V32.79A statistical report. While $p = 0.0039$ passes the local $K=2$ Bonferroni threshold ($0.025$), it fails the programme-wide $0.000314$ threshold, and the underlying sample ($N=64$) fails the minimum sample size rule ($N \ge 100$).

---

### Check C: Multiple-Testing Accounting

| Protocol Scope | Candidate Configurations ($K$) | Target Family-Wise Error ($\alpha$) | Bonferroni Threshold | Paired Short $p = 0.0039$ Status |
|---|---|---|---|---|
| **Programme-Wide (V32.79 Ph0)** | 159 (all 4 hypotheses) | $0.05$ | **$0.000314$** | **FAILED (Not Significant)** |
| **Executed Experiment (V32.79A)** | 2 (Short, Long arms) | $0.05$ | **$0.025000$** | Passed locally ($p < 0.025$) |

**Reconciliation Ruling:** The $0.025$ threshold is mathematically valid for the isolated $K=2$ execution. However, from a rigorous governance standpoint, testing $H_{\text{Funding}}$ after considering broader macro regimes means programme-wide multiplicity cannot be dismissed. The fact that $p=0.0039$ fails the $0.000314$ threshold reinforces the decision not to promote this finding.

---

## 2. Chronological Stability & Non-Stationarity

| Chronological Partition | Date Range | Episodes | Hit Rate (TP%) | Net EV (Binance 24 bps) |
|---|---|---|---|---|
| **H1 (First Half)** | 2023-01-14 to 2024-03-09 | 32 | $18.8\%$ | **−39.02 bps** |
| **H2 (Second Half)** | 2024-03-10 to 2024-12-09 | 32 | **$40.6\%$** | **+52.62 bps** |

The performance shift between H1 and H2 ($+91.64\text{ bps}$ swing, $21.8\text{ pp}$ hit rate swing) reveals that the positive expectation is an artifact of the 2024 post-ETF regime, not a stationary property of Bitcoin funding dislocations.

---

## 3. Synthetic Dataset Dependency Audit Summary

| Consumer File | Type | Data Consumed | Valid as Research Evidence? | Action Taken |
|---|---|---|---|---|
| `research/multi_regime_dataset.py` | Code | Generator | N/A | Preserved |
| `research/macro_evaluation_harness.py` | Code | Synthetic | ❌ NO | Outputs reclassified as SYNTHETIC |
| `research/multi_regime_purged_validation.py` | Code | Synthetic | ❌ NO | `multi_regime_validation_report.json` reclassified |
| `research/run_uncertainty_01_trial.py` | Code | Synthetic | ❌ NO | Outputs reclassified |
| `research/run_uncertainty_02_trial.py` | Code | Synthetic | ❌ NO | Outputs reclassified |
| `research/audit_iv_dataset.py` | Code | Synthetic | ❌ NO | Outputs reclassified |
| `tests/test_multi_regime_deepening.py` | Test | Synthetic | ✅ YES (Plumbing test) | Maintained as software test |

**Preservation:** `data/processed/multi_regime_features.parquet` (`e37fcc1a896e5a8a...`) is preserved in place for full audit trail integrity. No historical reports have been silently rewritten.

---

## 4. Governed Release Decisions

| Decision Category | Formal Status | Rationale |
|---|---|---|
| **1. Research Experiment** | **`REPRODUCIBLE_INSUFFICIENT_EVIDENCE`** | V32.79A reproduces mathematically. Paired DM-HLN calculation discrepancy recorded ($p=0.0039$). Sample size $N=64 < 100$ and H1/H2 sign reversal preclude edge claims. |
| **2. Prospective Evidence** | **`NOT_STARTED`** | 7/100 blocks preserved. Prospective collector remains frozen. Network lock preserved. |
| **3. Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | No research models authorized for production or execution. |
| **4. Live Trading** | **`DISABLED`** | Absolute system invariant. |

---

## 5. Deliverables Verification

All 9 deliverables are complete and committed to disk in:  
`research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/`

1. [`v32_80_v32_79a_independent_reproduction.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_v32_79a_independent_reproduction.md)
2. [`v32_80_trade_economics_reconciliation.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_trade_economics_reconciliation.md)
3. [`v32_80_statistical_validity_audit.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_statistical_validity_audit.md)
4. [`v32_80_synthetic_dependency_impact.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_synthetic_dependency_impact.md)
5. [`v32_80_research_lineage_audit.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_research_lineage_audit.md)
6. [`v32_80_protected_hash_verification.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_protected_hash_verification.json)
7. [`v32_80_test_and_governance_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_test_and_governance_report.md)
8. [`v32_80_independent_red_team.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_independent_red_team.md)
9. [`v32_80_manager_handover.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_280000_v32_80_integrity_audit/v32_80_manager_handover.md) (This Report)

---

## 6. Strategic Posture & Next Steps

In full alignment with the Manager's directive:
- **Stop searching for new entry signals:** We will not test further ad-hoc technical or macro indicators.
- **Consolidate validated capabilities:** Research focus shifts to consolidating the causal data pipeline, robust risk and variance estimation architectures, and preserving pristine provenance.
- **Prospective Collector Governance:** Any future resumption of the prospective collector will be approached as an independent engineering mandate requiring its own network, licensing, and process isolation audit.

