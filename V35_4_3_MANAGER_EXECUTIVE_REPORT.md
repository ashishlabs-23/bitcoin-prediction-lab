# BTCognitive V35.4.3 Manager Executive Report

## Executive decision

**Decision: BLOCKED.** Calibration quarantine and focused test-state isolation controls are partly verified. The milestone cannot be accepted because the complete offline analysis path was not exercised with the real engine and provenance-verified local BTCUSD data, and the final Python venue-provenance change did not receive a completed test run.

This decision does not mean protected data is corrupted. The current hashes of the prospective ledger, canonical market-memory database, raw OHLCV parquet, and listed frozen artifacts match the forward baseline capture. Their historical pre-remediation integrity remains `INTEGRITY_UNVERIFIABLE`.

## Repository state

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- No branch switch, commit, push, reset, stash, clean, restore, or destructive operation was performed.
- Final status counts and relevant paths were captured after all five V35.4.3 reports were added; see the status section below.
- No paid service, cloud/company infrastructure, external provider request, or subscription was used or introduced; the proposed controls are local and free-tier compatible.

## What changed for V35.4.3

The V35.4.3 working changes in this task include:

- `web/app.js`: suppresses current C2 path probability, N_eff, CI, directional-confidence and calibration displays; removes fabricated missing-provenance and historical expectancy fallbacks; makes missing path sample counts null/unavailable.
- `api/routes_prediction.py`: missing market-regime venue provenance now maps to `UNAVAILABLE`, not an implied Coinbase source; accuracy and calibration responses retain null/unavailable metrics.
- `api/routes_terminal.py`: unmeasured health and coverage values remain unavailable.
- `tests/conftest.py`: process-level test database redirection, protected-path write guard, non-loopback socket guard, and whole-inventory hash check.
- `tests/test_database_isolation.py`: verifies disposable operational database paths and blocked canonical access.
- `tests/test_v35_4_1_analysis_integrity.py`: offline route-contract, snapshot, failure and unavailable-calibration checks.
- `tests/test_fail_closed_data_contracts.py`: adds a regression test for missing venue provenance; the latest added test was not completed.
- `tests_frontend.js`: assertions for unavailable calibration/provenance and suppression of stale C2 path values.

Do not attribute other pre-existing dirty-tree entries to V35.4.3 without a trustworthy change baseline.

## Evidence summary

- Focused Python run before the last venue-provenance edit: 29 passed, 0 failed, 1 warning; 696.51 seconds. Test guard passed for 1,848 protected files with equal before/after manifest hashes.
- Frontend contract script: all 15 named sections passed; the script does not report an assertion count.
- JavaScript syntax check: passed.
- A later Python revalidation run was stopped after 1,342 seconds without a pytest summary. It is not a pass and contributes no test count.
- The API contract test used a mocked analysis function and generated deterministic test candles. It proves snapshot handoff and serialization, not real-engine analysis or market-data accuracy.
- Full browser integration and full repository tests: not run.

The focused commands and exact evidence are detailed in `V35_4_3_TEST_ISOLATION_REPORT.md`. Current integrity hashes and limitations are in `V35_4_3_FORWARD_INTEGRITY_BASELINE.md`.

## Protected data and model status

- Prospective forecast ledger: current SHA-256 is recorded in the forward baseline; historical integrity `INTEGRITY_UNVERIFIABLE`.
- Canonical market-memory database: current SHA-256 is recorded; no WAL or SHM sidecar was present at the forward capture; historical integrity `INTEGRITY_UNVERIFIABLE`.
- Raw OHLCV and listed frozen manifests/artifacts: current hashes match the forward baseline capture.
- `standard_har_v1.joblib`: absent. `STANDARD_HAR_ACCURACY = NOT_ESTABLISHED`.
- No protected data, ledger, model artifact, manifest, historical result, or statistical gate was intentionally changed.

## Governance decisions

1. Research experiment: `INCONCLUSIVE` for this milestone; no forecast performance experiment was run.
2. Prospective evidence: `COLLECTING` only if already authorized under the frozen protocol; this task did not start or alter collection.
3. Model authorization: `OFFLINE_RESEARCH_ONLY`.
4. Live trading: `DISABLED`.
5. Application posture: `ANALYSIS_ONLY`.
6. C2: `DISABLED`.

## Remaining blockers and next action

The decisive blocker is absence of a completed no-network API integration using a provenance-verified local BTCUSD snapshot and the real analysis engine. The existing deterministic fixture is test-only and synthetic; it is not market evidence. The latest missing-venue API fallback also lacks a completed Python regression run.

**Next action:** Run one controlled, no-network integration against a provenance-verified local BTCUSD hourly snapshot through `/api/tournament/analyse` and the real analysis engine, with the established disposable database and protected-file hash guards enabled; require explicit historical/stale labeling and unavailable calibration outputs.

## Final Git status

Captured after all five V35.4.3 reports were present:

```text
Branch: milestone/v35.3-critical-remediation
HEAD: 25d483f4c3646661b57311de9d0b53d2be881adb
git status --porcelain=v1 entries: 444
Tracked modified / unstaged: 115
Untracked: 329
Staged: 0
Deleted: 0
Renamed: 0
```

V35.4.3-related status entries:

```text
 M api/routes_prediction.py
 M api/routes_terminal.py
 M tests/conftest.py
 M tests/test_database_isolation.py
 M tests/test_fail_closed_data_contracts.py
 M tests_frontend.js
 M web/app.js
?? V35_4_3_ACCEPTANCE_MATRIX.md
?? V35_4_3_CALIBRATION_QUARANTINE_REPORT.md
?? V35_4_3_FORWARD_INTEGRITY_BASELINE.md
?? V35_4_3_MANAGER_EXECUTIVE_REPORT.md
?? V35_4_3_TEST_ISOLATION_REPORT.md
?? tests/test_v35_4_1_analysis_integrity.py
```

The other 431 entries are not attributed to this remediation; their contents were preserved. The working tree remains heavily modified and untracked. No existing dirty-tree state was discarded.
