# BTCognitive V24 — Governed Prospective Evaluation Protocol

**Specialist Role:** Agent D (Prospective Evidence & Monitoring Lead)  
**Date:** 19 October 2026  
**Status:** Protocol Frozen — Evidence Collection In Progress (`COLLECTING`)  
**Ledger Path:** `data/prospective_forecast_ledger.jsonl`  

---

## 1. Executive Summary & Epistemic Principle

Prospective evidence constitutes the highest standard of empirical validation in quantitative forecasting. Retrospective replay, out-of-sample holdout sets, and backtests inevitably suffer from researcher degree of freedom, data leakage, and selection bias.

### Core Protocol Tenet:
**Zero Post-Hoc Retuning:** A forward observation qualifies as confirmatory evidence **only** if the model parameters, features, and target definitions were permanently frozen prior to the generation of the forecast origin $t_{\text{origin}}$. Realized prices are appended only after target maturity $t_{\text{maturity}} = t_{\text{origin}} + h$.

---

## 2. Frozen Horizon & Target Definitions

The evaluation protocol freezes four operational horizons:

| Horizon Code | Horizon ($h$) | Target Definition | Realized Target Expression | Preregistered Baseline | Allowed Challenger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`1h`** | 1 Hour | Closed spot price at $t+1\text{h}$ | $P_{t+1\text{h}}$ | Persistence: $\hat{P}_{t+1\text{h}} = P_t$ | Ridge L2 (alpha=100.0) |
| **`4h`** | 4 Hours | Closed spot price at $t+4\text{h}$ | $P_{t+4\text{h}}$ | Persistence: $\hat{P}_{t+4\text{h}} = P_t$ | Ridge L2 (alpha=100.0) |
| **`24h`** | 24 Hours | Closed spot price at $t+24\text{h}$ | $P_{t+24\text{h}}$ | Persistence: $\hat{P}_{t+24\text{h}} = P_t$ | Ridge L2 (alpha=100.0) |
| **`168h`** | 168 Hours (7d) | Closed spot price at $t+168\text{h}$ | $P_{t+168\text{h}}$ | Persistence: $\hat{P}_{t+168\text{h}} = P_t$ | Ridge L2 (alpha=100.0) |

*Important Target Separation:* The price forecast protocol ($P_{t+h}$) is strictly separated from the HAR-RS-DOW volatility model, which forecasts 7-day annualized realized variance (`rv7d_var_ann`).

---

## 3. Non-Overlapping Clean Block Criteria & Statistical Power

### Definition of a Clean Non-Overlapping Block:
Two forward forecasts $i$ and $j$ for horizon $h$ are non-overlapping if and only if:
$$|t_{\text{origin}, j} - t_{\text{origin}, i}| \ge h$$
Forecasts issued at high frequency (e.g., hourly updates for a 24-hour horizon) share $23/24$ of their error paths and exhibit severe serial correlation. While high-frequency snapshots may be recorded for real-time monitoring, **confirmatory statistical tests must be computed exclusively on non-overlapping clean blocks**.

### Governance Hurdle vs. Statistical Power:
- **Governance Threshold:** A minimum of **100 clean non-overlapping blocks** must be recorded before an official confirmatory gate decision can be rendered.
- **Calendar Time Required:**
  - 1-hour horizon: 100 blocks = 100 hours (~4.2 days).
  - 4-hour horizon: 100 blocks = 400 hours (~16.7 days).
  - 24-hour horizon: 100 blocks = 2,400 hours (~100 calendar days).
  - 168-hour (7d) horizon: 100 blocks = 16,800 hours (~700 calendar days / 1.9 years).
- **Statistical Power Assessment:** Reaching 100 blocks does not automatically prove superiority. Under Diebold-Mariano / HLN testing with Student's $t_{99}$, detecting a tiny skill advantage (e.g., < 0.1% improvement over persistence in BTCUSD) requires several thousand independent blocks to achieve 80% power at $\alpha=0.05$. Therefore, 100 blocks serves as an entry hurdle for formal review, not an automatic release trigger.

---

## 4. Current Prospective Ledger Census

An audit of `data/prospective_forecast_ledger.jsonl` was conducted on 19 October 2026:
- **Total Records Logged:** 11 entries.
- **`24h` Horizon:**
  - Historical closed entries: Row 1 (Aug 31, resolved) and Row 2 (Oct 15, resolved).
  - Entries 4, 6, 8, 10 issued on Oct 15–16 are overlapping within the same 24-hour window.
  - **Clean Non-Overlapping Mature Blocks:** **1 block** (Aug 31 to Oct 15).
- **`168h` Horizon:**
  - 5 entries issued between Oct 15 and Oct 16 maturing between Oct 22 and Oct 23.
  - **Clean Mature Blocks:** **0 blocks** (all pending maturity).
- **Official Ledger Status:** **`COLLECTING`** (1 / 100 blocks for 24h, 0 / 100 blocks for 168h).

---

## 5. Ledger Integrity & Write Governance

1. **Append-Only Immutability:** `data/prospective_forecast_ledger.jsonl` is an append-only JSON Lines file. No past origin or forecast record may be modified or deleted.
2. **Delayed Outcome Resolution:** When a forecast reaches $t_{\text{maturity}}$, a resolution worker appends the realized closing price, actual return, absolute error, and directional outcome.
3. **Idempotency:** Re-running the evaluation or resolution worker must never create duplicate entries or alter existing prediction fields.
