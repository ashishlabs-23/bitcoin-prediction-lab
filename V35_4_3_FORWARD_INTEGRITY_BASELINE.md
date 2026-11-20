# BTCognitive V35.4.3 Forward-Only Integrity Baseline

**Baseline captured:** 2026-11-03 (UTC timestamps recorded per file)  
**Branch:** `milestone/v35.3-critical-remediation`  
**HEAD:** `25d483f4c3646661b57311de9d0b53d2be881adb`

This report records the present state as a forward-only reference. It does not assert that the ledger or canonical database were unchanged before this capture. No protected file was modified to produce this baseline.

## Protected state at baseline

| Asset | Size (bytes) | Modified (UTC) | SHA-256 / state |
|---|---:|---|---|
| `data/prospective_forecast_ledger.jsonl` | 19,129 | 2026-10-26T17:36:05.9845611Z | `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491` |
| `experiments/results/market_memory.db` | 69,787,648 | 2026-11-03T11:58:56.6910533Z | `4a663c704b6ced6e16d29aa5524ea6eafc7b716c1175b80184121dff7fefdcca` |
| `data/raw/ohlcv.parquet` | 2,334,866 | 2026-10-30T14:26:42.4141070Z | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` |
| `models/authoritative_model_registry.py` | 27,084 | captured 2026-11-03 | `ee784662054b0ede4dc4c9530fd8da10d85372252433e981c886da1c9eec6b34` |
| `experiments/results/freeze/standard_har_v1.joblib` | — | — | **NOT PRESENT** |
| `experiments/results/freeze/har_rs_dow_v1.joblib` | 945 | captured 2026-11-03 | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |

### Frozen manifest and audit artifact baseline

| Asset | Size (bytes) | SHA-256 |
|---|---:|---|
| `experiments/results/freeze/freeze_integrity_audit.json` | 13,009 | `26d0c33ef77962d360c840472c333ef8489a555bb86bf2f6710167b5c7a78222` |
| `experiments/results/freeze/freeze_integrity_report.md` | 5,500 | `fdc40e0e8c7c0fcfc992aeddc6e76ae0dbf9a4670f935c8e0df88bbf0d825431` |
| `experiments/results/freeze/har_rs_dow_v1_baseline_manifest.json` | 3,160 | `d88e8ed60a2331918007b889d46f3bb482abbaf2c07b08551bd1a4cf2db32fab` |
| `experiments/results/freeze/har_rs_dow_v1_CONTAMINATED_DO_NOT_USE.joblib` | 941 | `c576c80c41096709ca824389354f25b77af9c8dd4d1aa24a033471fd5c02fb4e` |
| `experiments/results/freeze/har_rs_dow_v1_contaminated_metadata.json` | 598 | `f3e88eec3df438265bcfd52f068795341b8956eede6d21e239ed059e878eaf78` |
| `experiments/results/freeze/har_rs_dow_v1_corrected.joblib` | 945 | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |
| `experiments/results/freeze/har_rs_dow_v1.joblib` | 945 | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |
| `experiments/results/freeze/phase_02_label_boundary_audit.json` | 2,397 | `e697ad51b17ca7c29d2220dcd2140af937c8f0e69ac8053b2c56ad93f27d59bd` |
| `experiments/results/freeze/phase_02_label_boundary_report.md` | 4,802 | `b8978cbef17bada3dd37b28a8c3057339a131b976c1782ef71530056423e696e` |
| `experiments/results/freeze/phase_03_reanchor_audit.json` | 1,540 | `c8549c82e955bafa38d1fefe6ddf044357223c53965f37d71733071e1c01f38d` |
| `experiments/results/freeze/phase_03_reanchor_report.md` | 4,157 | `0e206a173c6b3b8a4582f005c677be0bad9a8c5f775182e7eb55304e830e2d86` |
| `experiments/results/freeze/repaired_scientific_contract_manifest.json` | 2,416 | `23c6f0c8b9b9a2d22da20bb31fda36891c44ea88af270c3a490374b868ca3990` |
| `experiments/results/freeze/scientific_contract_manifest.json` | 1,025 | `e0c1544e5be24aacc4ee424bbc59a5ecd0b9f0968a2f260e8489a54a6ee85203` |

The local Standard HAR artifact is absent; the registry's `standard-har-v1-baseline-hash` value is a placeholder rather than a digest. Consequently `STANDARD_HAR_ACCURACY = NOT_ESTABLISHED`.

## Historical integrity classifications

| Asset | Classification | Basis |
|---|---|---|
| Prospective forecast ledger | `INTEGRITY_UNVERIFIABLE` | Valid current JSONL content is not a trusted pre-remediation comparison. The Git `HEAD` version is not a prior worktree baseline. |
| Canonical market-memory database | `INTEGRITY_UNVERIFIABLE` | Current SQLite integrity check was `ok`, but no contemporaneous pre-test database baseline exists. |

These classifications describe absence of historical evidence, not demonstrated corruption or a demonstrated V35.4.1 mutation.

## Test-run integrity policy

Before any authorized focused tests run, pytest must:

1. Use a fresh disposable database under the operating-system temporary directory; it must not copy, open, or write the canonical market-memory database.
2. Block external network connections and protected-file writes.
3. Hash protected datasets, the prospective ledger, frozen model/manifests, historical experiment outputs, and the canonical database before and after the run. Any changed path fails the test session.

Post-test hashes and exact test counts will be appended to the V35.4.3 test-isolation and manager reports; the captured baseline values above are not to be rewritten.

## Forward capture after V35.4.3 validation attempts

**Captured:** 2026-11-04T08:35:35.8217003Z. These are current-state values, not evidence of state before the V35.4.1 remediation.

| Asset | Size (bytes) | Modified (UTC) | SHA-256 / state |
|---|---:|---|---|
| `data/prospective_forecast_ledger.jsonl` | 19,129 | 2026-10-26T17:36:05.9845611Z | `ee58b37c71c5c3ff322af3084d27b306eb0a445a8bd6e01a74b76d8168ccd491` |
| `experiments/results/market_memory.db` | 69,787,648 | 2026-11-03T11:58:56.6910533Z | `4a663c704b6ced6e16d29aa5524ea6eafc7b716c1175b80121dff7fefdcca` |
| `data/raw/ohlcv.parquet` | 2,334,866 | 2026-10-30T14:26:42.4141070Z | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` |
| `models/authoritative_model_registry.py` | 27,084 | 2026-11-03T14:47:55.5885828Z | `ee784662054b0ede4dc4c9530fd8da10d85372252433e981c886da1c9eec6b34` |
| `experiments/results/freeze/standard_har_v1.joblib` | — | — | **NOT PRESENT** |
| `experiments/results/freeze/freeze_integrity_audit.json` | 13,009 | 2026-09-03T17:32:24.0628657Z | `26d0c33ef77962d360c840472c333ef8489a555bb86bf2f6710167b5c7a78222` |
| `experiments/results/freeze/freeze_integrity_report.md` | 5,500 | 2026-09-03T17:32:24.0809837Z | `fdc40e0e8c7c0fcfc992aeddc6e76ae0dbf9a4670f935c8e0df88bbf0d825431` |
| `experiments/results/freeze/har_rs_dow_v1_baseline_manifest.json` | 3,160 | 2026-09-03T17:32:24.1022078Z | `d88e8ed60a2331918007b889d46f3bb482abbaf2c07b08551bd1a4cf2db32fab` |
| `experiments/results/freeze/har_rs_dow_v1.joblib` | 945 | 2026-09-03T17:32:24.0856785Z | `750b5d15ed84c3cf24b8484ae928ff7c8098cab0c35eafe310ab28bf57ed285b` |

`experiments/results/market_memory.db-wal` and `experiments/results/market_memory.db-shm` were both absent at capture. Each listed current hash matches the earlier forward baseline above. This establishes no change in these listed files between the two captures; it does not establish historical pre-remediation integrity.

The completed focused Python run recorded in `V35_4_3_TEST_ISOLATION_REPORT.md` reported an unchanged protected inventory: 1,848 files, before and after manifest SHA-256 `d424b3c0dd43a0b4a91735a2050fd43315edd341d3f146655aad6698ec3ce031`. A later Python revalidation attempt was stopped before pytest produced a summary, so that attempt has no completed inventory-guard result. The individual hashes above were rechecked after that attempt.

The branch remained `milestone/v35.3-critical-remediation` at HEAD `25d483f4c3646661b57311de9d0b53d2be881adb`. Ledger and canonical-database historical classifications remain `INTEGRITY_UNVERIFIABLE`; no corruption or mutation is inferred from that uncertainty.
