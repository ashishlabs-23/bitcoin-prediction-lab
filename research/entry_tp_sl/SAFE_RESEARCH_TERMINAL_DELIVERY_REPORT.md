# Safe Research Terminal Delivery Report

**Date:** 2026-10-09
**Status:** `LOCALHOST_VERIFIED`

## Runtime and build

- Workspace: `C:\Projects\BTCognitive\BTCognitive`
- Python: `.venv_win\Scripts\python.exe`, Python 3.13.14.
- `python -m pip check`: passed; no broken requirements.
- The frontend is the existing static `web/index.html`, `web/app.js`, and `web/styles.css`. No `package.json` or lockfile/build script was found; no frontend install or build applies.
- `node --check web\app.js`: passed.
- Safe entry point: `api.local_safe_server:app`, served at `http://127.0.0.1:8000/`. It binds to loopback only.

## Safe application surface

The safe app serves the static UI and exposes `/health`, `/ping`, `/api/local/status`, `/api/market/status`, `/api/research/status`, `/api/research/entry-tp-sl`, `/prediction/latest`, and `/api/scenario/options`. `/api/scenario/calculate` is a deterministic, non-persistent calculation from explicit user inputs; it does not run inference or place orders. `/openapi.json` and `/docs` remain available.

The safe entry point does not import the production app, legacy inference engine, feature cache, market-memory module, or research pipeline. Tests assert this import isolation. It does not register legacy routers. Model inference reports `MODEL_UNAVAILABLE`; research reports `BLOCKED_AUDIT_FAILURE`; order execution is `DISABLED`.

The safe page removes external asset references and serves a sanitized local stylesheet under a cache-busted URL so blocked remote fonts do not cause browser CSP errors. It displays market data and model availability separately from application health and research authorization.

## Regression and dependency checks

- Focused safe-terminal, Bitstamp adapter, shared prediction, and frontend contract tests plus `tests\entry_tp_sl`: **151 passed, 0 failed**, exit code 0.
- Standalone `tests\entry_tp_sl`: **123 passed, 0 failed**, exit code 0.
- Warnings in the combined run: the existing Hypothesis `.hypothesis` collection warning and Starlette's `httpx` test-client deprecation warning. The standalone research run reported the Hypothesis warning only.
- Python syntax checks passed for the safe server, scenario calculator, Bitstamp adapter, and their focused tests.

## Live localhost verification

Observed HTTP status codes: `/` 200, `/health` 200, `/ping` 200, `/api/local/status` 200, `/api/research/status` 200, `/api/research/entry-tp-sl` 200, `/prediction/latest` 200, `/api/scenario/options` 200, and `/openapi.json` 200.

The browser loaded the existing Research Terminal from `http://127.0.0.1:8000/`. The safe UI's same-origin calls reached the local API. No console or page errors were observed in the final cache-busted browser session. The registered barrier pairs loaded dynamically. A browser-entered example using pair 04, LONG, reference price 100 USD, and ATR 2 USD returned the explicitly labelled `SCENARIO_CALCULATION — NOT A MODEL PREDICTION`: entry 100.00, TP 101.50, SL 98.50, and 120-minute horizon. These were user-input calculator outputs, not a model signal.

The final browser session showed market data as `DATA_UNAVAILABLE` after the read-only Bitstamp request failed with `ConnectError`; no price was displayed or substituted. `/prediction/latest` returned `MODEL_UNAVAILABLE` without Entry/TP/SL or probability values. Research authorization remained blocked, and the UI clearly stated that real order execution is disabled.

## Research authorization and protected state

`run_authorization.json` remains `BLOCKED_AUDIT_FAILURE`, `authorized: false`, with blocked findings B1, B2, and D5. No research experiment was run, no model was trained, and no holdout was opened. The trial ledger and frozen research artifacts listed below match the hashes recorded in the prior localhost verification report:

| Artifact | Current SHA-256 |
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

The contract manifest's raw-file SHA-256 is still `B5A17A75862339BCC8928971F323F6DF4F642F55B3A5A43A502A3AFA75E4F1CE`, while its embedded and registered hash is `b6b94d69e576be0357ce9249f24ca05fb44430e6e9050a940054833204e0013f`. This discrepancy remains unresolved and is reported as `PROVENANCE_FAILURE`; no manifest rewrite or claim of historical hash identity was made.

## Final classification

`LOCALHOST_VERIFIED` — the safe frontend rendered in a browser, local API connectivity and the user-input scenario calculation were observed, and all listed localhost endpoints responded. Market data and model inference remain honestly unavailable; research execution remains blocked.
