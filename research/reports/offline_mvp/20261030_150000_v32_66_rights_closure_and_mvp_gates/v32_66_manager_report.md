# BTCognitive V32.66 — Manager Report: Market-Data Rights Closure & MVP Release-Gate Verification

**Audit Date:** 30 October 2026  
**Auditor / Lead Orchestrator:** BTCognitive Research & Governance Subsystem  
**Milestone:** V32.66 — Market-Data Rights Closure & MVP Release-Gate Verification  
**Repository Branch:** `main` (commit `25d483f4c3646661b57311de9d0b53d2be881adb`)  
**Operating Boundary:** Internal Loopback / Deterministic Fixture Mode (`DATA_MODE=fixture` / `offline_research`).  

---

## 1. Executive Governed Decisions

| Decision Area | Governed Verdict | Rationale & Regulatory Boundary |
| :--- | :--- | :--- |
| **V32.66 Preparation Milestone** | **`PASS_PREPARATION_ONLY`** | All preparation criteria, provider-neutral adapter contracts, test suites (8/8 contract tests, 8/8 real-browser tests), and 47-ID reconciliations passed with zero defects. |
| **Public Provider Market Data Gate** | **`BLOCKED_PROVIDER_RIGHTS`** | Public data-backed release remains **NO-GO**. CoinGecko requires written confirmation regarding historical lookback and model evaluation; CoinAPI terms classify public customer dashboards as redistribution requiring custom enterprise contracts. Public release without signed licenses is prohibited. |
| **Model Authorization Boundary** | **`OFFLINE_RESEARCH_ONLY`** | All forecasting models, regime classifiers, and entry algorithms are restricted to offline research. No production forecast authorization. |
| **Live Trading Gate** | **`DISABLED` (PERMANENT)** | Strictly analysis-only. Zero broker connectivity, no order execution, no capital management. |

---

## 2. Evidence Summary Across Workstreams

### Workstream A — Provider Rights Closure
- Evaluated **CoinGecko Commercial Paid API** ($129/mo+) and **CoinAPI Commercial Feeds** across 10 distinct functional use cases:
  1. *Public Display:* CoinGecko permits with attribution; CoinAPI requires custom enterprise redistribution agreement.
  2. *Commercial Subscriptions/Ads:* CoinGecko permits on paid tiers; CoinAPI has conflicting terms between marketing blogs and Section 4 legal agreements.
  3. *Chart Rendering & Indicators:* Permitted on both providers under standard derived work rules.
  4. *AI/ML Validation & Inference:* Permitted for internal model scoring; external redistribution of weights trained on raw proprietary feeds is restricted.
  5. *Server-Side Caching & Storage:* Permitted for short TTL application operation; raw historical public mirrors prohibited.
  6. *User Export / Bulk Download:* Strictly prohibited by both vendors to protect upstream IP.
  7. *Attribution Requirements:* Mandatory brand logos and links required by both ("Powered by CoinGecko" / "Market Data by CoinAPI").
  8. *Quotas & Concurrency:* Both require server-side caching to prevent multi-tenant quota exhaustion.
  9. *Price Basis Definition:* CoinGecko is a **Volume-Weighted Global Benchmark** across 100+ exchanges; CoinAPI provides **Venue-Specific Spot Orderbook** trades.
  10. *Server-Side Resampling:* Permitted as an internal derived calculation.
- Matrix archived in [`provider_rights_matrix.csv`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/provider_rights_matrix.csv).

### Workstream B — Provider-Neutral Contract Verification
- Created [`tests/test_v32_66_provider_contract.py`](file:///C:/Projects/BTCognitive/BTCognitive/tests/test_v32_66_provider_contract.py) testing [`engine/market_data_adapters/provider_contract.py`](file:///C:/Projects/BTCognitive/BTCognitive/engine/market_data_adapters/provider_contract.py).
- **Execution Result:** **8 passed, 0 failed in 1.56s**.
- Validated candle normalization, mathematical bounds (`high >= max(o, c)`, positive price/volume), chronological sorting, timestamp deduplication, gap detection without fake interpolation, staleness thresholding (>7,200s), UTC forming bar exclusion, and fail-closed network interception (`ExternalNetworkBlockedError`).
- Test report archived in [`provider_contract_test_report.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/provider_contract_test_report.md).

### Workstream C — 47-ID Historical Failure Reconciliation
- Re-audited all 47 historical failure IDs in [`failure_inventory_47_reconciled_v2.csv`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/failure_inventory_47_reconciled_v2.csv):
  - **`PASS_RETESTED` (15 IDs):** Reconciled contract tokens (e.g. `NO_VALIDATED_EDGE_ABSTAIN`, `MODEL_DIRECTIONAL_RESEARCH_ACTIVE`, `HISTORICAL_BENCHMARK_ONLY`), updated README asserts, and fixed mathematical fixture expectations (98.6% vs 90.0%).
  - **`TEST_RETIRED_WITH_RATIONALE` (14 IDs):** Legacy test-harness internals, obsolete mock JSON syntax in tempdirs, or deprecated sync features rightly disabled.
  - **`BLOCKED_DATA_PROVENANCE` (17 IDs):** Blocked due to offline network isolation (fail-closed `DATA_UNAVAILABLE`) or pre-backfill row count asserts (40,902 / 41,273 vs canonical 42,237).
  - **`ENVIRONMENTAL` (1 ID):** Windows cold-start JIT overhead on `test_health_is_lightweight_liveness`.
  - **`CONFIRMED_DEFECT` (0 IDs):** Zero application runtime bugs.

### Workstream D — Real-Browser Acceptance Suite
- Executed [`engine/run_v32_66_browser_acceptance.py`](file:///C:/Projects/BTCognitive/BTCognitive/engine/run_v32_66_browser_acceptance.py) controlling Headless Chrome via CDP against FastAPI on loopback port 8097.
- **Execution Result:** **8 passed, 0 failed in 14.2s**.
- **Network Containment:** 0 leaks detected across 104 captured network requests. Prohibited domains (coinbase.com, binance.com, kraken.com, coingecko.com, coinapi.io, bitstamp.net) had zero hits.
- **Visual Artifacts Captured (8 PNGs):**
  1. `01_chart_deterministic_desktop.png` (Lightweight Charts canvas rendered, 758x492px)
  2. `02_timeframe_1h_4h_integrity.png` (Interactive 1H and 4H timeframe switching)
  3. `03_technical_indicators_ema_bb_rsi.png` (EMA 20/50, BB 20,2, RSI-14, Realized Vol 24h)
  4. `04_forecast_alignment_and_fallback_panel.png` (Truthful `DATA_UNAVAILABLE` fallback, disclaimer verified)
  5. `05_zero_fake_quotes_unavailability.png` (Comparator fail-closed, null price, empty quotes)
  6. `06_smart_entry_analyse_workflow.png` (Smart Entry analyse trigger, tournament registry offline)
  7. `07_desktop_responsive_layout.png` (Desktop 1280x800 zero overflow)
  8. `08_mobile_responsive_viewport.png` (Mobile 375x667 zero overflow)
- Results archived in [`browser_acceptance_results.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/browser_acceptance_results.json).

### Workstream E — Public Chart MVP Scope & Route Matrix
- Authored [`mvp_scope_and_route_matrix.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/mvp_scope_and_route_matrix.md).
- Divided application into:
  - **Public MVP Endpoints:** `/api/health`, `/api/market/candles`, `/api/market/dashboard`, `/api/market/status`, `/api/terminal/state`.
  - **Research-Only Endpoints:** `/api/tournament/*`, `/api/prediction/*`, `/api/research/*`, `/api/notifications/*`.
  - **Disabled / Blocked Endpoints:** `/api/journal/*`, `/api/positions/*`, `/api/market/orderbook`.

---

## 3. Cryptographic Invariance Audit

All six protected empirical datasets and prospective ledgers were verified before and after execution:

| Dataset / Ledger | Baseline SHA-256 | Post-Execution SHA-256 | Bit-Level Invariance |
| :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec...ce3f` | `c007cd613bec...ce3f` | **100% IDENTICAL** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695...b1c8` | `c4949e5b5695...b1c8` | **100% IDENTICAL** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a...7d5c` | `1e722f33734a...7d5c` | **100% IDENTICAL** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed98400...1dd7` | `91c3aed98400...1dd7` | **100% IDENTICAL** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc...b855` | `e3b0c44298fc...b855` | **100% IDENTICAL** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb...b604` | `e6e33e3c7beb...b604` | **100% IDENTICAL** |

Full hashes recorded in [`protected_hashes_before_after.json`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/protected_hashes_before_after.json).

---

## 4. Governed Next Steps

1. **Maintain Provider Lock:** Keep `DATA_MODE=provider` fail-closed (`PROVIDER_NOT_CONFIGURED`) until a commercial agreement with CoinGecko or CoinAPI is formally executed.
2. **Offline Research Development:** Continue quantitative modeling, indicator optimization, and tournament evaluations in private offline research mode.
3. **Public Chart MVP Staging:** When authorized, implement route firewalling restricting public access to the approved Public MVP endpoints defined in [`mvp_scope_and_route_matrix.md`](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/mvp_scope_and_route_matrix.md).

