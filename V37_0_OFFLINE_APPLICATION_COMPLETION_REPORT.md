# BTCognitive V37.0 — Offline Application Completion Report

**Assessment date:** 2026-11-04  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD:** `25d483f4c3646661b57311de9d0b53d2be881adb`

## 1. Manager decision

**Application:** `APPLICATION_PARTIALLY_FUNCTIONAL`  
**Research validation:** `RESEARCH_VALIDATION_BLOCKED`

This workstream made the existing 15-minute candle endpoint fail closed when external access is disabled and added deterministic regression coverage. Resolver changes were not authorized because the frozen contracts leave several execution semantics ambiguous. Existing frontend work was already present in the starting worktree; this milestone did not independently verify a full application startup or browser workflow. Therefore, the focused passing tests do not establish end-to-end application completion.

The unresolved provenance and custody issues continue to block historical outcome validation and performance claims. They do not block isolated engineering or synthetic tests.

## 2. Pre-flight and preservation

- Captured `git status --short --untracked-files=all`, tracked and cached diffs, branch, and HEAD before implementation.
- The initial status snapshot contained 1,712 entries. Existing user modifications and untracked files were preserved.
- The initial protected-asset inventory comprised 213 files (837,776,010 bytes), including local raw data, model files, relevant research contracts/manifests, experiment results, databases, and the prospective ledger. SHA-256 digests were recorded outside the repository.
- The current market-memory database and prospective ledger were already modified before this work. Neither was opened for analysis or changed.
- No branch changes, staging, commits, pushes, resets, cleanup, restores, stashes, merges, or rebases occurred.

## 3. Work completed by specialist

| Workstream | Result |
|---|---|
| Contract and resolver specialist | Read-only matrix completed. No files changed. Ambiguous contract items were returned to the manager rather than guessed. |
| Resolver engineer | Reviewed current call paths and existing diffs. No resolver edits or tests; no behavior change was authorized. |
| API/UI engineer | Updated `api/routes_market.py`: `get_candles` now returns explicit `DATA_UNAVAILABLE`/`UNAVAILABLE` in offline mode instead of invoking the Coinbase adapter. The docstring distinguishes 15-minute adapter access from the 1-hour feature-cache path. |
| Manager integration | Updated the existing local-source allowlist in `web/app.js` / `useCoinbaseFeed` to accept `LOCAL_HISTORICAL_CACHE`, the source returned by the active offline `/api/market/candles` route. Without this, the UI rejected a valid historical cache response. Non-`FRESH` data continues to be rendered as stale, not current. |
| QA engineer | Added `tests/test_workstream4_qa_contracts.py` with deterministic checks for resolver failure/finite outputs, unavailable market inputs, disabled execution, frontend stale/unavailable/malformed states, and active/legacy offline candle paths without provider calls. |
| Data-integrity specialist | Read-only findings: the 1-minute dataset remains unverified, its current snapshot is historical/stale, and existing holdout custody and claims remain unresolved. No files changed. |

### Files changed in this milestone

- `api/routes_market.py`
- `web/app.js` (one surgical integration change in a file already modified at pre-flight)
- `tests/test_workstream4_qa_contracts.py`
- `V37_0_OFFLINE_APPLICATION_COMPLETION_REPORT.md` (this report)

No frozen contract, manifest, dataset, model, research ledger, prospective ledger, or database was changed.

## 4. Existing architecture reused

The change uses the existing `api.routes_market.get_candles` route, `engine.data_mode.is_external_network_permitted`, the existing Coinbase 15-minute adapter, and the existing `feature_cache` for 1-hour candles. The active UI path uses `api.market_monitor_routes.market_candles`, which can serve a local historical cache or an explicit unavailable response in offline mode. The UI source allowlist now accepts that route's `LOCAL_HISTORICAL_CACHE` label. No provider, parallel market-data stack, model, strategy, or outcome pipeline was added.

In offline mode, the 15-minute endpoint returns a structured unavailable response with an empty candle list, null source/as-of values, and an explanation. The provider call is verified not to occur by a synthetic route test. Other market inputs are not fabricated by the failure-response test.

The frontend change only reconciles the accepted local-source label; it does not add a market source or present historical candles as current. Synthetic tests exercise the active API route, the no-provider behavior, and the forecast-state helper for fresh, stale, unavailable, and malformed payloads. This is not a browser-level end-to-end verification.

## 5. Frozen contract conformance and resolver decision

| Requirement | Evidence/status | Decision |
|---|---|---|
| Decision timestamp, point-in-time cutoff, and next-minute fill | The frozen execution contract specifies close-of-decision-bar triggering, `fill_timestamp = decision_timestamp + 60 seconds`, and next-1-minute-open price. The interval-open/interval-close interpretation leaves a material time/price alignment question. | No alignment code change until the timestamp and bar semantics are reconciled. |
| 2% entry-gap cancellation | The contract provides `max_allowed_entry_gap_pct = 2.0` and cancellation on exceedance but does not define the reference price, signed/directional calculation, measurement time, equality behavior, or precedence against actual-open fill. | `OWNER_DECISION_REQUIRED`. |
| Long/short barrier geometry and same-candle collision | The outcome contract specifies conservative stop-first handling for unresolved dual touches and requires collision metadata/sensitivity analysis. Existing research and engine resolvers implement side-specific barriers and conservative collision behavior; focused synthetic tests passed. | No change justified by this audit. |
| Opening gaps through exit barriers | Current implementations use opening prices in gap cases, but the frozen contract does not settle opening-gap precedence when the same candle also touches the opposite barrier. | `OWNER_DECISION_REQUIRED`; do not invent favorable or adverse ordering. |
| Holding horizon and incomplete path | Frozen horizons and timeout accounting are defined, but treatment of short/incomplete paths and whether the horizon counts elapsed minutes or observed bars is not fully settled. | `OWNER_DECISION_REQUIRED`; existing implementation not declared conformant for these cases. |
| Costs | Frozen scenarios specify fees, entry/exit slippage, half-spread, and total round-trip costs. The current research builder embeds entry slippage in price while also applying aggregate costs; spread allocation is not fully specified. | `OWNER_DECISION_REQUIRED`; do not remove legitimate entry/exit costs or change accounting speculatively. |
| A1 sweep/reclaim | Detector configuration includes a two-bar reclaim window; implementation evidence indicates same-bar reclaim behavior. Delayed-reclaim state/reference and boundary rules are not fully frozen. | `OWNER_DECISION_REQUIRED`; no detector change authorized. |

The research and engine resolver paths are distinct and were not treated as interchangeable. The unverified 1-minute CSV was not used as test ground truth. Tests in this milestone use synthetic fixtures only.

## 6. Data provenance, freshness, and research evidence

- **1-minute CSV:** `UNVERIFIED` for source authenticity and timestamp semantics. A matching local digest establishes file integrity against the recorded manifest, not the original provider, instrument, or bar-time meaning.
- **Snapshot freshness:** the recorded 1-minute snapshot ends at `2026-10-07T03:11:00Z`, so it is historical as of this assessment date, not a current market snapshot.
- **Holdout custody:** `UNVERIFIABLE`; no independent access-control/access-log evidence was established.
- **Historical claims:** prior count and performance discrepancies remain unreconciled by stable cohort/trade identifiers and counting rules. No result was recalculated or promoted.
- **Feature status:** implementation, execution, data availability, and validation are separate states. This milestone verifies selected unavailable/stale UI states and a fail-closed endpoint; it does not establish that all analytical features executed or that any feature is predictively valid.
- **Research outcome:** no historical replay, training, tuning, calibration, model promotion, or performance claim was made.

## 7. API, UI, and regression verification

| Command | Result |
|---|---|
| `.venv_win\Scripts\pytest tests\test_workstream4_qa_contracts.py -q` | **13 passed** on the final run. Includes synthetic active and legacy offline 15-minute candle paths without provider calls, unavailable-input response shape, disabled execution flags, resolver finite/fail-closed behavior, frontend source compatibility, and forecast status parsing. |
| `.venv_win\Scripts\pytest tests\test_entry_contracts_and_resolver.py tests\entry_tp_sl\test_triple_barrier.py tests\entry_tp_sl\test_intrabar_ambiguity.py tests\entry_tp_sl\test_timeout_accounting.py tests\entry_tp_sl\test_cost_accounting.py -q` | **22 passed.** Focused resolver/accounting regressions using the existing tests. |
| `node tests_frontend.js` | **Passed.** Documented frontend verification script completed its formatter, request/cache, polling-budget, API/WebSocket resolution, navigation, and feature-marker checks. |
| `npm run check` | **Passed.** JavaScript syntax checks completed for the configured frontend files. |
| `git diff --check -- api/routes_market.py` | **Passed** after the final docstring clarification. |

The pytest invocations reported the repository's `PROTECTED_FILE_HASH_GUARD` passing across 1,848 protected files with identical before/after manifest digests. The resolver/accounting suite ran before the final frontend source-label change; no resolver implementation changed during this milestone. The first run of the expanded QA file exposed a test-fixture error (the test patched a locally imported function on the wrong module); the fixture was corrected and the final run passed all 13 tests.

The full test suite, baseline suite before implementation, application server startup, and browser-based end-to-end workflow were not run. Given the large pre-existing modified worktree and tests that cover persistent research state, broad execution was not established as safe for this milestone. No test result is inferred from discovery or documentation.

## 8. Integrity and operating safeguards

Final `git status --short --untracked-files=all` contained 1,715 entries: exactly three new status entries relative to the 1,712-entry baseline (`api/routes_market.py`, `tests/test_workstream4_qa_contracts.py`, and this report), with no initial entries removed and no other additions. `web/app.js` was already modified at pre-flight and remains within that existing status entry; the source-allowlist edit was integrated without removing its prior changes. All 213 protected-asset hashes matched their pre-flight SHA-256 values. `git diff --check -- api/routes_market.py web/app.js` passed. Branch and HEAD remained unchanged at the values listed above.

Throughout this milestone:

- `ANALYSIS_ONLY` and `OFFLINE_RESEARCH_ONLY` were preserved.
- Live trading, broker integration, and order placement remained disabled.
- C2/conformal claims, model/strategy promotion, and use of holdout observations were not enabled.
- No external data provider, network acquisition, or live market fetch was used.

## 9. Remaining blockers and next milestone

1. **Owner contract decisions:** resolve the entry time versus bar timestamp convention; entry-gap reference/direction/boundary/precedence; opening-gap versus dual-touch ordering; incomplete-horizon behavior; cost component treatment and spread allocation; and A1 delayed-reclaim semantics.
2. **Resolver conformance:** after those decisions are frozen, implement only the specified behavior and add boundary-focused synthetic tests. Keep unresolved cases fail-closed without mislabeling them as contract-conformant.
3. **Application acceptance:** run a safe offline API lifespan and browser/integration workflow against controlled fixtures; verify source, timeframe, as-of, stale/unverified, unavailable, and validation states end-to-end.
4. **Separate research gate:** establish authoritative provenance or use a clearly documented replacement dataset with explicit timestamp semantics; independently resolve holdout custody before making any confirmatory historical claims.

### Release states

- **Application:** `APPLICATION_PARTIALLY_FUNCTIONAL`
- **Research validation:** `RESEARCH_VALIDATION_BLOCKED`
- **Prospective evidence:** `NOT_ESTABLISHED`
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`
- **Live trading:** `DISABLED`
