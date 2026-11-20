# V32.52 — Isolated QA Follow-up Addendum

**Captured:** 2026-10-27  
**Branch / HEAD:** `main` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Release status:** **FAIL / BLOCKED**

This addendum extends the initial [integrity and harness report](./20261027_075029_409880/integrity_harness_report.md). It records the real-HTTP fixture diagnosis, the focused rerun, the fresh full-suite result, and the remaining governance conflict. It does not amend the earlier integrity findings.

## Real-HTTP fixture diagnosis and correction

The initial focused run reported four setup errors after the Uvicorn app lifespan completed. The fixture started a background server thread and immediately attempted an HTTP health request. The isolated harness correctly rejected the connection while Uvicorn had not yet bound the QA-owned port. The fixture caught that guard `RuntimeError` as an arbitrary exception, hid its cause for 60 seconds, and did not stop its thread on failed setup.

The test fixture in [test_isolated_real_http_server.py](../../../tests/test_isolated_real_http_server.py) now waits for Uvicorn's `started` signal before connecting, reports startup and HTTP failures directly, uses a 120-second startup deadline, and stops only its own server thread on setup failure. The harness network policy was not weakened.

The corrected focused command was:

```powershell
.\.venv_win\Scripts\python.exe scripts\qa\v32_52_isolated_runner.py --run tests/test_isolated_real_http_server.py
```

Result: **4 passed in 62.64 seconds**, exit code 0. The isolated test run returned real HTTP responses and completed teardown. The earlier separate guarded Uvicorn reproduction also returned HTTP 200 on `/api/health` and reported its QA-owned thread stopped.

## Fresh full-suite result

The full serial command was:

```powershell
.\.venv_win\Scripts\python.exe scripts\qa\v32_52_isolated_runner.py --run
```

It collected **1,656** items: **1,597 passed, 58 failed, 1 deselected**, with **10 warnings**, in **2,732.75 seconds** (45m32s). Exit code was 1. This is a new V32.52 run; the historical V32.51 list of 51 failures is unavailable, so these 58 failures cannot be claimed to be a direct ID-by-ID reconciliation of that list.

Every current failed test ID is retained in [20261027_full_suite_failure_triage.csv](./20261027_full_suite_failure_triage.csv), with its observed assertion/exception, provisional classification, and confidence. The classification is evidence-based but not a claim that every fixture or stale-contract hypothesis is proven:

| Provisional classification | Count | Summary |
|---|---:|---|
| Fixture, configuration, stale contract, data, or sample limitation | 49 | Includes blocked external DNS/provider access, stale market inputs, persisted-state assumptions, malformed ledger inputs, historical row-count/hash expectations, and changed status strings. |
| Likely code or contract defect needing focused verification | 5 | Floating-point boundary, forecast disclosure wording, probability expectation, and 1h forecast timestamp alignment. |
| Resource-sensitive observation | 1 | One health request measured 1,302.1 ms against a 200 ms threshold during the full suite; this is not a controlled benchmark. |
| Protected-data provenance cannot be classified from test output alone | 3 | Tests pin the former `ohlcv.parquet` hash; the test failures cannot distinguish stale expected hashes from an unresolved data-integrity issue. |

Important observations:

- Multiple scenario tests correctly returned unavailable because copied market data was stale and public data access was isolated. Their expected `SUCCESS` responses were therefore not reproduced.
- Longitudinal tests observed 7 blocks where their expectations were 0; the run alone does not establish whether the persistent snapshot or test fixture is authoritative.
- Shadow/forward-validation tests encountered malformed JSON ledger input (`JSONDecodeError`), including an API HTTP 500. Ledger provenance remains unresolved; no ledger was repaired or rewritten.
- Several model-status, frontend-literal, and documentation assertions appear tied to older contracts; the CSV preserves each exact test ID and its evidence.
- The test suite confirmed the three old-hash assertions still fail against the current primary. This is not authorization to restore or overwrite the parquet.

The full-suite evidence is in [pytest.log](./20261027_082310_447603/pytest.log) and [manifest.json](./20261027_082310_447603/manifest.json). The focused passing run is in [pytest.log](./20261027_082042_352152/pytest.log) and [manifest.json](./20261027_082042_352152/manifest.json).

## Protected files and process ownership

The full-run manifest records identical before/after hashes, sizes, and last-write metadata for all five protected files:

| Protected file | SHA-256 |
|---|---|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` |

The QA-owned-port ledger contains 412 binds and 412 closes with no unreleased QA port at completion. No existing collector or service was stopped or reconfigured. Hash stability in this interval does not establish historical parquet provenance or content authority.

## Authorization and remaining release gates

The runtime health route maps a successful readiness gate to `PRODUCTION_VOLATILITY_INTELLIGENCE`; the readiness gate identifies `HAR-RS-DOW-v1.0` as authorized for volatility-risk-only serving. The same payload disables directional recommendations, order submission, and live trading, and the gate keeps directional research models `OFFLINE_RESEARCH_ONLY`.

This runtime state conflicts with the current README's statement that model authorization is strictly `OFFLINE_RESEARCH_ONLY` and with the V32.52 release requirement. Older audit material describes a risk-only exception, but no new governance decision was provided in this run. No authorization code or docs were changed. The conflict remains a release blocker; do not infer authorization for research challengers or trading.

No browser E2E, full feature-workflow QA, cold/warm performance benchmark, or dead-file cleanup was performed. No repository data was restored, rewritten, or deleted.

1. **Research experiment:** `INCONCLUSIVE`.
2. **Prospective evidence:** `COLLECTING` (prior state is stale/unverified; no fresh confirmatory evidence claimed).
3. **Model authorization:** required policy is `OFFLINE_RESEARCH_ONLY`; runtime risk-only authorization conflicts and remains unresolved.
4. **Live trading:** `DISABLED`.

**Release decision:** **FAIL / BLOCKED** — parquet provenance is unresolved; 58 current test failures remain classified but not all independently resolved; authorization documentation and runtime behavior conflict; critical browser workflows and controlled performance criteria remain unverified.
