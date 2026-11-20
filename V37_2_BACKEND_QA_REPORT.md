# V37.2 Backend QA Report

**Date:** 2026-11-04 (UTC+05:30)  
**Agent:** 3 — backend test files and report only  
**Branch / baseline commit:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`

## Scope and safety

Added `tests/test_v37_2_backend_contracts.py` and this report only. No production code, prior report, contract, protected dataset, SQLite database, or ledger was changed. No live network was used. Tests build a small FastAPI app containing only `market_monitor_routes.router`, use synthetic fixtures/stubs, and do not import `api.server` or run its lifespan/eager tournament constructor.

The initial worktree already contained extensive dirty API, test, data, and report files. Those were preserved. The repository test guard reported identical before/after protected-file manifest hashes; no protected observations were loaded or interpreted by the test code.

## Findings

### Reproducible defect — BTCUSDT candles were returned as BTC-USD; corrected

**Severity:** Data-identity / contract defect.  
**Root cause:** `api/market_monitor_routes.py::market_candles` normalizes the query symbol and accepts both `BTCUSD` and `BTCUSDT`, but the hourly fallback uses the same validated local BTC-USD snapshot and always labels the response `symbol: "BTC-USD"`. The endpoint therefore accepts a different quote instrument and can silently return BTC-USD data under an apparent BTCUSDT request. `api/server.py` registers this router before the legacy market router, so this is the active handler for `/api/market/candles`.

The initial synthetic TestClient case reproduced HTTP 200 / `FRESH` for `symbol=BTCUSDT`, with the response mislabeled as `BTC-USD`. No real data was used.

**Correction:** The manager changed the symbol allowlist to accept only normalized `BTCUSD`. `BTCUSDT` is now rejected as `UNSUPPORTED_REQUEST` before any market-data read. The regression case asserts the rejected response and patches the dashboard access path to fail if called. A separate BTC-USDT source was not added.

### Frontend mapping — verified statically

The active `web/index.html` mounts `web/app.js?v=35.4.1`. Its current fetches map market display to `/market/latest`, candles to `/api/market/candles` with `symbol=BTC-USD`, comparator to `/market/comparator`, and forecast views to `/api/forecast/latest` and `/api/prediction/price/forecast`. The checked router defines the market/dashboard, candles, comparator, forecast, and research-analysis contracts. `/api/research/entry-tp-sl` is not fetched by `app.js`; it remains an API-only fail-closed contract.

## Contract checks

| Area | Synthetic verification |
|---|---|
| Health / readiness | `/api/health` returns HTTP 200 with monitor-only mode and execution/trading disabled; `/api/readiness` retains the blocked authorization state and disabled execution. |
| Market / dashboard | `/api/market/latest` and `/api/dashboard` return the synthetic payload; `/api/market/dashboard` provider failure becomes `DATA_UNAVAILABLE` without leaking the synthetic exception message. Invalid dashboard horizon returns HTTP 422. |
| Candles | Invalid symbol/interval return `UNSUPPORTED_REQUEST`; offline 15m with an empty stub cache returns `DATA_UNAVAILABLE`; BTCUSDT is rejected before market-data access by the corrected handler. |
| Comparator | Synthetic stale quote state passes through as `DEGRADED`; fixture/offline mode returns `DATA_UNAVAILABLE` with `EXTERNAL_NETWORK_BLOCKED`. The latter path exits before any provider fetch. |
| Forecast | `/api/forecast/latest` returns a synthetic unavailable contract; `/api/prediction/latest` retains `NOT_ESTIMATED` and no live-capital authorization. `/api/prediction/price/forecast` was mapped statically, not invoked because its handler loads the forecast engine/data. |
| Analysis | `/api/research/entry-tp-sl` returns `BLOCKED`, null signal/entry/TP/SL, and trading disabled. |

## Prior evidence, not rerun

`V37_1_APPLICATION_RUNTIME_ADDENDUM_20261104.md` previously documented the isolated synthetic application-lifespan check and its `/api/health`, hourly/15m candles, and dashboard-unavailable responses. That evidence is referenced as prior work only; this task did not rerun the production app or lifespan. The addendum itself cautions that synthetic results do not establish real-data freshness or production readiness.

## Validation and release decisions

Command run:

```powershell
.\.venv_win\Scripts\pytest.exe tests\test_v37_2_backend_contracts.py -q
```

**Initial result:** 7 passed in 3.48s, including the then-failing behavior assertion that documented the mismatch.

**Post-fix rerun:**

```powershell
.\.venv_win\Scripts\pytest.exe tests\test_v37_2_backend_contracts.py -q
```

**Result:** 7 passed in 6.60s after the route allowlist and synthetic regression test were updated. The focused run is the only post-fix verification for this backend file; it does not establish real-data behavior or production app startup. Each pytest run's protected-file guard reported unchanged hashes.

The manager also ran the V37.1 focused regression set after this patch:

```powershell
.\.venv_win\Scripts\pytest.exe tests\test_workstream4_qa_contracts.py tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py tests\entry_tp_sl -q
```

**Result:** 118 passed in 14.55s. This did not include the full suite.

- **Research experiment:** `INCONCLUSIVE` — synthetic API contracts only; one data-identity defect reproduced.
- **Prospective evidence:** `NOT_STARTED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`

## Manager integration addendum

The agent's scope was limited to the synthetic market-monitor API contract tests; the statement above that its work changed no production code remains true for that workstream. During final integration, the manager found a separate no-fabrication defect in `api/routes_user_positions.py`: list/detail responses injected hard-coded directional probabilities (`0.45`/`0.55`) and a fixed momentum/moderate regime despite having no such model output. Those arguments are now omitted so the copilot emits empty forecast/regime context rather than unsupported signals.

Regression coverage was added to `tests/test_v37_2_backend_contracts.py`. It invokes both route handlers with an isolated fake tracker/copilot and a mocked unavailable quote; no provider request or protected market data is used. Final execution evidence is recorded in the manager acceptance report.

The final focused command was:

```powershell
.\.venv_win\Scripts\pytest.exe tests\test_v37_2_backend_contracts.py -q
```

**Final result:** 8 passed in 2,662.37 seconds. The pytest protected-file guard passed for 1,848 files with identical before/after manifest SHA-256 values.
