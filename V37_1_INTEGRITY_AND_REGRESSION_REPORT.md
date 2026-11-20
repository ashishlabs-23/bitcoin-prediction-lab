# BTCognitive V37.1 — Integrity and Regression Report

**Assessment date:** 2026-11-04  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD:** `25d483f4c3646661b57311de9d0b53d2be881adb`

## 1. Scope and preservation

This report records an integrity comparison against `C:\Users\Ashish\AppData\Local\Temp\v37_0_audit` and focused regression testing. No product source, tests, contracts, datasets, or prior reports were edited by this V37.1 task. The only created file is this report. No network access, model selection, training, or holdout-observation analysis was performed.

No staging, commit, reset, cleanup, restore, stash, branch change, or other destructive Git operation was performed. Existing worktree modifications were preserved.

## 2. Baseline comparison

The V37.0 snapshot contains `initial_git_status.txt` (1,712 entries), `initial_worktree.diff` (115 tracked-file patch sections), `initial_index.diff` (0 bytes), and `initial_protected_assets.tsv` (213 assets).

Before creating this report, the worktree had 1,715 status entries: all 1,712 baseline entries remained, with no baseline entries removed, plus exactly these three V37.0 additions/changes:

- `api/routes_market.py` — modified.
- `tests/test_workstream4_qa_contracts.py` — untracked.
- `V37_0_OFFLINE_APPLICATION_COMPLETION_REPORT.md` — untracked.

The current index was empty, matching the empty baseline index diff. Branch and HEAD remained unchanged from the baseline values above.

Comparing tracked added/deleted patch content across all files found post-baseline tracked changes in only two files:

- **`api/routes_market.py`:** 17 added and 3 removed lines. The diff adds the external-network permission check and a structured `DATA_UNAVAILABLE`/`UNAVAILABLE` response for disabled external access on the 15-minute candle path; it updates the endpoint documentation. This matches the V37.0 report's description of an offline fail-closed change.
- **`web/app.js`:** exactly one post-baseline hunk, at approximately line 1212. The source allowlist adds `LOCAL_HISTORICAL_CACHE`; the previous allowlist line is replaced. No other `web/app.js` content differs from the saved initial worktree.

The V37.0 test file and report are new untracked files relative to the snapshot. No other tracked-file patch content changed after the snapshot.

## 3. Protected-asset integrity

All **213/213** paths in `initial_protected_assets.tsv` matched both recorded byte lengths and SHA-256 hashes before and after the regression run; there were **0 missing or mismatched assets**. The pytest `PROTECTED_FILE_HASH_GUARD` also passed across 1,848 protected files with identical before/after manifest digest `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`.

No test changed protected state according to either check. Hash verification was integrity-only; protected holdout observations were not inspected or used for model selection.

## 4. Regression verification

Focused command:

```text
.\.venv_win\Scripts\pytest.exe tests\test_workstream4_qa_contracts.py tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py tests\entry_tp_sl -q
```

Result: **118 passed**, **0 failed**, **0 skipped** in 7.41 seconds. No warning summary was reported.

Discovery-only command:

```text
.\.venv_win\Scripts\pytest.exe --collect-only -q tests\test_workstream4_qa_contracts.py tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py tests\entry_tp_sl
```

Result: **118 tests collected**. Thus all collected tests in this focused invocation executed and passed; the collection count is not a separate test pass claim.

The V37.0 report also records its own earlier runs (13 QA tests and 22 entry/accounting tests passed), plus successful `node tests_frontend.js`, `npm run check`, and a scoped `git diff --check`. Those are historical V37.0 results, not newly executed here. The current focused pytest invocation reran the QA and entry/resolver coverage and additionally included the existing live/post-repair resolver tests and all `tests\entry_tp_sl` tests. The Node/npm commands were not rerun.

The full suite was **not run**. The baseline already contained 1,712 dirty status entries (1,715 immediately before this report), and this repository's broad suite includes tests touching persistent research state. A full run was not established as safe in this heavily modified worktree; avoiding potential state changes took precedence over broader coverage.

## 5. Post-test status and V37.0 report review

After testing and before this report was created, the status remained at 1,715 entries with only the three V37.0 status deltas listed above. There were no test-induced status changes. The 213 protected-asset hashes were rechecked after testing and still matched.

At the integrity agent's final status check, there were 1,717 entries: all 1,712 baseline entries remained, with five current-only entries:

- `api/routes_market.py`
- `V37_0_OFFLINE_APPLICATION_COMPLETION_REPORT.md`
- `tests/test_workstream4_qa_contracts.py`
- `V37_1_INTEGRITY_AND_REGRESSION_REPORT.md` (this report)
- `V37_1_CONTRACT_OWNER_DECISIONS.md` (additional untracked file, not created or modified by this task)

The additional `V37_1_CONTRACT_OWNER_DECISIONS.md` was absent from the immediately preceding post-test status check. Its origin cannot be attributed from this comparison; it was left untouched. No baseline status entries were removed. The runtime report was created after that check; the manager's later final status check found **1,718 entries**, with all 1,712 baseline entries retained and exactly six current-only entries: the five above plus `V37_1_APPLICATION_RUNTIME_REPORT.md`. The runtime agent subsequently added `V37_1_APPLICATION_RUNTIME_ADDENDUM_20261104.md`; the manager's final closeout check therefore found **1,719 entries**, with all 1,712 baseline entries retained and exactly seven current-only entries: the prior six plus the addendum. No baseline entries were removed and no other worktree items changed.

The V37.0 report's key integrity assertions are consistent with this comparison: it describes the same three additions relative to its 1,712-entry baseline, one surgical `web/app.js` source-label change, 213 matching protected assets, and no resolver modification. Its distinctions between fail-closed engineering tests and unresolved provenance/contract/research validation are retained here. The application's end-to-end startup/browser behavior and historical predictive performance are not established by this regression run.

## 6. Governed decisions

- **Research experiment:** `INCONCLUSIVE` — this was an integrity/regression task, not a research experiment.
- **Prospective evidence:** `NOT_STARTED` — no prospective observations were collected or evaluated.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.
