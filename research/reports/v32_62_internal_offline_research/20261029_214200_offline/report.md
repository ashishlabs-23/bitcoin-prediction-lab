# BTCognitive V32.62 — Internal Offline Research Mode Audit Report

**Date:** 29 October 2026  
**Auditor / Lead Orchestrator:** BTCognitive Lead Research Orchestrator  
**Audit Directory:** `research/reports/v32_62_internal_offline_research/20261029_214200_offline/`  
**Git Branch / Commit SHA:** `main` (clean audit boundary, zero Git mutations)  
**Host Binding:** `127.0.0.1:8000` (Private loopback interface only)  
**Product Scope:** Private, local research terminal for econometric market analysis, volatility risk intelligence, and strategy evaluation. Strictly NO broker integration, order execution, custody, or live capital deployment (`trading_enabled = False`).

---

## 1. Executive Summary & Governed Decisions

Following the strategic decision to adopt an **Internal Offline Research Path**, BTCognitive has completed a comprehensive audit of its runtime network dependencies and executed rigorous offline verification of its existing core features against local historical datasets on loopback (`127.0.0.1:8000`).

### Authoritative Governed Four-Part Decision Gate:
1. **Research Experiment Status:** **`PASS`**  
   *All 9 offline verification scenarios passed cleanly. Local historical data loading, technical indicators, strategy screening, and fail-closed governance gates operate deterministically without outbound network calls.*
2. **Prospective Evidence Accumulation:** **`COLLECTING`**  
   *Valid non-overlapping prospective blocks remain at 0/100 for the 168-hour horizon and 3/100 for the 24-hour horizon. Historical dataset integrity is preserved with zero synthetic data fabrication.*
3. **Model Authorization Level:** **`OFFLINE_RESEARCH_ONLY`**  
   *No models are authorized for live production inference or trade signals. Directional prediction claims remain an unproven research hypothesis.*
4. **Live Trading State:** **`DISABLED`**  
   *Strict non-execution in force (`trading_enabled = False`). Zero broker routing, order entry, or custody.*
5. **Public Release Gate:** **`NO-GO (INTERNAL_OFFLINE_RESEARCH_ONLY)`**  
   *Public commercial deployment remains permanently withheld. The application operates strictly as a local research tool bound to `127.0.0.1`.*

---

## 2. Runtime Network Dependency Inventory

A complete codebase audit was performed across all routes, background workers, and client scripts (documented in `network_dependency_inventory.md`):

| Classification | Component Count | Subsystems Included | Offline Behavior |
| :--- | :---: | :--- | :--- |
| **`LOCAL_COMPUTATION`** | 8 | FastAPI Server, Strategy Registry, Indicators, Position Simulator, Security Middleware, Rate Limiter | Computes in-memory with zero network or external file dependencies. |
| **`HISTORICAL_LOCAL_DATA`** | 5 | Parquet Historical Loader (`ohlcv.parquet`), Scientific Startup Gate, HAR-RS-DOW Conformal Engine, Prospective Ledgers | Reads static, read-only disk artifacts. Fails closed on hash mismatch. |
| **`CACHED_RESULT`** | 2 | Calibration Health Observatory, Feature Cache Startup Buffer | Evaluates rolling statistics over in-memory closed bar buffers. |
| **`EXTERNAL_SERVICE_DEPENDENT`** | 3 | Coinbase 15m Adapter, Multi-Exchange Comparator (`routes_market.py`), Legacy Fallback Chain (`http_client.py`) | **Fails closed gracefully** with `DATA_UNAVAILABLE` or empty lists when network is unreachable. |
| **`CURRENTLY_UNAVAILABLE`** | 1 | Pluggable Provider Adapters (`engine/market_data_adapters/`) | Disabled by default via feature flag (`BTC_ENABLE_PROVIDER_ADAPTER=false`). |

---

## 3. Subsystem Verification in Offline Research Mode

### 3.1 Historical Local Dataset Integrity
- **Canonical Dataset:** `data/raw/ohlcv.parquet` contains exactly **42,233 hourly candles** spanning January 1, 2022 to October 26, 2026.
- **Monotonicity & Data Quality:** Timestamps are strictly monotonic increasing ($T_{i} > T_{i-1}$) with zero `NaN` or `Inf` values across Open, High, Low, Close, and Volume.
- **No Synthetic Fabrication:** Zero synthetic bars or interpolated prices exist in the canonical dataset.

### 3.2 Offline Indicator & Strategy Tournament Engine
- **Local Mathematics:** EMA-21, Donchian 24-hour channels, and Average True Range (ATR-14) calculate locally over historical closed bars without outbound network calls.
- **Strategy Registry:** `GET /api/tournament/registry` serves the versioned regime-to-strategy descriptors from in-memory definitions under explicit `governance: "OFFLINE_RESEARCH_ONLY"`.

### 3.3 Offline Analyse Workflow & Zero-Attempt Invariant
- **Workflow Execution:** `POST /api/tournament/analyse` successfully evaluates submitted historical closed bars, determines the market regime, screens eligible strategies with the 7/10 hurdle, and returns candidate trade geometries.
- **Zero Attempts Created:** Confirmed `attempts_created == 0` without exception. Zero records were written to `data/prospective_entry_ledger*.jsonl`.

### 3.4 Governance Lock & Fail-Closed Behavior
- **Terminal Status:** `GET /api/terminal/status` returns the unified status contract with `execution_status = "DISABLED — ANALYSIS ONLY"` and `production_forecast_status = "UNAVAILABLE"`.
- **Live Inference Gate:** `GET /api/terminal/live` fails closed with **HTTP 503 Service Unavailable** (`code: "MODEL_UNAUTHORIZED"`), confirming that research models cannot be accidentally queried as production trade feeds.
- **Input Validation:** Submitting unsupported instruments (e.g., `ETH-USD`) or timeframes (e.g., `15m`) fails closed with **HTTP 422**.
- **Network Resilience:** Simulating total network disconnection on `/api/market/comparator` gracefully returns `status: "DATA_UNAVAILABLE"` without unhandled 500 exceptions.

---

## 4. Protected Research Artifact Invariance

All six protected research files were hashed before and after the audit. All hashes are bit-identical:

| File Path | SHA-256 Checksum | Verification |
| :--- | :--- | :---: |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | **BIT-IDENTICAL** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **BIT-IDENTICAL** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **BIT-IDENTICAL** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **BIT-IDENTICAL** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **BIT-IDENTICAL** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **BIT-IDENTICAL** |

---

## 5. Milestone Deliverables Archive

All artifacts for the V32.62 milestone are archived in `research/reports/v32_62_internal_offline_research/20261029_214200_offline/`:
1. `commands_and_environment.txt` — Environment specifications and Git commit metadata.
2. `git_status_before.txt` & `git_status_after.txt` — Git workspace tracking.
3. `protected_hash_manifest_before.json` & `protected_hash_manifest_after.json` — Bit-level data integrity manifests.
4. `network_dependency_inventory.md` — Complete runtime network dependency classification.
5. `test_run_report.md` — Itemized 9-test execution log with command strings and timings.
6. `report.md` — Executive summary and authoritative governed decisions.

