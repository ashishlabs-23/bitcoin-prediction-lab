# BTCognitive V36.3 — One-Minute Data Provenance Attestation

## Attestation result

**Dataset classification: `UNVERIFIED`**

The local CSV’s byte identity is established relative to the repository manifests. The original source authenticity and the timestamp’s open/close role are **not established by the repository evidence**. Therefore the file is not attested as an admissible source for confirmatory entry/exit labels in this gate. This is not a finding that the bytes are corrupt or that the claimed source is false.

## Observed repository evidence

| Question | Repository evidence | Finding |
|---|---|---|
| Local object identity | `data/raw/btcusd_1-min_data.csv`; SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`; 393,952,273 bytes. The current SHA matches `data_intake_manifest.json`, `contract_freeze_manifest.json`, and `6B_implementation_manifest.json`. | **Byte integrity: verified against local records.** This does not authenticate the publisher or acquisition. |
| Claimed source and instrument | `data_intake_manifest.json` names Kaggle dataset `mczielinski/bitcoin-historical-data`, v745, Bitstamp BTC/USD. `instrument_contract.json` freezes BTC/USD, spot, Bitstamp, Kaggle v745. `G0_FOUNDATION_INTEGRITY.md` says publisher metadata identifies Bitstamp BTC/USD minute OHLCV and publisher automation fetches 60-second Bitstamp bars. | **Claimed identity: Kaggle v745 / Bitstamp BTC/USD spot.** No original downloaded archive, Kaggle object/version response, upstream acquisition response, publisher source commit, or signed source record is present to independently authenticate that identity. |
| Acquisition record | `provenance.template.json` records `source_commit: null`, `artifact.sha256: null`, `immutable_object_id: null`, `timestamp_role: UNVERIFIED`, and `available_time_rule: null`. `dataset_manifest.template.json` says no Kaggle archive was downloaded/copied into the repository and a byte-exact snapshot/object ID was still required. `G0_FOUNDATION_INTEGRITY.md` likewise records that the dataset was initially only a candidate and no credentialed source access occurred. | **Acquisition method/date and the transition from candidate to this local object are not auditable from original acquisition records.** Later manifests assert the snapshot identity but do not supply the missing acquisition evidence. |
| Timestamp unit/timezone | `data_intake_manifest.json` and `instrument_contract.json` say Unix seconds and UTC. Dataset timestamps are recorded as 2012-01-01 00:01:00Z through 2026-10-07 03:11:00Z. | Unix-seconds/UTC interpretation is recorded and internally consistent with the listed endpoints. |
| Bar timestamp role | `instrument_contract.json` declares `INTERVAL_CLOSE`, with `t` representing `(t-60s,t]`; `data_intake_manifest.json` claims `VERIFIED_60S_BAR_CLOSE`. Conversely, `dataset_manifest.template.json` and `provenance.template.json` explicitly say timestamp role/open-vs-close and historical availability are unknown/unverified; the latter says publisher automation does not establish open-vs-close labeling. `DATA_INTAKE_BLOCKERS.md` calls timestamp semantics verified based on monotonicity and zero duplicates, which do not establish bar-boundary meaning. | **Open/close role: unverified.** Repository records conflict; regular spacing and monotonic order cannot prove the price timestamp convention or `available_time`. |
| OHLCV shape and continuity | `feasibility_audit.md` and `DATA_INTAKE_BLOCKERS.md` report 7,766,111 rows, 0 nulls, 0 duplicates, consecutive 60-second timestamps, and valid OHLC bounds. Prior V36.2 read-only parsing also reported minute spacing and no basic OHLCV anomalies. | The repository has internally consistent **reported structural checks**. Those checks establish neither provider authenticity nor timestamp semantics. No V36.3 replay or model development used the data. |
| Rights | `data_model_rights_checklist.md` says CC BY-SA 4.0 was user-approved for research; `dataset_manifest.template.json` still says license review required. | User research approval is recorded; upstream license terms and complete obligations are not independently authenticated here. Rights approval does not prove source lineage. |

## Why the timestamp claim is not closed

The frozen contracts assume a specific mapping:

- Decision time `t0` is the close of a completed 15-minute bar (`decision_contract.json`).
- Fill time is `t0 + 60s`, at the open of the execution bar (`entry_execution_contract.json`).
- The first path observation is `(t0 + 60s, t0 + 120s]` (`decision_contract.json`).
- `instrument_contract.json` says minute timestamps are **interval close** timestamps.

If a minute row at `t0+60s` is close-stamped, its `Open` is at `t0`, not at `t0+60s`. Under that frozen convention, the open at `t0+60s` belongs to the row closing at `t0+120s`. But `run_full_research_pipeline.py::run` searches for a row timestamped `t0+60s` and passes that row’s `Open` to `build_trade_contract`. If timestamps instead mean bar-open, that open can correspond to `t0+60s`, but the pipeline starts path evaluation at the following row and omits the first post-fill bar. Thus the current source cannot be certified against both the declared interval-close convention and the declared fill/path intervals without an explicit timestamp-role decision and index mapping.

`run_full_research_pipeline.py::run` also resamples with `.resample('15min')` without explicit `closed`/`label` arguments and uses the last constituent `Timestamp`. Consequently the required UTC close grid (:00/:15/:30/:45) is not demonstrated by the code under the frozen interval-close convention.

## Missing evidence required to change this classification

Using repository evidence only, the following are absent:

1. The original Kaggle v745 archive or equivalent source object identifier plus immutable source-side metadata matching this file’s bytes.
2. The exact publisher acquisition code/commit and a source record showing which response/export generated this CSV.
3. Authoritative timestamp-role documentation for this exact v745 artifact and an `available_time` rule.
4. A deterministic mapping from raw minute rows to 15-minute close timestamps, the `t0+60s` fill bar, and the first path observation consistent with that role.
5. A recorded gap-tolerance value; the manifest currently says only “greater than tolerance.”

No external network access or new acquisition was performed. Until the missing evidence is supplied from an already-authorized local record, the admissibility state remains `UNVERIFIED`; do not infer “close” from minute spacing, a file name, or a manifest status string.
