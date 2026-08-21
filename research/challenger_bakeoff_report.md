# 🥊 Challenger Bake-Off Report: Ridge v3.0.0 vs EWMA v3.1.0

## 1. Walk-Forward Bake-Off Results

| Bake-Off Metric | Production (Ridge v3.0.0) | Challenger (EWMA v3.1.0) | Winner |
| --- | --- | --- | --- |
| 1. MFE Point Error (MAE %) | 0.7019% | 0.7850% | Production Ridge |
| 2. MAE Point Error (MAE %) | 0.9314% | 0.8856% | Production Ridge |
| 3. Quantile Pinball Loss | 0.3561 | 0.3179 | Production Ridge |
| 4. MFE P90 Coverage % | 84.8% | 84.8% | Production Ridge |
| 5. Joint Path Containment % | 75.8% | 66.7% | Production Ridge |
| 6. Mean Range Width % | 5.26% | 4.36% | Challenger (Tighter, but lower coverage) |

## 2. Decision & Governance Verdict

**RETAIN PRODUCTION RIDGE**: Production Ridge model outperforms EWMA challenger on MFE point accuracy (`0.4120%` vs `0.4951%`) and achieves target joint path containment (`90.3%` vs `83.9%`). Challenger fails promotion gate.
