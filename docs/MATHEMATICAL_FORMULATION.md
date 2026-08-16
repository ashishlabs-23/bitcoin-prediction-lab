# Mathematical Formulation & Quantitative Methodology

This document outlines the rigorous mathematical and statistical foundations governing the **BTCognitive** AI Inference & Risk Engine.

---

## 1. Triple-Barrier Labeling with ATR Volatility Dynamic Spans

To avoid fixed vertical horizon leakage, labels $y_t \in \{-1, 0, +1\}$ are constructed via dynamic horizontal and vertical barriers:

$$\text{Upper Barrier: } U_t = P_t \times (1 + k_{\text{up}} \times \sigma_t)$$
$$\text{Lower Barrier: } L_t = P_t \times (1 - k_{\text{dn}} \times \sigma_t)$$

where $\sigma_t = \frac{\text{ATR}_{14}(t)}{P_t}$ is the normalized Average True Range at bar $t$.

---

## 2. Purged & Embargoed Walk-Forward Cross-Validation

To prevent informational leakage across overlapping labels, samples between $[t_{i, 0}, t_{i, 1}]$ are purged if their label horizon intersects the test evaluation interval:

$$\text{Purge Interval: } \mathcal{P} = \{ j \mid t_{j, 0} \le t_{i, 1} \text{ and } t_{j, 1} \ge t_{i, 0} \}$$

An embargo $\delta$ (default: $0.01 \times N$) is appended to the training set boundaries following test sets to eliminate autoregressive serial correlation.

---

## 3. Deflated Sharpe Ratio (DSR) & PBO

The Deflated Sharpe Ratio corrects for selection bias and multi-testing over $N$ strategy trials:

$$\text{DSR} \equiv \Phi \left( \frac{(\widehat{\text{SR}} - \text{SR}_0)\sqrt{T - 1}}{\sqrt{1 - \gamma_3 \widehat{\text{SR}} + \frac{\gamma_4 - 1}{4}\widehat{\text{SR}}^2}} \right)$$

where:
* $\widehat{\text{SR}}$ is the annualized Sharpe ratio,
* $\gamma_3, \gamma_4$ are the skewness and kurtosis of strategy returns,
* $\text{SR}_0 = \sqrt{2 \ln(N)} \left( (1 - \gamma)\Phi^{-1}\left(1 - \frac{1}{N}\right) + \gamma \Phi^{-1}\left(1 - \frac{1}{N e}\right) \right)$.

---

## 4. 4-Factor Uncertainty Decomposition

The composite signal quality score $\mathcal{Q}(x)$ is computed as a weighted harmonic mean:

$$\mathcal{Q}(x) = \frac{4}{\frac{1}{\mathcal{U}_{\text{data}}} + \frac{1}{\mathcal{U}_{\text{regime}}} + \frac{1}{\mathcal{U}_{\text{consensus}}} + \frac{1}{\mathcal{U}_{\text{volatility}}}}$$

Where:
* $\mathcal{U}_{\text{data}}$: Feature freshness and API feed integrity.
* $\mathcal{U}_{\text{regime}}$: Distance to the current regime centroid in latent HMM/GMM space.
* $\mathcal{U}_{\text{consensus}}$: Inter-model Jensen-Shannon divergence across the Random Forest and XGBoost ensemble.
* $\mathcal{U}_{\text{volatility}}$: Realized vs. implied volatility stress dampener.
