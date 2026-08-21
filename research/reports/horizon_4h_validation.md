# 🔬 4-Hour Intermediate Horizon Audit Report

## 1. Controlled Information Ablation (4H)

| Model Variant | Features | 4h MFE Error | 4h MAE Error | P90 Cov | Winkler | Direction AUC | Independent Blocks | N_eff | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Model A: Technical Only | ATR, Bollinger Band Width, 4h Momentum | 104.2 bps | 112.5 bps | 87.1% | 780.4 | 0.508 | 35 | 30 | BASELINE |
| Model B: Derivatives Only | Funding Rate, OI Acceleration, Basis | 118.6 bps | 125.4 bps | 83.5% | 890.1 | 0.514 | 35 | 30 | WEAK_STANDALONE |
| Model C: Volatility Only | 4h & 24h Realized Volatility | 94.50 bps | 102.1 bps | 89.4% | 710.2 | 0.501 | 35 | 30 | STRONG_BASELINE |
| Model D: Technical + Derivatives | Technical + Funding/OI Dislocation | 96.20 bps | 104.0 bps | 88.6% | 725.5 | 0.515 | 35 | 30 | RESEARCH |
| Model E: Tech + Deriv + Volatility | Full Multi-Factor 4h Stack | 88.40 bps | 96.50 bps | 90.1% | 685.4 | 0.518 | 35 | 30 | BEST_CANDIDATE |

## 2. Key Scientific Audit Findings

- **Derivatives Role:** Funding rates and OI dislocation do not serve as standalone directional alpha, but contribute meaningful conditional variance shaping when combined with technical realized volatility.
- **Bridging Capability:** 4h acts as the transition boundary where order flow disappears and macro/derivatives information emerges.
- **Sample Scale Status:** $N_{\text{eff}} = 30$ is strictly below the required $N_{\text{eff}} \ge 100$ threshold. Retained as `RESEARCH_ONLY`.
