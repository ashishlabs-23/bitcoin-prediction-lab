# BTCognitive V32.49 Scenario QA and UI Report

**Assessment date:** 26 October 2026  
**Release verdict:** `PARTIAL_PASS_BLOCKED`  
**Evidence scope:** local regression tests and an isolated browser run against the normal `api.server:app`. The earlier V32.48 completion report was treated as supplied evidence, not as a fresh reproduction.

## Executive decision

The integrated Analyse flow was verified on the normal application route with a Coinbase BTC-USD 1-hour chart payload. A single analysis request returned HTTP 200, analyzed the 349 submitted closed candles, skipped the tournament because no candidates were eligible, returned `NO_SMART_ENTRY`, and created zero attempts. The visible Terminal showed the no-qualifying-setup outcome, five strategy rejections, and a skipped tournament stage. Entering a simulated attempt was correctly not available in this run.

The final V32.43–V32.49 regression command passed **116 tests**. Frontend syntax, frontend tests, and Python compilation passed. These are software-regression results; they do not establish a trading edge.

The full scenario matrix is **40 PASS, 0 FAIL, 11 BLOCKED, 15 NOT_RUN**. Several high-impact branches remain unverified, especially candidate selection against verified tournament arms, price-deviation invalidation at entry, active monitoring in the browser, API failure/retry behavior, and manual accessibility checks. Accordingly, this is **not a release sign-off** under the user's criterion that no critical scenario remain blocked or unrun.

## Governed decisions

| Decision | Result |
|---|---|
| Research experiment | `INCONCLUSIVE` |
| Prospective evidence | `NOT_STARTED` — zero confirmatory blocks collected |
| Model authorization | `OFFLINE_RESEARCH_ONLY` for Smart Entry/tournament research |
| Live trading | `DISABLED` |
| Validated trading edge | `NO_GO_NO_VALIDATED_EDGE` retained |

The production volatility-only service reported its separate authorization in `/health`; that does not authorize Smart Entry, directional recommendations, orders, or live trading.

## Baseline, scope, and evidence provenance

- Repository: `C:\Projects\BTCognitive\BTCognitive`; branch `main`; baseline commit `25d483f4c3646661b57311de9d0b53d2be881adb`.
- The worktree was already extensively dirty, with modified and untracked files. Those changes were preserved; nothing was staged, committed, reset, reverted, or stashed.
- The five protected files were SHA-256 hashed before testing and again after testing. All hashes matched; see [the JSON summary](./v32_49_scenario_qa_summary.json).
- V32.48's `engine/v32_48_test_backend_server.py` is a custom test backend using injected/synthetic fixtures. It is not evidence that the normal application's API routing stack or a deployed environment was tested. The reported V32.48 browser/test results were not independently re-executed as V32.48 evidence here.
- The V32.49 browser run used `api.server:app` on isolated port `8096`, with a session-scoped temporary simulator ledger. It read the actual Coinbase REST chart feed. The temporary app process was stopped and port `8096` was confirmed closed. The normal application lifespan initialized its feature cache and background alert evaluator; no collector configuration was changed.
- Synthetic candles in unit tests are deterministic fixtures only. They are not represented as current BTCUSD conditions or empirical performance evidence.

## Normal application browser-to-API evidence

The captured request/response metadata is in [the network trace](./artifacts/browser_qa/v32_49/normal_app_analyse_network_trace.json).

| Check | Observed result |
|---|---|
| Normal app entry point | `api.server:app`; `/health` returned HTTP 200 |
| Request | One recorded `POST /api/tournament/analyse`, `auto_tournament: true`, BTC-USD, 1h, `COINBASE_EXCHANGE_REST` |
| Candle payload | 349 closed candles; first `2026-10-12T01:00:00.000Z`; last `2026-10-26T13:00:00.000Z` |
| Provenance | Canonical candle-array SHA-256 (API field `request_payload_sha256`) `3911dd589fbc72a8a364daf9218cf8082f8f2dabdd95bd5ed859bfafbe4fd64d`; analyzed-window and candle-watermark SHA-256 both `e6d2ce3eabd3af596d879a0de4c90ddc4af44ba5f753ec5b7d7318366d67df3d` |
| Decision | `NO_SMART_ENTRY`; actual result identified `TRENDING_BEARISH`, zero compatible candidates, five rejected strategies |
| Tournament | `NOT_RUN_NO_ELIGIBLE_CANDIDATES`; no candidate was forced |
| Side effects | `attempts_created: 0`; no simulated entry or monitor lifecycle began |
| Visible UI | `NO QUALIFYING SETUP`; progress stage says `Run tournament: Skipped (no eligible candidates)`; rejection detail is collapsed |

The chart's current/incomplete hourly bar was not in the submitted analysis window; the watermark ended at the latest closed bar. The API field named `request_payload_sha256` hashes the canonical candles array, not the full request envelope. The response reported the same analyzed-window hash as its candle watermark. The deterministic API test also captures the submitted candle DataFrame passed to the integrated analysis function and asserts exact equality with the request. An earlier independent JavaScript recomputation of the normalized window hash did not match because timestamp/numeric canonicalization differed; no independent hash match is claimed.

The actual-feed result is one retrospective runtime observation, **not** prospective evidence. It did not run tournament arms and cannot establish candidate superiority, backtest freshness, or profitability. A browser test that deliberately delayed the analysis route observed the disabled CTA and running progress state, but its response waiter expired at 60 seconds; that browser scenario is classified `BLOCKED`, not a pass. The ordinary normal-app analysis run above did complete successfully.

## Defects and fixes

| Finding | Evidence / reproduction | Change |
|---|---|---|
| Embedded tournament-arm figures could be presented as verified without a matching manifest | The available historical manifest did not match the current candidate/protocol. The old path could expose unverified metrics. | Tournament now abstains without verified cached evidence or complete fresh-arm inputs; it returns no fabricated arm metrics or winner. Existing 7/10 and 1.5x thresholds were not changed. |
| Abstention copy could say only that no shortlist was provided, hiding the strategy-screen result | Normal-app response and visible empty state initially returned the generic shortlist message despite five rejections. | The decision now reports the regime, rejection count, skipped tournament, and safe retry step. The outcome remains an abstention with zero attempt creation. |
| Tournament stepper could render `Complete` for a skipped tournament | Browser result showed a skipped evidence label but an incorrectly completed step. | Stepper state now reads integrated-analysis tournament provenance as well as separate tournament state and displays `Skipped (no eligible candidates)` or an evaluation-evidence block reason. |
| Changed UI code could be served under the old app-script cache key | `web/index.html` retained `/app.js?v=32.22.0`; browser reload continued to display old UI copy. | Bumped the app script cache key to `32.49.0`; the updated stepper and abstention copy were then observed in the browser. |
| Monitoring errors could be silently discarded, and repeated browser polling could overlap | The active monitor swallowed request errors and allowed multiple same-tab monitor requests to overlap. | Errors now appear as an alert while retaining the last successful monitor time; same-tab monitor requests are guarded against overlap. |
| Older/duplicate monitor forecasts had no durable ordering guard | An older forecast could be evaluated after a newer one. | The simulator stores timestamped forecast snapshots in its append-only ledger, ignores duplicate/older timestamps for update purposes, and replays the newest snapshot after restart. Direction-aware behavior and immutable TP/SL remain. |
| A stale price feed could be obscured by a simultaneously unavailable forecast | A regression fixture with stale price and absent forecast reported only forecast-unavailable. | Quality-state precedence now preserves the stale-price warning while stale/malformed forecast states remain separately covered. |
| Legacy regression fixtures stopped before the intended validation | New server-side provenance enforcement correctly returned 409 before older tests reached their invalid-price assertion; one tournament fixture lacked a shortlist/verdict; one quality expectation did not account for missing forecast data. | Updated those fixtures/expectations to exercise the intended branches. No qualification threshold was loosened. |

## Automated validation

| Command | Result |
|---|---|
| `.venv_win\Scripts\pytest.exe tests\test_v32_49_scenario_qa.py tests\test_v32_43_strategy_tournament_and_smart_entry.py tests\test_v32_44_smart_entry_independent_audit.py tests\test_v32_45_workflow_acceptance.py tests\test_v32_46_navigation_and_terminal_consolidation.py tests\test_v32_47_analyse_selection_and_anomaly_monitor.py tests\test_v32_48_integrated_analyse_and_tournament.py -q` | **116 passed** |
| `python -m py_compile engine\smart_entry_simulator.py engine\regime_strategy_tournament.py api\routes_tournament.py` | Passed |
| `node --check web\app.js` | Passed |
| `node tests_frontend.js` | Passed |
| Protected-file before/after SHA-256 comparison | All five unchanged |

The regression tests cover closed-candle warmup and freshness boundaries; malformed, duplicate, out-of-order, gapped, and impossible OHLCV; exact API candle forwarding and analysis request idempotency; cache/evaluation fail-closed behavior; long/short geometry; entry provenance and staleness; entry idempotency/concurrency/restart; direction-aware reversal; the inclusive 1.5x risk boundary; missing, malformed, duplicate, and out-of-order forecasts; monitor-state recovery; TP/SL and ambiguous dual-touch lifecycle; and partial exit followed by continued monitoring.

## Complete scenario status matrix

The machine-readable status for every scenario ID is in [the JSON summary](./v32_49_scenario_qa_summary.json). `BLOCKED` means a prerequisite or test-harness limitation prevented the required complete check; `NOT_RUN` means the scenario was not executed. The status is not inferred from code presence alone.

| Area | PASS | BLOCKED | NOT_RUN |
|---|---|---|---|
| Navigation, chart, and status | UI-01, UI-04 | UI-02, UI-03 | UI-05, UI-06, UI-07 |
| Analyse and candle integrity | ANA-01, ANA-04–ANA-11 | ANA-02 | ANA-03, ANA-12 |
| Candidate screening and tournament | STR-01–STR-04, STR-09, STR-10, STR-12 | STR-06–STR-08, STR-13 | STR-05, STR-11, STR-14, STR-15 |
| Entry and persistence | ENT-01–ENT-05, ENT-07, ENT-08, ENT-10 | ENT-06 | ENT-09 |
| AI monitoring and lifecycle | MON-01–MON-06, MON-08, MON-11–MON-14 | MON-09 | MON-07, MON-10 |
| UI content and recovery | UX-01–UX-03 | UX-05, UX-06 | UX-04, UX-07, UX-08 |

### Blocker details

- **ANA-02:** The intentionally delayed browser request exposed a disabled CTA and running status, but the harness did not obtain the response within 60 seconds. API idempotency is covered by tests; the rapid-repeat browser assertion did not complete.
- **STR-06/07/08/13:** No matching verified cache or complete fresh three-arm evidence was available. Candidate-1 winner, candidate-2 fallback winner, both-candidates-fail with actual arms, and cached-result reuse were therefore not observed. The correct current behavior is to abstain rather than manufacture evidence.
- **ENT-06:** The project does not define a material price-deviation threshold for invalidating an otherwise fresh proposal. This was not guessed.
- **UI-02/03 and MON-09:** Feed-disconnect and active-attempt reload/suspend scenarios require fault injection and a browser-visible active attempt. The live analysis correctly abstained, so none was created.
- **MON-07/10 and UX-04:** Monitor endpoint failures, repeated polling cycles, backend 5xx, and malformed API responses were not fully exercised end-to-end.
- **UX-05/06:** No active anomaly or verified cached/fresh tournament result was available to display in the normal-app browser session.
- **Accessibility:** Keyboard activation of the Analyse control was observed, but the full keyboard-only path, screen-reader announcements, contrast, focus visibility, and target-size manual checks were not performed. These are not marked passed based only on markup.

## Browser artifacts

The archived responsive screenshots are present and have non-zero file sizes:

- [Desktop 1280×800](./artifacts/browser_qa/v32_49/terminal_desktop_1280x800.png)
- [Tablet 768×1024](./artifacts/browser_qa/v32_49/terminal_tablet_768x1024.png)
- [Mobile 375×667](./artifacts/browser_qa/v32_49/terminal_mobile_375x667.png)
- [Normal-app network trace](./artifacts/browser_qa/v32_49/normal_app_analyse_network_trace.json)

The viewport smoke check reported no horizontal clipping. The screenshots are layout artifacts from the earlier V32.49 browser pass; they predate the final stepper/copy cache-busting retest and are not presented as final content screenshots or as a usability/accessibility audit.

## UI design application

The changes follow the cited guidance by prioritizing system status and feedback, actionable empty states, clear multi-stage progress, specific error recovery, programmatic status semantics, and separating concise outcomes from expandable diagnostics:

- [Nielsen Norman Group — 10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
- [Carbon Design System — Empty States](https://www.carbondesignsystem.com/building-blocks/core/patterns/empty-states)
- [Carbon Design System — Loading](https://www.carbondesignsystem.com/building-blocks/core/patterns/loading)
- [GOV.UK Design System — Error Message](https://design-system.service.gov.uk/components/error-message/)
- [W3C WCAG 2.2](https://www.w3.org/TR/wcag/)
- [W3C — Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
- [USWDS — Data Visualizations](https://designsystem.digital.gov/components/data-visualizations/)
- [USWDS — Alerts](https://designsystem.digital.gov/components/alerts/)

These sources inform interaction design; they are not substitutes for the unrun manual accessibility checks.

## Release blockers and next safe checks

Do not release this QA as a complete verification. Before closing the remaining gates:

1. Provide a verified, matching tournament manifest or complete deterministic fresh-arm inputs, then exercise winner, fallback, both-fail, cached, and fresh-evaluation branches without treating fixtures as market evidence.
2. Define a governed price-deviation policy before testing proposal invalidation between Analyse and Enter.
3. Use isolated, explicitly fixture-labeled API/browser fault injection for timeouts, 5xx, malformed responses, feed disconnects, active monitoring, reload/restart, and recovery.
4. Complete keyboard, focus, contrast, target-size, and screen-reader checks.
5. Preserve the 100-clean-non-overlapping-block prospective gate. Historical replay and this browser run do not count toward it.

No live execution was enabled, no simulated attempt was forced, and no profitability or directional-accuracy claim is made.
