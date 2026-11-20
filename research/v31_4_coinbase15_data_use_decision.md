# BTCognitive V31.4 — Coinbase 15m Data-Use Decision

**Decision:** `NOT AUTHORIZED FOR BTCognitive AI/ML USE — WRITTEN AUTHORIZATION NOT VERIFIED`

## 1. Result

The local Coinbase BTC-USD 15-minute artifact can be technically validated and isolated, but it cannot be treated as authorized for BTCognitive AI/ML research use under the currently applicable Coinbase Market Data Terms. The repository does not contain evidence of express written consent for the exact artifact and intended use.

## 2. Governing evidence

### Official source references
- `https://www.coinbase.com/legal/market_data_terms`
- `https://docs.cloud.coinbase.com/exchange/reference/`
- Access date for this environment: **2026-10-23**
- Revision date of the market-data terms (as provided in the task prompt): **2026-08-07**

### Relevant rule stated in task prompt
- **Section 3.5:** Market Data may not be used for AI/ML model, algorithm, or automated-system research, development, validation, benchmarking, improvement, or operation without prior express written consent.

### Environment note
- Automated fetches to Coinbase’s legal pages were blocked (`403 Forbidden` / `404` when proxied), so this environment could not directly render the page text. The decision therefore relies on the explicit task prompt’s summary of the governing clause and the local repository evidence, not on a fetched legal page snapshot.

## 3. Repository evidence for the intended use

The repo contains several research/AI and forecasting contexts that would be restricted if the dataset were used for model research or automated-system experimentation:

- `api/routes_arena.py` contains AI Experiment Arena endpoints and experimental analytics context.
- `api/market_drivers.py` is a market-data driver used by research paths.
- `docs/BTCognitive_PRD_Traceability_Matrix.md` documents forecasting and model-development requirements and governance context.
- `research/v31_3_coinbase15_contract.md` shows this dataset was intentionally isolated as a valid local artifact, but not as a broad-use permission.

This evidence is static; it does not prove that the repo was authorized to use the data for AI/ML study.

## 4. Evidence against authorization

The following evidence was not found in the repository:

- no express written authorization from Coinbase for this exact artifact and intended use;
- no separate data-use agreement;
- no repo-local permission record covering AI/ML model research, validation, benchmarking, or automated-system use;
- no evidence that the exact use case was separately reviewed and approved.

This absence is not proof that no permission exists, but it is proof that no such permission is currently established in this codebase or local artifact record.

## 5. Technical validity does not create permission

The technical validation of the artifact remains valid:

- artifact path: `data/raw/coinbase_15m.parquet`
- SHA-256: `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`
- local manifest: `data/raw/coinbase_15m_manifest.json`
- structure: 9000 rows; consistent 15-minute cadence; 0 duplicate timestamps; 0 gaps; 0 nulls

However, technical validity is separate from rights and permission. The applicable market-data terms restrict AI/ML research use without prior express written consent. Without that consent, the repository cannot treat the artifact as authorized for the intended use.

## 6. Final decision

`NOT AUTHORIZED FOR BTCognitive AI/ML USE — WRITTEN AUTHORIZATION NOT VERIFIED`

The local Coinbase 15m artifact may remain isolated as a technical artifact for separate review, but it is not authorized for BTCognitive AI/ML model research, forecasting, benchmarking, or automated-system use absent a separate human-reviewed written authorization.

## 7. Remaining human action

A qualified human reviewer must determine whether a written Coinbase authorization exists for the exact artifact and scope. Until then, the data remains quarantined from the repository’s AI/ML research paths and the project should not proceed with any broader model-development or validation use of the Coinbase dataset.

## 8. Files created and unchanged behavior

**Created:**
- `research/v31_4_coinbase_terms_compatibility_report.md`
- `research/v31_4_coinbase15_data_use_decision.md`

**Unchanged:**
- no strategy logic;
- no replay or tournament code execution;
- no collector or live behavior changes;
- no protected ledger modifications.
