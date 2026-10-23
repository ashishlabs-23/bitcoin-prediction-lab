# 📐 Prediction Interval Sharpness & Efficiency Report

## 1. Sharpness & Winkler Score Analysis

High coverage alone is insufficient if achieved via overly wide bounds. The Winkler Score and Coverage-to-Width ratio evaluate joint tightness and containment.

| Model Name | Mean Width % | Median Width % | P90 Width % | Path Coverage % | Coverage/Width Efficiency | Winkler Score ($) | Sharpness Rating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Production Ridge Conformal | 5.92 | 5.92 | 5.93 | 84.8% | 14.31 | 5023.22 | Wide |
| 2. Historical Percentile (168h) | 3.6 | 3.6 | 3.6 | 43.8% | 12.18 | 5552.12 | Good |
| 3. Average True Range (ATR) | 4.0 | 4.0 | 4.0 | 52.2% | 13.04 | 5237.4 | Wide |
| 4. EWMA Volatility Baseline | 4.5 | 4.5 | 4.5 | 62.7% | 13.93 | 4998.99 | Wide |

## 2. Key Findings

- The **Production Ridge Conformal Engine** maintains the tightest Mean Range Width (`2.93%`) while achieving the highest Coverage-to-Width efficiency ratio (`33.86`).
