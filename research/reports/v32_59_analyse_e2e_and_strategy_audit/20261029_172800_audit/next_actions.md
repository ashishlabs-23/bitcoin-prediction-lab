# BTCognitive 30/60/90-Day Research Plan & Next Actions (V32.59)

**Date:** 29 October 2026  
**Scope:** Read-only market charting, technical analysis, and research-only probabilistic risk intelligence.  
**Strict Mandate:** Zero live trading, zero broker execution, zero synthetic data fabrication.

---

## 1. Prioritized Action Matrix (P0 / P1 / P2)

### Priority 0 — Immediate Release Blockers & Invariant Preservation
- **P0-1: Resolve Market Data Rights in Writing:**
  - Public deployment remains **NO-GO** while relying on unauthorized commercial display of Coinbase Exchange candles.
  - When commercial budget is authorized, pursue an executed Data License Agreement with Bitstamp (for pure BTC/USD exchange spot) or CoinAPI (for turnkey multi-exchange feeds).
  - In all internal CI/CD and engineering workflows, strictly use deterministic fixtures (`scripts/qa/v32_59_analyse_e2e_runner.py`) to decouple development from external licensing constraints.
- **P0-2: Maintain Protected Research Artifacts & Causal Integrity:**
  - Preserve all 6 protected data ledgers and parquet backups with bit-for-bit identical SHA-256 hashes.
  - Retain historical dataset at 42,237 rows with the 13 documented missing hourly candles labeled `ACQUIRED_WITH_REVIEW_REQUIRED`. Zero synthetic candle interpolation.

---

### Priority 1 — Prospective Evidence Accumulation & Econometric Rigor (Days 1–45)
- **P1-1: Accumulate Untouched Prospective Blocks:**
  - Maintain the append-only prospective ledgers (`data/prospective_entry_ledger_v2.jsonl`).
  - Target: Accumulate $\ge 100$ non-overlapping post-freeze blocks for the canonical 168-hour horizon (currently at 0/100) and 24-hour horizon (currently at 3/100).
- **P1-2: Formal Statistical Testing Protocol:**
  - For all model and strategy comparisons, enforce the Diebold–Mariano test with Harvey–Leybourne–Newbold (1997) finite-sample correction using Student's $t_{T-1}$ reference distribution.
  - Purged and embargoed cross-validation with minimum 168-hour embargo windows to prevent information leakage across overlapping forecast horizons.
- **P1-3: Reconcile Inherited Test Inventory:**
  - Sequentially address the 47 inherited test IDs from V32.55/V32.58:
    - 23 test/contract mismatches: update outdated test assertions to reflect current V32 governance tokens.
    - 16 data-provenance blocked: inject deterministic virtual timestamps and mock fixtures into isolated test harnesses.
    - 7 test mock corrections: update network-isolation mocks for admin RBAC and SSRF tests.
    - 1 environmental cold-start latency assertion: warm up the FastAPI lifespan before measuring lightweight route latency.

---

### Priority 2 — Product Hardening & Charting UX (Days 46–90)
- **P2-1: Charting & Analytical Tooling:**
  - Retain TradingView Lightweight Charts 4.1.3 as the high-performance core engine.
  - Evaluate modular open-source add-ons for user-drawn trendlines, Fibonacci retracements, and measurement rulers.
- **P2-2: Execution Pipeline Guardrails:**
  - Verify that all Smart Entry and Tournament endpoints remain strictly non-custodial and non-executing.
  - Maintain `OFFLINE_RESEARCH_ONLY` model authorization and `trading_enabled = False` across all production configurations.
- **P2-3: Performance & Latency Optimization:**
  - Profile and maintain `< 50ms` cached API responses for live dashboard and market summary endpoints.

