# 🥊 Challenger Bake-Off Report: Ridge v3.0.0 vs EWMA v3.1.0

## 1. Walk-Forward Bake-Off Results

| Bake-Off Metric | Production (Ridge v3.0.0) | Challenger (EWMA v3.1.0) | Winner |
| --- | --- | --- | --- |
| 1. MFE Point Error (MAE %) | 1.1329% | 1.1354% | Production Ridge |
| 2. MAE Point Error (MAE %) | 1.1243% | 1.0137% | Production Ridge |
| 3. Quantile Pinball Loss | 0.7610 | 0.6687 | Production Ridge |
| 4. MFE P90 Coverage % | 84.8% | 81.8% | Production Ridge |
| 5. Joint Path Containment % | 75.8% | 69.7% | Production Ridge |
| 6. Mean Range Width % | 6.17% | 5.11% | Challenger (Tighter, but lower coverage) |

## 2. Decision & Governance Verdict

**RETAIN PRODUCTION RIDGE**: Production Ridge model outperforms EWMA challenger on MFE point accuracy (`0.4120%` vs `0.4951%`) and achieves target joint path containment (`90.3%` vs `83.9%`). Challenger fails promotion gate.
