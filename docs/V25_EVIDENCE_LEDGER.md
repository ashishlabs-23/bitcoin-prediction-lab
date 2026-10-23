# BTCognitive V25 — Evidence Ledger & Multi-Agent Investigation Log

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Baseline Commit:** `01f87cad6d189eb4b4c70c0a52e4e759ed8d8eba`  
**Branch:** `main`  
**Lead Coordinator:** Multi-Agent Research Orchestrator  

---

## 1. Investigation Protocol & Governance Standards

Every finding in this ledger represents an independently reproduced investigation adhering to BTCognitive Epistemic Principles:
1. **Zero Unverified Claims:** A claim is verified only when executed code, database queries, mathematical reproductions, or captured runtime evidence confirm it.
2. **Zero Mutation Baseline:** All forensic audits are performed read-only or in isolated working copies.
3. **No Synthetic Fabrication:** Unconfigured notification channels or absent data feeds are reported honestly (`NOT_CONFIGURED` / `UNAVAILABLE`).
4. **Target Separation:** Future price estimates ($P_{t+h}$) are strictly segregated from HAR-RS-DOW volatility estimates (`rv7d_var_ann`).
5. **Strict Non-Execution:** Live trading and paper order mutations remain permanently disabled (`DISABLED_ANALYSIS_ONLY`).

---

## 2. Evidence Register

| Finding ID | Claim Investigated | Source File / Report | Specialist Owner | Severity | Expected Behavior | Observed Behavior | Resolution / Corrective Action | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F-V25-001** | Strategy transition counts vs. friction: 87 bps round-trip friction applied as 43.5 bps per event vs turnover units and reversals | V24 strategy report, `research/run_v18_price_and_strategy_tournament.py` | Agent A (Strategy) | HIGH | Explicit separation of signal events, position transitions, and turnover units; reversals charged as 2 transitions | In Dual-SMA, 100 transition events contain 99 reversals (199 turnover units). V24 applied 43.5 bps to event count instead of turnover volume | Standardized backtesting accounting separating events, turnover units, and round trips; delivered `docs/V25_STRATEGY_ECONOMICS_RECONCILIATION.md` and `v25_canonical_strategy_manifest.json` | `VERIFIED_RESOLVED` |
| **F-V25-002** | Forecast model comparison: Nested structure of Persistence vs Ridge L2; Diebold-Mariano vs Clark-West (2007) test | V24 forecast report, `engine/price_forecast_engine.py` | Agent B (Econometrics) | HIGH | Evaluation of nested model hypothesis test; verification of Clark-West MSPE adjustment and origin windowing | Ridge nests persistence under $\beta=0$. Clark-West adjusted stats remain strictly negative (CW t = -0.82 to -0.29, $p > 0.60$); persistence remains undefeated | Delivered `docs/V25_FORECAST_VALIDATION_AND_MODEL_COMPARISON.md` and `v25_canonical_forecast_manifest.json` | `VERIFIED_RESOLVED` |
| **F-V25-003** | Prospective evidence governance: protocol freeze, ledger isolation, and 100 non-overlapping blocks hurdle | `data/prospective_forecast_ledger.jsonl`, `engine/prospective_evidence_pipeline.py` | Agent C (Prospective) | HIGH | Untouched forward observations, separate realized resolution, non-overlapping block definition | 11 records logged; 1 clean mature 24h block, 0 mature 168h blocks; status firmly `COLLECTING` | Delivered `docs/V25_PROSPECTIVE_RESEARCH_MONITORING.md` and verified immutability / idempotency | `VERIFIED_RESOLVED` |
| **F-V25-004** | Research-alert reliability: 60s background lifespan worker, deduplication, restart survival, and honest channel status | `api/server.py`, `api/notifications.py`, `data/research_alert_state.json` | Agent D (Alerts) | HIGH | Single worker instance, persisted state surviving restarts, truthful NOT_CONFIGURED | Worker starts in lifespan; state persists to disk; unconfigured channels return `NOT_CONFIGURED` | Delivered `docs/V25_RESEARCH_ALERT_RUNTIME_AND_DELIVERY.md` with explicit state distinction | `VERIFIED_RESOLVED` |
| **F-V25-005** | Historical database & CSV equality: 5,622 records in SQLite and CSV; 1,968 directional trades and 3,654 non-directional nulls | `market_memory.db`, `market_memory.csv`, `backups/v23_pre_reconciliation_backup` | Agent E (Data Integrity) | CRITICAL | Canonical field-level equality across all 5,622 records; backup hashes verified | Exactly 5,622 rows in both; 0 duplicate IDs; 0 scored non-directional; pre-backups verified | Delivered `docs/V25_DATA_INTEGRITY_REGRESSION.md`; zero unnecessary migrations executed | `VERIFIED_RESOLVED` |
| **F-V25-006** | Frontend & chart representation: Optional research markers toggle, legend, canonical MAE values, no order tickets | `web/app.js`, `web/index.html` | Agent F (Frontend) | MEDIUM | Pristine default chart, informative legend when toggled, canonical forecast MAEs | Audited via `/browser` at 1440x900 & 390x844; 0 order tickets; responsive card stacking verified | Delivered `docs/V25_FRONTEND_AND_CHART_VERIFICATION.md` with desktop & mobile screenshots | `VERIFIED_RESOLVED` |
| **F-V25-007** | Execution gate security and full repository regression health | Entire API surface, `tests/` | Agent G (Security & QA) | CRITICAL | Order endpoints disabled (HTTP 405/404); full test suite and frontend build pass | `/api/orders`, `/api/trade` fail closed (404/405); all core test suites pass, frontend build clean | Delivered `docs/V25_SECURITY_AND_FULL_REGRESSION.md` | `VERIFIED_RESOLVED` |
| **F-V25-008** | Independent red-team review: adversarial challenge of all V25 claims and artifacts | All V25 deliverables | Agent H (Red Team) | CRITICAL | Independent recalculations and verification of claims | Every claim validated against primary code and data; no unverified statements permitted | Delivered `docs/V25_INDEPENDENT_RED_TEAM_REVIEW.md` | `VERIFIED_RESOLVED` |

---

## 3. Final Release Decision

**Verdict:** **`V25_RESEARCH_OPERATIONS_VERIFIED_WITHIN_SCOPE`**
