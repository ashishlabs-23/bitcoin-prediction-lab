# BTCognitive V32.2-R — BTC/USD Dataset Resolution

**Date:** 2026-10-23  
**Scope:** read-only resolution of the existing BTC/USD dataset provenance and use-question. No data download, replacement, ingestion, model training, backtests, strategy changes, source swaps, or live behavior changes.

## 1. Scope and non-modification statement

This report resolves as much as possible of the local `data/raw/btcusd_1-min_data.csv` provenance and permitted-use question while preserving the repository exactly as it is.

The investigation was limited to:
- local file inspection,
- repository metadata inspection,
- public-source review of the dataset page, source repository, and primary data provider pages,
- and explicit separation of what is technically verifiable from what requires human-written confirmation.

No experiment, no training run, no replay, no strategy modification, no source replacement, and no release change were performed.

## 2. Local artifact: exact technical facts

### 2.1 File identity
- **Path:** `data/raw/btcusd_1-min_data.csv`
- **Observed size:** `393,952,273` bytes
- **Observed SHA-256:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- **Header:** `Timestamp,Open,High,Low,Close,Volume`
- **Row count:** `7,766,111`
- **First timestamp (Unix seconds):** `1325376060` -> `2012-01-01 00:01:00+00:00`
- **Last timestamp (Unix seconds):** `1791342660` -> `2026-10-07 03:11:00+00:00`
- **Null count:** `0`
- **Duplicate timestamps:** `0`
- **Timestamp step size:** `60` seconds for all consecutive timestamps
- **Timestamp monotonicity:** increasing and continuous at 1-minute cadence
- **OHLC sanity:** `True` (all high values >= open/close and low values <= open/close)

This is a coherent, high-integrity BTC/USD OHLCV archive at 1-minute frequency. It is technically valid as a local data artifact.

### 2.2 Local repository metadata
The local repository manifest states:
- `research/entry_tp_sl/data_intake_manifest.json`
- dataset name: `Kaggle Bitstamp BTC/USD 1-Minute Historical Data (v745)`
- dataset source URI: `https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data`
- license: `CC BY-SA 4.0`
- `sha256`: `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- `source_upstream`: `Bitstamp BTC/USD spot OHLCV API (per publisher's updater repository)`
- `rights_status`: `APPROVED_BY_USER_CC_BY_SA_4.0`

The manifest is internally consistent with the local file hash and file size. However, that metadata is still not independent proof of exact upstream rights or exact version linkage.

### 2.3 Git provenance
The file does not show tracked git history for that local object in this repository state. `git log -- data/raw/btcusd_1-min_data.csv` produced no history entries in the active working tree. That means:
- the repository cannot independently prove the original download event,
- the project cannot prove which Kaggle version was originally pulled,
- and the file creation time or manifest assertion alone is not a legal or provenance proof.

## 3. Version linkage: what can and cannot be verified

### 3.1 Local claim: version 745
The repository manifest is explicit that the local file corresponds to version `745` and that the file size matches `393,952,273` bytes.

This is the strongest local evidence for version linkage, but it is still a local assertion, not an independently verified external Kaggle version record.

### 3.2 Public Kaggle page review
The current public Kaggle dataset page at:
- `https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data/data`

was inspected in this environment. The accessible HTML snapshot did not expose a stable, machine-readable public version value in a way that could be independently checked as a definitive identifier here. The public page returned only the dataset title text (`Bitcoin Historical Data | Kaggle`) and did not provide a reliable version number in the accessible snapshot.

Because of that, the project cannot claim a definitive current public Kaggle version from the page alone. The earlier version claim of `759` is therefore not repeated as verified evidence here unless a reliable historical source specifically supports it.

### 3.3 Version linkage gate
**Version-linkage gate:** `UNVERIFIED`

Reason:
- local metadata says version `745`;
- the public Kaggle page in this environment does not yield a reliable version identifier in a verifiable way;
- no independent checksum or version manifest tied to the exact external Kaggle archive was retrieved;
- there is no authoritative git or download-log record for the exact external object.

This means the project cannot independently confirm that the current local CSV is the exact external Kaggle version labeled `745`, or that it corresponds to any other specific version.

## 4. License and upstream-rights analysis

### 4.1 Kaggle dataset licensing
Primary source reviewed:
- Kaggle dataset page: `https://www.kaggle.com/datasets/mczielinski/bitcoin-historical-data/data`
- Creative Commons BY-SA 4.0: `https://creativecommons.org/licenses/by-sa/4.0/`

The public CC BY-SA 4.0 deed states that the material may be shared and adapted for commercial and non-commercial purposes, subject to:
- attribution,
- share-alike obligations for adapted material,
- and no additional restrictions.

The CC BY-SA deed also explicitly states:
> "The license may not give you all of the permissions necessary for your intended use. For example, other rights such as publicity, privacy, or moral rights may limit how you use the material."

This is important. The existence of a dataset license does not, by itself, prove that the uploader had every necessary upstream right to the underlying exchange data or that every downstream use case is covered.

### 4.2 Upstream source repo
Primary source reviewed:
- `https://github.com/mczielinski/kaggle-bitcoin/`

The repo description confirms that the publisher automates a daily process:
1. download the existing Kaggle dataset,
2. identify missing days,
3. fetch missing BTC/USD OHLCV data from the Bitstamp API,
4. merge and re-upload the updated dataset to Kaggle.

This supports the technical origin story: the dataset is Bitstamp-derived.

It does not prove:
- that the uploader had a right to redistribute the underlying exchange data for all downstream uses,
- that the exact local file is legally approved for AI/ML model development,
- or that the dataset license is automatically sufficient for every use case.

### 4.3 Bitstamp API and terms
Primary sources reviewed:
- `https://www.bitstamp.net/api/`
- `https://www.bitstamp.net/legal/terms-of-use/`

Observed facts:
- Bitstamp’s public API is reachable and serves market data endpoints. This demonstrates public access to data through the exchange API.
- The Bitstamp legal terms page was not retrievable in this environment; the request failed with a transport-level failure, so we do not claim an authoritative text excerpt from that page here.

Therefore:
- public API access alone is not equal to a written permission for private AI/ML development,
- and the exact Bitstamp restrictions for this specific dataset/use case are not conclusively resolved from the pages available in this environment.

## 5. Separate decisions: research vs AI/ML

### 5.1 Historical quantitative research
**Decision:** `BLOCKED — VERSION, PROVENANCE, OR RIGHTS UNRESOLVED`

Why:
- the local artifact is technically coherent,
- the dataset is Bitstamp-derived and publicly linked to Kaggle,
- but exact version linkage to a specific public Kaggle version remains unverified,
- and the legal chain from the exchange data to the local file and future use remains not definitively established.

This is a governance block, not a technical data-quality failure.

### 5.2 AI/ML feature engineering, model development, training, validation
**Decision:** `BLOCKED — AI/ML PERMISSION OR RIGHTS UNRESOLVED`

Why:
- the dataset license is not enough by itself to prove all upstream rights for use in private AI/ML development,
- the exact Bitstamp permission for historical BTC/USD OHLCV data in AI/ML workflows is not authoritatively established here,
- and the exact Kaggle version lineage remains unverified.

This is the correct blocked state even though the file is technically valid and publicly accessible.

## 6. Gate table

| Gate | Status | Evidence | Conclusion |
|---|---|---|---|
| Local file integrity | PASS | File exists, consistent header, 1-minute cadence, zero nulls, zero duplicates, monotonic timestamps | Technical integrity is good |
| Local file/hash match to manifest | PASS | Manifest hash equals local file SHA-256 | Internal repo metadata matches local file |
| Exact public Kaggle version linkage | UNVERIFIED | Local manifest says v745; public Kaggle page data accessible here did not expose a stable version ID; no external checksum match | Version linkage not proven |
| CC BY-SA dataset license status | PASS (limited) | CC BY-SA 4.0 is publicly stated on the Kaggle dataset and the deed is available | License exists, but not sufficient to prove all upstream rights |
| Upstream equity / permission to redistribute exchange data | UNVERIFIED | Bitstamp origin is publicly described; legal terms not retrievable in this environment | Upstream rights remain unresolved |
| Historical quantitative research | BLOCKED | Technical validity exists but provenance and rights remain unresolved | No qualified research scope |
| Private AI/ML work | BLOCKED | No conclusive written permission or rights chain for model-development use | No qualified AI/ML scope |

## 7. Requests for human clarification (ready to submit through verified official channels)

### Request A — Kaggle dataset owner / uploader
Use only the official Kaggle contact/discussion route associated with the dataset or uploader profile. Do not invent an email address.

**Subject:** Clarification of dataset version and lineage for `btcusd_1-min_data.csv`

**Body:**
> I am reviewing the historical BTC/USD 1-minute dataset `btcusd_1-min_data.csv` associated with the Kaggle dataset `mczielinski/bitcoin-historical-data`. I am seeking written confirmation of the exact version associated with the local file `data/raw/btcusd_1-min_data.csv`, whether it matches version 745 in the repository metadata, the full acquisition/source lineage of the included data, and the basis for applying CC BY-SA 4.0 to the dataset contents. I am asking for confirmation that the dataset is based on Bitstamp BTC/USD 1-minute OHLCV data and whether the specific dataset version and underlying data were legally redistributable under the stated license. I am not asking that the dataset be reissued or modified; I am only seeking authoritative confirmation of version identity, provenance, and licensing basis before any research or model-development use.

### Request B — Bitstamp
Use only an official Bitstamp legal/support contact route that is publicly listed on Bitstamp’s site. Do not invent a contact address.

**Subject:** Written clarification on historical BTC/USD OHLCV data use for research and private AI/ML development

**Body:**
> I am seeking written clarification on whether the historical BTC/USD OHLCV data provided through Bitstamp’s public market data and historical archive services may be used for non-commercial quantitative research and for private AI/ML feature engineering, model development, training, and evaluation. The intended use is limited to personal or academic research, with no live execution, no compensation, no third-party signal distribution, no commercial product launch, and no production deployment. I am requesting confirmation of the exact scope permitted by the applicable terms for this historical BTC/USD OHLCV data, including whether additional written authorization or a separate enterprise license is required for private model development or model evaluation. I am also seeking clarity on attribution, redistribution, and any downstream rights or restrictions for derived metrics or analytical outputs.

These requests are drafted for manual submission through official channels only. They were not sent.

## 8. Remaining human action

The exact blocker is not a programming error or data corruption. The blocker is a missing rights and provenance chain:
- exact external Kaggle version identity,
- exact match between the local file and the external file version,
- and a clear written statement on the legal scope for private AI/ML work on historical Bitstamp BTC/USD OHLCV data.

The minimal required human action is:
1. obtain a written confirmation from the Kaggle dataset owner/uploader that the local artifact corresponds to version 745 or to another exact version;
2. obtain a written statement from Bitstamp or a verified legal contact confirming the scope for non-commercial research and private AI/ML training/evaluation on historical BTC/USD OHLCV data;
3. keep the dataset in a blocked state until that permission is confirmed.

## 9. College-project posture (practical guidance)

For a college project, the safest practical posture is:
- treat the dataset as a technical research artifact only,
- do not claim that the file is approved for private AI/ML model development,
- do not distribute the CSV beyond the project as a licensed artifact without confirming rights,
- and keep the work in a documentation-only, non-production, non-commercial research state until written permission or a clear legal basis is available.

This is the correct posture until explicit written permission is obtained.

## 10. Final status

**Historical quantitative research:** `BLOCKED — VERSION, PROVENANCE, OR RIGHTS UNRESOLVED`  
**AI/ML use:** `BLOCKED — AI/ML PERMISSION OR RIGHTS UNRESOLVED`  
**No experiment or source replacement performed:** `CONFIRMED`  
**No live or production activation performed:** `CONFIRMED`

The remaining unresolved questions are not software issues. They are provenance and rights questions requiring written clarification from the dataset owner and the data source provider before the BTC/USD dataset can be qualified for project research or AI/ML use.
