# Provider Adapter POC Test Run Report (V32.61)

**Date:** 29 October 2026  
**Auditor / Runner:** BTCognitive Lead Research Orchestrator  
**Target Suite:** `tests/test_v32_61_provider_adapter_poc.py`  
**Execution Environment:** Windows 11, Python 3.13.14, pytest-8.4.1  
**Working Directory:** `C:\Projects\BTCognitive\BTCognitive`  

---

## 1. Test Execution Command & Summary

```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_v32_61_provider_adapter_poc.py -v
```

### Result:
- **Total Tests Collected:** 14
- **Passed:** 14
- **Failed:** 0
- **Skipped:** 0
- **Duration:** 1.29 seconds
- **Exit Code:** 0 (`SUCCESS`)

---

## 2. Itemized Scenario Verification

| # | Test Function Name | Tested Behavior & Invariant | Status | Duration |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `test_valid_candle_response` | Parses Bitstamp raw OHLC response into canonical `NormalizedCandle` objects; validates $L \le O, C \le H$ extrema, ISO timestamps, and license notice. | **PASS** | 0.09s |
| 2 | `test_malformed_missing_ohlcv_fields` | Rejects bars where $H < O$ or non-finite numbers; returns `FeedFreshnessStatus.INCOMPLETE` with `MALFORMED_OHLCV_FIELDS`. | **PASS** | 0.05s |
| 3 | `test_duplicate_and_out_of_order_timestamps` | Detects duplicate timestamps or inverted time series; returns `ORDERING_OR_DUPLICATE_ERROR` and rejects series. | **PASS** | 0.04s |
| 4 | `test_unresolved_gaps_flagged_without_synthesis` | Flags 7200s gap in 1h series (`gap_count == 1`) while returning exactly 2 bars. Zero synthetic candles fabricated. | **PASS** | 0.04s |
| 5 | `test_stale_response_detection` | Flags response as `FeedFreshnessStatus.STALE` when latest bar age exceeds $2 \times \text{timeframe}$ (48h old). | **PASS** | 0.04s |
| 6 | `test_provider_quota_rate_limit_and_timeout` | Handles empty / disconnected upstream payload cleanly; returns `FeedFreshnessStatus.UNAVAILABLE` with `EMPTY_SERIES`. | **PASS** | 0.04s |
| 7 | `test_provider_unavailable_explicit_empty_candles` | When adapter is disabled (`BTC_ENABLE_PROVIDER_ADAPTER=false`), returns `FeedFreshnessStatus.UNAVAILABLE` with `candles: []`; zero fallback prices. | **PASS** | 0.04s |
| 8 | `test_source_quote_timeframe_mismatch` | Rejects unsupported symbols (`ETH/USD`) and unsupported intervals (`2m`) with HTTP 422 and structured error codes. | **PASS** | 0.04s |
| 9 | `test_volume_mapping_and_granularity` | Parses CoinGecko cross-venue format `[[time, o, h, l, c]]`; safely maps missing volume to 0.0 and verifies CoinGecko attribution. | **PASS** | 0.04s |
| 10 | `test_no_silent_provider_fallback` | Asserts that `is_fallback == False` in diagnostics; forbids silent multi-exchange fallback chains (`coinbase_silent_fallback` raises `ValueError`). | **PASS** | 0.03s |
| 11 | `test_forecast_origin_candle_alignment_guard` | Enforces that volatility forecast markers only anchor to the chart when provider, symbol, timeframe, and cutoff timestamp match. | **PASS** | 0.02s |
| 12 | `test_coingecko_ai_training_prohibition_guardrail` | Enforces governance guardrail: calling `assert_ai_training_permitted()` on CoinGecko adapter raises `PermissionError` due to terms ban. | **PASS** | 0.02s |
| 13 | `test_feature_flag_disabled_by_default` | Verifies that `is_provider_adapter_enabled()` defaults to `False` when the environment variable is unset. | **PASS** | 0.02s |
| 14 | `test_protected_artifacts_bit_level_invariance` | Computes SHA-256 hashes of all 6 protected research files and verifies they are bit-identical to the baseline. | **PASS** | 0.78s |

---

## 3. Regression & Defect Summary
- **Zero Failures:** All 14 tests passed on the first clean compilation.
- **Zero Outbound Calls:** Tests execute against deterministic mock payloads; zero external vendor network calls were made.
- **Zero Artifact Mutations:** The 6 protected research datasets and prospective ledgers were completely untouched.

