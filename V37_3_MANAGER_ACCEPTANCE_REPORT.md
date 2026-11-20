# BTCognitive V37.3 — Manager Acceptance Report

**Assessment date:** 2026-11-04  
**Branch / HEAD:** `milestone/v35.3-critical-remediation` / `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Posture:** `ANALYSIS_ONLY`  
**Default authorization:** `OFFLINE_RESEARCH_ONLY`

## Manager decision

| Area | Status | Evidence and limitation |
|---|---|---|
| Application | `APPLICATION_PARTIALLY_FUNCTIONAL` | Browser-rendered UI and focused route/security tests work under synthetic fixtures. A production FastAPI lifecycle/browser integration was not established; authenticated position/journal access is intentionally unavailable until a trusted principal provider exists. |
| Live-data integration | `LIVE_DATA_SMOKE_PARTIAL` | The single authorized Bitstamp GET returned HTTP 200 and 10 valid BTC/USD minute candles, but its latest completed candle was about 240 seconds old. Freshness acceptance therefore failed; no data was persisted. |
| Historical data | `UNVERIFIED` / `SOURCE_CORROBORATED_NOT_PROVEN` | Local manifests and hashes corroborate stored bytes. The 827-row Coinbase/Bitstamp hourly overlap aligns timestamps but has venue-specific prices and substantially different volume; neither source's original provenance or rights is thereby proven. |
| Backtest pipeline | `PIPELINE_TEST_ONLY` | 76 deterministic synthetic mechanics tests passed. No admissible historical replay, model fit, strategy performance, or forecast accuracy evaluation was performed. |
| Browser | `BROWSER_QA_PARTIAL` | Same-machine Chrome/Playwright rendered all 10 existing routes with a loopback-only unavailable-data API fixture. No uncaught page error was observed; the production backend, real candle chart data, freshness, and complete control interaction were not tested. |
| Security | `OWNER_BOUNDARY_IMPLEMENTED_FAIL_CLOSED` | Routes derive ownership from a trusted ASGI principal and reject spoofing/cross-owner access. This deployment supplies role credentials but no stable user identity; the APIs return 503 for a role-authenticated request without a principal and 401 to unauthenticated callers. |
| Research experiment | `INCONCLUSIVE` | No admissible market experiment was run. |
| Prospective evidence | `NOT_STARTED` | No prospective record was added or resolved. |
| Model authorization | `OFFLINE_RESEARCH_ONLY` | No model or strategy was promoted. |
| Live trading | `DISABLED` | No broker, order, or real-capital operation was enabled or attempted. |

These are separate decisions. The live-data HTTP response is not a freshness pass; browser rendering is not production-backend acceptance; and synthetic mechanics tests are not market evidence.

## Scope and feature preservation

BTCognitive remains the institutional-grade BTCUSD Market Intelligence and Quantitative Risk Analysis system. V37.3 preserved the existing engines, API capability families, and all 10 frontend hash routes. The frontend changes correct false fallbacks, clarify unavailable states, and fix responsive layout; they do not remove or replace research, forecasting, risk, paper-trading, or tournament functionality.

The owner-provided feature-preservation policy is present in the worktree's uncommitted [AGENTS.md](./AGENTS.md) change. The manager and specialists did not edit or revert that policy. Other pre-existing worktree changes were preserved.

## Workstreams and outcomes

| Specialist | Work | Manager integration result |
|---|---|---|
| 1 — Data and provenance | One-time Bitstamp smoke test; local snapshot fingerprints and provider overlap | Request succeeded but was stale. Bitstamp commercial terms remained unavailable behind an official-site interstitial. Cross-source hourly diagnostics are explicitly corroborative, not provenance certification. |
| 2 — Research recovery | Existing `research/entry_tp_sl` mapping; separate hourly and minute tracks | No real-data computation met admission requirements. Existing pipeline reused for synthetic mechanics checks only; no duplicate research engine was created. |
| 3 — Resolver sensitivity | Read-only boundary diagnostics for six frozen execution uncertainties | Synthetic alternatives show materially different outcomes. No contract, resolver, or ledger was changed. All six remain owner decisions. |
| 4 — Frontend/browser | Corrective rendering/fallback fixes and local Chrome tests | All routes rendered under an unavailable-only local fixture. A measured 29px Paper Trading mobile overflow was fixed and rechecked at 390px. Real backend integration remains unverified. |
| 5 — Security/regression | Trusted-principal ownership enforcement, snapshot sanitation, isolated and focused testing | Cross-owner access is blocked. Missing user identity fails closed rather than inventing an identity mapping. Full-suite execution remains incomplete. |

## Resolved defects and implementation changes

1. **User-position and journal ownership:** [api/security_auth.py](./api/security_auth.py) now provides `get_current_principal_id`, requiring the existing USER-or-higher role plus a trusted authenticated ASGI principal identity. [api/routes_user_positions.py](./api/routes_user_positions.py) and [api/routes_manual_journal.py](./api/routes_manual_journal.py) scope list/status/detail/mutations to that identity; conflicting request owner IDs are rejected, and records owned by someone else are concealed with 404. Caller-provided owner IDs are never stored as authority.
2. **No identity-provider fallback:** Existing API keys establish only a role, not an individual. No new auth system or key-to-person mapping was invented. The affected routes fail closed until the owner configures a trusted principal provider. Manual performance evaluation remains present but returns 503 because its evaluator aggregates owners.
3. **Manual forecast snapshot integrity:** Probability pairs are retained only when finite, within [0,1], and summing to one under the existing tolerance; unavailable/invalid values become explicit unavailable states. Unavailable regime input stays `UNKNOWN`. The immutable digest is recomputed after sanitation. Capture/regime exceptions are warning-logged by exception type only; tests verify sensitive exception text is not logged.
4. **Frontend correctness:** [web/app.js](./web/app.js) fixes two Chrome render-time `ReferenceError`s and replaces reviewed hard-coded market/portfolio/performance fallbacks with explicit unavailable states. [web/styles.css](./web/styles.css) wraps the Paper Trading execution-ledger header at mobile widths without hiding controls or content.
5. **BTCUSD identity and unsupported risk context:** V37.2's BTCUSD-only candle rejection and removal of injected directional probabilities/regime labels remain covered by regressions; no BTCUSDT source was added.

No frozen research contract, protected dataset, holdout, prospective ledger, or model registry was changed. No frontend or backend capability was removed.

## Data qualification

### One-time public Bitstamp request

Exactly one market-data GET was sent, without credentials or account endpoints:

```text
GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=10&exclude_current_candle=true
```

At `2026-11-04T14:04:58.561Z` through `14:05:00.100Z`, Bitstamp returned HTTP 200, pair `BTC/USD`, and 10 records from `13:51:00Z` through `14:00:00Z`. All values were finite; OHLC and nonnegative-volume invariants passed; timestamps were ordered with no duplicates or gaps inside that returned window. Assuming the timestamp is the minute open, the latest candle closed at `14:01:00Z`, making it approximately 238.6 seconds old at request start and 240.1 seconds old at completion. The response omitted newer completed minute starts. The cause and server-side snapshot time are unknown.

Current official commercial data-license terms were **not established**: the official terms lookup returned an anti-bot interstitial rather than substantive terms. The local “Private Research Scope” metadata is not a license. Commercial redistribution remains unauthorized/unverified. No raw live response was written into the repository or a research dataset; temporary evidence remains outside the repository.

### Local hourly cross-source fingerprint

Read-only alignment of the locally stored Coinbase V2/V3 and Bitstamp hourly snapshots found 827 exact matching UTC timestamps from `2026-09-22T23:00Z` to `2026-10-27T09:00Z`, with matching one-hour `available_time`. Coinbase V2 and V3 are byte-identical, not independent samples. Across the overlap, price correlations were high (`0.99997–0.99999`) but exact/two-decimal OHLC matches were rare; median absolute price differences ranged from $5.07 to $12.25. Median absolute volume difference was 105.8078 stored units (73.42% of Coinbase volume), and volume correlation was 0.83751. This supports compatible hourly indexing and demonstrates venue-specific candle differences; it proves neither source's original provenance nor commercial rights.

The Bitstamp minute CSV remains `UNVERIFIED` for original-source authenticity, timestamp role, availability time, and rights. Local byte hashes matching manifests qualify only as `SOURCE_CORROBORATED_NOT_PROVEN`. Coinbase and Bitstamp were not joined into a research history.

See [V37_3_DATA_QUALIFICATION.md](./V37_3_DATA_QUALIFICATION.md) for all local snapshot metadata, hashes, exclusions, and timestamp assumptions.

## Research and resolver findings

- **Track A — hourly:** The Coinbase hourly snapshot is a candidate for a separately frozen descriptive study, not currently source-verified under the provenance schema. Existing manifests report 42,237 rows from 2022-01-01 to 2026-10-27 09:00Z and 13 missing hours in three intervals. No Track A feature coverage or research metric was computed. The 24-hour and 168-hour HAR targets remain separate, and no volatility result is treated as directional performance.
- **Track B — minute execution:** Not admissible for historical outcomes: minute source/timestamp provenance is unresolved and frozen fill/path/cost semantics remain unsettled. No minute labels, holdout observations, replay, or outcome accounting were run.
- **Pipeline mechanics:** 76 focused deterministic tests passed. Their inputs are synthetic fixtures and establish mechanics only.
- **Six resolver decisions:** Entry timestamp/fill mapping; A1 2% execution-gap reference/direction/boundary; opening-gap versus dual-touch precedence; exact 240-minute horizon and missing-bar treatment; component-level fee/spread/slippage allocation; and A1 reclaim confirmation timing. The sensitivity report supplies synthetic examples, but no alternate is promoted to an authoritative outcome. No frozen contract was edited.

No historical performance, profitability, directional accuracy, calibration, or C2 coverage is established. See [V37_3_RESEARCH_RECOVERY_REPORT.md](./V37_3_RESEARCH_RECOVERY_REPORT.md) and [V37_3_RESOLVER_SENSITIVITY_REPORT.md](./V37_3_RESOLVER_SENSITIVITY_REPORT.md).

## Browser and frontend evidence

Local Google Chrome with Python Playwright exercised the checked-in React application through a loopback-only static harness. The harness mapped CDN script references to test-only local packages, blocked non-local HTTP and WebSocket traffic, and supplied only HTTP 503 `DATA_UNAVAILABLE` responses with no market values. It did **not** start `api.server` or the FastAPI lifespan.

All 10 existing routes rendered non-empty content, navigation worked, the disabled-trading label remained visible, and the final unavailable-only fixture caused no uncaught page errors. The final Paper Trading mobile test at 390×844 measured document/body/root/page widths of 390px with no overflowing descendant after the CSS correction. The terminal chart container mounted, but no candle data was supplied. No write or execution controls were activated; exhaustive control testing was not completed. Two external Google Fonts requests were blocked. No external WebSocket attempt was observed; the local fixture's `/ws` route was unsupported.

Screenshots are stored outside the repository:

- Desktop dashboard, 1440×1000, SHA-256 `a4cb6060530881e502288f85f8a1feac39def912a8e7e00f283c9d21a6704f21`: `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\files\v37_3_dashboard_desktop.png`
- Paper Trading mobile, 390×844, SHA-256 `0c3e040cc0f4fb33840b8e3f917a7e2cbea905f6ab460f24fe1b01a15a55437e`: `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\files\v37_3_paper_trading_mobile.png`

Real FastAPI startup, API/UI integration, real data freshness, candle plotting, and all disabled-control interactions remain unverified. The browser result is therefore partial, not acceptance of the full application.

## Security and regression test evidence

| Command/suite | Result |
|---|---|
| `.\.venv_win\Scripts\pytest.exe tests\test_security_auth.py tests\test_v37_3_user_data_ownership.py -q --tb=short` | **13 passed**, 1 existing Pydantic deprecation warning; run in the live checkout after the final security edits. Protected-file guard passed with unchanged before/after digest. |
| Focused API/auth integration in disposable `.qa_v37_3` copy | **40 passed**, 1 warning. Included ownership, lifecycle, V37.2 BTCUSD rejection/no-fabrication regressions. |
| Resolver regression suite in isolated copy | **17 passed**. |
| `npm test` | **Passed**; frontend assertions all passed (runner reports no numeric total). |
| `npm run check` | **Passed**; configured JavaScript syntax checks passed. |
| Focused synthetic entry/barrier mechanics | **76 passed in 8.97s**; protected-file guard passed. No market data or model result was used. |
| Broader security/resolver attempt | **35 passed, 5 failed, 15 errors**, 1 warning; lifespan-based tests failed to start because their redirected results directory lacked `repaired_scientific_contract_manifest.json`. |
| Full safe-suite attempt 1 | Collection stopped with **2 errors**, one network-marked test deselected, and **0 tests executed**. Two longitudinal tests instantiate SQLite under protected `results` during collection; the guard blocked it. |
| Full safe-suite attempt 2 | In a disposable copy, excluded those two modules and retained `-m "not network"`. Reached 48% after 600 seconds with failures/errors appearing; manager stopped the run before a summary. Exact counts are unavailable and not inferred. |
| Scoped `git diff --check` | **Passed** for V37.3 code, test, and report files. Repository-wide checks still encounter unrelated pre-existing whitespace in dirty files. |

The complete commands, failure conditions, test exclusions, and security limitations are in [V37_3_SECURITY_AND_REGRESSION_REPORT.md](./V37_3_SECURITY_AND_REGRESSION_REPORT.md). No full-suite pass is claimed.

## Integrity and repository preservation

- V37.0 protected asset baseline: **213/213 matched** by file length and SHA-256; missing 0, mismatched 0.
- V37.0 protected source baseline: **39/39 matched**; missing 0, mismatched 0.
- Focused test protected-file guards covered 1,848 files and reported identical before/after manifest digest `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`.
- Branch and HEAD are unchanged. No commit, push, branch switch, merge, rebase, reset, stash, or discard occurred.
- The disposable `.qa_v37_3` test copy was removed. The test-only React/Three/Charts packages were uninstalled; `package.json` and lockfiles remain unchanged. No QA copy, node_modules tree, or persistent test/browser process remains.
- Final pre-report Git status: 1,735 entries (119 modified, 1,616 untracked, 0 staged), including pre-existing worktree files and the V37.3 reports/test. This manager report adds one untracked deliverable; no unrelated entries were removed.

## Outstanding owner decisions and next implementation task

1. **Identity provider:** choose/configure a trusted ASGI principal provider and bind individual identity to existing credentials. Until then, position and journal routes correctly remain unavailable to role-only callers.
2. **Manual evaluation access:** approve an owner-filtered evaluator implementation or retain the explicit 503 until one is available.
3. **Execution semantics:** decide the six items in the resolver sensitivity report before any Track B historical outcome analysis; do not modify frozen contracts until approved.
4. **Data use/admission:** obtain authoritative Bitstamp data-use terms and original-source/timestamp evidence for historical inputs. Do not redistribute commercial data without established rights.
5. **Track A protocol:** before any hourly computation, freeze an immutable source snapshot, analysis dates, gap policy, feature/target definitions, and holdout exclusions.
6. **Application/browser integration:** once a safe local FastAPI startup fixture is available, connect the actual app to it and verify real API unavailable/freshness states and candle rendering in Chrome. The current browser fixture is UI-only.

**Next implementation task:** after owner approval of the identity-provider choice, integrate it with the existing role-auth stack and run the already-added cross-owner route regressions against the real ASGI middleware; separately implement owner-scoped manual evaluation only after its data aggregation can enforce per-principal filtering.

## Deliverables

- [Data qualification](./V37_3_DATA_QUALIFICATION.md)
- [Research recovery](./V37_3_RESEARCH_RECOVERY_REPORT.md)
- [Resolver sensitivity](./V37_3_RESOLVER_SENSITIVITY_REPORT.md)
- [Frontend and browser QA](./V37_3_FRONTEND_AND_BROWSER_REPORT.md)
- [Security and regression](./V37_3_SECURITY_AND_REGRESSION_REPORT.md)
- [Manager acceptance](./V37_3_MANAGER_ACCEPTANCE_REPORT.md)
