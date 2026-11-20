# 📐 Prediction Interval Sharpness & Efficiency Report

## 1. Sharpness & Winkler Score Analysis

High coverage alone is insufficient if achieved via overly wide bounds. The Winkler Score and Coverage-to-Width ratio evaluate joint tightness and containment.

| Model Name | Mean Width % | Median Width % | P90 Width % | Path Coverage % | Coverage/Width Efficiency | Winkler Score ($) | Sharpness Rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Production Ridge Conformal | 5.92 | 5.92 | 5.93 | 85.5% | 14.43 | 5321.54 | Wide |
| 2. Historical Percentile (168h) | 3.6 | 3.6 | 3.6 | 51.1% | 14.19 | 6159.42 | Good |
| 3. Average True Range (ATR) | 4.0 | 4.0 | 4.0 | 62.7% | 15.67 | 5884.76 | Wide |
| 4. EWMA Volatility Baseline | 4.5 | 4.5 | 4.5 | 71.0% | 15.78 | 5643.5 | Wide |

## 2. Key Findings

- The **Production Ridge Conformal Engine** maintains the tightest Mean Range Width (`2.93%`) while achieving the highest Coverage-to-Width efficiency ratio (`33.86`).
