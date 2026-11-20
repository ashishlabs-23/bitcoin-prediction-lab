# V32.79A — Manager Handover Report
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Generated:** 2026-10-30T17:00 UTC  
**Lead Orchestrator:** Antigravity  
**Authorization:** Manager — APPROVED, EXPLORATORY ONLY  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## Executive Summary

The V32.79A funding dislocation experiment has been executed to completion under full pre-registration compliance. Both arms triggered the pre-specified stop condition.

**Final determination: `INSUFFICIENT_EVIDENCE`**

The ±25% annualized BTCUSDT funding threshold, while conceptually sound, produces too few qualifying events in the 4.67-year dataset to support statistically reliable inference. The experiment does not establish, and does not refute, the existence of a funding-dislocation edge in BTCUSD.

---

## 1. Environment Verification

| Property | Value |
|---|---|
| Branch | `main` |
| HEAD commit | `25d483f` (unchanged) |
| External API calls | **ZERO** |
| Protected datasets modified | **NONE** |
| Protected hashes | OHLCV checkpoints: **MATCH** |
| Analysis ABSTAIN gate | **UNTOUCHED** |
| Prospective evidence | **7/100 blocks — UNCHANGED** |
| Prospective runner | **NOT RESTARTED** |
| Model training | **NONE** |
| Strategy promotion | **NONE** |

---

## 2. Pre-Registration Compliance

All 12 pre-registered elements were applied without deviation. The stop condition was triggered at the event-count check, before any acceptance/rejection decisions could be made on the primary endpoint. Full compliance is documented in `v32_79A_red_team_audit.md` Section 7.

---

## 3. Empirical Findings (Reference Only)

### Data Scope

| Dataset | Rows | Period |
|---|---|---|
| OHLCV checkpoint | 40,897 bars (overlap restricted) | 2022-01-01 → 2026-09-01 |
| Binance BTCUSDT funding | 5,113 settlements | 2022-01-01 → 2026-09-01 |

### Threshold Realized Frequency

| Parameter | Value |
|---|---|
| Threshold | ±0.000228 per 8h (±25% ann) |
| Threshold percentile (positive rates) | 96.7th |
| SHORT raw observations | 144 (longs crowded) |
| LONG raw observations | 5 (shorts crowded) |
| SHORT distinct episodes | **64** — below 100 minimum |
| LONG distinct episodes | **3** — critically below minimum |

### Key Results (both arms: INSUFFICIENT_EVIDENCE)

| Arm | N | TP Rate | Net EV (Binance) | 95% CI | DM-HLN p | Significant? |
|---|---|---|---|---|---|---|
| SHORT | 64 | 29.7% | +0.068% | [−0.415%, +0.563%] | 0.269 | **NO** |
| LONG | 3 | 66.7% | +1.260% | [−1.740%, +2.760%] | N/A | **N/A (N=3)** |
| Baseline SHORT | 1,704 | 17.2% | −0.194% | [−0.275%, −0.111%] | — | — |
| Baseline LONG | 1,704 | 16.6% | −0.225% | [−0.305%, −0.145%] | — | — |

**Notable observation (for reference, not conclusion):** The SHORT arm TP rate of 29.7% is above the unconditional baseline of 17.2%. The net EV of +0.068% compares favorably to the baseline −0.194%. A raw delta of +0.262pp exists. However, this is statistically indistinguishable from noise at N=64 and p=0.269.

**Chronological instability:** H1 = −0.390%, H2 = +0.526% for the SHORT arm — a sign reversal that undermines any interpretation of a stable effect.

**Coinbase sensitivity:** SHORT arm net EV = −0.562% — comfortably loss-making under retail fees.

---

## 4. Downstream Audit: Synthetic Macro Dataset

Per Manager's ruling, `data/processed/multi_regime_features.parquet` is formally classified as:

**`SYNTHETIC_DATA — NOT_VALID_FOR_EMPIRICAL_RESEARCH`**

### Dependency Audit

Files that reference `multi_regime_features.parquet`:

| File | Role | Impact |
|---|---|---|
| `research/multi_regime_dataset.py` | Generator | Creates the file — annotated as SYNTHETIC |
| `research/macro_evaluation_harness.py` | Consumer | Reads for evaluation — any results are INVALID as empirical evidence |
| `research/multi_regime_purged_validation.py` | Consumer — cross-validation | Results are INVALID as empirical evidence |
| `research/run_uncertainty_01_trial.py` | Consumer | Results are INVALID as empirical evidence |
| `research/run_uncertainty_02_trial.py` | Consumer | Results are INVALID as empirical evidence |
| `research/audit_iv_dataset.py` | Consumer | Results are INVALID as empirical evidence |
| `tests/test_multi_regime_deepening.py` | Test | Software pipeline test only — not an empirical claim |

**Key governance ruling:** The test (`test_multi_regime_deepening.py`) validates the software pipeline (shape, columns, dtypes) on synthetic data. This is acceptable for software testing purposes. The test does NOT make empirical research claims and is therefore unaffected by this classification.

**Experiments that used the FROZEN OHLCV dataset directly** (V32.74, V32.75, V32.76, V32.77, V32.78 barrier backtests) are assessed on their own data lineage and are NOT automatically invalidated. They used `ohlcv_checkpoint_42233_bars.parquet` (hash verified) as their price source.

**The synthetic dataset is preserved with its current hash recorded.** It must not be deleted. It must not be used as empirical evidence in any future research report.

---

## 5. Four Governed Decisions

| Decision | Status |
|---|---|
| **Research Experiment** | V32.79A: `INSUFFICIENT_EVIDENCE` — Stop condition triggered (N<100). No edge established, no edge refuted. |
| **Prospective Evidence** | `NOT_STARTED` — 7/100 blocks. Runner frozen. Confirmatory gate paused, not permanently blocked. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` — unchanged. |
| **Live Trading** | `DISABLED` — unchanged. |

---

## 6. What This Experiment Established

The experiment is informative even under `INSUFFICIENT_EVIDENCE`:

1. **The ±25% annualized threshold is too selective for the 4.67-year dataset.** At 64 SHORT episodes and 3 LONG episodes, no reliable inference is possible. This is a concrete empirical constraint, not a data quality problem.

2. **The BTCUSDT perpetual funding rate is predominantly positive.** Negative-funding events exceeding the threshold are near-absent. Any future investigation of the LONG arm (contrarian long at negative funding) would require a substantially longer dataset or a lower magnitude threshold.

3. **The unconditional baseline is reliably negative** (−0.194% to −0.225% net EV at Binance fees). This confirms V32.74–V32.78 findings on the same data. Entry filtering is necessary — but the funding signal at ±25% ann is not sufficiently frequent to provide it.

4. **The SHORT arm shows a directional improvement over the unconditional baseline** (+0.262pp delta in net EV). This is an observable direction-consistent with the mean-reversion hypothesis. However, the improvement is statistically indistinguishable from noise and displays chronological instability. It is a hypothesis-generating observation, not evidence.

5. **BTCUSD spot costs and BTCUSDT perpetual funding are properly distinguished throughout.** The instrument distinction requirement is fully maintained.

---

## 7. Deliverables Checklist

| # | Deliverable | Status |
|---|---|---|
| 1 | `v32_79A_funding_experiment_design.md` | ✅ Written (pre-registration) |
| 2 | `v32_79A_event_definition_and_counts.md` | ✅ Written |
| 3 | `v32_79A_funding_signal_results.md` | ✅ Written |
| 4 | `v32_79A_cost_and_funding_cashflow_audit.md` | ✅ Written |
| 5 | `v32_79A_statistical_validation.md` | ✅ Written |
| 6 | `v32_79A_red_team_audit.md` | ✅ Written |
| 7 | `v32_79A_protected_hash_verification.json` | ✅ Written |
| 8 | `v32_79A_manager_handover.md` | ✅ **This document** |

All deliverables written to:  
`BTCognitive/research/reports/offline_mvp/20261030_270000_v32_79A_funding_dislocation_research/`

---

## 8. Questions for Manager Decision

1. **Should the ±25% ann threshold be relaxed for a follow-up investigation?**  
   This would constitute threshold optimization — explicitly prohibited in the current authorization. A separate Manager authorization with a new pre-registered threshold (e.g., ±10% or ±15% ann) would be required.

2. **What is the forward research priority after INSUFFICIENT_EVIDENCE?**  
   V32.79 Phase 0 blocked all four hypotheses (three by provenance, one by insufficient events). V32.79A confirmed the one testable hypothesis is underpowered. The Manager's strategic position was: *"One experiment. One fixed rule. One defensible conclusion."* That conclusion is now delivered.

3. **What is the V32.80 mandate?**  
   Options include: (a) halt exploratory research and focus on prospective collector restart authorization, (b) define a new data acquisition plan for the blocked hypotheses, (c) investigate lower funding thresholds under new pre-registration, or (d) declare the current research phase complete and await the confirmatory gate.

---

*V32.79A complete. Awaiting Manager decision.*  
*Zero external API calls. Zero dataset modifications. All governance gates preserved.*

