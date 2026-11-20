# BTCognitive V32.1 — Application Health Audit

**Date:** 2026-10-23  
**Scope:** read-only application and contract audit only. No runtime-source change, no strategy modification, no data ingestion, no experiments, and no live execution.

## 1. Executive summary

The BTCognitive application is structurally healthy under its current research-only contract and no-live-trading guardrails. The backend and frontend enforcement logic are consistent with the project’s explicit design: the system serves research intelligence and empirical baselines, but it does not authorize live capital, order submission, or trade execution.

The separate, unresolved issue remains the data-source and rights gate: the BTC/USD source path is still not qualified for the project’s intended research and AI/ML scope. That is a source-governance problem, not an application-health problem.

## 2. Decision summary

**Application health status:** `FUNCTIONALLY HEALTHY UNDER READ-ONLY RESEARCH CONTRACTS`  
**Data-source gate status:** `BLOCKED — RIGHTS OR PROVENANCE UNRESOLVED`  
**Live trading status:** `DISABLED`  
**Model authorization:** `OFFLINE_RESEARCH_ONLY`

## 3. Evidence reviewed

### 3.1 Runtime guardrails and no-live-trading enforcement

The server startup and runtime policy were inspected in the project source and are aligned with the project’s risk boundaries:

- `api/server.py` initializes the FastAPI app and runs the startup freeze verification before accepting runtime operations.
- `validation/startup_gate.py` enforces scientific-contract verification before startup and fails closed when integrity checks fail.
- `engine/status_contract.py` defines a strict system status contract that keeps execution disabled and separates market status from research authorization.
- `api/market_monitor_routes.py` explicitly sets `live_trading_enabled = False`, `order_submission_enabled = False`, and `execution_status = "DISABLED_ANALYSIS_ONLY"`.
- `api/server.py` sets `live_engine.is_running = False` and keeps alert workers advisory-only.

This is consistent with a system designed for quantitative market intelligence without order placement or live execution.

### 3.2 Frontend and API contract checks

The project includes explicit tests that verify the application does not expose prohibited execution paths or misleading trade claims:

- `tests/test_frontend_contracts.py`
  - verifies the research entry/TP/SL endpoint is blocked unless evidence qualifies it;
  - verifies the API exposes no live order routes;
  - verifies the frontend does not contain misleading trade claims such as guaranteed profit, guaranteed entry, or “beat a coin flip”;
  - verifies the frontend clearly labels the system as a research terminal and discloses the forecast gate.

### 3.3 Operational health evaluation

The production health service attributes were inspected in `engine/production_health.py` and validated by tests:

- `tests/test_production_health.py`
  - verifies `MODEL_HEALTHY`, `MODEL_WATCH`, `MODEL_DEGRADED`, and `MODEL_INVALID` state logic;
  - verifies checksum failure triggers `MODEL_INVALID` with a zero score;
  - verifies canonical status returns a valid production health result.

### 3.4 Empirical market baseline behavior

The market-driver baseline logic is defined to remain non-executable and non-authorized for capital deployment:

- `tests/test_market_drivers.py`
  - ensures the empirical forecast is available only with sufficiently non-overlapping history;
  - ensures `live_capital_authorized` is always `False` in the forecast object;
  - ensures TP/SL values remain `None` for experimental baselines;
  - ensures invalid or insufficient-price inputs do not fabricate a forecast.

This is aligned with the project’s documented risk separation: the system can estimate a distributional baseline without claiming directional or executable trade authorization.

## 4. Operational findings

### 4.1 Positive findings

- The application does not expose live trading or broker execution routes.
- The API and frontend contract tests pass under the current read-only research posture.
- Production health is evaluated as an operational metric, not as a financial-performance metric.
- The system explicitly forbids live capital authorization despite having an empirical forecast engine.
- The startup gate and status contract enforce fail-closed behavior when provenance or scientific integrity are not verified.

### 4.2 Important separation

The application health audit did not find a live-trading capability or an execution pathway. However, this does not resolve the separate source-permission question for BTC/USD historical data and AI/ML development.

The repository’s data-source problem remains a decision gate on rights/provenance. In other words:

- Application health: `PASS` under the no-execution research contract.
- Source qualification: `BLOCKED` pending documented rights and provenance evidence.

## 5. Validation command and result

Executed:

```powershell
cd C:\Projects\BTCognitive\BTCognitive; .\.venv_win\Scripts\python -m pytest tests/test_production_health.py tests/test_market_drivers.py tests/test_frontend_contracts.py -q
```

Result:

- `14 passed` in `19.60s`
- `1 warning` from a FastAPI/Starlette deprecation notice (non-blocking)

## 6. Governance decisions

The project should continue under the following governance posture:

| Decision domain | Status |
|---|---|
| Research Experiment | `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY` |
| Prospective Evidence | `COLLECTING` |
| Model Authorization | `OFFLINE_RESEARCH_ONLY` |
| Live Trading | `DISABLED` |

This keeps the software usable as a research and risk intelligence terminal while preserving the unresolved BTC/USD source-rights requirement.

## 7. Remaining blocker

The remaining blocker is not a software bug in the application itself. The blocker is the unresolved legal and provenance basis for qualifying the BTC/USD dataset for the project’s intended historical quantitative research and AI/ML use.

Until that source gate is resolved, the application must remain in a restricted research-only mode, even though the codebase appears functionally healthy under its own no-execution contract.

## 8. File inspection and preservation

**Created:**
- `research/v32_1_application_health_audit.md`

**Inspected for evidence:**
- `api/server.py`
- `api/market_monitor_routes.py`
- `validation/startup_gate.py`
- `engine/status_contract.py`
- `engine/production_health.py`
- `tests/test_production_health.py`
- `tests/test_market_drivers.py`
- `tests/test_frontend_contracts.py`

**Preserved without modification:**
- all historical provenance reports and data-source decisions;
- all protected ledger files and runtime behavior are unchanged;
- all prior user work remains intact.

No trade routes, live execution logic, source replacement, or protected ledger writes were modified in this audit.
