# BTCognitive Localhost Verification Report

**Date:** 2026-10-09
**Final status:** `LOCALHOST_VERIFIED`

## 1. Python environment and dependencies

- Workspace: `C:\Projects\BTCognitive\BTCognitive`
- Interpreter: `C:\Projects\BTCognitive\BTCognitive\.venv_win\Scripts\python.exe`
- Version: Python 3.13.14
- Command: `.\.venv_win\Scripts\python.exe -m pip check`
- Exit code: 0 — `No broken requirements found.`

## 2. Frontend and build

- Frontend directory: `C:\Projects\BTCognitive\BTCognitive\web`
- Existing assets served: `index.html`, `app.js`, and `styles.css`.
- No `package.json`, lockfile, build script, or documented frontend dev-server command was found. This is a static frontend; no install or build was applicable, and no new tooling was introduced.
- The local-safe app serves the existing UI assets and sets local-safe mode in the returned index page. No frontend framework or project files were generated.

## 3. Safe application and permitted surface

- Entry point: `api.local_safe_server:app`
- Command:
  `.\.venv_win\Scripts\python.exe -m uvicorn api.local_safe_server:app --host 127.0.0.1 --port 8000`
- Bind address: `127.0.0.1` only.
- Read-only application routes: `/`, `/health`, `/ping`, `/api/local/status`, `/api/market/status`, `/api/research/status`, `/api/research/entry-tp-sl`, and `/prediction/latest`, plus static frontend assets. FastAPI's read-only `/openapi.json` and `/docs` were also available.
- The safe entry point imports no production app, legacy inference engine, feature cache, market-memory module, or experiment runner. An isolated subprocess test confirms these modules are not imported by the safe entry point. It does not register legacy routers.

## 4. Side-effect and inference safeguards

Local-safe startup and request handling did not call or import paths that sanitize operational market memory, start/train `live_engine`, fit `AdaptiveRegimeEnsemble`, build the legacy live dataset, persist predictions, resolve outcomes, write trial-ledger events, or run the Entry/TP/SL research pipeline.

The safe routes perform read-only status/artifact checks and static serving. Market data and model inference report `DATA_UNAVAILABLE`; current Entry/TP/SL signal and metrics are null/absent. Research execution reports `BLOCKED_AUDIT_FAILURE`; live order execution reports `DISABLED`.

The shared prediction API no longer republishes cached legacy 24-hour forecasts as current Entry/TP/SL results. Its Entry/TP/SL route exposes authorization/provenance state without manufacturing a signal. The arena what-if endpoint now requires explicit scenario boundaries and verified volatility/reference inputs instead of substituting default prices, barriers, volatility, costs, or solver probabilities.

## 5. Tests

- Dependency check: exit code 0.
- Command:
  `.\.venv_win\Scripts\python.exe -m pytest -q --timeout=30 tests\test_local_safe_server.py tests\test_shared_prediction_endpoint_guards.py tests\test_frontend_contracts.py tests\entry_tp_sl`
- Final result: **134 passed, 0 failed, 0 skipped**, exit code 0.
- This combined run includes the existing Entry/TP/SL regression suite and focused safe-server, shared prediction endpoint, and frontend contract tests.
- Warnings: (1) the existing Hypothesis pytest-plugin warning about `.hypothesis` collection due to `norecursedirs`; (2) Starlette deprecation warning for using `httpx` with `starlette.testclient`.
- An initial focused test attempt exposed two test-assertion mismatches with the safe route schema. The assertions were corrected, and the final combined run passed.

## 6. Runtime HTTP checks

The server remained running and bound only to `127.0.0.1:8000`. Observed responses:

| URL path | HTTP | Observed result |
|---|---:|---|
| `/` | 200 | Existing UI served as HTML |
| `/health` | 200 | App operational; market/inference unavailable; research blocked; execution disabled |
| `/ping` | 200 | `ok` with timestamp |
| `/openapi.json` | 200 | OpenAPI document served |
| `/docs` | 200 | Interactive docs served |
| `/api/local/status` | 200 | Truthful operational, market, inference, research, and execution states |
| `/api/market/status` | 200 | `DATA_UNAVAILABLE`, no source enabled |
| `/api/research/status` | 200 | `BLOCKED_AUDIT_FAILURE`, unauthorized |
| `/api/research/entry-tp-sl` | 200 | Blocked; no hypothetical signal or metrics |
| `/prediction/latest` | 200 | `DATA_UNAVAILABLE`; no numeric prediction payload |
| `/app.js` | 200 | Existing frontend script served |

The server log is at:
`C:\Users\Ashish\.copilot\session-state\5302c753-8afa-469c-a79e-08b987df05bb\files\local_safe_uvicorn.log`

## 7. Browser and frontend/API integration

- Browser opened `http://127.0.0.1:8000/`; the existing page rendered the local-safe Research Terminal.
- The page requested `/styles.css`, `/app.js`, `/health`, and `/api/local/status` from the same `http://127.0.0.1:8000` origin. Same-origin requests require no cross-origin CORS configuration.
- Browser console errors: 0. Page errors: 0.
- The UI explicitly showed market data and inference as unavailable, research authorization as blocked, historical outputs as unverified, and manifest integrity as failed.
- The UI displayed no Entry/TP/SL signal or performance estimate and stated that real order execution is disabled.
- No order execution pathway was registered or invoked.

## 8. Research authorization and protected artifacts

`research\entry_tp_sl\run_authorization.json` remains `BLOCKED_AUDIT_FAILURE`, `authorized: false`, with findings B1, B2, and D5. No experiment was run, no model was trained, the historical holdout was not opened, and no trial event or historical metric was changed.

SHA-256 values observed before launch:

| Artifact | SHA-256 |
|---|---|
| `trial_ledger.jsonl` | `E4D547C52586094ED50915DBC913E27A87F8876AA382547368CDD19461170789` |
| `contract_freeze_manifest.json` | `B5A17A75862339BCC8928971F323F6DF4F642F55B3A5A43A502A3AFA75E4F1CE` |
| `decision_contract.json` | `3AC4F0D2B93488ABDA84DC78A907749D6AE08ACB22FF651C41749B9A4A3D1268` |
| `entry_execution_contract.json` | `0DC17CED1BE5F7FD9219BFB22C49FC19B45618E04799A6F8067C02F10B4B6361` |
| `instrument_contract.json` | `CE441C4A1E63BD209AD478CEB234D35114D8C86E851DED46B72EE47C2007F9E7` |
| `outcome_accounting_contract.json` | `FC9578C0195249FAED6912001ADD1356355C513E38771BF8D37A8168A93D5A28` |
| `PREREGISTRATION_v1.md` | `38050919334B13D91A91D9E84AD726AB819CD7B3F8884621A31A362379C8EE89` |
| `resolver_contract.md` | `3B076BD5C21244E32347DBA3F0EE466F034730437B270E82714E32CA6700163F` |
| `barrier_contract.py` | `290311994DE7F14C7216C1B92053CBD085F0FD1D4A7749A24520C91D4D4E7FCC` |

### Manifest hash discrepancy

The manifest's raw file SHA-256 is `B5A17A75862339BCC8928971F323F6DF4F642F55B3A5A43A502A3AFA75E4F1CE`. Its embedded `manifest_sha256` and the implementation manifest's registered hash are both `b6b94d69e576be0357ce9249f24ca05fb44430e6e9050a940054833204e0013f`. They do not agree, so the runtime reports `PROVENANCE_FAILURE`.

The manifest records commit `cd1017aa90637bb81b1edf263f620e89346d84ca`; Git history inspection found the current manifest content at commit `fedfd16` and no evidence that the embedded value is the current raw-file hash. The manifest was not rewritten, and no historical hash identity is claimed.

## 9. Conclusion

**`LOCALHOST_VERIFIED`** — the isolated safe application started on loopback, the frontend rendered in a browser, and same-origin API calls returned the expected blocked/unavailable states. The existing Entry/TP/SL regression suite and focused safety tests passed. Research authorization remains blocked; no trading, model fitting, or research execution was enabled.
