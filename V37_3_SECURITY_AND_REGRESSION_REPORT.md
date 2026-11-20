# V37.3 Security and Regression Report

**Workstream:** 5 — user positions and manual journal ownership
**Date:** 2026-11-04
**Branch / starting revision:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`

## Result

The position and manual-journal routes now derive record ownership from a trusted authenticated ASGI principal, filter list/status responses to that owner, reject conflicting owner query/body values, and hide another owner's records with `404` before details or mutations. Client-supplied owner IDs are never used as the stored owner. Risk/journal status responses explicitly retain `ANALYSIS_ONLY`; offline research posture and disabled execution remain unchanged.

The current application has role-based API-key authentication but no configured per-person principal provider or authentication middleware. A role is not a user identity, so requests with a valid `USER`-or-higher API key but no trusted ASGI principal fail closed with `503`; unauthenticated/public requests fail closed with `401`. No identity mapping or replacement auth system was invented. This means the owner-scoped APIs remain unavailable in this deployment until a trusted principal provider is configured.

Manual forecast snapshots are sanitized before persistence: invalid or unavailable probability pairs are nulled and labeled unavailable; a regime is retained only when exposed by the live inference engine, otherwise it is `UNKNOWN`. The immutable digest is recomputed after sanitation. The performance-evaluation endpoint remains present but returns `503`: the current evaluator aggregates all owners and has no owner filter, so exposing its results would cross ownership boundaries.

## Exact changes

- `api/routes_user_positions.py`: applies principal ownership to status/list/history/detail/open/partial-exit/close; rejects conflicting legacy owner values; returns `404` for missing or non-owned records; retains `ANALYSIS_ONLY` and existing non-execution posture.
- `api/routes_manual_journal.py`: applies principal ownership to status/list/enter/detail/exit/adjust; sanitizes forecast probabilities/regimes and reseals the snapshot; keeps the evaluation endpoint but fails closed until an owner-scoped evaluator exists.
- `api/security_auth.py`: adds `get_current_principal_id`, which requires the existing USER-or-higher role and a trusted authenticated ASGI `scope["user"]` identity; it does not derive identity from client-controlled fields.
- `tests/test_security_auth.py`: covers absent role, missing identity provider, and trusted principal identity.
- `tests/test_v32_42_user_position_tracker_and_risk_copilot.py` and `tests/test_v32_42_manual_trade_journal_and_eval.py`: isolate API storage and inject a test principal for route lifecycle tests; update evaluation expectation to the owner-scope fail-closed response.
- `tests/test_v37_2_backend_contracts.py`: supplies the synthetic owner required by the existing no-fabricated-risk-context regression.
- `tests/test_v37_3_user_data_ownership.py`: adds regressions for missing identity, cross-owner reads/mutations, spoofed owner IDs, and invalid probability/regime sanitation.
- `V37_3_SECURITY_AND_REGRESSION_REPORT.md`: records blockers, test evidence, cleanup, and governed decisions.

## Regression evidence

- Commands were run from the disposable `.qa_v37_3` copy with its temp paths redirected inside that copy:
  - Focused API/auth: `pytest tests\test_security_auth.py tests\test_v37_3_user_data_ownership.py tests\test_v37_2_backend_contracts.py tests\test_v32_42_user_position_tracker_and_risk_copilot.py tests\test_v32_42_manual_trade_journal_and_eval.py -q --tb=short`.
  - Focused principal/ownership: `pytest tests\test_security_auth.py tests\test_v37_3_user_data_ownership.py -q --tb=short`.
  - Resolver: `pytest tests\test_entry_contracts_and_resolver.py tests\test_live_block_resolver.py tests\test_post_repair_outcome_resolver.py -q --tb=short`.
  - Broader security/resolver attempt: those three resolver files plus `tests\test_security_auth.py tests\test_security_regressions.py tests\test_authorization_consistency.py tests\test_agent_a_security_regression.py`, with `-q --tb=short`.
  - First full safe attempt: `pytest -q --tb=short` (repository default excludes `network`-marked tests).
  - Bounded follow-up attempt in a new disposable copy: `pytest -q --tb=short -m "not network" --ignore=tests/test_longitudinal_integrity.py --ignore=tests/test_longitudinal_monitor.py -p _qa_stop_on_collect_error`; this additionally excluded the two known protected-SQLite collection modules and used a QA-local hook to stop immediately on any collection error.
  - Frontend: `npm test`; `npm run check`.
- **Focused API/auth integration:** 40 passed, 1 warning. Included the V37.2 BTCUSDT rejection-before-market-access regression, no-injected-position-probability/regime regression, owner isolation, spoofed owner rejection, route lifecycle checks, and forecast-snapshot sanitation.
- **Focused principal/ownership security:** 12 passed, 1 warning.
- **Manager-review follow-up:** `_capture_safe_forecast_snapshot` now logs only the exception type at warning level on capture failure; added a regression confirming explicit unavailable snapshot values and that exception details are not logged. Re-ran `.\.venv_win\Scripts\pytest.exe tests\test_security_auth.py tests\test_v37_3_user_data_ownership.py -q --tb=short` from the checkout: **13 passed, 1 warning**. The protected-file hash guard passed for 1,848 files with the same before/after manifest SHA-256. These tests use isolated temporary route storage; no `.qa_v37_3` copy was recreated.
- **Additional manager-review note:** inference-service import/regime getter exceptions now also emit warning-level logs containing only exception type; `UNKNOWN` remains unchanged. Extended the sanitation regression with a failing regime getter and assertions that exception details are not logged. Re-ran the same focused command: **13 passed, 1 warning**; protected-file hash guard remained unchanged.
- **Resolver suite:** 17 passed.
- **Frontend:** `npm test` passed all frontend assertions; `npm run check` passed.
- **Protected-file guard:** passed in the isolated QA copy for 1,848 protected files; before/after manifest SHA-256 was unchanged (`d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`).
- **Broader security/resolver attempt:** 35 passed, 5 failed, 15 errors, 1 warning. The failures/errors were in pre-existing lifespan-based security/authorization tests: test setup redirects the results directory but does not provide `repaired_scientific_contract_manifest.json`, so application lifespan startup fails before those assertions run. This did not affect the focused route/auth suites.
- **First full safe-suite attempt:** collection stopped with 2 errors, 1 network-marked test deselected, and no suite tests executed. `test_longitudinal_integrity.py` and `test_longitudinal_monitor.py` instantiate a SQLite store under the protected `results` directory during collection; the repository's `tests/conftest.py` correctly blocks that access with `PROTECTED_SQLITE_ACCESS_BLOCKED`.
- **Requested alternate full-safe attempt:** used a separate disposable `.qa_v37_3` copy, explicitly excluded `tests/test_longitudinal_integrity.py` and `tests/test_longitudinal_monitor.py`, and retained `-m "not network"`. No collection error blocked the run; pytest began executing tests. It was still running after 600 seconds and progress output had reached 48%, with failures/errors appearing. At the manager-requested hard stop it was terminated before pytest produced a final summary. Therefore exact pass/fail/error counts are unavailable for this interrupted run and are not inferred from progress characters. No further attempt was made.
- **Whitespace checks:** scoped tracked auth changes passed `git diff --check`; repository-wide `git diff --check` exited `2` on unrelated pre-existing dirty changes in `README.md`, `engine/price_forecast_engine.py`, and `research/reports/*`. Those files were not edited by this workstream.

The isolated pytest runs emitted the existing Pydantic class-config deprecation warning. The full collection also emitted an existing invalid-escape `SyntaxWarning`.

## Constraints and blockers

- Disposable QA copies `.qa_v37_3` created by this workstream (including the interrupted alternate run) were removed in full. No `.qa_v37_3` files or directories remain and no cleanup is outstanding; the interrupted pytest process was stopped. No pre-existing checkout data or ledgers were removed or rewritten.
- Existing authentication can establish role, but not stable user identity. Configure a trusted ASGI principal provider and bind it to existing credentials before enabling these routes.
- Owner-scoped manual performance evaluation requires a separately approved owner-filtered evaluator implementation; no research/data contract was changed here.
- No live market-data access, trading execution, research evaluation, or prospective-evidence mutation was performed.

## Governed decisions

1. **Research experiment:** `INCONCLUSIVE` — this workstream is an API security correction, not a model experiment.
2. **Prospective evidence:** `NOT_STARTED`.
3. **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
4. **Live trading:** `DISABLED`.
