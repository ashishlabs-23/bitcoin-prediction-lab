# BTCognitive V31.4 — Coinbase Market Data Terms Compatibility Report

**Status:** `NOT AUTHORIZED FOR BTCognitive AI/ML USE — WRITTEN AUTHORIZATION NOT VERIFIED`

## 1. Scope and constraints

This report addresses only the data-use question for the local Coinbase BTC-USD 15-minute artifact at `data/raw/coinbase_15m.parquet`. It does not authorize any strategy, replay, tournament, training, or live behavior. No executable behavior was modified, no strategy code was executed, and no protected ledger was touched.

## 2. Official documentation reviewed

The environment could not retrieve Coinbase’s public legal pages directly because automated fetches were blocked with `403 Forbidden` and the direct `market_data_terms` URL returned `404` in the proxied view used for this environment. The repository task therefore uses the authoritative requirement described in the task prompt itself: Coinbase’s current Market Data Terms of Use, last updated **2026-08-07**, include a restriction in **Section 3.5** on using Market Data for AI/ML model, algorithm, or automated-system research, development, validation, benchmarking, improvement, or operation without prior express written consent.

### URLs cited
- `https://www.coinbase.com/legal/market_data_terms` — current Coinbase Market Data Terms page
- `https://docs.cloud.coinbase.com/exchange/reference/` — official Coinbase Exchange API documentation
- Access date from this environment: **2026-10-23**
- Revision date as stated in the task prompt: **2026-08-07**

### Relevant clause interpretation
- **Section 3.5 (as described by the task prompt):** Market Data may not be used for AI/ML model, algorithm, or automated-system research, development, validation, benchmarking, improvement, or operation without prior express written consent.
- This is a restriction on use, not a technical data-quality statement.
- Technical validity of a dataset does not establish legal permission to use it for model work.

## 3. Repository evidence and static map of potential use

The repository contains multiple AI/ML and forecasting paths that would be relevant if Coinbase market data were used beyond a limited, explicitly approved scope.

### Static repository map of relevant references

| File / area | Relevance to data-use question |
|---|---|
| `engine/coinbase_15m_adapter.py` | Defines the exact Coinbase BTC-USD 15m feed and local validation logic |
| `data/raw/coinbase_15m_manifest.json` | Declares the local artifact source and metadata |
| `api/routes_arena.py` | AI Experiment Arena endpoints and research-only strategy analytics |
| `api/market_drivers.py` | Market-data feed access used by research flows |
| `docs/BTCognitive_PRD_Traceability_Matrix.md` | Documents research/forecasting requirements and governance context |
| `research/v31_3_coinbase15_contract.md` | Defines the isolated 15-minute contextual contract |
| `research/v31_3_coinbase15_validation_report.md` | Confirms technical validity and notes the unresolved rights/provenance gate |

### Potential AI/ML / model-development use paths
- Research and forecasting endpoints in `api` and `engine` that consume market data and produce model-style outputs.
- The `AI Experiment Arena` and related experimental routes treat the system as research/analytics, not execution.
- Even if these paths are described as research-only, the Coinbase data-use restriction concerns use in model research, benchmarking, and algorithm development.

This report does not execute those paths. It only statically reads the code to establish the repository’s intended use context.

## 4. Acquisition and provenance status

### Known facts
- The local artifact exists at `data/raw/coinbase_15m.parquet`.
- It is identified as a Coinbase Exchange REST API BTC-USD 15-minute dataset.
- The local manifest says the file was created at `2026-10-23T14:24:40.311095+00:00` and has SHA-256 `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`.
- The file was validated locally for structure, interval consistency, and gap-free continuity.

### Missing or unresolved facts
- No repo-local record shows express written consent from Coinbase for this exact artifact and use case.
- No separate data-use agreement or written authorization file is present in the workspace.
- There is no evidence that the exact repository use case (AI/ML research, validation, benchmarking, or automated-system research) was explicitly approved.
- The environment’s direct legal-page fetches were blocked, so a full authoritative page-text review could not be completed from this environment without relying on the task’s supplied clause summary.

## 5. Technical integrity vs. data-use permission

### Technical integrity decision
- The Coinbase 15-minute artifact is technically coherent and internally consistent.
- It is suitable for a separate, isolated technical validation study.

### Data-use decision
- A technically valid dataset is not sufficient to establish permission for AI/ML research use under the Coinbase restriction.
- Since the object at hand is an AI/ML research project and the relevant terms restrict precisely that use without express written permission, the repository does not have evidence of legal compatibility.

## 6. Decision and evidence

**Decision:** `NOT AUTHORIZED FOR BTCognitive AI/ML USE — WRITTEN AUTHORIZATION NOT VERIFIED`

**Evidence:**
1. The task prompt explicitly identifies the applicable Coinbase market-data restriction in Section 3.5 for AI/ML and automated-system research without express written consent.
2. There is no repository evidence of a written authorization, data-use agreement, or other permission covering this exact artifact and intended use.
3. The repo contains static AI/ML research/forecasting paths that would fall within the described restricted use category.
4. Technical validation alone is not permission.

## 7. Human review needed

This report should be reviewed by a qualified human with authority over contractual, legal, and product-compliance review before any future use is considered. The remaining unresolved action is not technical; it is permissions and contractual scope.

## 8. Explicit prohibitions

- Do not use Coinbase market data in AI/ML model training, validation, benchmarking, or automated research without specific written authorization.
- Do not redistribute this artifact outside an approved scope.
- Do not treat repository technical validity as an authorization.
- Do not expand the isolated 15-minute technical validation into a broader research or model-development path without a separate human-reviewed, written permission.

## 9. Files inspected and created

**Inspected:**
- `data/raw/coinbase_15m.parquet`
- `data/raw/coinbase_15m_manifest.json`
- `engine/coinbase_15m_adapter.py`
- `research/v31_3_coinbase15_contract.md`
- `research/v31_3_coinbase15_validation_report.md`
- `api/routes_arena.py`
- `api/market_drivers.py`
- `docs/BTCognitive_PRD_Traceability_Matrix.md`

**Created:**
- `research/v31_4_coinbase_terms_compatibility_report.md`
- `research/v31_4_coinbase15_data_use_decision.md`

Protected artifacts and executable behavior were left unchanged.
