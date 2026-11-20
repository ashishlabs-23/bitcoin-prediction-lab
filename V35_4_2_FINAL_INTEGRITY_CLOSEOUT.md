# BTCognitive V35.4.2 - Final Repository Integrity Closeout

**Audit date:** 2026-11-03  
**Decision:** **BLOCKED**  
**Scope:** Read-only repository and evidence audit. No tests, application workflows, or network requests were run for this closeout.

## 1. Executive decision

The repository is **not accepted for milestone closeout**. The principal analysis route now consumes and validates the submitted candle snapshot, and the protected OHLCV parquet matches previously recorded hashes. However:

1. The prospective forecast ledger has no trustworthy pre-remediation byte/hash baseline. Its current bytes differ from `HEAD`, but that does not establish when or by whom the worktree changes were made.
2. The configured market-memory database passes SQLite integrity checking, but no suitable pre-test database snapshot exists to establish whether the earlier remediation test iteration changed it.
3. Unsupported current calibration/health outputs remain on the public multiscale API, and an arena context path can expose a zero Winkler value despite unavailable calibration.
4. The final V35.4.1 test totals are recorded in a report but not independently supported by a persisted raw execution log. Full live UI-to-backend acceptance was not run.

These are not findings of proven corruption. The ledger and database are classified **INTEGRITY_UNVERIFIABLE** because the required before-state evidence is missing. Keep `ANALYSIS_ONLY`, `OFFLINE_RESEARCH_ONLY`, and live-trading-disabled controls in force.

## 2. Repository identity and Git status

| Item | Audit result |
|---|---|
| Branch | `milestone/v35.3-critical-remediation` |
| HEAD | `25d483f4c3646661b57311de9d0b53d2be881adb` |
| `git status --porcelain=v1` entries | 428 (105 tracked changes plus 323 directory-collapsed untracked entries) |
| Expanded `git status --porcelain=v1 -uall` entries | 1,670 |
| Tracked files changed, unstaged | 105 |
| Untracked files (`git ls-files --others --exclude-standard`) | 1,565 |
| Staged changes | 0 |
| Deleted / renamed tracked paths | 0 / 0 |
| `git diff --stat` | 105 files; 14,855 insertions, 2,832 deletions |

Protected-directory status, before creation of this closeout report:

| Directory | Modified tracked files | Untracked files |
|---|---:|---:|
| `data/` | 2 | 368 |
| `experiments/` | 4 | 7 |
| `models/` | 4 | 0 |
| `research/` | 18 | 974 |

The modified tracked protected paths include:

- `data/prospective_forecast_ledger.jsonl`, `data/research_alert_state.json`
- `experiments/results/multi_regime_validation_report.json`, `experiments/results/post_repair_milestone_5_lock.json`, `experiments/results/stage10_shadow_validation/shadow_prediction_ledger.jsonl`, `experiments/results/stage11_forward_validation/forward_prediction_ledger.jsonl`
- `models/authoritative_model_registry.py`, `models/challengers/har_qlike_24h_challenger.py`, `models/challengers/har_qlike_challenger.py`, `models/risk_metrics.py`
- 18 tracked research files, including `research/post_repair_block_builder.py`, `research/risk_envelope.py`, baseline/challenger reports, and post-repair reports.

The five V35.4 reports and `V35_4_1_REMEDIATION_REPORT.md` are untracked. The earlier V35.4.1 report says the tree was already dirty before remediation; prior records also describe a pre-existing dirty tree. The available evidence does not support attributing every current file to V35.4 or V35.4.1. This audit adds only this closeout report; no source or protected content was changed.

The expanded status count above is the pre-report count. After adding this report, expected counts are 1,671 expanded entries, 1,566 untracked files, and 429 default porcelain entries; the final Git check below records the actual result.

## 3. Protected-file integrity

| Protected item | Current evidence | Classification |
|---|---|---|
| `data/raw/ohlcv.parquet` | 2,334,866 bytes; mtime `2026-10-30T14:26:42.4141070Z`; SHA-256 `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`; no Git status entry. The hash matches dated Oct. 30/31 protected-hash records and the V35.4 forecast report. | `VERIFIED_UNCHANGED` against the available dated hash records |
| `data/prospective_forecast_ledger.jsonl` | 19,129 bytes, 21 lines; mtime `2026-10-26T17:36:05.984561+00:00`; SHA-256 `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491`; modified in Git. Its diff from `HEAD` is 15 additions and 5 deletions (21 current lines versus 11 at `HEAD`). The V35.4 report describes 21 records, but no trusted before-remediation hash or byte-identical copy was found. | `INTEGRITY_UNVERIFIABLE` |
| Frozen Standard HAR artifact | `experiments/results/freeze/standard_har_v1.joblib` is absent. No artifact hash exists to verify. | `NOT PRESENT`; accuracy remains `NOT ESTABLISHED` |
| Frozen HAR-RS-DOW artifacts/manifests | Several challenger files and dated freeze manifests exist, but these are not the registered Standard HAR artifact. Current tracked status is shown above; no reconstruction or substitution was made. | Not evidence for Standard HAR identity |

The tracked `experiments/results/freeze/` directory had no Git status entries. Current SHA-256 values for its 13 files are:

| File | Size (bytes) | SHA-256 |
|---|---:|---|
| `freeze_integrity_audit.json` | 13,009 | `26d0c33ef77962d360c840472c333ef8489a555bb86bf2f6710167b5c7a78222` |
| `freeze_integrity_report.md` | 5,500 | `fdc40e0e8c7c0fcfc992aeddc6e76ae0dbf9a4670f935c8e0df88bbf0d825431` |
| `har_rs_dow_v1_baseline_manifest.json` | 3,160 | `d88e8ed60a2331918007b889d46f3bb482abbaf2c07b08551bd1a4cf2db32fab` |
| `har_rs_dow_v1_CONTAMINATED_DO_NOT_USE.joblib` | 941 | `c576c80c41096709ca824389354f25b77af9c8dd4d1aa24a033471fd5c02fb4e` |
| `har_rs_dow_v1_contaminated_metadata.json` | 598 | `f3e88eec3df438265bcfd52f068795341b8956eede6d21e239ed059e878eaf78` |
| `har_rs_dow_v1_corrected.joblib` | 945 | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |
| `har_rs_dow_v1.joblib` | 945 | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |
| `phase_02_label_boundary_audit.json` | 2,397 | `e697ad51b17ca7c29d2220dcd2140af937c8f0e69ac8053b2c56ad93f27d59bd` |
| `phase_02_label_boundary_report.md` | 4,802 | `b8978cbef17bada3dd37b28a8c3057339a131b976c1782ef71530056423e696e` |
| `phase_03_reanchor_audit.json` | 1,540 | `c8549c82e955bafa38d1fefe6ddf044357223c53965f37d71733071e1c01f38d` |
| `phase_03_reanchor_report.md` | 4,157 | `0e206a173c6b3b8a4582f005c677be0bad9a8c5f775182e7eb55304e830e2d86` |
| `repaired_scientific_contract_manifest.json` | 2,416 | `23c6f0c8b9b9a2d22da20bb31fda36891c44ea88af270c3a490374b868ca3990` |
| `scientific_contract_manifest.json` | 1,025 | `e0c1544e5be24aacc4ee424bbc59a5ecd0b9f0968a2f260e8489a54a6ee85203` |

Both `har_rs_dow_v1.joblib` and its corrected-named copy hash to the challenger registry digest `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b`. This verifies only that challenger file, not Standard HAR.

Other modified protected outputs are also dirty versus `HEAD`. Their current hashes anchor their present bytes but cannot establish when those changes occurred:

| Modified path | Size (bytes) | Current SHA-256 |
|---|---:|---|
| `data/research_alert_state.json` | 298 | `2f8e285778ed651715258364e1da7eb693ef2d0b0eb3de9ac7de987996137ecb` |
| `experiments/results/multi_regime_validation_report.json` | 2,640 | `4e5ccf8efcd9232df274b04d128a5bbc38d7888c6ee8d86424b257a562dc23ac` |
| `experiments/results/post_repair_milestone_5_lock.json` | 465 | `7f377ee2c726fe741e2107ac78c220280f208de5deac714b148bbed076ec722c` |
| `experiments/results/stage10_shadow_validation/shadow_prediction_ledger.jsonl` | 47,052,331 | `a35aae2eea0d8e79623c3a29127a1fb85a7446d26fa1db2d4539f8c10a57848a` |
| `experiments/results/stage11_forward_validation/forward_prediction_ledger.jsonl` | 2,399,463 | `6b79c9f232268f9b47cf243c6287ea15047879e2276bd0eebbe463f4c282c684` |
| `models/authoritative_model_registry.py` | 27,084 | `ee784662054b0ede4dc4c9530fd8da10d85372252433e981c886da1c9eec6b34` |

The older `research/data_audit_summary.json` and `experiments/results/freeze/freeze_integrity_audit.json` refer to an earlier OHLCV vintage and different hash/row count. They do not match the current parquet, but are dated historical records. The newer dated hash records match the current file; therefore the stale older manifests are not treated as evidence that the current parquet changed during V35.4.1.

### Prospective ledger content checks

The ledger was read and parsed without writing:

- 21/21 lines parse as JSON; no duplicate forecast IDs were found.
- 11 `rv24h_var_ann` records (24-hour horizon); all 11 resolved.
- 10 `rv7d_var_ann` records (168-hour horizon); 5 resolved and 5 pending.
- Feature-availability cutoffs do not follow issue times; scheduled maturity agrees with issue time plus the target horizon; no premature resolution or inconsistent resolved-state fields were found.
- The records contain overlapping target intervals: 20 overlapping pairs at 24 hours and 41 at 168 hours. Raw record counts therefore do not represent independent blocks and do not establish confirmatory evidence.

The current ledger is structurally valid, but the committed baseline is not the pre-remediation working-copy baseline. Its Git diff cannot establish whether the V35.4.1 work changed, rewrote, or merely preserved the already-dirty ledger.

## 4. Market-memory database

`config/database.py` selects `experiments/results/market_memory.db` unless `SQLITE_DB_PATH` is set. The environment override was unset; the canonical database was inspected using SQLite read-only mode. The similarly named `data/market_memory.db` is a zero-byte noncanonical file and is not the configured database.

| Property | Result |
|---|---|
| Canonical path | `experiments/results/market_memory.db` |
| Size / mtime | 69,787,648 bytes / `2026-11-03T11:58:56.6910533Z` |
| Current SHA-256 | `4a663c704b6ced6e16d29aa5524ea6eafc7b716c1175b80184121dff7fefdcca` |
| SQLite journal mode | `wal` |
| Read-only `PRAGMA integrity_check` | `ok` |
| Tables | 10 |
| `-wal` / `-shm` sidecars | Not present before or after the read-only inspection |
| Classification | `INTEGRITY_UNVERIFIABLE` |

Read-only table census:

| Table | Rows | Latest relevant timestamp |
|---|---:|---|
| `excursion_forecasts` | 60,921 | `2026-11-03T11:58:56.671167+00:00` |
| `range_forecasts` | 60,921 | `2026-11-03T11:58:56.671167+00:00` |
| `uncertainty_forecasts` | 60,921 | `2026-11-03T11:58:56.671167+00:00` |
| `forecast_outcomes` | 9,233 | latest resolution `2026-10-21T05:35:43.935051+00:00` |
| `predictions` | 5,622 | latest prediction `2026-10-19T07:45:24.979728+00:00` |
| `hawkes_forecasts` | 225 | `2026-10-22T11:26:13.166943+00:00` |
| `hawkes_outcomes` | 27 | `2026-10-14T17:45:40.552292+00:00` |
| `quarantined_forecast_outcomes` | 71 | `2026-10-14T17:48:28.068529+00:00` |
| `shadow_decision_records` | 0 | none |
| `stress_trials` | 1 | `2026-08-18 10:05:00 UTC` |

The current database and newest forecast rows have matching Nov. 3 timestamps, confirming recent database activity, but not its cause. Existing database snapshots/backups found were dated Oct. 14, Oct. 16, and Oct. 19; none is a contemporaneous pre-test baseline. The database integrity check proves structural consistency, not that tests did not append rows. No baseline is available to distinguish a test write from ordinary prior activity, so no change is attributed to the V35.4.1 tests.

## 5. Standard HAR artifact and authorization

`models/authoritative_model_registry.py` identifies `Standard-HAR-v1.0`, target `rv7d_var_ann`, 168-hour horizon, and `OFFLINE_RESEARCH_ONLY` authorization. Its artifact path is `experiments/results/freeze/standard_har_v1.joblib`; that exact file is absent. The registry digest is the placeholder `standard-har-v1-baseline-hash`, not a SHA-256.

No artifact was reconstructed, retrained, replaced, or promoted. Other HAR challenger artifacts are not substitutes.

**`STANDARD_HAR_ACCURACY = NOT ESTABLISHED`.** No accuracy percentage is reported.

## 6. V35.4.1 remediation verification

### Analysis snapshot and network path

- `api/routes_tournament.py` requires submitted candles and an accepted source label, validates the submitted DataFrame, hashes the request payload, and passes that same DataFrame to the analysis function. Stale input returns an abstention; missing or invalid input fails closed. Analysis exceptions and malformed model output become explicit HTTP errors.
- `web/analysis_contract.js` checks local-source/freshness/candle invariants and recomputes the submitted candle hash against response provenance. `web/app.js` checks that response before presenting the analysis result.
- The source confirms exact payload identity, but the backend accepts `data_source` as a client-supplied allowlisted label; it does not cryptographically attest that a client-provided snapshot originated from the configured local cache. The hash establishes which bytes were analyzed, not independent source authenticity.
- `engine/data_mode.py` returns external-network permission as false in every mode. Bitstamp and Coinbase REST fetch methods call `assert_no_external_network` before their subprocess/HTTP/socket operations. The Coinbase browser WebSocket is gated by `window.__BTC_ALLOW_EXTERNAL_WS__`; no code setting that flag was found, so it remains disabled by default. No provider request was made during this audit.

### Freshness behavior

- The local hourly-candle route validates cached data and responds with explicit `FRESH`, `STALE`, or `DATA_UNAVAILABLE` states, identifies local historical/cache source, and does not mark its cache result `LIVE`.
- The frontend treats only `FRESH` data as ready. Stale and unavailable responses are not accepted as an analysis snapshot.
- A complete browser-to-backend run was not performed, so these are source-level findings, not end-to-end acceptance evidence.

### Calibration governance: remaining defect

The V35.4.1 changes do disable C2/default calibrated outputs in several relevant routes: the smart-entry API constrains `c2_health` to `UNAVAILABLE`; arena and terminal observatory paths set calibration unavailable or return null metrics; uncertainty/range services return unavailable calibration fields. However, the claim that unsupported current calibration/health metrics have been fully suppressed is **not verified**:

1. `GET /prediction/multiscale/health` returns fixed `ridge_coverage=90.32`, `hawkes_coverage=92.5`, and `overall_health="HEALTHY"` from `engine/multiscale_health.py`. `GET /prediction/multiscale` also supplies `vol_24h=0.015` and returns `shadow_health="HEALTHY"` in `api/routes_prediction.py`. These are current API outputs, not dated historical report entries, and lack request-specific calibration evidence.
2. `engine/observatory.py` returns 100% coverage for the no-resolved-record baseline branch and zero Winkler/breach values. `api/routes_arena.py` masks coverage and tail asymmetry but leaves Winkler and breach values in the response. The frontend renders `30D Winkler` as a number, so unavailable evidence can appear as `0.000`.
3. `api/routes_research.py` still serves dated historical research entries containing past coverage claims. They are labeled with dates and source reports and were not treated as current model performance; they were not rewritten.

These live API paths contradict the broad remediation claim that missing calibration evidence always produces unavailable outputs. No code was changed during this audit.

## 7. V35.4.1 test evidence

The V35.4.1 report records the following commands and results. The final raw console output/log for those runs was not found in the repository, so the counts below are **reported, not independently verified in this closeout**:

| Check | Reported evidence | Audit qualification |
|---|---|---|
| Focused Python pytest command across nine selectors | 66 collected, 66 passed, 0 failed, 0 deselected, 1 Pydantic deprecation warning | The report provides the command, but no corresponding raw run log was found. |
| Standard HAR API/registry spot check | 2 passed, 1 warning | The report says these tests overlap the focused suite; do not add them to 66. No raw log found. |
| `node tests_frontend.js` | Passed; script supplied no assertion count | Recorded in report; raw log not found. |
| `node --check web\\app.js` | Passed | Recorded in report; raw log not found. |
| Full repository suite | Not run | Explicitly excluded. |
| Live provider tests / complete browser UI-to-backend integration | Not run | No external request or full E2E evidence. |

The retained remediation checkpoint documents earlier, distinct iterations: one with 36 passed and 3 failed, and another with 37 passed, 1 failed, and 1 deselected; it also records an earlier frontend pass. Those intermediate results are not the final 66-test run and must not be combined with it. Existing root test logs are from October and do not establish the November V35.4.1 result. No tests were run for this read-only audit.

## 8. Acceptance matrix

| ID | Acceptance criterion | Result | Evidence / limitation |
|---|---|---|---|
| A01 | Current branch and HEAD identified | PASS | Exact branch and commit recorded above. |
| A02 | Existing Git work preserved | PASS | No reset, restore, clean, checkout, stash, branch, commit, push, or delete operation. |
| A03 | Protected ledger integrity | UNVERIFIABLE | Current bytes parse, but no trusted pre-remediation hash/copy exists; current file differs from `HEAD`. |
| A04 | Market-memory database integrity | UNVERIFIABLE | SQLite integrity is `ok`; no suitable pre-test baseline exists to establish no test writes. |
| A05 | Historical dataset integrity | PASS | OHLCV hash matches dated Oct. 30/31 protected records; file is clean in Git. |
| A06 | Standard HAR artifact identity | PASS | Exact registered artifact is absent and digest is a placeholder; status correctly remains `NOT ESTABLISHED`. |
| A07 | Analysis snapshot consistency | PASS | Source uses submitted candles and hashes response provenance; source authenticity itself remains client-asserted. |
| A08 | External network restrictions | PASS | Provider guards precede external calls; network permission is false; browser provider WebSocket is disabled by default. No network request was made. |
| A09 | Stale-data handling | PASS | Stale/unavailable data does not become an analysis-ready or `LIVE` cache result. |
| A10 | C2 governance | PASS | Examined C2 controls/defaults are unavailable and request schema does not allow caller activation. |
| A11 | Calibration representation | FAIL | Multiscale API still emits hardcoded coverage/health and the arena context can expose zero Winkler as measured output. |
| A12 | Test evidence | UNVERIFIABLE | Final counts are in a report, but raw execution records are absent; earlier run results are distinct. |
| A13 | Full end-to-end acceptance | UNVERIFIABLE | NOT RUN; no complete live UI-to-backend request was evidenced. |
| A14 | Live execution | PASS | No live trading/broker execution authorization was found; live trading remains disabled. |

## 9. Remaining blockers and next action

### Blockers

- No trustworthy pre-remediation byte-level baseline for the modified prospective forecast ledger.
- No contemporaneous pre-test market-memory database snapshot to distinguish test writes from other activity.
- Current multiscale API calibration/health responses remain unsupported by verifiable evidence.
- Final focused test totals cannot be independently checked from persisted run logs; full end-to-end acceptance is not established.
- Standard HAR remains unavailable and its forecast accuracy remains `NOT ESTABLISHED`.

### Recommended next action

**Before any further test or application run, locate trusted pre-remediation copies/hashes for the prospective ledger and market-memory database and compare them read-only with the current files; do not restore or rewrite either file.**

## 10. Final repository status and audit actions

No destructive Git operation, branch operation, commit, push, source edit, test run, application workflow, external request, or protected-file write was performed. SQLite was opened read-only; the existing database and its sidecar state were not altered.

Final Git status must include this one new untracked report. All pre-existing modifications and untracked files remain untouched. The exact final counts are confirmed after report creation:

```text
Branch: milestone/v35.3-critical-remediation
HEAD:   25d483f4c3646661b57311de9d0b53d2be881adb
Status entries (default porcelain): 429
Expanded status entries (-uall):     1,671
Tracked unstaged files:              105
Untracked files:                    1,566
Staged files:                       0
Deleted / renamed tracked paths:    0 / 0
```

Final governed decisions:

- **Research experiment:** `INCONCLUSIVE` for registered Standard HAR accuracy; exact artifact unavailable.
- **Prospective evidence:** `COLLECTING`; 21 ledger records are overlapping and do not establish 100 independent clean blocks.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.
- **Milestone:** `BLOCKED`.
