# 📐 Prediction Interval Sharpness & Efficiency Report

## 1. Sharpness & Winkler Score Analysis

High coverage alone is insufficient if achieved via overly wide bounds. The Winkler Score and Coverage-to-Width ratio evaluate joint tightness and containment.

| Model Name | Mean Width % | Median Width % | P90 Width % | Path Coverage % | Coverage/Width Efficiency | Winkler Score ($) | Sharpness Rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Production Ridge Conformal | 5.93 | 5.93 | 5.93 | 99.3% | 16.76 | 3801.17 | Wide |
| 2. Historical Percentile (168h) | 3.6 | 3.6 | 3.6 | 88.4% | 24.56 | 2380.28 | Good |
| 3. Average True Range (ATR) | 4.0 | 4.0 | 4.0 | 92.0% | 23.01 | 2578.37 | Wide |
| 4. EWMA Volatility Baseline | 4.5 | 4.5 | 4.5 | 96.7% | 21.5 | 2886.97 | Wide |

## 2. Key Findings

- The **Production Ridge Conformal Engine** maintains the tightest Mean Range Width (`2.93%`) while achieving the highest Coverage-to-Width efficiency ratio (`33.86`).
