# V37.2 — Live Data and Provenance Report

**Scope:** Controlled, read-only qualification of one Bitstamp public-data request and review of existing dataset provenance. No code or tests were run. No raw response was stored or published.

**Repository state:** At task start, branch `milestone/v35.3-critical-remediation` was at `25d483f4c3646661b57311de9d0b53d2be881adb`, with extensive pre-existing working-tree changes. Final status showed 1,720 entries including this report; no other path was created or edited for this task.

## Decision

**Live retrieval: NOT PERFORMED.** The one permitted Bitstamp GET was withheld because current public-data terms and permission for the stated research scope could not be established from authoritative terms already available locally. This follows the stop condition in the task. No other provider, endpoint, or network request was used.

**Reason:** The repository contains references to Bitstamp’s official Terms of Use URL, but no current authoritative terms text. Existing V32.0/V32.2 reports say the legal page was not retrieved with substantive content and classify the relevant rights as unresolved. A local provider-rights matrix describes a Bitstamp commercial DLA as requiring written confirmation and an executed bilateral agreement; that is neither current public-data terms nor evidence that such an agreement is in force. It cannot resolve the terms question. Fetching the legal page would violate the instruction to make no request to another endpoint.

## Request authorization and outcome

| Item | Record |
|---|---|
| Permitted request, not sent | `GET https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=60&limit=10&exclude_current_candle=true` |
| Parameters | `step=60`, `limit=10`, `exclude_current_candle=true` |
| HTTP requests made for this task | **0** |
| Retrieval time / response status / headers / body | Not applicable; no request was made |
| Credentials, account endpoints, orders, websocket, other provider | None used |
| Provider and instrument requested | Bitstamp public OHLC endpoint; BTC/USD (`btcusd`) is indicated by the URL, not confirmed by a response |
| Requested interval | 60 seconds (1 minute); no returned interval observed |
| Response shape and candle count | Not observed |
| Timestamp semantics for a live response | Unknown; no response |
| Latest returned candle age and completion | Not measurable; no returned candle |
| Ordering, duplicates, missing minute intervals | Not evaluated |
| Non-finite values, OHLC invariants, volume | Not evaluated |

No values are inferred from the endpoint name or from the service implementation to fill these missing live observations.

## Local timestamp-contract evidence

The local `engine/bitstamp_market_data_service.py` describes the existing Bitstamp service as hourly. Its validation computes a putative end as `timestamp + step_seconds` and checks that against retrieval time (with a 120-second allowance); its dataframe builder labels the input timestamp as `timestamp`/`t_open` and the computed endpoint as `available_time`/`t_close`. This is evidence of the local implementation’s **assumption**, not authoritative Bitstamp documentation establishing the timestamp convention for the requested 1-minute response. Therefore live and provider-level timestamp semantics remain **unknown**.

For the historic local minute CSV, repository reports identify a conflict: the intake/instrument records assert interval-close semantics, while provenance/candidate records leave timestamp role or availability unverified. V36.3 and V36.3A classify the dataset `UNVERIFIED`; neither the filename, cadence, nor manifest status string resolves that conflict.

## Latest local snapshot metadata comparison

Metadata only was consulted; no Parquet or CSV observation rows were opened. Ages below are measured at the metadata inventory time, `2026-11-04T11:38:40Z`, from the locally recorded latest timestamp. They describe metadata timestamps, not independently validated data freshness.

| Local object | Manifest/provenance metadata | Age at inventory time | Qualification |
|---|---|---:|---|
| `data/providers/bitstamp/BTCUSD_1h.parquet` with `data/providers/bitstamp/provenance.json` | Claims Bitstamp BTC/USD spot, 1h, 1,000 rows; latest candle open `2026-11-03T14:00:00Z`, close `15:00:00Z`; retrieval `15:08:31Z` on Nov 3. Filesystem metadata: 56,271-byte Parquet, modified `2026-11-03T15:08:36Z`. | 20h 38m 40s since metadata-reported close; 20h 30m 09s since metadata-reported retrieval. | Latest Bitstamp cache metadata found. The local service’s code sets a two-hour freshness threshold, so this metadata is older than that threshold; no cache rows or runtime status were checked. |
| `data/research/coinbase_btc_usd_hourly_verified_v3` | Acquisition/validation manifests identify Coinbase BTC-USD 1h and UTC candle-open timestamps; recorded range `2022-01-01T00:00:00Z` through `2026-10-27T09:00:00Z`. | 8d 2h 38m 40s since manifest-reported last timestamp. | Historical Coinbase dataset; manifest claims are reported, not revalidated in this task. |
| `data/raw/coinbase_15m.parquet` with `data/raw/coinbase_15m_manifest.json` | Coinbase Exchange BTC-USD, 15m; manifest reports 16,200 validated candles, one segment, zero gaps, and last completed timestamp `2026-10-26T17:30:00Z`. Filesystem metadata: 830,946-byte Parquet, modified `2026-10-26T17:46:34Z`. | 8d 18h 08m 40s since metadata-reported last completed timestamp. | Manifest-only historical snapshot; not row-checked here. |
| `data/raw/btcusd_1-min_data.csv` | `data/research/entry_tp_sl/data_intake_manifest.json` claims Kaggle dataset `mczielinski/bitcoin-historical-data` v745, Bitstamp BTC/USD, UTC Unix seconds, 1m; reports 7,766,111 rows, 393,952,273 bytes, SHA-256 `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`, and last listed timestamp `2026-10-07T03:11:00Z`. | 28d 8h 27m 40s since the last listed timestamp; its open/close role is unresolved. | Local bytes are bound to repository manifests, but original-source authenticity, exact acquisition chain, timestamp role, and availability time remain unverified per V36.3/V36.3A. |

The 1h Bitstamp cache provenance records a private-research licensing scope, but that is a local metadata assertion, not authoritative current terms or proof of permission.

## Coinbase/Bitstamp boundary and historical-data classification

- **Bitstamp 1m CSV:** Claimed Kaggle v745 / Bitstamp BTC/USD. **`UNVERIFIED`** as a historical source: the local digest and size match repository manifests, but the upstream object/acquisition is not authenticated, and timestamp semantics conflict across local contracts and provenance records.
- **Coinbase 1h V3:** Coinbase BTC-USD, UTC candle-open timestamps and 2022–2026 coverage are recorded in its acquisition manifest. **Separate historical Coinbase dataset**; this task did not inspect observations or independently certify its acquisition or continuity.
- **Coinbase 15m cache:** Coinbase BTC-USD, 15m, with validation/count/coverage assertions in its local manifest. **Separate historical snapshot**; not independently validated here and not a 1m path substitute.
- **Bitstamp 1h cache:** Metadata claims a separately persisted Bitstamp BTC/USD snapshot. **Separate provider snapshot**, not appended to Coinbase history; no underlying observations were examined.

The Coinbase and Bitstamp records have different venues, product identifiers (`BTC-USD` versus `BTC/USD`), resolutions, and documented timestamp conventions (Coinbase V3 says candle-open; the Bitstamp 1m role is unresolved). The manifests also report different latest times. No row-level overlap, price discontinuity, or gap was measured. These records must not be silently concatenated or described as one continuous, venue-neutral series; any boundary or transformation would require an explicit source/contract decision and row-level verification under authorization.

## Evidence consulted

- `V36_3_DATA_PROVENANCE_ATTESTATION.md`
- `V36_3A_PARALLEL_DATA_PROVENANCE_FINDINGS.md`
- `research/entry_tp_sl/data_intake_manifest.json` (metadata only)
- `data/providers/bitstamp/provenance.json` (metadata only)
- `data/raw/coinbase_15m_manifest.json` (metadata only)
- `data/research/coinbase_btc_usd_hourly_verified_v3/acquisition_manifest.json` and `validation.json` (metadata only)
- `engine/bitstamp_market_data_service.py` (local implementation contract)
- `research/v32_0_btcusd_license_provenance_decision.md`, `research/v32_2_btcusd_dataset_resolution.md`, and the local V32.67 provider-rights matrix (terms-access and rights-status records, not authoritative current terms)

## Governance

- **Research experiment:** `INCONCLUSIVE` — no live observations were obtained.
- **Prospective evidence:** `NOT_STARTED` by this task; no prospective observation was collected.
- **Model authorization:** `OFFLINE_RESEARCH_ONLY`.
- **Live trading:** `DISABLED`.

No source, dataset, cache, manifest, or prior report was changed. The only task deliverable is this report.
