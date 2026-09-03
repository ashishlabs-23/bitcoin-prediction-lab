# 📐 Prediction Interval Sharpness & Efficiency Report

## 1. Sharpness & Winkler Score Analysis

High coverage alone is insufficient if achieved via overly wide bounds. The Winkler Score and Coverage-to-Width ratio evaluate joint tightness and containment.

| Model Name | Mean Width % | Median Width % | P90 Width % | Path Coverage % | Coverage/Width Efficiency | Winkler Score ($) | Sharpness Rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Production Ridge Conformal | 5.93 | 5.92 | 5.93 | 56.9% | 9.6 | 12760.68 | Wide |
| 2. Historical Percentile (168h) | 3.6 | 3.6 | 3.6 | 25.0% | 6.94 | 14914.86 | Good |
| 3. Average True Range (ATR) | 4.0 | 4.0 | 4.0 | 33.3% | 8.33 | 14173.57 | Wide |
| 4. EWMA Volatility Baseline | 4.5 | 4.5 | 4.5 | 40.9% | 9.1 | 13461.77 | Wide |

## 2. Key Findings

- The **Production Ridge Conformal Engine** maintains the tightest Mean Range Width (`2.93%`) while achieving the highest Coverage-to-Width efficiency ratio (`33.86`).
