# V32.52 — Data Integrity and Isolated QA Harness Preflight

**Run ID:** `20261027_075029_409880`  
**Captured:** `2026-10-27T07:50:53+05:30`  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Branch / HEAD:** `main` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Milestone status:** **FAIL / BLOCKED** — integrity discrepancy unresolved; no release advancement

## Executive result

The current primary parquet is unchanged from the post-incident V32.51 state. A read-only comparison found an exact byte-for-byte copy of the historical pre-incident hash at `data/raw/ohlcv_backfilled.parquet`, and the current primary contains the same 42,177 overlapping timestamped rows plus 56 current-only timestamps. This is consistent with data having been appended, but it does not establish who wrote the primary, when those added records were obtained, or whether the copy is an authorized source of record. **No parquet or ledger was restored, rewritten, regenerated, or deleted. The incident remains open.**

A disposable-repository QA runner was added and its guard self-test and `--prepare-only` flow were verified. **No pytest suite, browser test, API test, collector, ingestion command, or writer was run.** The V32.50 51-failure reconciliation, browser workflows, and performance measurements remain outstanding.

## Read-only integrity findings

| File / evidence | Current observation |
|---|---|
| `data/raw/ohlcv.parquet` | SHA-256 `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f`; 2,329,745 bytes; mtime `2026-10-26T23:12:20.3982917+05:30`; 42,233 rows; UTC range `2022-01-01 00:00`–`2026-10-26 16:00`. |
| `data/raw/ohlcv_backfilled.parquet` | SHA-256 `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c`—exactly the previously recorded hash; 2,326,699 bytes; 42,177 rows; UTC range `2022-01-01 00:00`–`2026-10-24 08:00`. |
| `research/data_audit_summary.json` | Records that same historical hash for `data/raw/ohlcv.parquet`, with 42,177 rows and the same end timestamp. File mtime is `2026-10-24T15:25:25.8453604+05:30`. It is an unsigned local report, not a chain-of-custody record. |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | SHA-256 `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8`; 2,284,681 bytes; 41,434 rows. It differs from both hashes above and is not authorized for recovery. |

The current primary, historical-hash candidate, and pre-backfill backup all have the same Parquet columns: `timestamp` (UTC), `open`, `high`, `low`, `close`, `volume`, and `available_time`. The historical-hash candidate and current primary share **42,177 timestamps with zero value mismatches across their shared columns**; the candidate has no rows absent from the current file, while the current file has 56 additional timestamps. This establishes content similarity only, not exchange/API provenance, authorization, or correctness of the added rows.

Git reports no tracked history for either primary parquet path; `data/raw/` is ignored. The old hash is present in both the audit JSON and the byte-identical `ohlcv_backfilled.parquet`. These are local artifacts, not independent authoritative records. No recovery source or cause is established. The different-hash pre-backfill backup was not used.

The fresh source-level investigation continues to identify possible writers documented in the V32.51 report. This pass observed no matching prospective/shadow/ingestion/backfill worker process. Ports **8096** and **8102** were closed. The pre-existing Chrome debugging listener remained on **9222** (PID 23872); it was not used or stopped. No API or browser session was started.

## Protected-file integrity

The five protected paths had identical start/end hash, size, and last-write metadata during preflight:

| Protected path | SHA-256 | Size |
|---|---|---:|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | 3,385 |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | 12,744 |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | 2,329,745 |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | 2,284,681 |

Hash verification records byte-content integrity and last-write metadata. Read-only inspection may advance NTFS last-access metadata; that is distinct from content or last-write changes.

## Isolated QA harness

Added [v32_52_isolated_runner.py](../../../../scripts/qa/v32_52_isolated_runner.py). Its contract:

- Copies the current repository into a unique `%TEMP%` sandbox, preserving the current source/test snapshot while excluding Git/virtual environments, symlinks, environment files, and the root `scratch` directory.
- Excludes `scratch` because two existing ad hoc scripts contain absolute workspace paths and can write to source files. A scan found no references to those scripts in code, tests, or configuration. The scripts themselves were left untouched.
- Runs Python tests from the disposable copy, with sandbox-first imports, bytecode writes disabled, isolated temporary and SQLite paths, and no inherited application credentials or database URLs.
- Installs a Python `sitecustomize` guard for the five canonical protected files. It blocks tested Python file-write, delete, rename/replace, copy/move, hard-link, and metadata mutation paths. It allows only the active Python interpreter as a child process and restricts Python socket activity to loopback; test groups are serial and xdist flags are rejected.
- Records source hashes before and after each pytest invocation and fails without attempting recovery if they differ.

Validation executed:

1. In-memory Python syntax compilation of the runner — **PASS**.
2. `v32_52_isolated_runner.py --self-test` — **PASS**. Disposable sentinels verified blocked writes and replacements; DNS/external connection and non-Python process attempts were blocked; a child using the active Python interpreter was allowed.
3. `v32_52_isolated_runner.py --prepare-only` — **PASS**. The preflight scanned for absolute source-root references, prepared the disposable copy, and verified all five source-file hashes, sizes, and mtimes unchanged. It explicitly recorded `tests_executed: false`.

The machine-readable result is in [manifest.json](./manifest.json); the exact guard used for the preflight is [sitecustomize.py](./guard/sitecustomize.py). The prepared copy is at the temporary path recorded in that manifest. **No pytest command was executed.**

### Isolation limitations

This is a repository-copy and Python-level guard, not a kernel sandbox. Native extensions are not intercepted by `sitecustomize`; before a broader run, the selected tests still require review for native writers, hard-coded paths, and child-process behavior. Hash checks detect changes but never restore files. The copied market data is disposable input, not a newly verified or authoritative source. Do not treat this preflight as satisfying the release integrity gate.

## Unresolved gates and decision

- **Integrity/root cause:** unresolved; the historical-hash file is a local candidate, not an authorized recovery decision.
- **51 reported failures:** not rerun or reconciled.
- **Feature/API/browser QA:** not run.
- **Performance samples:** not run.
- **Dead-file cleanup:** not started; no files deleted.
- **Release verdict:** **FAIL**.
- **Research experiment:** `INCONCLUSIVE`.
- **Prospective evidence:** last recorded state remains stale/unverified `COLLECTING`; no fresh evidence claimed.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.

Software QA does not validate a profitable trading edge.
