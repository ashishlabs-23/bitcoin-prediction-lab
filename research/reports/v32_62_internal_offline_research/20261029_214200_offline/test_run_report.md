# Offline Research Mode Test Run Report (V32.62)

**Date:** 29 October 2026  
**Auditor / Runner:** BTCognitive Lead Research Orchestrator  
**Target Suite:** `tests/test_v32_62_offline_research_mode.py`  
**Execution Environment:** Windows 11, Python 3.13.14, pytest-8.4.1  
**Working Directory:** `C:\Projects\BTCognitive\BTCognitive`  
**Host Binding:** `127.0.0.1:8000` (Loopback only)  

---

## 1. Test Execution Command & Outcome

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_v32_62_offline_research_mode.py -v
```

### Result:
- **Total Tests Collected:** 9
- **Passed:** 9
- **Failed:** 0
- **Skipped:** 0
- **Duration:** 26.24 seconds
- **Exit Code:** 0 (`SUCCESS`)

---

## 2. Itemized Verification Results

| # | Test Function Name | Subsystem & Invariant Verified | Outcome |
| :---: | :--- | :--- | :---: |
| 1 | `test_historical_dataset_integrity_and_gap_preservation` | Canonical `ohlcv.parquet` contains exactly 42,233 hourly bars with strictly monotonic timestamps and zero NaN / Inf prices. Zero synthetic interpolation. | **PASS** |
| 2 | `test_offline_technical_indicator_computation` | EMA-21, Donchian 24h channels, and ATR-14 calculate locally over historical closed bars without outbound network calls. | **PASS** |
| 3 | `test_offline_terminal_status_and_live_intelligence` | `/api/terminal/status` returns `execution_status = "DISABLED — ANALYSIS ONLY"`. `/api/terminal/live` fails closed under `OFFLINE_RESEARCH_ONLY` with HTTP 503 (`MODEL_UNAUTHORIZED`). | **PASS** |
| 4 | `test_offline_strategy_registry` | `/api/tournament/registry` serves versioned regime-to-strategy descriptors from in-memory registry (`status: "SUCCESS"`). | **PASS** |
| 5 | `test_offline_analyse_setup_on_historical_bars` | `POST /api/tournament/analyse` executes the complete 7-step analysis workflow over local historical bars. Confirms `attempts_created == 0` and zero ledger mutations. | **PASS** |
| 6 | `test_offline_fail_closed_on_unsupported_inputs` | Unsupported instruments (`ETH-USD`) and unsupported timeframes (`15m`) are rejected with HTTP 422. | **PASS** |
| 7 | `test_external_comparator_fails_closed_when_network_down` | When external network calls are simulated offline, `/api/market/comparator` catches network errors gracefully and fails closed with `DATA_UNAVAILABLE`. | **PASS** |
| 8 | `test_provider_adapter_gated_offline` | Market data provider adapters remain disabled by default (`BTC_ENABLE_PROVIDER_ADAPTER=false`). | **PASS** |
| 9 | `test_protected_artifacts_bit_level_invariance` | SHA-256 hashes of all 6 protected research datasets and prospective ledgers are verified bit-identical. | **PASS** |

---

## 3. Epistemic & Security Summary
- **Zero Outbound Calls in Offline Suite:** Feature evaluation, strategy screening, and technical indicators execute strictly locally.
- **Fail-Closed Safeguards:** Where an endpoint has an external dependency (such as live multi-exchange price comparison), it degrades gracefully to `DATA_UNAVAILABLE` rather than crashing with unhandled 500 errors.
- **Zero Ledger Contamination:** No simulated trades, attempts, or ledger writes were generated during the offline analysis runs.

