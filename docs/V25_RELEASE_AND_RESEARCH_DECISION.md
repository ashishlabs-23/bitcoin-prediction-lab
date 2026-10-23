# BTCognitive V25 — Governed Release & Research Decision Report

**Final Release Verdict:** **`V25_RESEARCH_OPERATIONS_VERIFIED_WITHIN_SCOPE`**  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Baseline Git Commit:** `01f87cad6d189eb4b4c70c0a52e4e759ed8d8eba` on branch `main`  
**Execution Posture:** `PERMANENTLY DISABLED — ANALYSIS ONLY`  
**Authoritative Evidence Ledger:** `docs/V25_EVIDENCE_LEDGER.md`  

---

## 1. Release Acceptance Criteria Assessment

| Acceptance Criterion | Verification Standard | Observed Empirical Result | Release Status |
| :--- | :--- | :--- | :--- |
| **1. Strategy Turnover & Cost Units** | Distinguish events from turnover units ($\sum |s_t - s_{t-1}|$). Charge reversals 2 one-way executions ($87\text{ bps}$). | Verified in `docs/V25_STRATEGY_ECONOMICS_RECONCILIATION.md` and `experiments/results/v25_canonical_strategy_manifest.json`. Zero-exposure wins decisively. | `CRITERION_MET` |
| **2. Canonical Forecast Metrics** | Reproduce 1h, 4h, 24h metrics from raw parquet dataset hash `43c8881b...` on preregistered window $[20000, 35000]$. | Persistence MAE: $283.66 (1h), $560.48 (4h), $1,458.31 (24h). All reproduced identically. | `CRITERION_MET` |
| **3. Nested Econometric Testing** | Evaluate Clark-West (2007) nested model MSPE test alongside Diebold-Mariano / HLN. | Clark-West $t$-statistics remain strictly negative (-0.82 to -0.29, $p > 0.60$). Persistence unbeaten. | `CRITERION_MET` |
| **4. Database Integrity & Backups** | Verify 5,622 rows in SQLite and CSV, 1,968 directional trades, 3,654 non-directional nulls, and backups. | Exact match across all stores. Pre-reconciliation backups verified. Zero mutations executed. | `CRITERION_MET` |
| **5. Governed Prospective Ledger** | Append-only forward logging, separate realized outcomes, non-overlapping clean blocks. | 11 entries logged; 1 mature clean 24h block, 0 mature 168h blocks. Status: `COLLECTING`. | `CRITERION_MET` |
| **6. Research Alert Reliability** | Background lifespan worker (60s), 15m cooldown, restart persistence, honest channel delivery. | Lifespan starts and stops cleanly; state persists to `data/research_alert_state.json`; channels report `NOT_CONFIGURED`. | `CRITERION_MET` |
| **7. Live UI & Browser Verification** | `/browser` audit at 1440×900 and 390×844. Clean default chart, optional markers, zero order tickets. | Verified live DOM and screenshots. No trade buttons or paper execution forms exist. | `CRITERION_MET` |
| **8. Automated Regression Census** | Complete Python test census, frontend checks, and build. | 52/52 automated tests passed (100%). `npm run check`, `npm test`, and `npm run build` all passed. | `CRITERION_MET` |
| **9. Execution-Gate Security** | POST `/api/orders`, `/api/trade`, `/api/paper/order` fail closed (404/405). | Verified fail-closed across all direct routes, aliases, and admin endpoints. | `CRITERION_MET` |
| **10. Independent Red Team** | Adversarial verification of all claims without feature implementation. | Completed by Agent H (`docs/V25_INDEPENDENT_RED_TEAM_REVIEW.md`). Release recommended. | `CRITERION_MET` |

---

## 2. Four Explicit Governed Decisions

1. **Research Experiment Decision:**  
   `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`  
   - Persistence remains the undefeated future-price baseline across all evaluated horizons.
   - All active strategy candidates fail to beat the zero-exposure benchmark after accounting for realistic retail turnover friction (87 bps round-trip).
2. **Prospective Evidence Decision:**  
   `COLLECTING`  
   - 1 clean mature 24h block accumulated; 0 clean mature 168h blocks accumulated. The governance hurdle (100 blocks) has not yet matured.
3. **Model Authorization Decision:**  
   `OFFLINE_RESEARCH_ONLY`  
   - All experimental challengers (Ridge L2, HAR-RS-DOW, HAR-QLIKE-24h) remain strictly restricted to offline research and visualization.
4. **Live Trading Decision:**  
   `DISABLED`  
   - No execution capabilities exist. BTCognitive operates exclusively as a risk intelligence and market analysis terminal.

---

## 3. Residual Limitations & Declared Operational Boundaries

1. **Confirmatory Prospective Timeline:** Reaching 100 non-overlapping clean blocks will require ~100 calendar days for the 24-hour horizon and ~700 calendar days for the 168-hour horizon. Realized evidence will continue accumulating in `data/prospective_forecast_ledger.jsonl`.
2. **External Notification Channel Verification:** In environments where external webhook URLs or bot tokens are unconfigured, delivery status will honestly report `NOT_CONFIGURED`. Live dispatch testing is only conducted when authorized channels are supplied.
3. **Analysis-Only Scope:** The application permanently rejects paper trading workflows, order books, and broker API keys.
