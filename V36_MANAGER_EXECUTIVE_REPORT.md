# BTCognitive V36.0 — Phase Gate Report

## Executive decision

**BLOCKED at Phase 0 / Phase B.** The local Bitstamp snapshot is authentic to its on-disk provenance manifest and structurally valid, but is stale. The current `/api/tournament/analyse` handler returns a stale/abstain result before invoking the real analysis engine. Therefore the required real-engine API integration is not complete.

Per the requested execution order, feature inventory, orchestrator, trade labels, probability model, ablation, walk-forward evaluation, ranking, and full-system acceptance work were not started. No placeholder reports or fabricated findings were created for those phases.

## Phase A — repository state

Read-only inspection recorded:

- Branch: `milestone/v35.3-critical-remediation`
- HEAD: `25d483f4c3646661b57311de9d0b53d2be881adb`
- Before this report was created, `git status --porcelain=v1` had **444 entries**: 115 tracked dirty entries, 329 untracked entries, 0 staged, 0 deleted, and 0 renamed.
- No source, test, dataset, model, manifest, database, or ledger was changed for this V36 gate.

### Changes not identified in the V35.4.3 manager summary

The current status includes `api/routes_tournament.py` as modified and `engine/regime_strategy_tournament.py` as untracked. These are relevant to the analysis path but are not listed among the V35.4.3 manager report's itemized changes. The available status snapshot does not establish when or by whom they were introduced. Their contents were preserved and not edited.

The current modified route validates a submitted candle payload and computes a request hash. Its stale-data branch returns an abstention before calling `analyse_current_market`; only the fresh-data branch invokes the analysis engine. Thus an authentic but stale local snapshot cannot satisfy the real-engine integration gate through the current route.

## Phase B — local snapshot evidence

The authoritative configured offline source is `data/raw/ohlcv.parquet` according to `engine/data_mode.py`. A more recent, separately stored provider snapshot is available at `data/providers/bitstamp/BTCUSD_1h.parquet`; it has a corresponding `provenance.json` and is the only inspected local candidate suitable for the attempted BTCUSD API handoff.

### Bitstamp cache checks

Read-only inspection and a local Parquet validation script found:

| Check | Result |
|---|---|
| Parquet SHA-256 | `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54` |
| Provenance `parquet_sha256` match | PASS |
| Provenance row count | 1,000; matches file |
| Parsed UTC timestamps | PASS |
| Monotonic ordering | PASS |
| Duplicate timestamps | 0 |
| One-hour continuity deviations | 0 |
| `available_time == timestamp + 1 hour` | PASS for all rows |
| Numeric missing/non-finite values | None found |
| Positive OHLC and OHLC geometry | PASS |
| Volume nonnegative | PASS |
| First candle open | `2026-09-22T23:00:00+00:00` |
| Last candle open / close | `2026-11-03T14:00:00+00:00` / `2026-11-03T15:00:00+00:00` |
| Provenance retrieval time | `2026-11-03T15:08:31Z` |
| Freshness against 2-hour policy | **STALE**; approximately 18.5 hours old at validation |

The stored parquet hash matches its manifest; the original raw provider response is not stored here, so `raw_payload_sha256` could not be independently recomputed. The Parquet itself has no `is_closed` field; closure is represented by `available_time` and the manifest's retrieval timestamp. The route schema requires explicit `is_closed`, which would need to be derived in the request payload from those verified close timestamps.

The protected `data/raw/ohlcv.parquet` is not substituted for the provider cache. Its current SHA-256 is `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`. The frozen HAR-RS-DOW manifest records a different training-data hash (`689390a737402fd2ea4ec78d3dcde2eaca2a34617d6bd4f002de87c65d8a2697`); this run did not investigate or reconcile that historical dataset difference.

### API execution status

No API request or model analysis was run. Since the local cache is stale and source inspection shows the handler returns before calling the analysis engine, forcing it through a longer freshness threshold would mislabel stale data and violate the requirement not to call it current analysis. No external provider request was made.

Consequently, there is no response snapshot ID to compare, no evidence that the real engine consumed the submitted snapshot, and no feature-level point-in-time execution result. The stale-input fail-closed behavior is established by source inspection, not by a new endpoint run.

## Protected state

Current read-only hashes and sidecar checks:

| Asset | Size | SHA-256 / state |
|---|---:|---|
| `data/prospective_forecast_ledger.jsonl` | 19,129 bytes | `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491` |
| `experiments/results/market_memory.db` | 69,787,648 bytes | `4a663c704b6ced6e16d29aa5524ea6eafc7b716c1175b80121dff7fefdcca` |
| `data/raw/ohlcv.parquet` | 2,334,866 bytes | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` |
| `data/providers/bitstamp/BTCUSD_1h.parquet` | 56,271 bytes | `d64cd2591b4cc5c5a6328785b1722ec5f8e01b78f30dee7f1dc7dff583e7fc54` |
| `data/providers/bitstamp/provenance.json` | 860 bytes | `f3ad886d1097b5adb60901b99bb7af2e3e8f2919f4b2bf01e340fe99517af48a` |
| `experiments/results/freeze/standard_har_v1.joblib` | — | **ABSENT** |
| `experiments/results/freeze/har_rs_dow_v1.joblib` | 945 bytes | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |

The market-memory `-wal` and `-shm` sidecars were absent. These values match the available V35.4.3 forward capture where overlap exists. That comparison does not establish earlier historical integrity. The prospective ledger and canonical database remain `INTEGRITY_UNVERIFIABLE`, not demonstrated corrupted.

Standard HAR remains `NOT_ESTABLISHED`; no artifact was recreated, no accuracy percentage was produced, and no model was promoted. C2 remains disabled.

## Work and validation performed

- Files inspected: V35.4.3 manager and test-isolation reports; `engine/data_mode.py`; Bitstamp service and provenance; `api/routes_tournament.py`; `engine/regime_strategy_tournament.py`; relevant research and frozen manifests.
- Files changed: only this new phase-gate report.
- Data validation: read-only local Parquet/provenance validation script; no dataset writes.
- Tests: none run for V36. No full test suite or API server was started.
- External access: no provider request, socket call, subprocess-based market request, prospective collection, or live workflow was run.
- Not started: feature inventory, feature orchestrator, outcome-label implementation, trade-probability model, model calibration, walk-forward validation, trade ranking, and full-system acceptance.

## Governance

- Instrument scope: BTCUSD only.
- Application posture: `ANALYSIS_ONLY`.
- Model authorization: `OFFLINE_RESEARCH_ONLY`.
- C2: `DISABLED`.
- Live trading, broker connectivity, and order placement: `DISABLED`.
- Forecast accuracy: no new claim; Standard HAR accuracy remains `NOT_ESTABLISHED`.

## Next action

Implement and test an explicit **historical replay** mode for the existing analysis endpoint. It must invoke the real engine with the submitted snapshot while preserving the original snapshot ID, use only features available by the last candle's `available_time`, mark results `HISTORICAL_STALE` (never `FRESH` or `LIVE`), and force execution/trade authorization off. Only after a guarded replay proves exact snapshot parity should the feature-inventory phase begin.

## Final status after this report

This report is one new untracked file; all pre-existing worktree entries were preserved. Branch and HEAD remain unchanged. The final status is expected to contain 445 entries (115 tracked dirty and 330 untracked, with none staged, deleted, or renamed); no Git cleanup or other destructive operation was performed.
