# V32.80A — Synthetic Dataset Lineage & Dependency Matrix

**Milestone:** BTCognitive V32.80A — Audit Closure Addendum  
**Generated:** 2026-10-30T17:35:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report delivers the exhaustive repository-wide dependency matrix for `data/processed/multi_regime_features.parquet` (SHA-256: `e37fcc1a896e5a8a...`), resolving **Section 3 & 4** of the Manager's ruling.

### Key Audit Conclusions:
1. **Repository Inventory:** A comprehensive search across all repository directories located **exactly two code files**, **two JSON manifests**, and **one historical markdown pre-registration** that reference this file, plus the recent audit reports that documented it.
2. **Prior Barrier Milestone Lineage (V32.74, V32.77, V32.78):**
   - **V32.74 (Conditional Entry Filters):** Evaluated strictly on `data/raw/ohlcv_backfilled.parquet` ($42,177$ bars). Zero synthetic features used.
   - **V32.77 (Volatility-Adaptive ATR Barriers):** Evaluated strictly on `data/raw/ohlcv_checkpoint_42233_bars.parquet` ($42,233$ bars). Zero synthetic features used.
   - **V32.78 (Asymmetric Regime-Conditioned Entry):** Evaluated strictly on `data/raw/ohlcv_checkpoint_42233_bars.parquet` ($42,233$ bars). Regime boundaries were calendar timestamp intervals applied to real OHLCV. Zero synthetic features used in barrier backtesting.
3. **Artifacts Contaminated by Synthetic Data:**
   - `experiments/results/baseline_neff_manifest.json`
   - `results/baseline_neff_manifest.json`
   - `results/volatility_compression_arena_preregistration.md`
   - `experiments/results/multi_regime_validation_report.json`
   These four artifacts are formally designated as **`SYNTHETIC_DATA_DERIVED — NOT_VALID_AS_EMPIRICAL_EVIDENCE`**.

---

## 2. Complete Dependency Matrix

| File Path | Type | Role | Reads Synthetic Data? | Impact on Strategy Research Conclusions | Status / Action |
|---|---|---|---|---|---|
| `research/multi_regime_dataset.py` | Python Script | **Generator** (creates parquet via `np.random.normal`, seed 42) | Generates | N/A (Code only) | Preserved with clear synthetic header |
| `research/macro_evaluation_harness.py` | Python Script | Evaluation tool (line 118) | **YES** | ❌ Produces non-empirical validation metrics | Annotated as synthetic evaluation harness |
| `experiments/results/baseline_neff_manifest.json` | JSON Artifact | Metadata record referencing dataset | Contains path | ❌ Metric values reflect synthetic baseline | **RECLASSIFIED: SYNTHETIC_DATA_DERIVED** |
| `results/baseline_neff_manifest.json` | JSON Artifact | Duplicate manifest | Contains path | ❌ Metric values reflect synthetic baseline | **RECLASSIFIED: SYNTHETIC_DATA_DERIVED** |
| `results/volatility_compression_arena_preregistration.md` | Markdown | Early research design notes | References path | ❌ Pre-registration based on synthetic fixture | **RECLASSIFIED: SYNTHETIC_DATA_DERIVED** |
| `experiments/results/multi_regime_validation_report.json` | JSON Artifact | Cross-validation report (near-zero ICs) | Contains outputs | ❌ ICs reflect i.i.d. random simulation | **RECLASSIFIED: SYNTHETIC_DATA_DERIVED** |
| `tests/test_multi_regime_deepening.py` | Test Suite | Pipeline software test | **YES** | ✅ Valid software test (schema, shape, types) | Retained as plumbing regression test |

---

## 3. Disentangling V32.78 Research Lineage

In V32.78 (*Asymmetric Regime-Conditioned Entry Research*), the Manager asked whether its findings were contaminated.

### Forensic Breakdown of V32.78:
1. **Barrier Backtests & Strategy P&L:**
   - Script: Run against `data/raw/ohlcv_checkpoint_42233_bars.parquet`.
   - Sample: 10,521 out-of-sample hourly bars (bars 31,632 to 42,153).
   - Execution Costs: Binance 24 bps, Coinbase 87 bps.
   - Result: All tested barrier configurations failed economic hurdles ($-0.39\text{ bps}$ net under retail fees).
   - **Lineage Verdict:** **100% AUTHENTIC REAL OHLCV DATA**. This determination stands entirely independent of the synthetic dataset.
2. **Regime Segmentation Labels in V32.78:**
   - The regime labels (e.g., `REGIME_4_SPOT_ETF_INSTITUTIONAL`) were constructed using `assign_macro_regime()`:
     ```python
     conditions = [ts < "2021-11-10", (ts >= "2021-11-10") & (ts < "2023-01-01"), ...]
     ```
   - These are pure calendar date-slicing functions applied directly to the real OHLCV timestamps. They did not import or consume rows from `multi_regime_features.parquet`.
3. **Contaminated Supporting Narrative:**
   - In V32.78's background discussion, the near-zero Spearman ICs from `multi_regime_validation_report.json` were cited as evidence that macro features had no predictive power.
   - **Correction:** Those near-zero ICs were artifacts of random normal draws. They are dismissed. However, because V32.78 rejected the strategy anyway (`BLOCKED_BY_COST_ECONOMICS`), the dismissal of the synthetic ICs does not overturn or weaken the negative economic conclusion.

---

## 4. Preservation & Quarantining Status

- `data/processed/multi_regime_features.parquet` has SHA-256: `e37fcc1a896e5a8ab8667a73f84860b299c084136e054cfd34208d132644e5bc`.
- The file is preserved in place for cryptographic auditability.
- No files were deleted or rewritten.
- All four contaminated manifests/reports are formally indexed as synthetic.

