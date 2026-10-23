# V27 Release & Governed Research Decision

**Release Version:** 27.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Final Governed Research & Engineering Decision for BTCognitive V27  

---

## 1. Authoritative Four-Point Governance Decision

Pursuant to the BTCognitive Operating Contract (`AGENTS.md`) and Master PRD governance standards, the Lead Orchestrator and specialist workstreams issue the following four explicit, non-negotiable decisions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BTCognitive V27 Governance Decision                   │
├────────────────────────────────┬────────────────────────────────────────────┤
│ 1. Research Experiment         │ RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY   │
│ 2. Prospective Evidence Status │ COLLECTING (1/100 Clean Mature Blocks)     │
│ 3. Model Authorization Status  │ OFFLINE_RESEARCH_ONLY                      │
│ 4. Live Trading Authorization  │ DISABLED — ANALYSIS ONLY                   │
└────────────────────────────────┴────────────────────────────────────────────┘
```

### Detailed Decision Rationale:
1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`
   - Point-by-point forecast errors evaluated on the canonical frozen sample boundaries ($N=15,000$ for 1h, $N=3,750$ for 4h, $N=625$ for 24h) confirm that Random Walk Persistence beats Ridge L2 regression across all horizons. Clark–West HAC statistics remain strictly negative. Persistence is unbeaten.
   - Compounded equity simulations across all active strategies yield severe losses ($-56.97\%$ to $-99.50\%$) and drawdowns exceeding $68\%$. The Zero Exposure Cash Benchmark remains the top-performing tested baseline within this window.
2. **Prospective Evidence:** `COLLECTING`
   - `data/prospective_forecast_ledger.jsonl` records 11 entries, with exactly 1 clean mature 24h block resolved and 0 mature 168h blocks resolved ($1.0\%$ hurdle attainment). The 100-block hurdle remains strictly frozen.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
   - Only `HAR-RS-DOW-v1.0` is authorized for volatility risk envelope monitoring. Zero directional price models are authorized. Newly introduced realized semi-variance, cross-venue dislocation, and funding rate modules are classified as research-only foundations.
4. **Live Trading:** `DISABLED — ANALYSIS ONLY`
   - All trade and order endpoints return HTTP 404/405 fail-closed. Live order placement is permanently disabled.

---

## 2. Test Suite Census & Regression Audit

- **Complete Repository Test Census:** Exactly **1,286 automated tests across 299 test files** in `tests/`.
- **Selected Active Version Regression Suite:** **65 tests** across 7 core test files:
  - `tests/test_v27_metric_repair_and_features.py` (8 tests)
  - `tests/test_v26_research_gap_and_econometrics.py` (5 tests)
  - `tests/test_v25_strategy_and_forecasting.py` (5 tests)
  - `tests/test_v24_audit_and_prospective.py` (5 tests)
  - `tests/test_v23_forecast_reconciliation_and_audit.py` (9 tests)
  - `tests/test_v22_forecast_and_alerts.py` (9 tests)
  - `tests/test_notifications.py` (24 tests)
- **Pass Rate:** **100% PASSING (65/65 passed in 121.6 seconds)**.

---

## 3. Browser UI & Visual Evidence

A live browser audit across desktop (1440x900) and mobile (390x844) confirmed:
- Header displays `READ-ONLY MONITOR · TRADING DISABLED`.
- Decision Anatomy card displays deterministic `Action: ABSTAIN`.
- Arena strategy accounts display transparent costs and negative net returns after friction (`COST_ERASED`).
- Responsive layouts adapt cleanly with zero visual defects.

**Final Release Status:** **`V27_DATA_FOUNDATIONS_VERIFIED — NO NEW MODEL AUTHORIZATION`**.
