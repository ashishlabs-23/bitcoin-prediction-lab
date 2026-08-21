# 📊 Range Model Validation Contract & Evidence Dossier

## 1. Frozen Candidate Invariants

* **Model Version**: `v3.0.0-excursion-ridge-conformal`
* **Target Horizon**: 24 hours ($H = 24$)
* **Nominal Target**: $\ge 78.87\%$ Joint Full-Path Containment ($0.90 \times 0.90 = 81.0\%$ theoretical limit)
* **Validation Primary Unit**: Non-overlapping 24-hour independent blocks

---

## 2. Empirical Longitudinal Evidence ($N = 31$ Blocks, $744$ Hours)

| Metric | Empirical Result | Nominal Target | Validation Status |
| :--- | :---: | :---: | :---: |
| **MFE P90 Coverage** | **`93.5%`** | $\ge 90.0\%$ | **PASS** |
| **MAE P90 Coverage** | **`96.8%`** | $\ge 90.0\%$ | **PASS** |
| **Joint Full-Path Containment** | **`90.32%`** | $\ge 78.87\%$ | **PASS** |
| **Mean Range Width** | **`5.92%`** | $\le 8.0\%$ | **PASS** |
| **Paired MAE Delta vs EWMA** | **`-0.0831%`** | $< 0.0000\%$ | **PASS ($p = 0.0172$)** |

---

## 3. Regime & Volatility Stability Matrix

* **Market Regimes**: Trending Bull ($90.0\%$), Trending Bear ($90.0\%$), Sideways ($90.9\%$), Breakout ($88.9\%$).
* **Volatility Tiers**: Low ($91.7\%$), Normal ($90.0\%$), High Volatility ($88.9\%$).
* **Conclusion**: Calibrated, sharp, and statistically resilient across changing market conditions.
