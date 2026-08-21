# 🔬 1-Hour Intermediate Horizon Audit Report

## 1. Controlled Information Ablation (1H)

| Model Variant | Features | 1h MFE Error | 1h MAE Error | P90 Cov | Winkler | Direction AUC | Independent Blocks | N_eff | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Model A: Technical Only | RSI, MACD, 1h Return Momentum | 48.20 bps | 54.10 bps | 86.5% | 395.2 | 0.512 | 60 | 48 | BASELINE |
| Model B: OFI Only | Depth OFI, Multi-level Imbalance | 52.40 bps | 58.60 bps | 84.2% | 420.1 | 0.516 | 60 | 48 | WEAK |
| Model C: Technical + OFI | Technical + OFI Residuals | 44.60 bps | 50.40 bps | 88.4% | 365.4 | 0.521 | 60 | 48 | RESEARCH |
| Model D: Volatility Only | 1h & 24h Realized Volatility | 45.10 bps | 51.00 bps | 89.0% | 358.2 | 0.502 | 60 | 48 | STRONG_BASELINE |
| Model E: Tech + OFI + Vol + Hawkes | Full Stack + 5m Hawkes Intensity Handoff | 42.50 bps | 48.20 bps | 89.2% | 342.1 | 0.524 | 60 | 48 | BEST_CANDIDATE |

## 2. Key Scientific Audit Findings

- **Primary Driver:** Realized volatility and technical momentum provide the bulk of predictive excursion containment at 1h.
- **Hawkes State Handoff:** Adding the 5m Hawkes point-process state provides marginal improvement (+0.003 AUC, -2.1 bps MFE error), indicating high-frequency intensity has largely decayed by 1 hour.
- **Sample Scale Status:** $N_{\text{eff}} = 48$ is strictly below the required $N_{\text{eff}} \ge 150$ threshold. Retained as `RESEARCH_ONLY`.
