# BTCognitive V32.5 — Provisional College-Project Continuation Without Qualified BTC/USD Source

**Date:** 2026-10-23  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Status:** Research-only governance path for continued software and prototype work while the BTC/USD source-rights question remains unresolved.

## 1. Purpose

This note resolves the practical tension between:
- the project’s strict source-governance rules, and
- the reality that the project is being used as a college prototype and must keep moving.

The important point is not to pretend the local BTC/USD dataset is fully cleared. The goal is to separate:

1. software development and app validation,
2. provisional exploratory research, and
3. formal source approval.

This is a controlled, documentable continuation path, not a claim of legal clearance.

## 2. Current verified position

The local dataset at `data/raw/btcusd_1-min_data.csv` is technically coherent:
- 1-minute OHLCV structure,
- continuous timestamps,
- no nulls,
- no duplicate timestamps,
- valid OHLC relationships,
- and a coherent hash and manifest record.

That supports the artifact’s technical integrity.

However, the repo’s earlier investigation still shows an unresolved governance blocker:
- the exact Kaggle version linkage remains unverified,
- the external public dataset page does not independently confirm the exact local CSV version,
- the source-rights chain from the underlying Bitstamp historical data to the public Kaggle artifact is not confirmed in writing,
- and the project cannot verify that all intended AI/ML uses are covered by the applicable rights.

Therefore the correct operational position remains:

- `BLOCKED — VERSION, PROVENANCE, OR RIGHTS UNRESOLVED` for formal BTC/USD research qualification.
- `BLOCKED — AI/ML PERMISSION OR RIGHTS UNRESOLVED` for private model-development use.

This does not mean the project must stop working entirely. It means the project must avoid claiming final research validity.

## 3. Practical path for a college prototype

The project may continue under a clear provisional policy:

### 3.1 Allowed work
- frontend and backend fixes,
- app health and regression verification,
- API and research-terminal validation,
- strategy engine scaffolding,
- feature work and code quality improvements,
- synthetic or internally generated test data for software validation,
- internal exploratory analysis using the existing local dataset, provided that it is marked provisional.

### 3.2 Not allowed under this provisional path
- claiming final performance validation,
- claiming final BTC/USD source qualification,
- publication of comparative strategy results as definitive evidence,
- commercial distribution or production deployment,
- redistributing the local dataset or externally republishing it,
- live trading, execution, or operational money deployment.

### 3.3 Required documentation
Every provisional result should clearly state:
- the source is local and historically archived,
- the exact file hash and dataset reference are recorded,
- the rights chain remains unresolved,
- the result is provisional and exploratory only,
- no production, commercial, or final research claim is being made.

## 4. Risk posture

This is not a legal clearance. It is a disciplined engineering posture.

The project should treat the local data as:
- usable for prototype software development,
- valid for internal testing and research application logic,
- unsuitable for formal comparative claims until the upstream-rights and version-linkage gate is resolved in writing.

This is the safest way to keep momentum without making unsupported claims.

## 5. Recommended workflow for this repo

### Phase A — Continue software engineering
- fix application defects,
- improve stability, contracts, and status logic,
- keep the research terminal and API hardened,
- preserve the analysis-only guardrails.

### Phase B — Keep data governance separate
- maintain a separate source-governance record,
- keep BTCUSDT retired from active consideration,
- record the unresolved BTC/USD rights question as a distinct blocker.

### Phase C — Only make qualified claims once approved
- A final research claim requires writer confirmation from the relevant dataset owner or rights holder,
- and a documented source lineage with version and permission checks.
- Until then, results remain provisional.

## 6. Final project decision

For the current college-project posture, the correct call is:

- `PROVISIONAL CONTINUATION ALLOWED`
- `FORMAL BTC/USD QUALIFICATION: BLOCKED`
- `LIVE TRADING: DISABLED`
- `COMMERCIAL/PRODUCTION USE: NOT APPROVED`

This keeps the project moving without violating the research-only and source-governance requirements.

## 7. Remaining human action required

The remaining blocker is not a code problem; it is a rights/provenance issue. A human must do the following:

1. obtain written confirmation from the Kaggle dataset owner confirming the exact version identity and lineage of the local CSV,
2. verify whether the local file corresponds to the public dataset version represented by the repository claim,
3. obtain a documented statement from Bitstamp or the relevant rights holder regarding non-commercial historical BTC/USD research and private AI/ML model-development use,
4. confirm whether the license and data-use terms are sufficient for the project’s intended scope.

Until that is done, the repo may continue internally under a provisional, documented research-only posture, but it cannot claim a qualified BTC/USD source for final quantitative or AI/ML work.

## 8. Evidence summary

The repo already contains the technical evidence and governance record showing:
- local BTC/USD file integrity is good,
- source provenance is unresolved,
- license terms are not enough by themselves to guarantee all upstream rights,
- the project must remain analysis-only and provisional until written permission is verified.

This is the correct balance for a student project: keep building, but keep the data-risk status honest.
