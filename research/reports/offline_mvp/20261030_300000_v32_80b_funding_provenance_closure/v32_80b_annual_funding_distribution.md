# V32.80B — Annual Funding Rate Distribution Analysis (Workstream 1)

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T17:50:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report performs a comprehensive, yearly statistical census of `data/raw/binance_funding_2022_2026.parquet` ($5,113$ rows, spanning 2022-01-01 00:00 UTC to 2026-09-01 00:00 UTC).

### Core Finding on the $+0.000100$ Level:
We explicitly distinguish among three distinct mathematical properties:
1. **Is every positive value capped at $+0.000100$?**
   - **2022:** **YES.** No positive value exceeds $+0.000100$ ($\max = 0.000100$).
   - **2023:** **NO.** $69$ settlements exceed $+0.000100$, up to $+0.000552$.
   - **2024:** **NO.** $213$ settlements exceed $+0.000100$, up to $+0.000881$.
   - **2025:** **YES.** No positive value exceeds $+0.000100$ ($\max = 0.000100$).
   - **2026:** **YES.** No positive value exceeds $+0.000100$ ($\max = 0.000100$).
2. **Do all observations equal $+0.000100$?**
   - **NO.** In all years, there is a rich continuum of values between $0$ and $+0.000100$, as well as negative rates. For example, in 2025, there are $874$ unique values and only $17.17\%$ equal $+0.000100$. In 2026, only $6.71\%$ equal $+0.000100$.
3. **What does $+0.000100$ represent?**
   - Per Binance documentation, $+0.000100$ ($0.01\%$ per 8 hours) is the **default baseline interest rate component**. When the premium index fluctuates within the $\pm 0.05\%$ clamp window around the interest rate, the total funding rate clamps exactly to $+0.000100$.
   - However, the fact that positive rates in 2022, 2025, and 2026 are **strictly bounded from above by $+0.000100$** while 2023 and 2024 exhibit heavy right-tail excursions represents an **empirical and provenance asymmetry** that must be scrutinized.

---

## 2. Year-by-Year Statistical Census

| Metric | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep 1) | Full Dataset (2022–2026) |
|---|---|---|---|---|---|---|
| **Total Settlements ($N$)** | 1,095 | 1,095 | 1,098 | 1,095 | 730 | **5,113** |
| **Minimum Rate** | $-0.001192$ | $-0.000110$ | $-0.000112$ | $-0.000122$ | $-0.000152$ | **$-0.001192$** |
| **Maximum Rate** | **$+0.000100$** | **$+0.000552$** | **$+0.000881$** | **$+0.000100$** | **$+0.000100$** | **$+0.000881$** |
| **Mean Rate** | $+0.000038$ | $+0.000072$ | $+0.000109$ | $+0.000047$ | $+0.000024$ | **$+0.000060$** |
| **Median Rate** | $+0.000051$ | $+0.000083$ | $+0.000100$ | $+0.000048$ | $+0.000029$ | **$+0.000060$** |
| **Standard Deviation** | $0.000082$ | $0.000068$ | $0.000119$ | $0.000041$ | $0.000049$ | **$0.000084$** |
| **10th Percentile (P10)** | $-0.000049$ | $-0.000000$ | $+0.000008$ | $-0.000006$ | $-0.000044$ | **$-0.000017$** |
| **25th Percentile (P25)** | $+0.000006$ | $+0.000029$ | $+0.000052$ | $+0.000019$ | $-0.000006$ | **$+0.000018$** |
| **75th Percentile (P75)** | $+0.000100$ | $+0.000100$ | $+0.000100$ | $+0.000083$ | $+0.000059$ | **$+0.000100$** |
| **90th Percentile (P90)** | $+0.000100$ | $+0.000100$ | $+0.000223$ | $+0.000100$ | $+0.000088$ | **$+0.000100$** |
| **95th Percentile (P95)** | $+0.000100$ | $+0.000147$ | $+0.000344$ | $+0.000100$ | $+0.000100$ | **$+0.000144$** |
| **99th Percentile (P99)** | $+0.000100$ | $+0.000348$ | $+0.000644$ | $+0.000100$ | $+0.000100$ | **$+0.000424$** |

---

## 3. Rate Bracket Decomposition

| Condition | 2022 | 2023 | 2024 | 2025 | 2026 | Full Dataset |
|---|---|---|---|---|---|---|
| **$> +0.000100$ ($> 10\text{ bps}$)** | **0** ($0.0\%$) | **69** ($6.3\%$) | **213** ($19.4\%$) | **0** ($0.0\%$) | **0** ($0.0\%$) | **282** ($5.5\%$) |
| **$== +0.000100$ ($10\text{ bps}$ default)** | **337** ($30.8\%$) | **422** ($38.5\%$) | **462** ($42.1\%$) | **188** ($17.2\%$) | **49** ($6.7\%$) | **1,458** ($28.5\%$) |
| **$0 < x < +0.000100$** | **516** ($47.1\%$) | **493** ($45.0\%$) | **331** ($30.1\%$) | **766** ($70.0\%$) | **473** ($64.8\%$) | **2,579** ($50.4\%$) |
| **$\le 0$ (Negative or Zero)** | **242** ($22.1\%$) | **111** ($10.1\%$) | **92** ($8.4\%$) | **141** ($12.9\%$) | **208** ($28.5\%$) | **794** ($15.5\%$) |
| **Unique Values** | 747 | 653 | 628 | 874 | 670 | **2,836** |
| **Consecutive Identical Repeats** | 222 | 339 | 370 | 120 | 21 | **1,072** |

---

## 4. Key Analytical Insights

1. **Not a Degenerate Constant:** In 2025 and 2026, the series is **not** a frozen constant of $0.000100$. Over $64\%$ to $70\%$ of all observations fluctuate continuously below $0.000100$ with 8 decimal places of floating-point precision ($874$ unique values in 2025).
2. **Asymmetric Upper Truncation:**
   - In 2023 and 2024, funding rates frequently surged above $+0.000100$, reaching $+0.000881$ ($+96.5\%$ annualized).
   - In 2022, 2025, and 2026, the rate never once exceeded $+0.000100$.
   - This upper bound coincides with Binance's interest rate component $I = 0.01\% = 0.000100$.
3. **The Provenance Question:** Did Binance BTCUSDT perpetual funding rates in reality never trade above $+0.000100$ in 2025–2026 (despite Bitcoin trading between $\$75\text{k}$ and $\$125\text{k}$ during this period), or does the acquisition pipeline have an issue? This question is investigated in Workstream 2 and 5.

