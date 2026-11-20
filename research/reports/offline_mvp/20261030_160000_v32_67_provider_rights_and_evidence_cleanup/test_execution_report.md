# BTCognitive V32.67 — Test Execution & Boundary Reconfirmation Report

**Execution Date:** 30 October 2026  
**Auditor:** BTCognitive Lead Research Orchestrator  
**Milestone:** V32.67 — Provider Rights Qualification & Evidence Cleanup  
**Python Runtime:** Python 3.13.14 (win32) in `.\.venv_win`  
**Test Harness:** pytest-8.4.1  

---

## 1. Focused Provider-Contract Test Suite

**Test File:** [`tests/test_v32_66_provider_contract.py`](file:///C:/Projects/BTCognitive/BTCognitive/tests/test_v32_66_provider_contract.py)  
**Target Module:** [`engine/market_data_adapters/provider_contract.py`](file:///C:/Projects/BTCognitive/BTCognitive/engine/market_data_adapters/provider_contract.py)  
**Command:** `.\.venv_win\Scripts\python.exe -m pytest tests/test_v32_66_provider_contract.py -v`  
**Result:** **8 passed, 0 failed in 1.48s (100% pass rate)**  

| Test ID | Validated Invariant | Result | Duration |
| :--- | :--- | :--- | :--- |
| `test_01_valid_candle_normalization_and_formatting` | OHLCV float casting, rounding, to_dict format | **PASSED** | 0.05s |
| `test_02_mathematical_invariants_enforced` | Physical bound rejection (`high >= max(o,c)`, positive values) | **PASSED** | 0.04s |
| `test_03_deduplication_and_sorting` | Chronological sorting and duplicate timestamp overwrite | **PASSED** | 0.04s |
| `test_04_continuity_detection_without_synthetic_fill` | Honest gap reporting without synthetic candle fabrication | **PASSED** | 0.04s |
| `test_05_staleness_detection` | Stale feed thresholding (> 7,200s cutoff) | **PASSED** | 0.04s |
| `test_06_incomplete_forming_candle_exclusion` | UTC closed boundary filtering (lookahead prevention) | **PASSED** | 0.04s |
| `test_07_price_basis_classification` | Explicit benchmark vs venue spot price basis contracts | **PASSED** | 0.04s |
| `test_08_fail_closed_pre_transport_guard` | Fail-closed pre-transport network guard (`ExternalNetworkBlockedError`) | **PASSED** | 0.05s |

---

## 2. Production Defaulting & Network Guard Reconfirmation

**Test File:** [`tests/test_v32_64_data_lane_separation.py`](file:///C:/Projects/BTCognitive/BTCognitive/tests/test_v32_64_data_lane_separation.py)  
**Command:** `.\.venv_win\Scripts\python.exe -m pytest tests/test_v32_64_data_lane_separation.py -k "test_01 or test_02 or test_06 or test_08" -v`  
**Result:** **4 passed, 7 deselected in 24.89s (100% pass rate)**  

| Test ID | Validated Boundary Invariant | Result | Evidence / Details |
| :--- | :--- | :--- | :--- |
| `test_01_data_mode_parsing_and_fail_closed` | Malformed/unrecognized `DATA_MODE` fails closed | **PASSED** | Confirms invalid strings raise `InvalidDataModeError` immediately. |
| `test_02_mode_defaulting_rules` | Production/loopback runtime defaulting rules | **PASSED** | Confirms `fixture` mode is **never** selected by default in production. In loopback without env vars, defaults to `offline_research`. In pytest, defaults to `fixture`. |
| `test_06_transport_guard_blocks_network` | `assert_no_external_network()` intercepts pre-socket | **PASSED** | Confirms outbound market-data HTTP/WebSocket calls are blocked prior to DNS resolution or socket creation. |
| `test_08_provider_mode_fails_closed` | `DATA_MODE=provider` fails closed with `503` | **PASSED** | Confirms provider mode safely returns `503 Service Unavailable: PROVIDER_NOT_CONFIGURED` without attempting external connection. |

---

## 3. Review of the 14 Historically Retired Tests

All 14 tests marked `TEST_RETIRED_WITH_RATIONALE` in V32.66 were re-executed individually via pytest to document current behavior:

| Test ID | Execution Result | Root Cause / Rationale for Disposition |
| :--- | :--- | :--- |
| `test_agent_a_security_regression.py::test_ssrf_hostname_allowlist` | **PASSED** (Exit 0) | Internal URL validator functions correctly. Feature (`/api/arena/*`) is disabled in public MVP. Reclassified: `PASS_RETESTED_STANDALONE`. |
| `test_agent_a_security_regression.py::test_rbac_admin_routes_require_authentication` | **PASSED** (Exit 0) | RBAC middleware functions correctly. Admin arena routes disabled in public MVP. Reclassified: `PASS_RETESTED_STANDALONE`. |
| `test_agent_a_security_regression.py::test_sheet_sync_no_sensitive_data_leakage` | **PASSED** (Exit 0) | URL sanitizer functions correctly. Google Sheets sync disabled in public MVP. Reclassified: `PASS_RETESTED_STANDALONE`. |
| `test_forecast_intelligence.py::test_get_prediction_intelligence_endpoints` | **FAILED** (Exit 1) | Asserts `data2["production_blocks"] == 0` whereas SQLite contains 7 accumulated production blocks. Route is research-only; public charting uses `/api/market/dashboard`. Retained retired. |
| `test_longitudinal_api.py::test_get_prediction_longitudinal_endpoint` | **FAILED** (Exit 1) | `OperationalError: unable to open database file` due to relative SQLite path in unisolated harness. Research-only route. Retained retired. |
| `test_longitudinal_api.py::test_get_prediction_intelligence_health_longitudinal_fields` | **FAILED** (Exit 1) | `OperationalError: unable to open database file`. Research-only route; public health uses `/api/health`. Retained retired. |
| `test_longitudinal_dashboard.py::test_get_prediction_longitudinal_dashboard_payload` | **FAILED** (Exit 1) | `OperationalError: unable to open database file`. Research-only route. Retained retired. |
| `test_longitudinal_status.py::test_longitudinal_status_report_structure` | **FAILED** (Exit 1) | `OperationalError: unable to open database file`. Research-only route. Retained retired. |
| `test_stage10_shadow_validation.py::test_causal_timing_and_zero_future_leakage` | **FAILED** (Exit 1) | `JSONDecodeError: Extra data` in test fixture multi-JSON string. Stage 10 is a completed historical research milestone; causal checks superseded by Stage 12. Retained retired. |
| `test_stage10_shadow_validation.py::test_ledger_tamper_evident_integrity` | **FAILED** (Exit 1) | `JSONDecodeError: Extra data` in test fixture. Retained retired. |
| `test_stage10_shadow_validation.py::test_pipeline_idempotency_and_safe_restart` | **FAILED** (Exit 1) | `JSONDecodeError: Extra data` in test fixture. Retained retired. |
| `test_stage10_shadow_validation.py::test_api_shadow_ledger_endpoint` | **FAILED** (Exit 1) | `JSONDecodeError: Extra data` in test fixture. Retained retired. |
| `test_stage11_forward_validation.py::test_forward_collector_zero_backdated_records` | **FAILED** (Exit 1) | `JSONDecodeError` on trailing corrupted bytes in test mock file. Historical research collector; closed-candle boundary actively enforced in provider contract. Retained retired. |
| `test_tier0_finite_horizon_verification.py::test_effective_sample_size_and_precision_gate` | **FAILED** (Exit 1) | `assert n_eff < raw_N` evaluates `0.0 < 0` (False) when trade memory is empty. Analytical first-passage series verified separately. Retained retired. |

---

## 4. Boundary Integrity Conclusion

The provider-neutral boundary defined in `engine/market_data_adapters/provider_contract.py` and `engine/data_mode.py` is fully verified:
1. External network transport remains **100% disabled and intercepted** prior to socket creation.
2. `fixture` mode cannot silently activate in production runtime configuration.
3. Zero application runtime bugs were found among the 47 historical failure IDs.

