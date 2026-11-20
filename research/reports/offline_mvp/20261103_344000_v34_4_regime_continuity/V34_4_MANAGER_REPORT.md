# BTCognitive V34.4 — Historical Continuity and Regime Robustness Research Manager Report

**Mission:** BTCognitive V34.4 — Historical Continuity and Regime Robustness Research  
**Date:** 2026-11-03  
**Status:** COMPLETE / GOVERNED  
**Role:** Senior Quantitative Research Manager  
**Branch:** `main` | **Git Commit:** `25d483f` (ahead 1 vs `origin/main`)  
**Trading Authorization:** `OFFLINE_RESEARCH_ONLY`  
**Live Trading:** `DISABLED`

---

## 1. Executive Summary & Authoritative Governed Decisions

Milestone V34.4 was initiated to resolve fundamental historical data continuity questions, reconcile the strategy performance divergence between the 2024 and 2026 Bitstamp windows, explain statistical inference discrepancies in volatility modeling, investigate conformal risk calibration failures, and conduct an unsparing adversarial red-team audit.

### Authoritative Governed Decisions
1. **Historical Coverage:** `HISTORICAL_COVERAGE_INSUFFICIENT`  
   Bitstamp unauthenticated public REST endpoints are protected by Imperva Incapsula WAF. Rapid pagination triggers TLS resets. The repository contains two isolated segments separated by an **828.5-day gap (19,883 missing hours)**. Contiguous multi-year coverage cannot be constructed via public REST.
2. **Regime Robustness:** `REGIME_DEPENDENCE_SUPPORTED`  
   The frozen HTF breakout strategy's early 2024 performance was an artifact of the single strongest Bitcoin spot ETF rally in recent history. Across both periods, applying identical causal screening funnels reveals **negative net expectancy** (-122.3 bps in 2024, -134.7 bps in 2026) under realistic assumed 70 bps friction.
3. **Volatility Forecasting:** `RISK_MODEL_ADVANTAGE_NOT_CONFIRMED`  
   The Holm-Bonferroni $p$-value discrepancy between V34.2 ($p = 0.2632$) and V34.3 ($p = 0.3948$) has been reconciled: both stem from the identical underlying test statistic ($t = -1.842, p_{\text{raw}} = 0.0658$) under 4-test vs. 6-test families. Neither achieves statistical significance ($\alpha = 0.05$).
4. **C2 Conformal Calibration:** `C2_CALIBRATION_FAILED`  
   The reported 93.90% coverage was an artifact of post-hoc selection bias over an un-prespecified 590-hour calm period. On the full 1,943-hour multi-regime sample, coverage is **78.02%** ($N_{\text{eff}} = 17.2$, CI `[55.8%, 96.5%]`). Furthermore, the 168-hour feedback latency renders online adaptive conformal inference unable to track sudden regime changes.
5. **Overall Research Status:** `RESEARCH_INCONCLUSIVE`  
   Zero models or strategies are eligible for production promotion. The system remains locked in `OFFLINE_RESEARCH_ONLY`.

---

## 2. Multi-Agent Workstream Summary

```
+-------------------------------------------------------------------------------------------------------+
|                                    BTCognitive V34.4 Research Flow                                    |
+-------------------------------------------------------------------------------------------------------+
|  Agent 1 & 2: Data Acquisition & Gap Audit                                                           |
|  - WAF blocked rapid REST pagination (Imperva Incapsula TLS reset).                                  |
|  - Confirmed 828.5-day gap (19,883 missing hours) between 2024 and 2026 segments.                     |
|  - Strict segment isolation: No rolling indicators computed across the gap.                         |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|  Agent 3: HTF Causal Screening Funnel                                                                |
|  - Enforced identical 6-stage funnel on both segments without lookahead bias.                         |
|  - 2024 Slice (1k bars): 3 trades, 33.3% win rate, -122.3 bps net expectancy, PF 0.25.              |
|  - 2026 Slice (4k bars): 14 trades, 21.4% win rate, -134.7 bps net expectancy, PF 0.29.             |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|  Agent 4: Regime Robustness Analysis                                                                  |
|  - Canonical regime proportions are macroscopically stable (~35% transition, ~20% bullish).          |
|  - 2024 bullish regime was high-persistence ETF momentum; 2026 was choppy liquidity traps.           |
|  - Descriptively supported, but trade count (N=17 total) is inferentially underpowered.              |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|  Agent 5: Volatility Forecast Econometrics                                                           |
|  - Raw DM-HLN t = -1.842, p = 0.0658. Holm p = 0.2632 (m=4) vs 0.3948 (m=6) both fail alpha=0.05.    |
|  - QLIKE delta of 0.0025 reconciled between Log-HAR (0.3951) and Linear-HAR (0.3976).                |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|  Agent 6: C2 Conformal & Delayed Feedback                                                            |
|  - 93.90% coverage exposed as post-hoc cherry-pick of 590h calm window.                             |
|  - Full sample coverage fails at 78.02% (nominal 90%).                                                |
|  - 168h feedback latency mathematically breaks online adaptive conformal updates.                    |
+-------------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
+-------------------------------------------------------------------------------------------------------+
|  Agent 7: Adversarial Red-Team Audit                                                                 |
|  - All 5 red-team challenges verified and sustained. Zero premature claims allowed.                 |
+-------------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Numerical Ledger

### A. Data Provenance & Cryptographic Signatures

| Dataset Descriptor | Segment 1 (2024 Slice) | Segment 2 (2026 Slice) |
| :--- | :--- | :--- |
| **Path** | `data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet` | `data/providers/bitstamp/BTCUSD_1h_v34_expanded.parquet` |
| **SHA-256** | `811c9704629d3b735643c0d931ad1998cf0604e9dd96b9790aaf1241ee807436` | `9e8d92a2db78a5c71737146713541c3db5f27d398684114f09d5db3a4493ec81` |
| **Row Count** | 1,000 | 4,000 |
| **Time Span (UTC)** | 2024-01-01 00:00 to 2024-02-11 15:00 | 2026-05-20 02:00 to 2026-11-02 17:00 |
| **Span Duration** | 41.6 days (1,000 hours) | 166.6 days (4,000 hours) |
| **Gap Duration** | **828.5 days (19,883 hours / 2.27 years)** between segments | N/A |

### B. HTF Causal Screening Funnel & Performance

| Funnel Stage / Metric | Segment 1 (2024 Slice) | Segment 2 (2026 Slice) |
| :--- | :--- | :--- |
| **Stage 1: Raw Breakout Candidates** | 22 | 76 |
| **Stage 2: Classified 4h Bars** | 250 | 1,001 |
| **Stage 3: Regime Compatible** | 5 | 20 |
| **Stage 4: 3-Bar Confirmed** | 5 | 20 |
| **Stage 5: Eligible Setups** | 4 | 14 |
| **Stage 6: Completed Trades** | **3** | **14** |
| **Win Rate (%)** | **33.3%** | **21.4%** |
| **Net Expectancy / Trade (assumed 70 bps)** | **-122.3 bps** | **-134.7 bps** |
| **Net Total Cumulative Return** | **-366.9 bps** | **-1,886.0 bps** |
| **Profit Factor** | 0.25 | 0.29 |
| **Maximum Drawdown** | 492.1 bps | 1,682.5 bps |
| **Mean MFE / MAE** | 102.2 bps / 142.2 bps | 163.2 bps / 282.5 bps |
| **Average Holding Duration** | 4.0 hours | 16.3 hours |
| **Monthly Signal Frequency** | 2.19 / month | 2.56 / month |
| **Market Exposure** | 1.2% | 5.7% |

### C. Volatility Forecasting & Econometrics

| Comparison / Metric | Formula / Source | Numerical Result | Inferential Status |
| :--- | :--- | :--- | :--- |
| **Raw DM-HLN $t$-statistic** | Loss differential / HAC std | $t = -1.842$ | $p_{\text{raw}} = 0.0658$ |
| **V34.2 Holm Adjusted $p$** | $m=4$ hypothesis family | $p_{\text{adj}} = 0.2632$ | **FAIL ($\alpha = 0.05$)** |
| **V34.3 Holm Adjusted $p$** | $m=6$ hypothesis family | $p_{\text{adj}} = 0.3948$ | **FAIL ($\alpha = 0.05$)** |
| **V34.1 QLIKE Benchmark** | Log-HAR with exponential link, L2 $\lambda=0.05$ | $0.3951$ | ~18% gain over OLS |
| **V34.2 / V34.3 QLIKE** | Linear-HAR unregularized | $0.3976$ | ~18% gain over OLS |
| **QLIKE Delta** | Truncation & regularization variance | $+0.0025$ (+0.63%) | Within sampling noise |

### D. Conformal Calibration (C2)

| Parameter / Metric | Full Sample (Multi-Regime) | Calm Sub-Slice (Cherry-Picked) |
| :--- | :--- | :--- |
| **Nominal Confidence Target** | 90.0% ($\alpha = 0.10$) | 90.0% ($\alpha = 0.10$) |
| **Empirical Coverage** | **78.02%** | **93.90%** |
| **Sample Size (Hours)** | 1,943 hours | 590 hours |
| **Effective Sample Size ($N_{\text{eff}}$)** | 17.2 | 97.1 |
| **Robust 95% Bootstrap CI** | **[55.84%, 96.45%]** | **[86.95%, 99.66%]** |
| **Feedback Latency** | **168 hours (7.0 days)** | 168 hours (7.0 days) |
| **Governed Decision** | **`C2_CALIBRATION_FAILED`** | **REJECTED (POST-HOC BIAS)** |

---

## 4. Deliverables Index

The following 9 governed files reside in `research/reports/offline_mvp/20261103_344000_v34_4_regime_continuity/`:
1. `V34_4_MANAGER_REPORT.md` (this report)
2. `V34_4_DATA_CONTINUITY_AUDIT.md` (Agent 1 & 2 data provenance and WAF audit)
3. `V34_4_HTF_RECONCILIATION.md` (Agent 3 screening funnel and trade ledger)
4. `V34_4_REGIME_ROBUSTNESS.md` (Agent 4 regime distribution and failure mode analysis)
5. `V34_4_FORECAST_RECONCILIATION.md` (Agent 5 Holm $p$ and QLIKE econometrics audit)
6. `V34_4_C2_DELAYED_FEEDBACK.md` (Agent 6 conformal prediction and latency audit)
7. `V34_4_ADVERSARIAL_REVIEW.md` (Agent 7 red-team stress test)
8. `V34_4_FINAL_ACCEPTANCE_MATRIX.md` (governed criteria evaluation)
9. `V34_4_EXPERIMENT_LEDGER.csv` (machine-readable experimental results)

And the primary brain artifact:
- `C:\Users\Ashish\.gemini\antigravity\brain\1ae7aeff-968f-4a42-b599-198389cab42b\V34_4_MANAGER_REPORT.md`

---

## 5. Next Steps for BTCognitive

1. **Obtain Official Data Archives:** Transition away from unauthenticated Bitstamp public REST scraping. Procure official historical trade archives (or licensed daily parquet drops) to bridge the 828-day gap legitimately.
2. **Strategy Redesign Gate:** The frozen HTF breakout strategy possesses no positive edge on unconditional Bitcoin data under 70 bps friction. Any future strategy exploration must be pre-registered and must address whipsaws in transition regimes.
3. **Volatility Model Baseline:** Retain standard HAR as the sole authorized baseline. Do not promote HAR-RS-DOW until prospective forward evaluation on 100+ non-overlapping blocks demonstrates statistically significant edge.
4. **Permanent Guardrail:** Live trading remains strictly `DISABLED`. System authorization is permanently locked in `OFFLINE_RESEARCH_ONLY`.

