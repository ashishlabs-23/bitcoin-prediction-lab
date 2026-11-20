# V32.79 Phase 0 — Manager Handover Report
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30T16:40 UTC  
**Lead Orchestrator:** Antigravity (Phase 0 only, no empirical experiments)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## Executive Summary

Phase 0 is **complete**. Ten deliverables have been written. The data provenance audit reveals a **critical synthetic data finding** that structurally blocks two of the four proposed research hypotheses, and independently confirms the remaining two as blocked by data absence.

**Phase 0 Determination: `BLOCKED_BY_PROVENANCE`** (for three of four hypotheses)

One hypothesis — $H_{\text{Funding}}$ — is **provisionally approachable** with a narrowly defined protocol using only real, verified local data.

---

## 1. Environment Verification (Phase 0 Step 1)

| Property | Value |
|---|---|
| Branch | `main` |
| HEAD commit | `25d483f` |
| Modified/untracked files | 342 (all preserved) |
| Test suite health | 79/79 passing (last confirmed run) |
| Python environment | `.venv_win\Scripts\python.exe` |
| External API calls made | **ZERO** |
| Protected datasets modified | **NONE** |
| Analysis ABSTAIN gate | **UNTOUCHED** |
| Prospective runner | **FROZEN at 7/100 blocks — NOT restarted** |

---

## 2. Eight-Workstream Findings Summary

### Workstream A — Funding Dataset (PROVISIONALLY USABLE)

| Finding | Detail |
|---|---|
| Instrument | **BTCUSDT** (Binance USDⓈ-M perpetual) throughout. Zero COIN-M mixing. |
| Settlement interval | **Uniformly 8h** throughout. Sub-millisecond jitter only. No genuine non-8h settlements. |
| Date range | 2022-01-01 → 2026-09-01 (5,113 rows) |
| Coverage gap | **51-day tail gap** — OHLCV extends to 2026-10-26, funding only to 2026-09-01 |
| Mark price quality | **2,005 zeros (all 2022)** — funding rate populated; mark price missing |
| Available_time field | **ABSENT** — timestamp represents settlement confirmation time |
| Empirical median rate | **+0.006%/8h** (not +0.010% as assumed in V32.77 — prior was conservative by 67%) |
| Causal status | ✅ Confirmed funding rate at $t$ is causally available for bars at $t+\epsilon$ |

### Workstream B — Macro Feature Lineage (CRITICAL FINDING)

> [!CAUTION]
> **`data/processed/multi_regime_features.parquet` is entirely SYNTHETIC. Built from `np.random.normal()` simulated price paths with `np.random.seed(42)`. Not real BTCUSD historical data.**

| Finding | Detail |
|---|---|
| Data source | Stochastic simulation (`research/multi_regime_dataset.py`) |
| OHLCV used | NO — synthetic paths from regime-calibrated Gaussian draws |
| High/Low/Volume | Also simulated from same random seed |
| Regime labels | Date-range only — zero lookahead, but R2/R3 boundaries are retrospectively defined |
| MFE/MAE | Forward-looking outcomes (correctly treated as targets, not inputs) |
| Validation IC | Near-zero (expected for simulated i.i.d. returns) |
| Evidential value | **NONE** — simulation results cannot substitute for real-data evaluation |

### Workstream C — ETF Flow Data (BLOCKED BY PROVENANCE)

No ETF/ETP flow dataset exists locally. Search across all 407 data files confirmed absence. $H_{\text{ETF}}$ is blocked. Even with data, reverse causality (price → flows) must be established via Granger causality before any strategy experiment.

### Workstream D — Macro Event Calendar (BLOCKED BY PROVENANCE)

No FOMC/CPI calendar with sub-hour UTC timestamps exists locally. $H_{\text{Macro\_Abstain}}$ requires exact release times for a valid abstention filter. Blocked.

### Workstream E — OHLCV Hash Verification (PASS)

| File | Expected Hash | Actual Hash | Status |
|---|---|---|---|
| `ohlcv_checkpoint_42233_bars.parquet` | `f5c15cb11b9d51cf...` | `f5c15cb11b9d51cf...` | ✅ MATCH |
| `ohlcv_version_42326_bars.parquet` | `ba06fb533c0b5338...` | `ba06fb533c0b5338...` | ✅ MATCH |

Both frozen datasets are intact and unmodified since V32.76.

### Workstream F — Cost Reconciliation (FROZEN)

| Parameter | Value |
|---|---|
| Binance VIP0 round-trip | **24 bps** (confirmed, 21 bps figure superseded) |
| Coinbase Advanced round-trip | **87 bps** (confirmed, 84 bps figure superseded) |
| Binance BEP (3%/1.5% barrier) | **38.7%** (Manager-corrected, verified) |
| Coinbase BEP (3%/1.5% barrier) | **52.7%** (Manager-corrected, verified) |
| Funding drag (empirical) | **+0.006%/8h** (prior reports used 0.010%/8h — conservative) |

The 21/84 bps figures are permanently superseded by 24/87 bps.

### Workstream G — Statistical Protocol (FROZEN)

| Parameter | Value |
|---|---|
| Multiple comparisons (K) | ≤ 159 testable configurations |
| Bonferroni threshold at α=0.05 | 0.000314 |
| DM-HLN correction | Required — Student's $t_{T-1}$ reference |
| Newey-West bandwidth (24h) | 31 lags |
| Newey-West bandwidth (72h) | 93 lags |
| OOS window status | EXPLORATORY ONLY |
| Prospective blocks | 7 of 100 — NOT_STARTED for confirmatory gate |
| N_eff (24h, 10,521-bar window) | ~438 non-overlapping observations |
| N_eff (72h) | ~146 |
| N_eff (168h) | ~62 — **UNDERPOWERED** |

### Workstream H — Red-Team (STRUCTURAL BLOCKS CONFIRMED)

| Hypothesis | Red-Team Verdict |
|---|---|
| $H_{\text{ETF}}$ | **BLOCKED** — no data, reverse causality unresolved |
| $H_{\text{Funding}}$ | **CONDITIONALLY APPROACHABLE** — 24h only, Binance only, extreme quantile pre-specified |
| $H_{\text{Macro}}$ | **STRUCTURALLY BLOCKED** — OOS window is 100% Regime 4; R2/R3 hindsight in boundaries |
| $H_{\text{Macro\_Abstain}}$ | **BLOCKED** — no event calendar |

---

## 3. Phase 0 Determination

> [!IMPORTANT]
> **Overall Phase 0 Determination: `BLOCKED_BY_PROVENANCE`**
> 
> Three of four hypotheses are blocked by data absence or structural invalidity. One hypothesis ($H_{\text{Funding}}$) is provisionally approachable subject to the strict protocol below.

**Detailed determinations by hypothesis:**

| Hypothesis | Determination | Primary Reason |
|---|---|---|
| $H_{\text{ETF}}$ | `BLOCKED_BY_PROVENANCE` | No local ETF data; acquisition prohibited; reverse causality unresolved |
| $H_{\text{Funding}}$ | `READY_FOR_NARROWLY_SCOPED_EXPLORATORY_RESEARCH` | Real data exists locally; causal availability confirmed; requires 24h protocol |
| $H_{\text{Macro}}$ | `BLOCKED_BY_INSTRUMENT_MISMATCH` | Multi-regime features are synthetic; OOS window is 100% Regime 4; hindsight in regime boundaries |
| $H_{\text{Macro\_Abstain}}$ | `BLOCKED_BY_PROVENANCE` | No FOMC/CPI calendar; no verifiable publication timestamps |

---

## 4. Recommended Protocol for V32.79 Phase 1 (If Approved)

If the Manager approves $H_{\text{Funding}}$ exploratory research, the following protocol is pre-specified:

### 4.1 Data Sources (Real Only)
- Price: `data/raw/ohlcv_checkpoint_42233_bars.parquet` (42,233 bars, 2022-01-01 → 2026-10-26)
- Funding: `data/raw/binance_funding_2022_2026.parquet` (5,113 rows, 2022-01-01 → 2026-09-01)
- Evaluation window: Restricted to overlap period (2022-01-01 → 2026-09-01)

### 4.2 Pre-Specified Primary Test
- **Signal:** Funding rate crosses the 90th percentile of its 180-day rolling window → contrarian short entry
- **Barrier:** 3% TP / 1.5% SL (asymmetric, Manager-approved barrier)
- **Horizon:** 24h (maximum)
- **Cost scenario (primary):** Binance VIP0 = 24 bps
- **Cost scenario (conservative):** Coinbase Advanced = 87 bps
- **Net funding drag:** Subtract actual 8h funding payments accrued during 24h hold

### 4.3 Acceptance Criteria
| Gate | Threshold |
|---|---|
| TP rate (Binance) | > 38.7% (BEP) |
| TP rate (Coinbase) | > 52.7% (BEP, secondary) |
| Net PnL (Binance) | > 0 bps after all costs |
| DM-HLN p-value | < 0.000314 (Bonferroni-corrected) |
| DSR | > 0 |
| Minimum qualifying events | ≥ 100 at chosen quantile threshold |

### 4.4 What This Is NOT
- Not a trading strategy — OFFLINE_RESEARCH_ONLY
- Not a model training run
- Not promotion of any model
- Not a prospective confirmatory test (7/100 blocks, confirmatory gate not met)
- Not applicable to Regime 2 or Regime 3 conditioning (OOS window is entirely R4)

---

## 5. Four Governed Release Decisions

| Decision | Status |
|---|---|
| **Research Experiment** | V32.79 Phase 0: `INCONCLUSIVE` — provisionally blocked. Phase 1 pending Manager authorization for $H_{\text{Funding}}$ only. |
| **Prospective Evidence** | `NOT_STARTED` — 7/100 blocks; runner frozen; cannot reach confirmatory gate. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` — unchanged. |
| **Live Trading** | `DISABLED` — unchanged. |

---

## 6. Deliverables Checklist

| # | Deliverable | Status |
|---|---|---|
| 1 | `v32_79_phase0_dataset_inventory.md` | ✅ Written |
| 2 | `v32_79_funding_provenance_audit.md` | ✅ Written |
| 3 | `v32_79_macro_feature_lineage.md` | ✅ Written |
| 4 | `v32_79_etf_flow_availability_audit.md` | ✅ Written |
| 5 | `v32_79_macro_event_calendar_audit.md` | ✅ Written |
| 6 | `v32_79_execution_cost_reconciliation.md` | ✅ Written |
| 7 | `v32_79_statistical_protocol_review.md` | ✅ Written |
| 8 | `v32_79_red_team_audit.md` | ✅ Written |
| 9 | `v32_79_protected_hash_verification.json` | ✅ Written |
| 10 | `v32_79_phase0_manager_handover.md` | ✅ **This document** |

All deliverables written to:  
`BTCognitive/research/reports/offline_mvp/20261030_260000_v32_79_phase0_provenance_audit/`

---

## 7. Key Decision Required from Manager

**The Manager must decide:**

1. **Authorize V32.79 Phase 1 for $H_{\text{Funding}}$ only?**  
   The pre-specified protocol is documented in Section 4 above. This would be an exploratory experiment only — not confirmatory.

2. **Or halt V32.79 entirely given that only one hypothesis survived Phase 0?**  
   The expected value of Phase 1 research is uncertain. $H_{\text{Funding}}$ is the most defensible but still requires a ~3pp improvement over the 35-36% TP rate observed in prior unconditional strategies to break even at Binance fees.

3. **Should the prospective runner be restarted?**  
   Without explicit Manager authorization, the runner remains frozen at 7/100. This is the single largest governance blocker for reaching a confirmatory gate.

---

*V32.79 Phase 0 complete. Awaiting Manager decision.*  
*No external data fetched. No datasets modified. No models trained. All protected files verified intact.*

