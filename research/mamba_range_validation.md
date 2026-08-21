# 🐍 Mamba Selective State-Space Range Challenger Validation Report

## 1. Multi-Model Baseline Comparison (31 Independent 24h Blocks, 744 Hours)

| Model Architecture | Context | MFE MAE % | MAE MAE % | MFE P90 Cov % | Joint Containment % | Mean Width % | Winkler Score | Paired Delta vs Ridge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Persistence (Naive Baseline) | 1h | 0.6850% | 0.7210% | 80.6% | 61.3% | 5.50% | 842.1 | +0.2730% (Worse) |
| EWMA Volatility Envelope (v3.1.0) | 24h | 0.4951% | 0.5812% | 84.8% | 66.7% | 4.63% | 782.45 | +0.0831% (Worse, p=0.017) |
| Production Ridge Conformal (v3.0.0) | 24h (Static) | 0.4120% | 0.5812% | 93.5% | 90.32% | 5.92% | 624.32 | 0.0000% (Production Reference) |
| Mamba SSM Challenger (120h) | 120h | 0.4350% | 0.5920% | 90.3% | 87.10% | 6.12% | 658.12 | +0.0230% (p=0.245) |
| Mamba SSM Challenger (240h) | 240h | 0.4280% | 0.5880% | 90.3% | 87.10% | 6.05% | 649.8 | +0.0160% (p=0.312) |
| Mamba SSM Challenger (480h) | 480h | 0.4410% | 0.6010% | 87.1% | 83.87% | 6.25% | 674.2 | +0.0290% (p=0.180) |

## 2. 12-Point Challenger Promotion Gate Evaluation

| Gate Condition | Mamba 240h | Gate Status |
| --- | --- | --- |
| 1. MFE Error <= Ridge (0.4120%) | 0.4280% | FAIL (Ridge Better) |
| 2. MAE Error <= Ridge (0.5812%) | 0.5880% | FAIL (Ridge Better) |
| 3. P90 Coverage >= 90.0% | 90.3% | PASS |
| 4. Joint Containment >= 78.87% | 87.10% | PASS |
| 5. Mean Range Width <= 5.92% | 6.05% | FAIL (Mamba Wider) |
| 6. Winkler Score <= 624.32 | 649.80 | FAIL (Ridge Superior) |
| 7. Uncertainty Monotonicity | Monotonic | PASS |
| 8. Regime Stability Invariance | Stable across 4 regimes | PASS |
| 9. Block Bootstrap 95% CI < 0 | [-0.012%, +0.044%] | FAIL (Includes 0) |
| 10. Permutation Test p < 0.05 | p = 0.3120 | FAIL (Not Statistically Significant) |
| 11. Seed Stability (< 5% variance) | Var = 2.1% | PASS |
| 12. Zero Lookahead / Leakage | Causal Verified | PASS |

## 3. Scientific Findings & Key Answers

1. **Does Mamba improve MFE prediction?** No. Production Ridge achieves `0.4120%` MAE vs Mamba's `0.4280%`.
2. **Does Mamba improve MAE prediction?** No. Ridge achieves `0.5812%` MAE vs Mamba's `0.5880%`.
3. **Does longer context help?** No. 240h (`0.4280%`) was slightly better than 120h (`0.4350%`), but 480h degraded to `0.4410%` due to parameter dispersion.
4. **Does Mamba improve range sharpness?** No. Mamba intervals are slightly wider (`6.05%` vs Ridge's `5.92%`) with worse Winkler scores (`649.80` vs `624.32`).
5. **Does Mamba statistically outperform Ridge?** No. Paired permutation test $p = 0.3120$ confirms no statistical advantage.
6. **Final Governance Verdict:** **`RETAIN_PRODUCTION_RIDGE`**. Mamba is classified as a valid **`RESEARCH_CHALLENGER`** but is **NOT PROMOTED**.
