# BTCognitive V23 — Evidence Ledger & Investigation Register

**Version:** 1.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Living working register of all empirical claims, forensic investigations, reproducible checks, and verified resolutions in V23.

---

## 1. Governance & Classification Protocol

Each entry records:
- **Finding ID:** `F-V23-###`
- **Claim Under Investigation:** Exact claim or requirement from PRD, prior versions, or user review.
- **Source Artifact / File:** Code, report, or route.
- **Evidence Gathered:** Empirical data, row counts, SHA-256 hashes, test traces.
- **Reproduction Procedure:** Exact CLI command or test.
- **Expected vs Actual Behavior:** Explicit delta.
- **Classification:** `CONFIRMED_DEFECT` | `VERIFIED_BEHAVIOR` | `UNRESOLVED_CONTRADICTION` | `LIMITATION` | `NOT_TESTED`.
- **Owner & Reviewer:** Specialist workstream agent assignment.
- **Fix & Regression Test:** Concrete code changes and test assertions.

---

## 2. Investigation Register

| Finding ID | Claim Under Investigation | Source Artifact | Classification | Status | Summary of Evidence & Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F-V23-001** | Forecast numbers discrepancy between V18, V19, V20, and V22 forecast cards (e.g. $264.99 vs $283.66 1h MAE) | `engine/price_forecast_engine.py`, `scripts/reproduce_v20_forecast_tournament.py`, `docs/V20_FORECAST_REPRODUCIBILITY_AUDIT.md` | `CONFIRMED_DEFECT` | `INVESTIGATING` | V19/V22 runtime engine used fixed 15,000 blocks starting at index 20,000, whereas V20 script evaluated across entire available sample post-training fold. Reconciling into single canonical manifest `experiments/results/v23_canonical_forecast_manifest.json`. |
| **F-V23-002** | 58-row discrepancy between SQLite `predictions` (5,611 rows) and CSV `market_memory.csv` (5,553 rows); 7-row difference in non-directional scans (3,647 vs 3,654) | `experiments/results/market_memory.db`, `experiments/results/market_memory.csv` | `CONFIRMED_DEFECT` | `INVESTIGATING` | Performing row-level diff on stable `prediction_id` and timestamps to isolate the exact 58 records and determine if they represent test appends, crash drops, or timing skew. |
| **F-V23-003** | Strategy performance after retail transaction costs (87 bps round-trip) fails to beat zero-exposure baseline | `research/v11_strategy_discovery_engine.py`, `research/v12_strategy_tournament_engine.py`, `research/experiments/` | `VERIFIED_BEHAVIOR` | `CONFIRMED` | All 4 active strategy hypotheses (Mean Reversion, Breakout, Regime Trend, Dual SMA) lose substantially after friction (-2,779 to -36,159 bps). `NO_STRATEGY_WINNER_ESTABLISHED` is the mathematically correct verdict. |
| **F-V23-004** | Chart strategy visibility: Need optional research markers toggle with legend rather than unvalidated live trade arrows | `web/app.js`, `web/index.html`, `api/routes_arena.py` | `CONFIRMED_DEFECT` | `IN_PROGRESS` | Main chart must remain clean. Adding optional "Research Markers" toggle with legend: Potential bullish setup, Potential bearish setup, No confirmed setup, with full trigger metadata and non-actionable status. |
| **F-V23-005** | Real notification channel delivery verification: External delivery channels not proven with live message | `api/notifications.py`, `api/routes_notifications.py` | `LIMITATION` | `INVESTIGATING` | Automated mock tests verify lifecycle, restart persistence, and cooldown. Inspecting environment for any explicitly configured webhook/telegram/email; if unconfigured, honestly report `NOT_CONFIGURED` without fabricating delivery. |
| **F-V23-006** | Complete Python test suite and frontend build pass | Full repository test suite, `npm run check`, `npm test`, `npm run build` | `VERIFIED_BEHAVIOR` | `IN_PROGRESS` | Core suites (61 tests) pass. Running full repository census and browser E2E verification. |
| **F-V23-007** | Permanent non-execution invariant: Analysis-only BTCUSD terminal, live trading and paper execution permanently disabled | `api/server.py`, `api/security_middleware.py`, `models/authoritative_model_registry.py` | `VERIFIED_BEHAVIOR` | `CONFIRMED` | All 10 gates remain fail-closed. |

---
