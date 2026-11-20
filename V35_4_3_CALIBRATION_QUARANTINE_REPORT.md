# BTCognitive V35.4.3 Calibration Quarantine Report

## Decision

Calibration and reliability outputs are suppressed in the active dashboard and selected current-status API responses. C2 remains disabled. This report does not certify the complete application or enable any forecast, strategy, or execution path.

## Findings and changes

| Surface | V35.4.3 handling | Evidence / limitation |
|---|---|---|
| Dual-hypothesis first-passage, no-exit, effective-sample-size, and interval cards | The frontend now renders `N/A — C2 DISABLED` or `N/A`; it no longer reads probability, N_eff, or CI values from a potentially stale payload. | `web/app.js`; frontend contract script passed. |
| Decision path evidence | Sample size and interval defaults are null; path probability, sample size, interval, and quality are rendered unavailable while C2 is disabled. | `web/app.js`; prior focused tests cover unavailable calibration contracts. |
| Directional confidence | Current directional probability and live signal are forced unavailable in the dashboard. | `web/app.js`; code inspection and frontend contract assertions. This is not evidence about the forecast model. |
| Historical evidence panel | Missing source-provenance status now displays `UNAVAILABLE`; hardcoded retained-subgroup expectancy/sample fallback was removed. Historical values remain dated and explicitly retrospective when supplied by the historical evidence endpoint. | `web/app.js`; frontend contract script passed. |
| Accuracy and calibration endpoints | Accuracy, range coverage, reliability, and calibration metrics remain null/unavailable; no zero or 100% placeholder is treated as an observed metric. | `api/routes_prediction.py`; prior focused Python run and source inspection. |
| Terminal health/status | Unmeasured latency/capacity and coverage values remain unavailable rather than healthy/validated. | `api/routes_terminal.py`; prior focused Python run and source inspection. |
| Missing regime venue provenance | API no longer substitutes `Coinbase Exchange Spot`; it emits `UNAVAILABLE`. | `api/routes_prediction.py`; the added targeted Python test was not completed, so this exact latest change is not runtime-verified. |
| Arena active-position API | The entry guard returns `UNAVAILABLE`, `C2_DISABLED`, null live price and disabled execution authorization while `C2_CALIBRATION_ENABLED` is false. | `api/routes_arena.py`; source inspection. |

## Preserved research and remaining risks

- Dated retrospective research outputs in `api/routes_research.py` were not rewritten or relabelled as prospective evidence.
- The legacy arena implementation behind the disabled C2 guard still contains fallback probabilities, sample counts, and coverage diagnostics. It is not reachable while the guard is false; it must not be re-enabled until those defaults are removed and calibration artifacts are independently verified.
- The API/frontend integration fixture is deterministic test data, not observed market data. The API test mocks the analysis engine, so it verifies route validation, snapshot handoff, provenance, and unavailable fields, but not a full market-analysis computation.
- Other active and historical research surfaces were inspected by source search; this task did not run every API endpoint or browser-render every panel. No complete UI/API calibration audit is claimed.

## Governance state

- C2: `DISABLED`
- Calibration status: `UNAVAILABLE` absent a verifiable artifact
- Model authorization: `OFFLINE_RESEARCH_ONLY`
- Application posture: `ANALYSIS_ONLY`
- Standard HAR accuracy: `NOT_ESTABLISHED`; registered artifact absent
- Live trading and order submission: `DISABLED`
