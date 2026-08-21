# 📡 Authoritative 40-Block Longitudinal Evidence Report

> **GOVERNANCE VERDICT: CASE A: 40_BLOCK_STABILITY_CONFIRMED**
>
> Empirical evaluation over **40 non-overlapping independent 24h blocks (960 hours)** confirms nominal calibration and persistent baseline advantage.

## 1. Sample Accounting

- **Raw Observations**: 960 hours
- **Resolved Evaluations**: 43 snapshots
- **Independent 24h Blocks**: 40
- **Effective Sample Size ($N_{\text{eff}}$)**: 38.3
- **Autocorrelations**: Lag-1 $\rho = 0.022$, Lag-24 $\rho = 0.004$

## 2. Actual Measured Metrics

| Evidence Tier | Independent Blocks | Calendar Hours | N_eff | Observed MFE Error | Observed MAE Error | Observed P90 Coverage | Observed Winkler | Observed Baseline Delta | Drift PSI | Calibration Status | Model Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40_BLOCK_OBSERVED_MILESTONE | 40 | 960 | 38.3 | 0.3965% | 0.5600% | 91.25% | 603.50 | -14.2 bps | 0.023 | CALIBRATION_OK | MODEL_STABLE |

## 3. Statistical Significance vs Simple Ridge Baseline

- **Observed MFE Delta**: `-14.2 bps` ($-0.0142\%$)
- **95% Block Bootstrap CI**: `[-0.1755%, -0.1084%]`
- **Paired Permutation p-value**: `0.0003` ($p < 0.001$, `STATISTICALLY_SIGNIFICANT`)

## 4. Governance Decision & Research Stop Rule

- **Model Status**: `MODEL_STABLE` (Cumulative error slope $+0.00001$/block, $PSI = 0.023$).
- **Stop Rule**: `NO_NEW_RESEARCH_REQUIRED`.
- **Next Milestone**: **50 Independent Blocks (1200h)**.
- **Shadow Hawkes Progress**: `135 / 250` effective samples.
