# V36.3A — Agent A: BTCUSD Data Provenance Findings

## Decision

**Dataset decision: `UNVERIFIED`**

Local file integrity is established relative to the repository digest. The repository does not establish original-source authenticity, exact acquisition history, or interval timestamp semantics. The label `VERIFIED_LOCAL_SNAPSHOT` should not be read as proof of provider authenticity.

## Evidence matrix

| Question | Finding | Evidence and confidence |
|---|---|---|
| Current file identity | **Verified bytes:** 393,952,273 bytes; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`. Matches `research/entry_tp_sl/data_intake_manifest.json::sha256`; local file is not tracked by Git. | Direct hash/stat check and manifest: high confidence for local byte identity. Not source authentication. |
| Provider | Manifest declares Kaggle `mczielinski/bitcoin-historical-data`, version 745 (`data_intake_manifest.json::dataset_name/source_uri`). `G0_FOUNDATION_INTEGRITY.md` describes publisher-provided metadata. | **Claimed Kaggle origin; unverified.** No archived Kaggle response/download record or immutable upstream object binding this local file was found. High confidence about what repository documents say; low confidence about source authenticity. |
| Exchange and instrument | `data_intake_manifest.json` and `instrument_contract.json::instrument` state Bitstamp BTC/USD spot. The earlier `dataset_manifest.template.json` records that claim as candidate metadata, and `provenance.template.json::source.upstream_source` says “per publisher documentation.” | **Claimed Bitstamp BTC/USD spot; unverified.** No independent Bitstamp acquisition response or publisher source revision was located. Filename is not evidence. |
| Acquisition trace | `provenance.template.json` leaves `source_commit`, artifact hash/object ID, time rules, and record hash null. `dataset_manifest.template.json::notes` says no Kaggle archive was downloaded/copied and its snapshot fields were null. `G0_FOUNDATION_INTEGRITY.md` describes the source as a candidate and states no credentialed Kaggle/Drive access occurred. | Acquisition method, date, and source-to-file chain are not established. High confidence based on these missing fields and records. |
| UTC and timestamp unit | Intake manifest declares UTC/Unix seconds and includes endpoints 2012-01-01 00:01:00Z to 2026-10-07 03:11:00Z. | Recorded interpretation is UTC; no contrary timezone evidence surfaced. This does not resolve open/close role. |
| Open/close semantics | `instrument_contract.json::bar_interval_semantics` says `INTERVAL_CLOSE`, `(t-60s,t]`. In contrast, `dataset_manifest.template.json::bars.timestamp_role` is `unknown`, and `provenance.template.json::time_semantics` is `UNVERIFIED` with null `available_time_rule`. `G0_FOUNDATION_INTEGRITY.md` says those semantics were not verified. | **Unverified and internally conflicting documentation.** Monotonicity and a :01 first timestamp cannot establish interval boundary or historical availability. High confidence. |
| Frequency and structural checks | Intake manifest asserts 7,766,111 rows, no nulls/duplicates, monotonic timestamps, and valid OHLC bounds. `DATA_INTAKE_BLOCKERS.md` calls timestamp checks resolved; the candidate template says `gap_audit_status: NOT_RUN`, and the G0 report says gaps may occur. | **Not independently established by this specialist review.** Current file header was read; no row-level audit was run. Prior V36.2 audit reports minute spacing, but the evidentiary conflict still requires an auditable, reproducible gap report with a declared tolerance. |
| Manifest binding | Intake manifest digest exactly matches the current CSV and the dataset digest repeated in the freeze and implementation manifests. | Strong local integrity binding. SHA matching proves neither source nor timestamp semantics. |
| Existing exchange records | Local Coinbase V1/V2/V3 acquisition manifests identify Coinbase BTC-USD hourly datasets and provide API acquisition details. They are different datasets and do not authenticate the claimed Bitstamp minute snapshot. No equivalent original Bitstamp acquisition log was located in the scoped records. | Strong distinction between the separate Coinbase records and the claimed Bitstamp file. |

## Main-manager independent review

The manager independently recomputed the current CSV SHA-256 and size; both match the intake manifest. The manager also verified that the manifest’s documented source commit `cd1017aa90637bb81b1edf263f620e89346d84ca` contains no `research/entry_tp_sl/` tree. Neither fact closes the CSV’s source or timestamp uncertainty.

## Evidence required to move to `VERIFIED`

Provide already-authorized local evidence (no new online acquisition in this milestone) that establishes:

1. An immutable Kaggle v745 source object/archive identity and metadata, plus a source-side digest or archived acquisition record binding it to this exact local SHA.
2. The exact upstream publisher/updater source revision and acquisition method/date for this export, or an equivalent auditable provider record.
3. Authoritative timestamp-role documentation for this exact dataset version: interval-open or interval-close, UTC treatment, and when each row becomes available.
4. A reproducible structural audit bound to the exact SHA: schema, OHLCV invariants, duplicate count, irregular/gap intervals, and the declared fail-closed tolerance.
5. A row-to-time mapping demonstrating `t0`, 15-minute close, next-minute fill Open, and first path interval under the evidenced timestamp convention.
6. A completed provenance record with non-null source revision, immutable artifact identity, hash, event-time rule, availability-time rule, transformations, and rights disposition.

If that evidence is unavailable, the bounded alternative is a replacement dataset with a provenance-bearing original Bitstamp BTC/USD 1m source snapshot and explicit timestamp semantics. Do not silently substitute Coinbase or infer from this filename.

## Recommendation, unresolved questions, and confidence

**Recommendation:** Keep this dataset `UNVERIFIED` for confirmatory trade-path outcome work. Static resolver development and synthetic conformance tests do not require market data; historical labels/performance claims on this CSV do.

**Unresolved:** Which original source object produced the file? What source record proves the claimed Bitstamp venue and BTC/USD instrument? Are rows interval-close or interval-open? What is the approved irregular-bar tolerance?

**Confidence:** High for digest agreement and the internal documentation conflict; high that the scoped repository records do not supply the missing source chain; low for the claimed original source because it cannot be independently corroborated.

## Files inspected

- `data/raw/btcusd_1-min_data.csv` (file metadata, digest, and header only; no holdout observations)
- `research/entry_tp_sl/data_intake_manifest.json`
- `research/entry_tp_sl/instrument_contract.json`
- `research/entry_tp_sl/dataset_manifest.template.json`
- `research/entry_tp_sl/provenance.template.json`
- `research/entry_tp_sl/DATA_INTAKE_BLOCKERS.md`
- `research/entry_tp_sl/data_model_rights_checklist.md`
- `research/entry_tp_sl/G0_FOUNDATION_INTEGRITY.md`
- Local Coinbase V1, V2, V3 acquisition manifests and V2 provenance comparison report
- Relevant local Git history for the intake records and recorded source commit
