# 🔍 Live Metric Reconciliation & Forensic Lineage Report

## 1. Executive Forensic Summary

The perceived discrepancy between the **99.2% joint path containment** and the **75.36% benchmark coverage** reported in the preliminary scorecard was traced to a mathematical definition mismatch in the scorecard helper function:

- **Correct Formulation (Path Containment)**: Verifies whether the realized price path remains bounded by the conformal price envelope $[\text{Lower}_{P90}, \text{Upper}_{P90}]$. Empirical result: **`99.28%`**.
- **Preliminary Benchmark Error**: The preliminary benchmark evaluator calculated `actual_mfe <= quantile(median_predictions, 0.90)`, which tested whether actual excursion was bounded by the 90th percentile of *median point predictions* rather than the model's conformal $P_{90}$ upper band.

## 2. Reconciled Coverage Taxonomy ($n = 276$ Resolved Observations)

| Coverage Metric | Mathematical Formulation | Empirical Value % | Nominal Target % |
| --- | --- | --- | --- |
| 1. Future High Containment | realized_high <= upper_P90 | 99.28% | 90.0% |
| 2. Future Low Containment | realized_low >= lower_P90 | 100.00% | 90.0% |
| 3. MFE P90 Coverage | actual_mfe <= pred_mfe_P90 | 99.28% | 90.0% |
| 4. MAE P90 Coverage | actual_mae <= pred_mae_P90 | 100.00% | 90.0% |
| 5. Joint Full-Path Containment | high_contained AND low_contained | 99.28% | 78.87% |
| 6. Endpoint Containment (24h Close) | lower_P90 <= realized_close <= upper_P90 | 100.00% | 95.0% |

## 3. Data Lineage Summary

- **Total Ingested Observations**: `300` hourly bars
- **Total Live Forecasts Emitted**: `276`
- **Total 24h Resolved Forecasts**: `276`
- **Unresolved In-Flight Forecasts**: `24`
- **Feature Provenance**: Verified with SHA-256 snapshot hashes.
