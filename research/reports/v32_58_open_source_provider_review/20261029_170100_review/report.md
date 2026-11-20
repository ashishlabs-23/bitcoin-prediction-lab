# BTCognitive V32.58: Rights Matrix, Browser QA, Open-Source Spike, and Failure Reconciliation Report

**Audit Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_58_open_source_provider_review/20261029_170100_review/`  
**Governing Standard:** BTCognitive Permanent Operating Contract (`AGENTS.md`)

---

## 1. Executive Summary & Governed Decisions

| Decision Area | Status | Authoritative Reason |
| :--- | :--- | :--- |
| **Public Market Data Release** | **`BLOCKED`** | Coinbase Market Data Terms (last updated 7 August 2026) prohibit public display, redistribution of Derived Works, and AI/ML model training/validation without express written consent. Written commercial licensing (via Bitstamp DLA, CoinAPI, CoinGecko, or Twelve Data) is required before launch. |
| **Research Experiment** | **`INCONCLUSIVE`** | Historical volatility modeling does not confer statistically significant directional prediction of unconditional returns. |
| **Prospective Evidence** | **`COLLECTING`** | 0/100 non-overlapping blocks for 168h horizon; 3/100 for 24h horizon. |
| **Model Authorization** | **`OFFLINE_RESEARCH_ONLY`** | Econometric models serve observational risk telemetry only; zero production trading authorization. |
| **Live Trading** | **`DISABLED`** | Real order execution, broker routing, and custody remain strictly non-existent in the public runtime. |
| **Application Software Readiness** | **`PARTIAL_PASS_BLOCKED`** | Backend, frontend, charting, and browser journeys are robust, decoupled, and verified on deterministic fixtures; public launch is gated strictly by data rights. |

---

## 2. Key Audit Deliverables & Results

### Workstream A: 47 Inherited Failure ID Reconciliation
- Every inherited failure ID has been individually reviewed and recorded with exact command, exit code, classification, and terminal disposition in [v32_58_failure_reconciliation.csv](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/v32_58_failure_reconciliation.csv).
- **Initial Breakdown:** 7 `TEST_OR_CONTRACT_MISMATCH`, 16 `DATA_PROVENANCE_BLOCKED`, 23 `NOT_REPRODUCED / Contract Gaps`, 1 `ENVIRONMENT_OR_FLAKY`.
- **Key Diagnoses:**
  - `test_health_is_lightweight_liveness`: Cold-start call measured 3,425ms due to Starlette TestClient executing lifespan startup and freeze validation during the first request; warm route requests measure ~380ms for full typed system status evaluation.
  - Data Provenance tests: Stale assertions hardcoded historical row counts (40,902 and 41,273) against the 42,237-row canonical file with 13 absent intervals.
  - Ledger Fixture tests: Stage 10/11 failures stemmed from malformed mock JSONL fixtures rather than production engine logic.

### Workstream B: Elimination of Fabricated Quotes
- In V32.56, a hardcoded fallback `$80,000` in user-position monitoring (`api/routes_user_positions.py`) was remediated and confirmed passing (`tests/test_v32_56_no_fabricated_position_quote.py`).
- In V32.58, the residual `$80,000` fallback in `api/routes_tournament.py` line 561 was audited and remediated:
  - If client candles are absent, historical bars are empty, and no live price is provided, `_post_analyse_market` now raises an explicit HTTP 400 error rather than inventing a price quote.
  - **Verification Evidence:** `tests/test_v32_58_no_fabricated_analyse_quote.py` passed (`1 passed in 21.39s`).
  - **Conclusion:** Zero fabricated market quotes can reach any enabled public UI or API route during upstream provider outages.

### Workstream C: Decoupled Real Browser QA
- Decoupled UI testing from external market-data rights by deploying `scripts/qa/v32_58_browser_qa_runner.py` on a dynamic loopback port with deterministic scenario fixtures.
- Headless Chrome captured 5 complete scenarios with full DOM inspection:
  1. `NORMAL_DESKTOP` (1280x800): Candlesticks, volume, aligned directional marker (296,013 bytes). **PASS**
  2. `MOBILE_375PX` (375x667): Fully responsive mobile layout, controls accessible, zero overflow (116,119 bytes). **PASS**
  3. `TIMEFRAME_MISMATCH` (1280x800): 15m origin on 1h chart; marker strictly withheld from candle; status displayed in overlay panel (330,344 bytes). **PASS**
  4. `DATA_STALE` (1280x800): Market data age > 2h; explicit `STALE` status displayed (304,689 bytes). **PASS**
  5. `PROVIDER_UNAVAILABLE` (1280x800): Clean fail-closed UI; price is null; zero fake quotes (316,910 bytes). **PASS**
- Full details in [browser_qa_report.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/browser_qa_report.md).

### Workstream D: Open-Source Component Spike
- Evaluated CandleKit, dipping-charts, OpenCharts, and Lightweight Charts in `scratch/v32_58_spike/`.
- Benchmarked vectorized technical indicator calculations (EMA 20/50, RSI 14, Bollinger Bands 20,2, ATR 14) and Fibonacci retracements across 50,000 candles in **20.84 ms**.
- **Decision:** Retain TradingView Lightweight Charts 4.1.3 as the production baseline; reject wholesale application migrations (e.g. OpenCharts); adopt drawing tool geometry formulas natively on canvas without bloated NPM wrappers. Detailed in [chart_library_spike.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/chart_library_spike.md).

### Workstream E: Market-Data Rights & Model Protocols
- Compiled [provider_rights_matrix.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/provider_rights_matrix.md) evaluating Bitstamp, CoinAPI, CoinGecko, and Twelve Data.
- Drafted formal outreach letter in [license_inquiry_draft.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/license_inquiry_draft.md).
- Established research-only benchmarking plan in [forecast_model_benchmark_plan.md](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_58_open_source_provider_review/20261029_170100_review/forecast_model_benchmark_plan.md) with **Google TimesFM 3.0 explicitly excluded** from commercial roadmaps due to its Non-Commercial License v1.0.

---

## 3. Cryptographic Proof of Repository Invariants

Protected files were verified before and after this milestone; **all hashes remain strictly identical**:

| Protected File Path | Initial SHA-256 | Final SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec...` | `c007cd613bec...` | **UNMODIFIED** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695...` | `c4949e5b5695...` | **UNMODIFIED** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a...` | `1e722f33734a...` | **UNMODIFIED** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed98400...` | `91c3aed98400...` | **UNMODIFIED** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc...` | `e3b0c44298fc...` | **UNMODIFIED** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb...` | `e6e33e3c7beb...` | **UNMODIFIED** |

---

## 4. Immediate Next Dependencies

1. **Vendor Outreach:** Send `license_inquiry_draft.md` to Bitstamp (`partners@bitstamp.net`) and CoinAPI (`sales@coinapi.io`) to establish commercial data terms.
2. **Deterministic Test Isolation:** Replace fragile static fixture timestamps in scenario tests with virtualized timestamps to clear remaining data-provenance test blockers.
3. **CI Pipeline Integration:** Integrate `v32_58_browser_qa_runner.py` into automated GitHub Actions.

