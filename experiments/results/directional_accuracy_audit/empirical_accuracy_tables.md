# Empirical Directional Accuracy Audit Tables

### Horizon 1H (1h) Baseline-First Forecast Accuracy Ladder

| Model Candidate | Sample Size ($N$) | Out-of-Sample Accuracy | 95% Wilson CI | ROC AUC | Brier Score | Mean Net Return (BASE 35 bps) | Null Test ($H_0: p \ge 70\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority_Class_Baseline** | `33,919` | `50.40%` | `[49.9%, 50.9%]` | `0.4973` | `0.2500` | `-34.8 bps` | `p < 1e-10` |
| **Momentum_Persistence** | `33,919` | `47.09%` | `[46.6%, 47.6%]` | `0.4708` | `0.5291` | `-35.6 bps` | `p < 1e-10` |
| **Logistic_Regression_L2** | `33,919` | `52.74%` | `[52.2%, 53.3%]` | `0.5417` | `0.2488` | `-35.1 bps` | `p < 1e-10` |
| **Random_Forest** | `33,919` | `53.25%` | `[52.7%, 53.8%]` | `0.5448` | `0.2485` | `-34.9 bps` | `p < 1e-10` |
| **Gradient_Boosting** | `33,919` | `53.30%` | `[52.8%, 53.8%]` | `0.5435` | `0.2490` | `-34.6 bps` | `p < 1e-10` |

#### Selective Confidence Filtering on Gradient Boosting (1H)

| Coverage Target | Active Predictions | Empirical Coverage | Accuracy | 95% Wilson CI | Mean Net Return (BASE 35 bps) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `100%` | `33,919` | `100.0%` | `53.30%` | `[52.8%, 53.8%]` | `-34.6 bps` |
| `50%` | `16,960` | `50.0%` | `54.98%` | `[54.2%, 55.7%]` | `-34.6 bps` |
| `25%` | `8,482` | `25.0%` | `55.87%` | `[54.8%, 56.9%]` | `-33.9 bps` |
| `10%` | `3,392` | `10.0%` | `57.05%` | `[55.4%, 58.7%]` | `-32.2 bps` |
| `5%` | `1,696` | `5.0%` | `56.19%` | `[53.8%, 58.5%]` | `-32.9 bps` |


### Horizon 4H (4h) Baseline-First Forecast Accuracy Ladder

| Model Candidate | Sample Size ($N$) | Out-of-Sample Accuracy | 95% Wilson CI | ROC AUC | Brier Score | Mean Net Return (BASE 35 bps) | Null Test ($H_0: p \ge 70\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority_Class_Baseline** | `33,916` | `50.60%` | `[50.1%, 51.1%]` | `0.4963` | `0.2500` | `-34.0 bps` | `p < 1e-10` |
| **Momentum_Persistence** | `33,916` | `46.93%` | `[46.4%, 47.5%]` | `0.4691` | `0.5307` | `-35.6 bps` | `p < 1e-10` |
| **Logistic_Regression_L2** | `33,916` | `52.96%` | `[52.4%, 53.5%]` | `0.5368` | `0.2493` | `-35.4 bps` | `p < 1e-10` |
| **Random_Forest** | `33,916` | `52.64%` | `[52.1%, 53.2%]` | `0.5392` | `0.2490` | `-35.3 bps` | `p < 1e-10` |
| **Gradient_Boosting** | `33,916` | `52.54%` | `[52.0%, 53.1%]` | `0.5329` | `0.2510` | `-34.3 bps` | `p < 1e-10` |

#### Selective Confidence Filtering on Gradient Boosting (4H)

| Coverage Target | Active Predictions | Empirical Coverage | Accuracy | 95% Wilson CI | Mean Net Return (BASE 35 bps) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `100%` | `33,916` | `100.0%` | `52.54%` | `[52.0%, 53.1%]` | `-34.3 bps` |
| `50%` | `16,958` | `50.0%` | `53.76%` | `[53.0%, 54.5%]` | `-34.2 bps` |
| `25%` | `8,479` | `25.0%` | `54.86%` | `[53.8%, 55.9%]` | `-33.1 bps` |
| `10%` | `3,394` | `10.0%` | `53.03%` | `[51.4%, 54.7%]` | `-35.7 bps` |
| `5%` | `1,696` | `5.0%` | `53.01%` | `[50.6%, 55.4%]` | `-38.0 bps` |


### Horizon 24H (24h) Baseline-First Forecast Accuracy Ladder

| Model Candidate | Sample Size ($N$) | Out-of-Sample Accuracy | 95% Wilson CI | ROC AUC | Brier Score | Mean Net Return (BASE 35 bps) | Null Test ($H_0: p \ge 70\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority_Class_Baseline** | `33,900` | `49.72%` | `[49.2%, 50.3%]` | `0.4925` | `0.2503` | `-41.7 bps` | `p < 1e-10` |
| **Momentum_Persistence** | `33,900` | `47.74%` | `[47.2%, 48.3%]` | `0.4765` | `0.5226` | `-29.9 bps` | `p < 1e-10` |
| **Logistic_Regression_L2** | `33,900` | `50.49%` | `[50.0%, 51.0%]` | `0.5066` | `0.2525` | `-42.9 bps` | `p < 1e-10` |
| **Random_Forest** | `33,900` | `50.53%` | `[50.0%, 51.1%]` | `0.5109` | `0.2544` | `-42.8 bps` | `p < 1e-10` |
| **Gradient_Boosting** | `33,900` | `50.40%` | `[49.9%, 50.9%]` | `0.5066` | `0.2598` | `-41.9 bps` | `p < 1e-10` |

#### Selective Confidence Filtering on Gradient Boosting (24H)

| Coverage Target | Active Predictions | Empirical Coverage | Accuracy | 95% Wilson CI | Mean Net Return (BASE 35 bps) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `100%` | `33,900` | `100.0%` | `50.40%` | `[49.9%, 50.9%]` | `-41.9 bps` |
| `50%` | `16,954` | `50.0%` | `50.38%` | `[49.6%, 51.1%]` | `-47.5 bps` |
| `25%` | `8,475` | `25.0%` | `50.47%` | `[49.4%, 51.5%]` | `-51.3 bps` |
| `10%` | `3,411` | `10.1%` | `54.03%` | `[52.4%, 55.7%]` | `-37.7 bps` |
| `5%` | `1,696` | `5.0%` | `53.30%` | `[50.9%, 55.7%]` | `-48.8 bps` |
