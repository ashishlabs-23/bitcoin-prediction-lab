# V32.80 — Synthetic Dataset Dependency Impact (Workstream 4)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Synthetic Dataset Classification

**File:** `data/processed/multi_regime_features.parquet`  
**SHA-256:** `e37fcc1a896e5a8a...` (recorded in `v32_79A_protected_hash_verification.json`)  
**Official classification:** `SYNTHETIC_DATA — NOT_VALID_FOR_EMPIRICAL_RESEARCH`  
**Action:** Preserved. Not deleted. Not modified. Hash recorded for auditability.

**Source code:** `research/multi_regime_dataset.py`  
The file is generated from `np.random.normal()` draws seeded with `np.random.seed(42)`. It does not use real BTC price data.

---

## 2. Seven Downstream Consumers — Full Impact Audit

### Consumer 1: `research/multi_regime_dataset.py`
| Property | Assessment |
|---|---|
| Role | **Generator** — creates the synthetic file |
| Reads synthetic data? | No (creates it) |
| Research output? | None — code only |
| Conclusions to reclassify? | None |
| **Impact** | ✅ None — generator code only |

---

### Consumer 2: `research/macro_evaluation_harness.py`
| Property | Assessment |
|---|---|
| Role | Evaluation harness — reads `multi_regime_features.parquet` at line 118 |
| Reads synthetic data? | **YES** |
| Used only for pipeline plumbing? | **NO** — computes evaluation metrics |
| Research result produced? | Validation experiment reports (e.g., `multi_regime_validation_report.json`) |
| Reports used as evidence? | Only in the V32.78/V32.79 regime-conditioned research direction |
| **Impact** | ⚠️ Any empirical claim from this harness is INVALID. Results were already classified as DEGRADED_BELOW_TARGET (near-zero ICs). The finding that ICs are near zero is consistent with synthetic data and is not informative about real BTC. |

---

### Consumer 3: `research/multi_regime_purged_validation.py`
| Property | Assessment |
|---|---|
| Role | Cross-validation harness — purged k-fold validation on regime features |
| Reads synthetic data? | **YES** |
| Research result produced? | Validation metrics in `experiments/results/multi_regime_validation_report.json` |
| Reports used as evidence in? | Referenced in V32.78 regime-conditioned research handover |
| **Impact** | ⚠️ The validation report (`multi_regime_validation_report.json`) is based on synthetic data. The reported Spearman ICs (near zero) are expected for i.i.d. simulated returns and do NOT constitute evidence about real BTC predictability. The report itself should be annotated as SYNTHETIC_DATA_DERIVED. |

---

### Consumer 4: `research/run_uncertainty_01_trial.py`
| Property | Assessment |
|---|---|
| Role | Uncertainty quantification trial |
| Reads synthetic data? | **YES** |
| Research result produced? | Uncertainty trial outputs |
| Identified as evidence in prior reports? | Not directly cited in Manager-approved milestone reports |
| **Impact** | ⚠️ Trial outputs are invalid as empirical evidence. Not cited in validated milestones — low risk to research record integrity. |

---

### Consumer 5: `research/run_uncertainty_02_trial.py`
| Property | Assessment |
|---|---|
| Role | Uncertainty quantification trial (variant) |
| Reads synthetic data? | **YES** |
| Research result produced? | Uncertainty trial outputs |
| Identified as evidence in prior reports? | Not directly cited in Manager-approved milestone reports |
| **Impact** | ⚠️ Same as Consumer 4. Low risk. |

---

### Consumer 6: `research/audit_iv_dataset.py`
| Property | Assessment |
|---|---|
| Role | IV dataset audit — references multi_regime_features path |
| Reads synthetic data? | **YES** (reads the parquet) |
| Research result produced? | IV audit outputs |
| Identified as evidence in prior reports? | Not cited in Manager-approved milestone reports |
| **Impact** | ⚠️ Any IV audit results derived from synthetic regime features are invalid. Not cited in validated milestones — low risk. |

---

### Consumer 7: `tests/test_multi_regime_deepening.py`
| Property | Assessment |
|---|---|
| Role | Software test — validates pipeline shape, columns, dtypes |
| Reads synthetic data? | **YES** |
| Makes research claims? | **NO** — validates software contracts only |
| Impact on research record? | None |
| **Impact** | ✅ **UNAFFECTED** — this is a software pipeline test, not an empirical claim. Continues to be valid as a regression test that the pipeline runs correctly. |

---

## 3. Impact on Milestone Research Records

### V32.78 — Asymmetric Regime-Conditioned Entry Research

V32.78 referenced regime labels and the multi-regime validation report. Assessment:

| V32.78 element | Data source | Impact |
|---|---|---|
| Entry strategy evaluation | `ohlcv_checkpoint_42233_bars.parquet` (REAL) | ✅ Unaffected — uses real price data |
| Cost economics | Fixed parameters | ✅ Unaffected |
| Regime conditioning (the factor) | Date-range boundaries applied to real OHLCV | ✅ Unaffected — `assign_macro_regime()` is a date-range function, not derived from synthetic features |
| Multi-regime validation IC claims | `multi_regime_features.parquet` (SYNTHETIC) | ⚠️ ICs near-zero are synthetic-data artifacts, not real BTC evidence |
| Overall `BLOCKED_BY_COST_ECONOMICS` determination | Based on real-price barriers | ✅ Unaffected — cost calculation correct |

**V32.78 determination (`BLOCKED_BY_COST_ECONOMICS`) is based on real OHLCV data and real cost arithmetic. It is NOT invalidated by the synthetic data finding.**

### V32.74–V32.77 — Barrier and Volatility Research

All barrier backtests (TP/SL simulations) used the frozen OHLCV checkpoint directly. No dependency on `multi_regime_features.parquet`. ✅ **Unaffected.**

---

## 4. Downstream Impact Summary

| Consumer | Category | Empirical Claim Risk | Action Required |
|---|---|---|---|
| `multi_regime_dataset.py` | Generator | None | None |
| `macro_evaluation_harness.py` | Empirical consumer | HIGH — outputs invalid | Annotate outputs as SYNTHETIC_DATA_DERIVED |
| `multi_regime_purged_validation.py` | Empirical consumer | HIGH — ICs invalid | Annotate `multi_regime_validation_report.json` |
| `run_uncertainty_01_trial.py` | Empirical consumer | LOW — not cited | Note in lineage audit |
| `run_uncertainty_02_trial.py` | Empirical consumer | LOW — not cited | Note in lineage audit |
| `audit_iv_dataset.py` | Empirical consumer | LOW — not cited | Note in lineage audit |
| `test_multi_regime_deepening.py` | Software test | NONE | No action |

**No milestone determination (V32.74–V32.79A) is invalidated by this finding.** The synthetic dataset was used for regime-feature validation, not for barrier backtest P&L calculations. The cost-economics determinations stand.

---

*No files modified. No datasets deleted. All hashes preserved.*

