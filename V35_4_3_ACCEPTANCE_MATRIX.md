# BTCognitive V35.4.3 Acceptance Matrix

Status definitions: `PASS` means evidence was observed for the stated scope; `FAIL` means a known requirement is unmet; `UNVERIFIABLE` means the required evidence was not obtained.

| ID | Criterion | Status | Evidence / limitation |
|---|---|---|---|
| A01 | Existing branch and HEAD preserved | PASS | `milestone/v35.3-critical-remediation`, `25d483f4c3646661b57311de9d0b53d2be881adb`. |
| A02 | Protected files unchanged during a completed permitted focused test run | PASS | Pytest guard reported 1,848 files unchanged; matching inventory digests recorded in the test report. |
| A03 | Historical ledger/database integrity | UNVERIFIABLE | No trustworthy pre-remediation byte-identical baseline; current hashes match the forward capture only. No corruption is inferred. |
| A04 | Test databases use disposable paths and canonical access is blocked | PASS, focused scope | Isolation tests passed in the completed 29-test run; full suite not run. |
| A05 | All test writers and caches isolated across the repository | UNVERIFIABLE | Static searches found legacy database/file-write references; full suite and every writer were not executed. |
| A06 | C2 remains disabled and current calibration metrics are unavailable | PASS, inspected surfaces | Arena guard, prediction/terminal payloads, frontend suppression, and frontend assertions show disabled/unavailable semantics. |
| A07 | Unknown regime venue does not silently default to Coinbase | UNVERIFIABLE | Source now returns `UNAVAILABLE`; the newly added Python regression test was in a run stopped before summary. |
| A08 | No hardcoded current calibration/coverage defaults | PASS, active dashboard scope | Hardcoded current path probabilities/CI/N_eff are suppressed; historical fallback metric removed. Legacy arena fallbacks remain behind the disabled C2 guard. |
| A09 | API analyzes precisely the submitted candle snapshot | PASS, route handoff only | TestClient API test checks exact submitted candle ordering/count and snapshot hash, but mocks the real analysis engine. |
| A10 | Verified real local BTCUSD data is analyzed by the real engine offline | UNVERIFIABLE | No complete real-engine API run using a provenance-verified local snapshot was performed. The deterministic fixture is synthetic test data; the checked-in local parquet is historical and not a verified fresh snapshot. |
| A11 | Frontend test contract and JavaScript syntax | PASS | `node tests_frontend.js`; `node --check web\app.js`. |
| A12 | Python validation after the latest API venue change | UNVERIFIABLE | Revalidation command was stopped after 1,342 seconds with no pytest summary. Earlier 29-test run predates that one-line change. |
| A13 | Complete browser/API/real-engine integration | UNVERIFIABLE | Not run. |
| A14 | Standard HAR exact registered artifact and accuracy | PASS, correctly quarantined | `standard_har_v1.joblib` absent; registry digest remains a placeholder. Accuracy remains `NOT_ESTABLISHED`; no percentage is reported. |
| A15 | Live trading, broker, order submission, and C2 activation | PASS, disabled | Authorization remains `OFFLINE_RESEARCH_ONLY`; application is `ANALYSIS_ONLY`; trading and order submission remain disabled; C2 remains disabled. |

## Milestone decision

**BLOCKED.** The active calibration outputs and focused test isolation controls are improved and have evidence, but real-engine offline analysis using verified local BTCUSD data and Python validation of the latest provenance fallback are not established. This is not a finding of protected-data corruption.
