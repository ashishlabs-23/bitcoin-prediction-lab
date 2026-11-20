# BTCognitive V32.0 — BTC/USD License and Provenance Decision

**Date of decision:** 2026-10-23  
**Scope:** source qualification only; no dataset downloads, no ingestion, no experiments, no strategy validation, no runtime changes.

## 1. Decision

**Outcome:** `BLOCKED — VERSION, PROVENANCE, OR RIGHTS UNRESOLVED`

**Qualified for specified BTC/USD research scope:** `NO`

**AI/ML model development support:** `UNRESOLVED / NOT QUALIFIED`  
**Commercial use or production approval:** `NOT APPROVED`

The existing local `data/raw/btcusd_1-min_data.csv` is technically coherent and appears to match a Bitstamp-derived BTC/USD 1-minute OHLCV archive, but the evidence chain is incomplete. The project cannot establish the exact Kaggle dataset version used locally, the exact source-version provenance, or the governing Bitstamp data-use terms for the intended research and AI/ML use.

## 2. Evidence reviewed

### 2.1 Local artifact
- **Path:** `data/raw/btcusd_1-min_data.csv`
- **Observed header:** `Timestamp,Open,High,Low,Close,Volume`
- **Observed sample rows:**
  - `1325376060,4.58,4.58,4.58,4.58,0.0`
  - `1325376120,4.58,4.58,4.58,4.58,0.0`
  - `1325376180,4.58,4.58,4.58,4.58,0.0`
  - `1325376240,4.58,4.58,4.58,4.58,0.0`
- **Repository manifest evidence:** `research/entry_tp_sl/data_intake_manifest.json` and `research/entry_tp_sl/dataset_manifest.template.json`
- **Manifested size:** 393,952,273 bytes
- **Manifested file hash:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- **Declared version in local repo manifest:** `Kaggle Bitstamp BTC/USD 1-Minute Historical Data (v745)`
- **Local manifest notes:** `rights_status: REVIEW_REQUIRED`, `timestamp_contract_status: VERIFIED_MONOTONIC_UNIX_SECONDS_UTC`, `approved_for_research: true` (but this is a local repo assertion, not proof of legal permission)

### 2.2 Kaggle dataset page
- **URL:** `https://www.kaggle.com/mczielinski/bitcoin-historical-data/data`
- **Access date:** 2026-10-23
- **Observed dataset description:** the page states the dataset is `Bitcoin Historical Data` and includes `btcusd_1-min_data.csv`.
- **Observed metadata:** the page states the dataset is licensed under `CC BY-SA 4.0` and identifies the uploader as mczielinski.
- **Observed source description:** the page and repository text state the data was collected from Bitstamp and updated from the Bitstamp API.
- **Important version mismatch:** the Kaggle page metadata indicates a current dataset version number of `759` in the download URL, while the repository manifest identifies a local version `745`.

### 2.3 Original source repository
- **URL:** `https://github.com/mczielinski/kaggle-bitcoin`
- **Access date:** 2026-10-23
- **Observed repository description:** the repo states it automatically fetches missing days from the Bitstamp API and reuploads the dataset to Kaggle daily.
- **Observed evidence:** the repository expressly says the updater script downloads the existing Kaggle dataset, fills missing rows from Bitstamp, and reuploads the result.
- **Material limitation:** this is evidence that the dataset is updated from Bitstamp and then republished, but it does not establish that the dataset uploader had a complete right to sublicense the exchange data under a specific research or AI/ML model-development use case.

### 2.4 Official Bitstamp API and legal channel
- **API base:** `https://www.bitstamp.net/api/`
- **Access date:** 2026-10-23
- **Observed result:** the Bitstamp API is reachable and exposes public market data endpoints, including the BTC/USD OHLCV endpoint.
- **Legal page result:** `https://www.bitstamp.net/legal/terms-of-use/` returned a minimal HTML shell with no substantive legal terms content in this environment.
- **Conclusion:** the legal permission question remains unresolved because the relevant Bitstamp terms were not successfully retrieved as authoritative, content-bearing documentation in this task.

### 2.5 CC BY-SA 4.0
- **URL:** `https://creativecommons.org/licenses/by-sa/4.0/`
- **Access date:** 2026-10-23
- **Observed conditions:** attribution and share-alike are required for adapted material; the page also states the license may not give all permissions needed for a particular use and that other rights may limit use.
- **Important caveat:** the CC BY-SA 4.0 label is not the same as a legal conclusion that the uploader possessed all necessary rights to the underlying exchange data or to sublicense it for all downstream uses.

## 3. Artifact identity and technical coherence

### 3.1 Technical integrity
The local CSV is internally coherent and has the expected structure for a BTC/USD OHLCV dataset:

- 1-minute interval
- Unix timestamp field
- open/high/low/close/volume columns
- monotonic and non-null values in the inspected rows
- file is consistent with the repo’s dataset-manifest declarations

This supports artifact identity and local coherence, but it does not resolve legal rights or exact provenance.

### 3.2 Provenance gap
The evidence currently supports that:

- the local file is a Bitstamp-derived BTC/USD 1-minute archive;
- the current Kaggle page labels the dataset `btcusd_1-min_data.csv` and the data as Bitstamp-derived;
- the repo updater script confirms the dataset is refreshed by pulling Bitstamp data and reuploading to Kaggle;

But the evidence does not support a definitive chain to the exact local file version in the repo because:

- the local manifest records version 745;
- the current Kaggle page metadata shows version 759;
- there is no hash comparison to the current Kaggle artifact in the repository;
- there is no authoritative Bitstamp terms record in this environment that states the legal status for AI/ML or derived model use.

This is the decisive provenance gap.

## 4. License and rights analysis

### 4.1 Kaggle license
The Kaggle page explicitly states `CC BY-SA 4.0` for the dataset. That is a real and specific license fact. It gives a clear base license for the published dataset under the platform’s metadata.

However, the license is insufficient to prove the following without further evidence:

- that the uploader had all rights needed to redistribute the underlying exchange data;
- that the dataset is valid for any and all AI/ML research uses;
- that the project may use derivative models or adapted data without additional human review;
- that the local file exactly matches the version currently displayed by Kaggle.

### 4.2 Bitstamp rights / downstream use
The project has not recovered an authoritative, substantive Bitstamp data-use policy for this exact dataset and use case. The official legal page was inaccessible in this environment, and the repo does not contain a verified legal permission record for the exact file and intended use.

Therefore, the rights question remains unresolved. This is not a dismissal of the dataset as a technical artifact; it is a blocker on legal-use qualification.

## 5. Decision gates

| Gate | Status | Evidence | Notes |
|---|---|---|---|
| Artifact identity | PASS | Local file exists, has expected OHLCV columns and sample entries; repo manifest matches size and source naming | This confirms technical coherence, not legal permission |
| Kaggle license | PASS (limited) | Kaggle page states `CC BY-SA 4.0` | License exists but does not solve upstream rights or AI/ML use |
| Source provenance | BLOCKED | Local manifest says version 745; current Kaggle page metadata says version 759; no exact hash match to current public artifact | Material version gap |
| Bitstamp data-use terms | UNRESOLVED | Official legal page not successfully retrieved; no authoritative data-use statement in repo | Cannot establish permission for AI/ML work |
| Historical research support | UNRESOLVED | Non-commercial historical research may be supported by the dataset metadata, but not proven with a complete rights chain | Human review still required |
| AI/ML support | BLOCKED | No direct written permission or explicit license carve-out for AI/ML development or model-training use on this dataset | Needs explicit permission or legal review |
| Commercial use | BLOCKED | No explicit commercial approval and no complete rights chain | Not approved |

## 6. Final decision

**`BLOCKED — VERSION, PROVENANCE, OR RIGHTS UNRESOLVED`**

### Why this is the correct decision
1. The local file is coherent and appears to be a valid Bitstamp BTC/USD 1-minute dataset.
2. The Kaggle dataset page and repo do show a public CC BY-SA 4.0 dataset path and a Bitstamp-derived provenance chain.
3. The unresolved issue is not whether the file is technically valid; it is whether the exact artifact/version, its upstream rights, and its legal-use status are sufficient for BTCognitive’s intended non-commercial research and AI/ML use.
4. The current evidence does not support that conclusion.

This means the project cannot qualify the local BTC/USD dataset as an approved research input without additional human review and source-specific permission evidence.

## 7. Remaining blockers and human action

### Remaining blockers
- **Exact version linkage:** local repo manifest says version 745; current Kaggle page shows version 759.
- **Missing upstream rights evidence:** no authoritative Bitstamp terms record or written permission was recovered for this exact dataset and scope.
- **AI/ML permission gap:** no explicit permission for private AI/ML model development, training, or validation is established.

### Human action required
A human reviewer should obtain or verify:

1. the exact Kaggle version used in the repo and the matching hash for that exact dataset file;
2. the relevant Bitstamp terms for the specific dataset and research use;
3. whether a separate written permission expressly covers AI/ML training, model development, or private analytical outputs derived from the dataset;
4. whether the project’s intended use remains within a non-commercial research-only scope or extends beyond it.

Until that is complete, the dataset remains unqualified.

## 8. Files inspected

- `data/raw/btcusd_1-min_data.csv`
- `research/entry_tp_sl/data_intake_manifest.json`
- `research/entry_tp_sl/dataset_manifest.template.json`
- `research/v31_9_btcusd_source_decision.md`
- `research/v31_2_dataset_options_assessment.md`
- `research/v31_2_blocker_resolution.md`

## 9. Preservation and no-experiment confirmation

No strategy logic, adapters, collectors, runtime manifests, live behavior, or protected ledgers were modified. No experiments, backtests, model-training runs, or dataset replacement operations were performed.
