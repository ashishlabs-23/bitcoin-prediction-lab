# BTCognitive — Phase 0 Baseline Audit Report

**Date:** 29 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/offline_mvp/20261029_231000_phase0_baseline/`  
**Execution Context:** Internal Offline Research MVP (`127.0.0.1:8000`), Python 3.13.14 on Windows 11  

---

## 1. Repository State & Environment Baseline

- **Current Branch:** `main` (Verified: `## main...origin/main [ahead 1]`).
- **Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`.
- **Pre-Existing Modified / Untracked Files:** Fully preserved. Zero branches created, zero commits, zero stashes, zero resets, zero cleans.
- **Python Virtual Environment:** `.venv_win\Scripts\python.exe` (Python 3.13.14, pytest-8.4.1).
- **Host Binding:** `127.0.0.1:8000` (Loopback interface only).

---

## 2. Protected Files Bit-Level Invariance Proof

All six protected research datasets and prospective ledgers were verified bit-for-bit identical before any execution:

| Protected File Path | SHA-256 Hash | Size (Bytes) | Verification Status |
| :--- | :--- | :---: | :---: |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | 2,329,745 | **BIT_IDENTICAL_PRESERVED** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | 2,284,681 | **BIT_IDENTICAL_PRESERVED** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | 2,326,699 | **BIT_IDENTICAL_PRESERVED** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | 3,385 | **BIT_IDENTICAL_PRESERVED** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | **BIT_IDENTICAL_PRESERVED** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | 12,744 | **BIT_IDENTICAL_PRESERVED** |

---

## 3. Current Test Inventory & Minimal Safe Baseline

- **Total Test Files in Repository:** 343 files across historical and modern stages.
- **Historical "47 Unresolved" Reconciliation:**
  - Audited against `research/reports/v32_59_analyse_e2e_and_strategy_audit/20261029_172800_audit/v32_58_failure_reconciliation_final.csv`.
  - The historical failures were primarily caused by:
    1. Tests asserting stale dataset row counts (e.g., 40,902 or 41,273 vs. current 42,233/42,237).
    2. Static fixture age rejection (tests checking `time.time() - bar_timestamp < 2 hours` without virtualizing current time).
    3. Test harness isolation gaps (attempting unmocked SSRF / Google sheets checks).
    4. Mutating live ledger files in tests without tmpdir isolation.
- **Minimal Safe Baseline Executed:**
  - `tests/test_v32_62_offline_research_mode.py`: **9 passed in 15.97s** (Exit Code 0).
  - `tests/test_v32_63_calculation_correctness.py`: **10 passed in 32.51s** (Exit Code 0).
- **Clean Execution Commands:**
  ```powershell
  Set-Location "c:\Projects\BTCognitive\BTCognitive"
  .\.venv_win\Scripts\python.exe -m pytest tests/test_v32_62_offline_research_mode.py -v
  .\.venv_win\Scripts\python.exe -m pytest tests/test_v32_63_calculation_correctness.py -v
  ```

---

## 4. Source Map for the Offline-First MVP

| Component / Subsystem | Primary Implementation Files | API Endpoints / Entry Points | Operational Role in Offline Research MVP |
| :--- | :--- | :--- | :--- |
| **Frontend UI Entrypoint** | `web/index.html`, `web/app.js` | `http://127.0.0.1:8000` | Renders TradingView Lightweight Charts v4.1.3 canvas, overlays, and Analyse button. |
| **Candle Data Service** | `api/candle_manager.py`, `api/routes_market.py` | `GET /api/market/candles` | Reads from `data/raw/ohlcv.parquet` (42,233 rows); validates timestamps, monotonicity, and OHLC integrity. |
| **Technical Indicators** | `engine/regime_strategy_tournament.py`, `engine/feature_pipeline.py` | Internal / `/api/tournament/analyse` | Causal computation of EMA (20/50/200), ATR-14, Bollinger Bands, and Donchian channels with strict shift(1). |
| **Market Regime Classifier** | `engine/regime_strategy_tournament.py:159-255` | `POST /api/tournament/analyse` | 168-bar causal decision tree: classifies market into TRENDING, RANGE_BOUND, or VOLATILITY_EXPANSION. |
| **Strategy Tournament** | `engine/regime_strategy_tournament.py:278-380` | `GET /api/tournament/registry`, `POST /api/tournament/run` | Evaluates versioned regime-compatible strategies and 7/10 preliminary screen with Wilson 95% CIs. |
| **Execution Cost Model** | `engine/execution_cost_model.py:17-200` | `GET /api/tournament/contract/{id}` | Calculates roundtrip friction in R and break-even win rate across exchange fee schedules. |
| **Forecast Contract** | `engine/har_rs_dow_features.py:31-100` | `GET /api/prediction/price/forecast` | Point-in-time 168h variance forecast with strict causal ordering $t_{\text{feat}} \le t_{\text{issue}} < t_{\text{maturity}}$. |
| **Governance Lockdown** | `engine/status_contract.py`, `api/routes_terminal.py` | `GET /api/terminal/status`, `POST /api/terminal/live` | Reports `OFFLINE_RESEARCH_ONLY` and fails closed on live execution with HTTP 503 (`MODEL_UNAUTHORIZED`). |

---

## 5. Network Exposure & Runtime Gates Audit

### Critical Finding:
`OFFLINE_RESEARCH_ONLY` in `config.py` is a **governance authorization flag** for model execution; it does **NOT** prevent low-level socket creation if a component invokes external HTTP clients.

Specifically:
1. **Frontend Client-Side Leak (`web/app.js:1180`):** The browser script currently attempts to fetch `https://api.exchange.coinbase.com/products/BTC-USD/candles` directly from the user's browser before falling back to the backend. In offline mode, this causes network errors in the browser console.
2. **Backend Outbound Route (`api/routes_market.py:115`):** `GET /market/comparator` invokes `engine/spot_exchange_comparator.py`, which calls external Coinbase, Kraken, and Bitstamp endpoints via `api/market_drivers.py:_fetch_quote()`. While exceptions are caught and degraded to `DATA_UNAVAILABLE`, socket connection attempts still occur.
3. **15-Minute Candle Route (`engine/coinbase_15m_adapter.py:21`):** Calls Coinbase REST using `urllib.request` if 15m intervals are requested.

### Phase 1 Remediation Mandate:
Enforce explicit three-lane architecture (`fixture`, `offline_research`, `provider`). When `DATA_MODE != "provider"`, short-circuit all low-level network calls before socket creation.

---

## 6. Confirmed Facts vs. Assumptions

| Domain | Confirmed Facts (Empirically Verified) | Prior Assumptions Disproven or Clarified |
| :--- | :--- | :--- |
| **Dataset Size** | `data/raw/ohlcv.parquet` has exactly **42,233 rows** with zero interior gaps and zero NaNs. | Assumption that `ohlcv.parquet` had 42,237 rows was incorrect; 42,237 belongs to `data/research/..._v2` (which has 13 missing candles and 17 extra trailing bars). |
| **Time Horizon** | Data terminates at `2026-10-26 16:00 UTC` (3.04 days prior to Oct 29 audit date). | The dataset is strictly historical replay data, not a live streaming feed. |
| **Indicators** | EMA, ATR, Bollinger, Parkinson, and Donchian channels match mathematical reference values. | Assumption that all ADX implementations were identical was disproven: `regime_strategy_tournament.py` applies full double-smoothing, while `strategy_signal_engine.py` terminates at raw $DX$. |
| **Network Gating** | Low-level HTTP requests were reachable via `web/app.js:1180` and `/market/comparator`. | Assumption that `OFFLINE_RESEARCH_ONLY` prevented all network calls was false; explicit data-lane gating is required. |
| **Execution Safety** | Live trading is strictly disabled (`trading_enabled = False`); `POST /api/terminal/live` returns HTTP 503. | No live execution, broker integration, or order placement paths exist. |

---

## 7. Phase 0 Gate Sign-off

- **Protected Datasets:** 6/6 verified bit-identical.
- **Pre-existing Dirty Files:** Preserved intact without modification.
- **Source Map & Network Paths:** Fully documented and mapped.
- **Gate Status:** **PHASE 0 AUDIT COMPLETE — APPROVED TO PROCEED TO PHASE 1.**

