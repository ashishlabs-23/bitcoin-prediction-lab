# BTCognitive V31.7 — Binance BTCUSDT 1m Source Contract

**Date of source-selection record:** 2026-10-23  
**Scope:** controlled source-contract record only. No experiments, training, validation, replay, backtests, adapter implementation, collector changes, or live behavior were run.

## 1. Coinbase retirement status

**Coinbase BTC-USD 15-minute dataset status:** `QUARANTINED AND RETIRED FROM ACTIVE CANDIDATE CONSIDERATION`

This is a governance-only retirement. The local artifact and historical evidence remain preserved exactly as-is for audit continuity:

- `data/raw/coinbase_15m.parquet`
- `data/raw/coinbase_15m_manifest.json`
- all prior V31.x Coinbase reports

The Coinbase path is not deleted, relabeled, or treated as a valid active candidate for BTCognitive AI/ML research because the current official Coinbase Market Data Terms still restrict AI/ML and automated-system use without prior express written consent. No source-use permission was located that covers the BTCognitive scope.

This retirement is not a rewrite of history. It is a formal quarantine and removal from the active selection list without altering the original evidence trail.

## 2. Selected alternative candidate

**Selected source:** Binance Vision public market data  
**Venue:** Binance  
**Market:** Spot  
**Instrument:** BTCUSDT  
**Interval:** 1 minute  
**Purpose:** separate historical, non-commercial research only  
**Status:** `SELECTED CANDIDATE — NOT YET APPROVED FOR EXPERIMENTS`

### Official source references
- Terms: `https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md`
- Repository: `https://github.com/binance/binance-public-data`
- Archive: `https://data.binance.vision/`
- Access date: 2026-10-23
- Revision date stated in the official terms: `Last Updated: August 26, 2026`

## 3. Applicable official terms

The Binance Vision terms are the governing primary-source documentation for the selected alternative path.

### Relevant conditions
The official terms state that the datasets are subject to the Vision Dataset Terms and Binance Terms of Use, and that access/use indicates agreement to those terms. The primary clause structure is:

- Section 3: non-commercial license grant under `CC BY-NC-SA 4.0`
- Section 4: scope of non-commercial use and express prohibitions
- Section 3.4: commercial licensing is excluded and requires separate written enterprise data license agreement
- Section 4.1: permitted non-commercial use includes academic research, non-monetized educational projects, personal non-production historical backtesting, and non-commercial open-source data science evaluation
- Section 4.2: no live proprietary trading execution, automated commercial order generation, or compensation-based signal distribution
- Section 4.3 and 4.4: no commercial exploitation or commercial product integration
- Section 4.5: redistributed derivative works must provide attribution and retain identical CC BY-NC-SA 4.0 licensing

### License-scope decision
**Current decision:** `SELECTED CANDIDATE — NON-COMMERCIAL RESEARCH ONLY`

This candidate is acceptable only for a separate, non-commercial historical research path. It remains outside the scope of:

- live trading or direct execution
- commercial product use
- paid signal or subscription distribution
- any production deployment or operational automation
- any AI/ML or model-training use unless a separate human review confirms that the intended use sits inside the terms’ non-commercial research permission

### AI/ML boundary
The terms do not expressly grant a blanket AI/ML training or model-validation license. Because the project is a research prototype and not a retail or commercial product, this decision must remain strict: if the intended use expands into AI/ML experimentation, benchmarking, development, or model improvement beyond the original non-commercial research scope, the gate is:

**`BLOCKED — HUMAN LICENSE REVIEW REQUIRED`**

This is the governing boundary until a separate written permission or enterprise license is reviewed.

## 4. Contract definition

### 4.1 Contract identity
- **Provider:** Binance
- **Market:** Spot
- **Instrument:** BTCUSDT
- **Interval:** 1 minute
- **Purpose:** separate historical non-commercial research only
- **Data access source:** public archive from the official Binance Vision repository and data portal
- **Instrument warning:** BTCUSDT is not BTC-USD and is not interchangeable with BTC-USD-specific assumptions, thresholds, strategy framing, or downstream metrics without a separate contract and human approval

### 4.2 Source provenance requirements
Before any future ingestion or use, the project must preserve the following evidence for the selected archive:

- official source URL and repository hash or archive provenance
- exact dataset file name, daily/monthly archive path, and interval
- date range and symbol metadata
- timezone and timestamp meaning for the file being used
- coverage and gap checks
- attribution and license preservation record
- a note that this is a Binance Spot BTCUSDT dataset, not a BTC-USD dataset

### 4.3 Timestamp semantics required
The selected contract must explicitly document:

- whether the 1-minute bars are open-time, close-time, or bucket-closed timestamps
- the timezone convention used by the archive file
- whether the archive is treated as a complete historical dataset or a specific locally downloaded slice
- whether any upstream data corrections or archive replacement events affect the financial interpretation

No timestamp assumptions may be imported from Coinbase or any other venue without re-documenting the source semantics.

### 4.4 Integrity checks required before future ingestion
A future ingestion path for this candidate must include at least:

- file identity and checksum verification
- row count and interval consistency checks
- duplicate detection
- gap detection and null detection
- order verification by timestamp ascending
- symbol and market metadata verification
- explicit distinction between BTCUSDT and BTC-USD in all stored metadata and docs

### 4.5 Licensing and attribution obligations
The contract must preserve:

- `CC BY-NC-SA 4.0` licensing semantics as the rule for the archival dataset
- attribution to Binance Vision when derivative work is redistributed
- share-alike requirements for derivative datasets or public derivative analytics
- explicit non-commercial restrictions for all uses not approved by a human review

## 5. Exclusions and warnings

This contract must explicitly exclude the following:

- any use of Coinbase 15-minute data as an active candidate for BTCognitive AI/ML work
- any implicit substitution of BTCUSDT for BTC-USD
- any direct rollover of BTC-USD thresholds, assumptions, entry logic, or outcome framing onto BTCUSDT data
- any live or production deployment
- any paid-product or commercial-source use
- any unapproved AI/ML training or benchmarking path beyond the strict, documented non-commercial research scope

## 6. Operational status

**Current operational status:** `HOLD — SOURCE SELECTED, EXPERIMENTS BLOCKED`

This source is selected for a separate, non-commercial research path only. It is not approved for experimentation, training, benchmarking, or model validation until a human review confirms the scope and any necessary permissions.

## 7. Files inspected and created

**Created:**
- `research/v31_7_binance_btcusdt_1m_contract.md`

**Retained as historical evidence without alteration:**
- all existing V31.x Coinbase and prior-source reports
- `data/raw/coinbase_15m.parquet`
- `data/raw/coinbase_15m_manifest.json`

No strategy logic, runtime manifests, collectors, protected ledgers, or live behavior were modified.
