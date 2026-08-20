# 🧭 Conditional Direction & Structural Asymmetry Report

## Directional Performance Conditioned on Excursions

| Conditional Execution Strategy | Sample Count (n) | Coverage % | P(Up | Condition) % | P(Down | Condition) % | Directional Accuracy % | Directional ROC AUC | Avg Net Return % (14 bps) | Cost-Adjusted Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Unconditional Global Direction (Baseline) | 450 | 100.0 | 51.78 | 48.22 | 46.0 | 0.453 | -0.4608 | -40.0362 |
| 2. Conditioned on Pred MFE > 14 bps Hurdle | 450 | 100.0 | 51.78 | 48.22 | 46.0 | 0.453 | -0.4608 | -40.0362 |
| 3. Conditioned on Pred MFE > 25 bps Hurdle | 450 | 100.0 | 51.78 | 48.22 | 46.0 | 0.453 | -0.4608 | -40.0362 |
| 4. Conditioned on Pred MFE > 50 bps Hurdle | 450 | 100.0 | 51.78 | 48.22 | 46.0 | 0.453 | -0.4608 | -40.0362 |
| 5. Asymmetric Envelope: Pred MFE High (> 75th) & Pred MAE Low (< 25th) | 36 | 8.0 | 50.0 | 50.0 | 52.78 | 0.3735 | -0.6182 | -11.8718 |

## Long vs Short Structural Excursion Asymmetry

| Position Side | Mean Favorable MFE % | Mean Adverse MAE % | Favorable/Adverse Ratio |
| --- | --- | --- | --- |
| Long Excursion (Upside) | 0.94 | 1.019 | 0.922 |
| Short Excursion (Downside) | 1.038 | 0.94 | 1.105 |