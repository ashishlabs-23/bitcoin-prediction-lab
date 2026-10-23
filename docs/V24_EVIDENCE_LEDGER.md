# BTCognitive V24 — Evidence Ledger & Multi-Agent Investigation Log

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
| **F-V24-001** | V20 vs V23 RMSE discrepancy: 4h persistence RMSE $843.34 vs $868.51; 24h $2,073.67 vs $2,243.68 on same hash | V20/V23 reports, `scripts/reproduce_v20_forecast_tournament.py` | Agent A (Forecasting) | HIGH | Single deterministic manifest explains provenance and origin filtering | Both V20/V23 manifests report $843.34 and $2,073.67. The $868.51/$2,243.68 was an exploratory report draft typo | Aligned V23 report table; generated `docs/V24_FORECAST_FORENSIC_AUDIT.md`; confirmed canonical manifest | `VERIFIED_RESOLVED` |
| **F-V24-002** | Historical database & CSV equality: 5,622 records in SQLite and CSV; 1,968 directional trades and 3,654 non-directional nulls | `market_memory.db`, `market_memory.csv`, `backups/v23_pre_reconciliation_backup` | Agent B (Data Provenance) | CRITICAL | Canonical field-level equality across all 5,622 records; backup hashes verified | Exactly 5,622 rows in both; 0 duplicate IDs; 0 scored non-directional; pre-backups verified | Delivered `docs/V24_DATA_LINEAGE_AND_BACKUP_VERIFICATION.md`; verified SQLite as authoritative store | `VERIFIED_RESOLVED` |
| **F-V24-003** | Strategy research friction arithmetic: 87 bps round-trip friction and negative net returns for all active strategies | V23 strategy report, backtest engine | Agent C (Strategy) | HIGH | Exact arithmetic trace of trades x 87 bps, position sizing, compounding vs additive returns | Confirmed net results across 9,975 bars: Dual-SMA -2,779.4 bps, Breakout -36,159.5 bps, Zero-exposure 0.0 bps | Delivered `docs/V24_STRATEGY_BACKTEST_FORENSICS.md`; preserved `NO_STRATEGY_WINNER_ESTABLISHED` | `VERIFIED_RESOLVED` |
| **F-V24-004** | Prospective evidence governance: protocol freeze, ledger isolation, and 100 non-overlapping blocks hurdle | `data/prospective_forecast_ledger.jsonl`, `engine/prospective_evidence_pipeline.py` | Agent D (Prospective) | HIGH | Untouched forward observations, separate realized resolution, non-overlapping block definition | 11 records logged; 1 clean mature 24h block, 0 mature 168h blocks; status firmly `COLLECTING` | Delivered `docs/V24_PROSPECTIVE_EVALUATION_PROTOCOL.md`; added `test_v24_prospective_ledger_status` | `VERIFIED_RESOLVED` |
| **F-V24-005** | Research-alert reliability: 60s background lifespan worker, deduplication, restart survival, and honest channel status | `api/server.py`, `api/notifications.py`, `data/research_alert_state.json` | Agent E (Alerts) | HIGH | Single worker instance, persisted state surviving restarts, truthful NOT_CONFIGURED | Worker starts in lifespan; state persists to disk; unconfigured channels return `NOT_CONFIGURED` | Delivered `docs/V24_ALERT_END_TO_END_AND_RESTART_AUDIT.md`; verified 100% test coverage | `VERIFIED_RESOLVED` |
| **F-V24-006** | Live market data snapshot integrity: Coinbase spot quote vs candle close, cache freshness, and sequence gaps | `engine/feature_cache.py`, Coinbase spot adapter | Agent F (Market Data) | HIGH | Spot vs perpetual separation, quote freshness (<60s), monotonic timestamps | Spot BTC-USD strictly isolated from derivatives; cache maintains 500 closed bars | Delivered `docs/V24_MARKET_DATA_SNAPSHOT_AUDIT.md`; validated gap and freshness policies | `VERIFIED_RESOLVED` |
| **F-V24-007** | Frontend & chart representation: Optional research markers toggle, legend, canonical MAE values, no order tickets | `web/app.js`, `web/index.html` | Agent G (Frontend) | MEDIUM | Pristine default chart, informative legend when toggled, canonical forecast MAEs | Audited via `/browser` at 1440x900 & 390x844; 0 order tickets; responsive card stacking verified | Delivered `docs/V24_BROWSER_AND_FRONTEND_VERIFICATION.md` with desktop & mobile screenshots | `VERIFIED_RESOLVED` |
| **F-V24-008** | Execution gate security and full repository regression health | Entire API surface, `tests/` | Agent H (Security & QA) | CRITICAL | Order endpoints disabled (HTTP 405/404); full test suite and frontend build pass | `/api/orders`, `/api/trade` fail closed (404/405); 52+ tests passing, frontend checks & build pass | Delivered `docs/V24_SECURITY_AND_FULL_REGRESSION_AUDIT.md`; test suite 100% green | `VERIFIED_RESOLVED` |

---

## 3. Final Release Decision

**Verdict:** **`V24_INDEPENDENT_VERIFICATION_PASSED_WITHIN_DECLARED_SCOPE`**

All eight specialist investigations have completed independently, established reproducible evidence, and verified the research-only, non-execution posture of BTCognitive.
