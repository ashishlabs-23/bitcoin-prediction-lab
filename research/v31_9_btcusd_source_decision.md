# BTCognitive V31.9 — BTC/USD Source Decision

**Date:** 2026-10-23  
**Scope:** source qualification only. No data download, no ingestion, no experiments, no strategy test, no model validation, and no runtime-source change.

## 1. Decision summary

**Selected candidate:** Bitstamp BTC/USD 1-minute data path, existing local file `data/raw/btcusd_1-min_data.csv`  
**Status:** `BLOCKED — RIGHTS OR PROVENANCE UNRESOLVED`  
**Overall BTC/USD decision:** `NO QUALIFIED BTC/USD CANDIDATE`

This decision is based on the evidence available in the repository and the current public-source review. The file is real, structurally coherent, and BTC/USD-identified by its symbol and endpoint usage, but it does not yet satisfy the permission, provenance, and source-governance requirements to be qualified as the approved BTC/USD research source.

## 2. Retired candidate status

**Binance BTCUSDT retired from active candidate consideration:** yes.

This retirement is preserved only as a governance decision and historical record. The earlier V31.6–V31.8 reports remain intact and are not rewritten. The selected BTC/USD path is not replaced by BTCUSDT, BTCUSDC, or any derivatives.

## 3. Existing BTC/USD candidate review

### Candidate reviewed
- **Venue:** Bitstamp
- **Asset/quote:** BTC/USD
- **Granularity:** 1-minute
- **File:** `data/raw/btcusd_1-min_data.csv`
- **Observed path:** present in the repository and active in the local data tree

### File-level evidence
- **File exists:** yes
- **Size:** 393,952,273 bytes
- **Last modified:** 2026-07-10 21:48:49
- **Header observed:** `Timestamp,Open,High,Low,Close,Volume`
- **Sample rows observed:**
  - `1325376060,4.58,4.58,4.58,4.58,0.0`
  - `1325376120,4.58,4.58,4.58,4.58,0.0`
  - `1325376180,4.58,4.58,4.58,4.58,0.0`
  - `1325376240,4.58,4.58,4.58,4.58,0.0`

This file appears structurally consistent with an OHLCV BTC/USD 1-minute archive and is clearly intended as a Bitstamp BTC/USD feed. However, the file alone does not establish the governing legal terms, provenance chain, or permissions for AI/ML research and derived model work.

## 4. Source identity and technical integrity

### Technical findings
- The dataset is present locally and has a standard OHLCV layout.
- It uses a Unix epoch timestamp convention and a 1-minute interval pattern consistent with a raw exchange feed.
- The file does not establish the exact acquisition origin, source-version record, or publisher-license status by itself.
- It is not a proof of lawful use beyond public access to a public API or file fetch.

### Provenance and permission findings
The repository contains prior audit records showing repeated source-gap and provenance concerns, including contradictory conclusions about the same source in different historical reports. Those contradictions are not resolved by the local file alone.

The critical issue is not whether the file is technically valid; it is whether the source can be used under the relevant rights and use terms for the intended research scope. That remains unresolved.

## 5. Official source evidence reviewed

### Bitstamp public API evidence
- **Official API base:** `https://www.bitstamp.net/api/`
- **Evidence in repo:** `api/market_drivers.py` uses Bitstamp public endpoints such as:
  - `https://www.bitstamp.net/api/v2/ohlc/btcusd/`
  - `https://www.bitstamp.net/api/v2/ticker/btcusd/`

This confirms the public endpoint identity and the BTC/USD instrument path, but it does not establish consent, rights, or exactly-applicable terms for AI/ML model development, benchmarking, or derived-output use.

### Important distinction
Public API access is not the same as a written data-use authorization. An exchange endpoint and a valid data file are technical facts; data permissions are a separate legal/use question.

## 6. Why the Bitstamp candidate is not qualified

The Bitstamp BTC/USD path remains blocked because the following are not proven by authoritative evidence in the project:

- the exact version of the file at acquisition time;
- the governing Bitstamp data-use terms applicable to this dataset and access method;
- the exact permission status for private AI/ML model development, training, validation, or benchmarking on historical BTC/USD market data;
- the exact source lineage and reuse rights for local historical CSV files stored in the repository;
- whether a separate written permission or source-specific license exists beyond public API access.

Without that evidence, the project must not treat the Bitstamp 1-minute file as an approved BTC/USD research input.

## 7. Decision status by gate

**`BLOCKED — RIGHTS OR PROVENANCE UNRESOLVED`**

This is the correct gate result for the current Bitstamp BTC/USD file because the repository does not provide a defensible, source-backed authorization chain for the project’s intended research and AI/ML scope.

## 8. Minimal human action required

The minimal next step is a human review or written authorization check to establish one of the following:

1. a definitive Bitstamp data-use policy or agreement covering historical BTC/USD data for the exact research scope;
2. a clear written permission for private AI/ML model development, training, and validation on the dataset;
3. or a separate, documented, approved BTC/USD source contract with preserved provenance.

If no such permission is identified, the project should keep the BTC/USD source unqualified and continue with no strategy or model work.

## 9. Files inspected and created

**Created:**
- `research/v31_9_btcusd_source_decision.md`

**Inspected as evidence:**
- `data/raw/btcusd_1-min_data.csv`
- `api/market_drivers.py`
- `research/v31_2_dataset_options_assessment.md`
- `research/v31_2_blocker_resolution.md`
- `research/v31_7_binance_btcusdt_1m_contract.md`
- `research/v31_8_binance_data_use_gate.md`

**Preserved without alteration:**
- all prior historical reports and Coinbase/Binance records
- no protected ledger files were modified

No strategy logic, experiments, adapters, collectors, live behavior, or protected ledger entries were changed.
