# V26 Release & Governed Research Decision

**Release Version:** 26.0.0  
**Effective Date:** 19 October 2026  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Final Governed Research & Engineering Decision for BTCognitive V26  

---

## 1. Authoritative Four-Point Governance Decision

Pursuant to the BTCognitive Operating Contract (`AGENTS.md`) and Master PRD governance standards, the Lead Orchestrator and specialist workstreams issue the following four explicit, non-negotiable decisions:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BTCognitive V26 Governance Decision                   │
├────────────────────────────────┬────────────────────────────────────────────┤
│ 1. Research Experiment         │ RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY   │
│ 2. Prospective Evidence Status │ COLLECTING (1/100 Clean Mature Blocks)     │
│ 3. Model Authorization Status  │ OFFLINE_RESEARCH_ONLY                      │
│ 4. Live Trading Authorization  │ DISABLED — ANALYSIS ONLY                   │
└────────────────────────────────┴────────────────────────────────────────────┘
```

### Detailed Decision Rationale:
1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`
   - Non-nested Diebold–Mariano and nested Clark–West (2007) tests incorporating Newey–West HAC standard errors (Bartlett kernel) confirmed that Ridge L2 regression produces negative test statistics across all horizons ($-0.8726$ at 1h, $-0.4385$ at 4h, $-0.2877$ at 24h). The Random Walk Persistence benchmark remains strictly unbeaten in empirical accuracy.
   - Strategy backtests across multiple fee tiers (Coinbase Retail 87 bps, Binance VIP0 24 bps, Institutional 14 bps) demonstrated that all active trading strategies suffer negative net returns or catastrophic drawdowns (>79%). The Zero Exposure Cash Benchmark remains the decisive winner.
2. **Prospective Evidence:** `COLLECTING`
   - The prospective evaluation ledger contains 11 entries, with exactly 1 clean mature 24-hour block resolved and 0 mature 168-hour blocks resolved.
   - Attainment is $1 / 100$ ($1.0\%$). In accordance with epistemic invariants, this hurdle will not be accelerated or simulated.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
   - Only the annualized variance risk model `HAR-RS-DOW-v1.0` is authorized for risk monitoring and volatility envelope generation. No directional price model inherits production authorization.
4. **Live Trading:** `DISABLED`
   - Live order placement, broker connections, and paper-trading order workflows are permanently disabled and fail-closed across all endpoints.

---

## 2. Evidence Ledger & Findings Reconciliation

| Finding ID | Scope & Summary | Resolution in V26 |
| :--- | :--- | :--- |
| **F-V26-001** | Naive standard errors in DM / Clark-West tests | **RESOLVED:** Implemented Newey–West HAC variance with Bartlett kernel weights. All test statistics confirmed negative ($t < 0$). Persistence superiority established. |
| **F-V26-002** | Dual-SMA vs Dual-EMA nomenclature mismatch | **RESOLVED:** Standardized strategy ID as Dual-EMA Crossover (24h/168h); evaluated reference True Dual-SMA. Both fail after costs. |
| **F-V26-003** | Turnover units and reversal arithmetic | **RESOLVED:** Standardized accounting ($\sum |s_t - s_{t-1}|$). Entries/exits = 1 unit; reversals = 2 units. |
| **F-V26-004** | PRD requirement completion count ambiguity | **RESOLVED:** Reconciled 53 Milestone 1 items against Master PRD aspirational goals; created definitive Traceability Matrix. |
| **F-V26-005** | Test census conflation (52 vs full repo) | **RESOLVED:** Cataloged full census of 1,286 tests across 299 files; separated from the active 57-test release suite. |
| **F-V26-006** | Notification channel delivery reporting | **RESOLVED:** Worker queueing strictly separated from external delivery. Channels return `NOT_CONFIGURED` without keys. |
| **F-V26-007** | Prospective evidence hurdle compliance | **RESOLVED:** Preserved 100-block hurdle; confirmed status `COLLECTING` (1 block mature). |
| **F-V26-008** | Non-execution invariant on API routes | **RESOLVED:** Verified all order/trade routes return HTTP 404/405 fail-closed. |
| **F-V26-009** | Market data feature roadmap prioritization | **RESOLVED:** Established ranked 6-dimension roadmap (V27–V30) focusing on free public derivatives and cross-exchange data. |

---

## 3. Test & Verification Summary

- **Selected Active Release Regression Suite:** **57 tests passed** across 6 core test files (100% pass rate in 69.5 seconds).
- **Frontend / Browser Verification:** Verified live DOM rendering at Desktop (1440x900) and Mobile (390x844). Verified honest `ABSTAIN` actions, risk gauges, and non-execution banners.
- **Independent Red-Team Review:** All findings challenged and verified; zero lookahead leakage, zero data fabrication.

**Final Release Status:** **`V26_RESEARCH_GAP_AUDIT_VERIFIED_WITHIN_SCOPE`**.
