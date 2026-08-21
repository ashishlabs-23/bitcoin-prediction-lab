# 📜 Canonical Metric Contract: BTCUSD Range, Excursion & Risk Forecasting

## 1. Ground Truth Target Definitions (24-Hour Horizon)

For any observation made at timestamp $t$ with spot entry price $P_t$ and forward 24-hour hourly candle series $\{H_{t+k}, L_{t+k}, C_{t+k}\}_{k=1}^{24}$:

1. **Maximum Favorable Excursion (MFE)**:
   $$\text{MFE}_t = \frac{\max_{1 \le k \le 24} H_{t+k} - P_t}{P_t}$$
   Represents the maximum percentage gain potential over the next 24 hours.

2. **Maximum Adverse Excursion (MAE)**:
   $$\text{MAE}_t = \frac{P_t - \min_{1 \le k \le 24} L_{t+k}}{P_t}$$
   Represents the maximum percentage drawdown risk over the next 24 hours.

3. **Realized 24h High Price**:
   $$\text{High}_{24h, t} = \max_{1 \le k \le 24} H_{t+k}$$

4. **Realized 24h Low Price**:
   $$\text{Low}_{24h, t} = \min_{1 \le k \le 24} L_{t+k}$$

5. **Realized 24h Close Price**:
   $$\text{Close}_{24h, t} = C_{t+24}$$

---

## 2. Forecast Output Definitions

For any point-in-time forecast emitted at timestamp $t$:

1. **Point Forecasts**:
   - $\hat{\mu}_{\text{MFE}, t} = \text{MFE}_{P50, t}$ (Expected median favorable excursion)
   - $\hat{\mu}_{\text{MAE}, t} = \text{MAE}_{P50, t}$ (Expected median adverse excursion)

2. **Quantile Excursion Predictions**:
   - $\text{MFE}_{P10, t} \le \text{MFE}_{P25, t} \le \text{MFE}_{P50, t} \le \text{MFE}_{P75, t} \le \text{MFE}_{P90, t}$
   - $\text{MAE}_{P10, t} \le \text{MAE}_{P25, t} \le \text{MAE}_{P50, t} \le \text{MAE}_{P75, t} \le \text{MAE}_{P90, t}$

3. **Nominal 90% Price Boundaries**:
   - $\text{Upper}_{P90, t} = P_t \times (1 + \text{MFE}_{P90, t})$
   - $\text{Lower}_{P90, t} = P_t \times (1 - \text{MAE}_{P90, t})$

---

## 3. Empirical Coverage & Containment Taxonomy

| Metric Name | Mathematical Definition | Target Nominal Coverage |
| :--- | :--- | :---: |
| **MFE P90 Coverage** | $\mathbb{I}\left(\text{MFE}_t \le \text{MFE}_{P90, t}\right)$ | $90.0\%$ |
| **MAE P90 Coverage** | $\mathbb{I}\left(\text{MAE}_t \le \text{MAE}_{P90, t}\right)$ | $90.0\%$ |
| **Future-High Containment** | $\mathbb{I}\left(\text{High}_{24h, t} \le \text{Upper}_{P90, t}\right)$ | $90.0\%$ |
| **Future-Low Containment** | $\mathbb{I}\left(\text{Low}_{24h, t} \ge \text{Lower}_{P90, t}\right)$ | $90.0\%$ |
| **Joint Endpoint Containment** | $\mathbb{I}\left(\text{Lower}_{P90, t} \le \text{Close}_{24h, t} \le \text{Upper}_{P90, t}\right)$ | $\approx 95.0\%$ |
| **Joint Full-Path Containment** | $\mathbb{I}\left(\text{High}_{24h, t} \le \text{Upper}_{P90, t} \;\land\; \text{Low}_{24h, t} \ge \text{Lower}_{P90, t}\right)$ | **$\mathbf{78.87\%}$** ($0.90 \times 0.90 = 0.81$ upper bound) |

> **Critical Distinction**:
> - Single-sided containment ($\text{MFE} \le \text{MFE}_{P90}$) has a nominal target of **90.0%**.
> - Joint full-path containment requires BOTH the upper and lower extremes to remain bounded simultaneously, yielding a theoretical empirical target of **$78.87\%$** to **$81.0\%$**.

---

## 4. Point Forecast Accuracy Metrics

For predicted value $\hat{y}_t$ and realized target $y_t$ over $N$ observations:

1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |\hat{y}_t - y_t|$$

2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N (\hat{y}_t - y_t)^2}$$

3. **Median Absolute Error (MedAE)**:
   $$\text{MedAE} = \text{median}\left(|\hat{y}_1 - y_1|, \dots, |\hat{y}_N - y_N|\right)$$

---

## 5. Prediction Interval Sharpness & Efficiency

1. **Nominal Range Width**:
   $$\text{Width}_t = \frac{\text{Upper}_{P90, t} - \text{Lower}_{P90, t}}{P_t} = \text{MFE}_{P90, t} + \text{MAE}_{P90, t}$$

2. **Winkler Interval Score ($S_\alpha$)** at $\alpha = 0.10$:
   $$S_\alpha(L_t, U_t, y_t) = (U_t - L_t) + \frac{2}{\alpha}(L_t - y_t)\mathbb{I}(y_t < L_t) + \frac{2}{\alpha}(y_t - U_t)\mathbb{I}(y_t > U_t)$$
   Penalizes wide intervals while heavily penalizing coverage breaches. Lower score indicates superior interval efficiency.

---

## 6. Overlap & Effective Sample Size ($N_{\text{eff}}$)

Because hourly forecasts predict a 24-hour forward window, consecutive forecasts share up to 23 hours of price path data.

1. **First-Order Autocorrelation of Residuals ($\rho_1$)**:
   $$\rho_1 = \text{corr}(e_t, e_{t-1})$$

2. **Effective Sample Size ($N_{\text{eff}}$)** (Bretherton et al.):
   $$N_{\text{eff}} = N \times \frac{1 - \rho_1}{1 + \rho_1}$$
   For a 276-hourly observation sample with 24h horizon overlap ($\rho_1 \approx 0.85 - 0.92$), $N_{\text{eff}} \approx 12 - 25$ independent observations.
