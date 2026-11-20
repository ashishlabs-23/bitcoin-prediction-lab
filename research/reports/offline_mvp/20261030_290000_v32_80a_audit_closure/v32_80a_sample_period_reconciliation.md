# V32.80A — Sample Period Reconciliation & Coverage Audit

**Milestone:** BTCognitive V32.80A — Audit Closure Addendum  
**Generated:** 2026-10-30T17:30:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report resolves **Issue B** raised in the Manager's V32.80 Ruling by reconciling the apparent discrepancy between the **4.67-year dataset span** and the **under-2-year span** (January 2023–December 2024) containing all 64 qualifying episodes.

### Root Cause Identified:
The 4.67-year dataset (`data/raw/binance_funding_2022_2026.parquet`) covers 2022-01-01 to 2026-09-01. However:
1. **In 2022:** The market was in a deep post-Luna / FTX bear market. Positive funding rates **never exceeded the default $+0.0001$ baseline rate** ($\max = 0.000100$, or $+10.95\%$ ann). The $+25\%$ ann threshold ($+0.000228$) was never breached once in 2022.
2. **In 2025–2026:** In this local historical parquet dataset, funding rates in 2025 and 2026 are identically capped at $+0.000100$ ($\max = 0.000100$).
3. **In 2023–2024:** Only during 2023 and 2024 did Binance BTCUSDT perpetual funding rates uncap and reach extreme contango levels ($\max = 0.000552$ in 2023; $\max = 0.000881$ in 2024).

Therefore, the entire 4.67-year dataset was evaluated without any artificial date exclusions. The concentration of the 64 episodes in 2023–2024 is an **inherent empirical characteristic of the data**, not an undocumented filtering artifact.

---

## 2. Dataset Boundaries & Overlap Analysis

| Dataset | File Path | Start Timestamp (UTC) | End Timestamp (UTC) | Total Observations |
|---|---|---|---|---|
| **Authoritative OHLCV Checkpoint** | `data/raw/ohlcv_checkpoint_42233_bars.parquet` | 2022-01-01 00:00:00 | 2026-10-26 16:00:00 | 42,233 1H bars |
| **Binance Funding Rates** | `data/raw/binance_funding_2022_2026.parquet` | 2022-01-01 00:00:00 | 2026-09-01 00:00:00 | 5,113 8H settlements |
| **Genuine Overlapping Period** | Evaluated Window | **2022-01-01 00:00:00** | **2026-09-01 00:00:00** | **40,897 1H bars (5,113 8H)** |
| **Excluded Tail Gap** | OHLCV post-funding freeze | 2026-09-01 01:00:00 | 2026-10-26 16:00:00 | 1,336 1H bars (55.6 days) |

**Tail Gap Verification:**
The 55.6-day period (1,336 bars) from 2026-09-01 to 2026-10-26 was strictly excluded from analysis because funding data is absent. No forward filling or synthetic imputation was performed.

---

## 3. Annual Distribution of Funding Rates and Episodes

Below is the verified census of the full 5,113 settlements in `binance_funding_2022_2026.parquet`:

| Calendar Year | Total 8H Rows | Min Funding Rate | Max Funding Rate | Mean Funding Rate | Rows $\ge +25\%$ Ann ($+0.000228$) | Rows $\le -25\%$ Ann ($-0.000228$) | Distinct Short Episodes (24h cooldown) | Distinct Long Episodes (24h cooldown) |
|---|---|---|---|---|---|---|---|---|
| **2022** | 1,095 | $-0.001192$ | $+0.000100$ | $+0.000038$ | **0** | **5** | **0** | **3** |
| **2023** | 1,095 | $-0.000110$ | $+0.000552$ | $+0.000072$ | **34** | **0** | **7** | **0** |
| **2024** | 1,098 | $-0.000112$ | $+0.000881$ | $+0.000109$ | **110** | **0** | **57** | **0** |
| **2025** | 1,095 | $-0.000122$ | $+0.000100$ | $+0.000047$ | **0** | **0** | **0** | **0** |
| **2026** (to Sep 1) | 730 | $-0.000152$ | $+0.000100$ | $+0.000024$ | **0** | **0** | **0** | **0** |
| **Total** | **5,113** | **$-0.001192$** | **$+0.000881$** | **$+0.000060$** | **144** | **5** | **64** | **3** |

### Key Observations:
1. **Short Arm (64 Episodes):**
   - 2022: 0 episodes (funding never exceeded $+0.0001$)
   - 2023: 7 episodes (first occurs January 14, 2023)
   - 2024: 57 episodes (ETF launch euphoria, heavy institutional contango)
   - 2025–2026: 0 episodes (capped at $+0.000100$ in this dataset)
   - **Total Short Episodes:** $0 + 7 + 57 + 0 + 0 = \mathbf{64}$.
2. **Long Arm (3 Episodes):**
   - 2022: 3 distinct episodes (May 12 Luna collapse; Nov 9–10 FTX collapse)
   - 2023–2026: 0 episodes
   - **Total Long Episodes:** $3 + 0 + 0 + 0 + 0 = \mathbf{3}$.

---

## 4. Reconciling the 4.67-Year Narrative

- The statement *"64 episodes over approximately 4.67 years"* meant that the search spanned the entire 4.67-year window (2022–2026).
- However, because the threshold $+0.000228$ was **never triggered in 2022, 2025, or 2026**, all 64 positive episodes occurred within a 23-month window from **January 14, 2023 to December 9, 2024**.
- This makes the strategy even more regime-dependent than initially described:
  - It was completely dormant for the first 12 months.
  - It generated occasional signals in 2023 ($N=7$).
  - It generated clustered signals in 2024 ($N=57$).
  - It went completely dormant again post-December 2024 in this dataset.

This explains why H1 (first 32) and H2 (second 32) split across March 2024:
- **H1 (32 episodes):** 2023-01-14 to 2024-03-09 (14 months, $-39.02\text{ bps}$ net).
- **H2 (32 episodes):** 2024-03-10 to 2024-12-09 (9 months, $+52.62\text{ bps}$ net).

This reconciliation closes **Issue B** completely.

