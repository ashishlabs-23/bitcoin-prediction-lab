# BTCognitive V37.4 — QA and Provenance Report

**Review date:** 2026-11-04  
**Disposition:** Partial QA; no full safe-suite pass asserted.

## Runtime and preflight

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- Baseline status captured before this task: 1,736 entries; 119 tracked modified, 1,617 untracked, 0 staged, 0 deletions.
- Python: 3.13.14; Node: v24.14.0; npm: 11.9.0.
- `.venv_win\Scripts\pytest.exe` and `.venv_win\Scripts\python.exe` exist.
- The `websockets`, `httpx`, FastAPI, pytest, pandas, and PyArrow Python modules are installed.
- `node_modules` was absent; the existing frontend test/check scripts ran without installing packages.
- Documented startup command: `python -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload`. It was not run because the current lifespan's side effects were not cleared for a live-checkout start.
- Complete baseline `git status --porcelain=v1 --untracked-files=all` was saved outside the repository at `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\v37_4_preflight_git_status.txt`.

## Test evidence

| Command | Result |
|---|---|
| `.\.venv_win\Scripts\pytest.exe -q -p no:cacheprovider -m "not network and not quarantined" tests\test_v32_61_provider_adapter_poc.py tests\test_v32_66_provider_contract.py tests\test_candle_manager.py tests\test_coinbase_l2_collector_and_gating.py tests\test_market_monitor_routes.py` | **42 passed, 1 failed**, 23.04s; one Pydantic deprecation warning. The failure is `test_protected_artifacts_bit_level_invariance`: its hard-coded expected SHA-256 for tracked `data/raw/ohlcv.parquet` is `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`, while the checkout file is `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`. The file was not modified in the preflight or current Git status; the test's expected digest is stale/inconsistent with this checkout. We did not update a protected hash or alter the dataset. The protected-file guard itself passed with identical before/after manifest digest. |
| `npm test` | **Passed**; existing frontend verification markers and unavailable-response checks passed. |
| `npm run check` | **Passed**; active and `web_src` JavaScript syntax checks passed. |
| Full Python safe suite | **Not run**; V37.3 reported prior incomplete attempts. No full-suite pass is claimed. |

## Actual-feed QA

One public Bitstamp WebSocket subscription acknowledged correctly and emitted three parseable BTC/USD trades. The `microtimestamp` values interpreted as epoch microseconds were about 226.08 seconds behind local receive times. This is a freshness failure/uncertainty, not a feed-readiness pass. A 30-minute soak was started but stopped before completion; no final soak summary was produced.

The smoke did not test a repository collector, API, existing engine, or browser. No ordinary test depends on public exchange availability.

## Historical candidate and protected-data boundary

- `ff137/bitstamp-btcusd-minute-data` states that portions of its history use flat, zero-volume gap fills. Do not treat those bars as observed trades or genuine zero-activity intervals.
- HF `mrorigo/btc_bitstamp_1min` card advertises 4.86M rows, OHLCV and timestamp fields, but its MIT metadata does not establish upstream data rights; card examples contain null OHLCV records. No parquet/CSV shards were downloaded, and no row-level gap or duplicate rate was calculated.
- HF `WinkingFace/CryptoLM-Bitcoin-BTC-USDT` is BTC/USDT, not BTC/USD; it is excluded from BTCUSD analysis.
- Existing local datasets remain `UNVERIFIED`/`SOURCE_CORROBORATED_NOT_PROVEN` as described in V37.3. No protected holdout observations or labels were accessed for selection. No dataset was written, merged, or backfilled.
- Coinbase terms prohibit unapproved AI/ML validation/training use; no Coinbase data was used in this smoke.

## Integrity and limitations

The pytest protected-file guard reported an unchanged manifest digest before/after the targeted run. No project code or protected data were changed during this task run. The baseline worktree is very large and already dirty; V37.4 reports were added without touching pre-existing files. Final Git counts are recorded in the manager report.

Not verified: completed 30-minute soak, real FastAPI startup/lifecycle, live API response, engine handoff, real browser rendering, reconnect/recovery, durable raw-event recording, and historical data admission.
