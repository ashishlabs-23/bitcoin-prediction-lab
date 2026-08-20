# ⏳ Horizon-Specialized Models & Multi-Head Report

## Specialized Model Performance

| Specialized Model | Target Horizon | Features Used | Mean OOS AUC | AUC Std | Mean Balanced Acc | Mean MCC | Spearman IC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MODEL 1 (1–4h Microstructure Specialist) | 4h | 6 | 0.5301 | 0.0167 | 0.347 | 0.0153 | 0.0694 |
| MODEL 2 (12–24h Swing Specialist) | 24h | 12 | 0.55 | 0.0812 | 0.3315 | 0.0002 | 0.0187 |
| MODEL 3 (24–48h Macro Specialist) | 48h | 8 | 0.57 | 0.0454 | 0.377 | 0.0702 | 0.0512 |
| MODEL 4 (Multi-Head Shared Encoder) | 24h | 35 | 0.5415 | 0.0479 | 0.3765 | 0.0721 | -0.0444 |