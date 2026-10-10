# GitHub Push Checkpoint

**Status:** `PUSH_VERIFIED`

## Repository and branch

- Repository: `ashishlabs-23/bitcoin-prediction-lab`
- Feature branch: `fix/safe-research-terminal`
- Initial safe-localhost commit: `cd7742fb758f720519d339402294309a1050d6dc`
- Pull request: https://github.com/ashishlabs-23/bitcoin-prediction-lab/pull/1
- The remote branch was verified with `git ls-remote` to point to the initial commit SHA above before this checkpoint was added.

## Files included in the initial push

- `api/local_safe_server.py`
- `api/routes_arena.py`
- `api/routes_market.py`
- `api/routes_notifications.py`
- `api/routes_prediction.py`
- `engine/inference_service.py`
- `research/entry_tp_sl/INDEPENDENT_REPAIR_REPORT.md`
- `research/entry_tp_sl/LOCALHOST_VERIFICATION_REPORT.md`
- `research/entry_tp_sl/run_authorization.json`
- `tests/test_frontend_contracts.py`
- `tests/test_local_safe_server.py`
- `tests/test_shared_prediction_endpoint_guards.py`
- `web/app.js`

## Pre-push checks

- Python interpreter: `.venv_win\Scripts\python.exe` — Python 3.13.14.
- `python -m pip check`: passed, exit code 0.
- Focused + Entry/TP/SL regression command:
  `.\.venv_win\Scripts\python.exe -m pytest -q --timeout=30 tests\test_local_safe_server.py tests\test_shared_prediction_endpoint_guards.py tests\test_frontend_contracts.py tests\entry_tp_sl`
- Result: **134 passed, 0 failed, 0 skipped**, exit code 0.
- `git diff --cached --check`: passed, exit code 0.
- Browser and local API integration were verified as recorded in `LOCALHOST_VERIFICATION_REPORT.md`.

## Protected files and scope

Frozen contracts, the trial ledger, raw datasets, credentials, virtual environments, model artifacts, and unrelated research implementation changes were excluded from the initial commit. The research authorization file was included with its existing blocked state (`authorized: false`, `BLOCKED_AUDIT_FAILURE`). No model fitting, experiment, holdout read, or trial event write was performed.

Other pre-existing uncommitted work remains in the local working tree and was not included in the initial push.

## Unresolved issues

- The contract manifest's raw SHA-256 differs from its embedded and registered SHA-256. This is documented as `PROVENANCE_FAILURE`; the manifest was not changed.
- The GitHub push and PR creation were confirmed. The pull request is awaiting review and merge.
