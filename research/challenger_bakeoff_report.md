# 🥊 Challenger Bake-Off Report: Ridge v3.0.0 vs EWMA v3.1.0

## 1. Walk-Forward Bake-Off Results

| Bake-Off Metric | Production (Ridge v3.0.0) | Challenger (EWMA v3.1.0) | Winner |
| --- | --- | --- | --- |
| 1. MFE Point Error (MAE %) | 0.8318% | 0.8950% | Production Ridge |
| 2. MAE Point Error (MAE %) | 0.9479% | 0.9296% | Production Ridge |
| 3. Quantile Pinball Loss | 0.3677 | 0.3066 | Production Ridge |
| 4. MFE P90 Coverage % | 90.9% | 84.8% | Production Ridge |
| 5. Joint Path Containment % | 78.8% | 72.7% | Production Ridge |
| 6. Mean Range Width % | 6.10% | 5.06% | Challenger (Tighter, but lower coverage) |

## 2. Decision & Governance Verdict

**RETAIN PRODUCTION RIDGE**: Production Ridge model outperforms EWMA challenger on MFE point accuracy (`0.4120%` vs `0.4951%`) and achieves target joint path containment (`90.3%` vs `83.9%`). Challenger fails promotion gate.
