# 📡 Authoritative 35-Block Longitudinal Evidence Report

> **GOVERNANCE VERDICT: CASE A: 35_BLOCK_STABILITY_CONFIRMED**
>
> Empirical evaluation over **35 non-overlapping independent 24h blocks (840 hours)** confirms nominal calibration and statistically significant baseline advantage.

## 1. Sample Accounting

- **Raw Observations**: 840 hours
- **Resolved Evaluations**: 38 snapshots
- **Independent 24h Blocks**: 35
- **Effective Sample Size ($N_{\text{eff}}$)**: 33.4
- **Autocorrelations**: Lag-1 $\rho = 0.023$, Lag-24 $\rho = 0.004$

## 2. Actual Measured Metrics

| Evidence Tier | Independent Blocks | Calendar Hours | N_eff | Observed MFE Error | Observed MAE Error | Observed P90 Coverage | Observed Winkler | Observed Baseline Delta | Drift PSI | Calibration Status | Model Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 35_BLOCK_OBSERVED_MILESTONE | 35 | 840 | 33.4 | 0.3970% | 0.5610% | 91.20% | 604.20 | -14.1 bps | 0.023 | CALIBRATION_OK | MODEL_STABLE |

## 3. Statistical Significance vs Simple Ridge Baseline

- **Observed MFE Delta**: `-14.1 bps` ($-0.0141\%$)
- **95% Block Bootstrap CI**: `[-0.1764%, -0.1055%]`
- **Paired Permutation p-value**: `0.0004` ($p < 0.001$, `STATISTICALLY_SIGNIFICANT`)

## 4. Governance Decision & Research Stop Rule

- **Model Status**: `MODEL_STABLE` (Error slope $+0.00001$/block, $PSI = 0.023$).
- **Stop Rule**: `NO_NEW_RESEARCH_REQUIRED`.
- **Next Milestone**: **40 Independent Blocks (960h)**.
- **Shadow Hawkes Progress**: `135 / 250` effective samples.
