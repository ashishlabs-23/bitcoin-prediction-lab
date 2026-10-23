# BTCognitive V26 — Evidence Ledger & Multi-Agent Investigation Log

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Baseline Commit:** `01f87cad6d189eb4b4c70c0a52e4e759ed8d8eba`  
**Branch:** `main`  
**Lead Coordinator:** Multi-Agent Research Orchestrator  

---

## 1. Investigation Protocol & Governance Standards

Every finding in this ledger represents a strictly reproducible investigation adhering to BTCognitive Epistemic Principles:
1. **Zero Unverified Claims:** A claim is verified only when executed code, database queries, mathematical reproductions, or captured runtime evidence confirm it.
2. **Zero Mutation Baseline:** All forensic audits are performed read-only or in isolated working copies.
3. **No Synthetic Fabrication:** Unconfigured notification channels or absent data feeds are reported honestly (`NOT_CONFIGURED` / `UNAVAILABLE`).
4. **Target Separation:** Future price estimates ($P_{t+h}$) are strictly segregated from HAR-RS-DOW volatility estimates (`rv7d_var_ann`).
5. **Strict Non-Execution:** Live trading and paper order mutations remain permanently disabled (`DISABLED_ANALYSIS_ONLY`).

---

## 2. Evidence Register

| Finding ID | Claim Investigated | Source File / Report | Specialist Owner | Severity | Expected Behavior | Observed Behavior | Resolution / Corrective Action | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F-V26-001** | HAC / Newey-West variance estimation in Diebold-Mariano & Clark-West tests | V25 report, `engine/price_forecast_engine.py` | Agent B (Econometrics) | HIGH | Dependence-aware long-run variance estimation using Bartlett kernel / Newey-West bandwidth | Prior evaluation used i.i.d. variance ($K=0$). Rerun with Newey-West HAC bandwidth ($K=12$ for 1h, $K=8$ for 4h, $K=6$ for 24h). Stats remain negative ($t_{\text{CW}} = -0.87$ to $-0.29$) | Standardized HAC Bartlett variance estimator; delivered `docs/V26_FORECAST_STATISTICS_AUDIT.md` and `v26_canonical_forecast_manifest.json` | `VERIFIED_RESOLVED` |
| **F-V26-002** | Strategy naming mismatch: Dual-SMA vs Dual-EMA implementation in `run_v18_price_and_strategy_tournament.py` | V25 report, `research/run_v18_price_and_strategy_tournament.py` | Agent C (Strategy) | MEDIUM | Label in reports must match underlying technical indicator rule (EMA vs SMA) | Code constructs `ema_24` and `ema_168`, which was called "Dual-SMA" in narrative reports. True Dual-SMA(24,168) yields -9,486.7 bps net | Reconciled label to Dual-EMA Crossover (24h/168h); documented both variants in `docs/V26_STRATEGY_COST_AND_EXECUTION_AUDIT.md` | `VERIFIED_RESOLVED` |
| **F-V26-003** | PRD requirement-to-code-to-test mapping and completion percentage reconciliation | Master PRD v1.0, v2.0, Traceability Matrix | Agent A (PRD Architecture) | HIGH | Exhaustive mapping of all canonical requirements to actual code, tests, and runtime state | 1,286 total tests collected in repository; previous reports cited 52-61 selected regression tests. PRD has 53 requirements across v1.0/v2.0 | Delivered `docs/V26_PRD_TRACEABILITY_MATRIX.md` with explicit statuses (`IMPLEMENTED_VERIFIED`, `FORMALLY_RESOLVED_FAIL_CLOSED`, etc.) | `VERIFIED_RESOLVED` |
| **F-V26-004** | BTC Market-Data Feature Gap Matrix & Prioritized Roadmap | Primary market data adapters, exchange APIs | Agent D (Market Data) | MEDIUM | Systematic gap analysis of derivatives, microstructure, order book depth, options IV, and macro data | Existing engine relies exclusively on spot OHLCV; funding rates, open interest, and order book imbalance are unexploited | Delivered `docs/V26_MARKET_DATA_FEATURE_GAP_MATRIX.md` and `docs/V26_PRIORITIZED_IMPLEMENTATION_ROADMAP.md` | `VERIFIED_RESOLVED` |
| **F-V26-005** | Probabilistic forecasting, calibration, and selective abstention gates | `models/`, `engine/scenario_contract_engine.py` | Agent E (Probabilistic Gates) | HIGH | Conformal risk intervals, P10/P50/P90 distributions, Brier scores, and explicit abstention triggers | Conformal C2 envelope active on HAR-RS-DOW; directional classification abstains on negative EV; interval width transparent | Delivered `docs/V26_CALIBRATION_AND_SELECTIVE_PREDICTION_AUDIT.md` | `VERIFIED_RESOLVED` |
| **F-V26-006** | Prospective evidence governance: protocol freeze, ledger isolation, and 100 non-overlapping blocks hurdle | `data/prospective_forecast_ledger.jsonl`, `engine/prospective_evidence_pipeline.py` | Agent F (Prospective Evidence) | HIGH | Untouched forward observations, separate realized resolution, non-overlapping block definition | 11 records logged; 1 clean mature 24h block, 0 mature 168h blocks; status firmly `COLLECTING` | Delivered `docs/V26_PROSPECTIVE_EVALUATION_AUDIT.md` | `VERIFIED_RESOLVED` |
| **F-V26-007** | Operations, API routes, alert delivery verification, and execution security | `api/`, `tests/` | Agent G (Security & Operations) | CRITICAL | Order endpoints disabled (HTTP 405/404); distinguish detection, dispatch, and delivery | Lifespan starts worker; channels report `NOT_CONFIGURED` when unconfigured; full test census documented | Delivered `docs/V26_API_OPERATIONS_AND_SECURITY_AUDIT.md` | `VERIFIED_RESOLVED` |
| **F-V26-008** | Browser visual verification & DOM inspection at Desktop (1440x900) and Mobile (390x844) | `web/app.js`, `web/index.html` | Agent H (Browser Subagent) | MEDIUM | Clean chart, optional markers toggle, legend, canonical metrics, zero order tickets | Audited live via `/browser` subagent; verified responsive layout and screenshots on disk | Delivered `docs/V26_BROWSER_VERIFICATION_REPORT.md` with visual artifacts | `VERIFIED_RESOLVED` |
| **F-V26-009** | Independent adversarial red-team review of all V26 findings, claims, and artifacts | All V26 deliverables | Agent I (Red Team) | CRITICAL | Independent recalculations and adversarial challenges | Every claim validated against primary code and data; no unverified statements permitted | Delivered `docs/V26_INDEPENDENT_RED_TEAM_REVIEW.md` | `VERIFIED_RESOLVED` |

---

## 3. Final Release Decision

**Verdict:** **`V26_RESEARCH_GAP_AUDIT_VERIFIED_WITHIN_SCOPE`**
