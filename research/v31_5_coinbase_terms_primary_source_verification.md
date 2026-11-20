# BTCognitive V31.5 — Coinbase Terms Primary-Source Verification

**Date of verification:** 2026-10-23  
**Scope:** Source-verification addendum to V31.4 only. No strategy, replay, training, model validation, experimentation, or live behavior was run.

## 1. Sources fetched directly

### 1) Coinbase Market Data Terms of Use
- **URL:** `https://www.coinbase.com/en-in/legal/market_data`
- **Access date:** 2026-10-23
- **Retrieved successfully:** Yes
- **Document title:** `Market Data Terms of Use`
- **Revision date stated on page:** `Last updated: August 7, 2026`
- **Relevant clause location:** Section 3, item 5 of the restrictions list (not labeled as a distinct `Section 3.5` in the page source)

The fetched page states:

> “Absent prior express written consent from Coinbase, you may not: ... 5. Use any Market Data to, or permit or authorize any third party to, in whole or in part, develop, train, fine-tune, teach, validate, benchmark, or otherwise improve any artificial intelligence or machine learning model, algorithm, chatbot, agent, or other automated system, whether generative or non-generative, or for any other purpose related to the research, development, or operation of artificial intelligence technologies.”

This is the clearest primary-source restriction directly relevant to BTCognitive’s AI/ML research use. The source language is broad and clearly applies to AI/ML research and automated-system development or operation without prior express written consent.

### 2) Coinbase Exchange API documentation
- **URL:** `https://main.d39g7xymw2r1c0.amplifyapp.com/exchange/docs/welcome`
- **Access date:** 2026-10-23
- **Retrieved successfully:** Yes
- **Relevant content observed:** The page states that the Exchange APIs are separated into two categories: trading and market data, and that market data APIs are public.

The fetched page did not contain the explicit sentence, “Accessing the Exchange Market Data API subjects you to the Market Data Terms of Use,” in the HTML retrieved from this environment. The page does confirm the public market-data API category, but it does not itself provide the legal permission statement in the retrieved HTML.

## 2. Why earlier fetch attempts failed

Earlier attempts to fetch the path `https://www.coinbase.com/legal/market_data_terms` and similar variants failed with `403 Forbidden` or `404`. Those failed paths are not the verified market-data legal page. The correct verified source is `https://www.coinbase.com/en-in/legal/market_data`.

The V31.4 reports were therefore using the wrong legal-path identifier, not a verified primary source. This V31.5 report corrects that evidence chain without altering the historical V31.4 file content.

## 3. Technical integrity of the local artifact

The local file remains technically coherent and separately valid:

- **Artifact:** `data/raw/coinbase_15m.parquet`
- **Size:** 464,798 bytes
- **SHA-256:** `7fcd61d21a995c251688e6ae687fa1678f0bec7bfb5cf08ea87f5ebb6f9d1091`
- **Manifest:** `data/raw/coinbase_15m_manifest.json`
- **Observed checks:** 9000 rows, 15-minute cadence, no duplicates, no gaps, no nulls

This speaks to data integrity and local source identity only. It does not establish legal permission for AI/ML use.

## 4. Current published restrictions on use of Coinbase Market Data

The direct primary-source restriction is clear and operationally important:

- Coinbase Market Data is governed by the Market Data Terms of Use.
- The page states the terms were last updated August 7, 2026.
- Section 3, item 5 prohibits use of Market Data to develop, train, fine-tune, teach, validate, benchmark, or otherwise improve AI/ML models, algorithms, agents, or automated systems without prior express written consent.
- This restriction applies to research, development, and operation of AI technologies.

This is materially different from a technical or data-quality statement. It is a use restriction.

## 5. Acquisition date and applicable terms

The exact acquisition history and terms applicability for this local artifact remain only partly known:

- The local manifest records a creation timestamp for the file: `2026-10-23T14:24:40.311095+00:00`.
- This demonstrates the artifact exists locally and was written in the repo on that date.
- It does not prove the exact external acquisition date, the governing-version terms at the moment of acquisition, or whether any separate permission existed outside the repository.

The repository does not show a separate data-use agreement or written consent for this exact artifact and the intended BTCognitive AI/ML use. That gap remains unresolved.

## 6. Whether written authorization was located

The repository does not contain a separate Coinbase authorization, agreement, or written consent covering the exact local artifact and the intended AI/ML use. No such evidence was located in the workspace or the local artifact metadata.

This means:

- The source restriction is directly supported by primary-source evidence.
- The authorization exception has not been established in this repository or by the direct source verification performed here.
- The conclusion is not a definitive legal opinion that no external permission exists; it is a documented operational hold because the relevant permission is not established in the available evidence.

## 7. Operational decision

**Operational hold decision:** `NOT AUTHORIZED FOR BTCognitive AI/ML USE — WRITTEN AUTHORIZATION NOT VERIFIED`

This remains the correct operational decision because:

1. The current Coinbase Market Data Terms of Use directly prohibit the relevant AI/ML use without prior express written consent.
2. The repo does not contain evidence of such consent for this exact artifact and intended scope.
3. The exact external acquisition record or any separate prior written consent may exist outside the repo, but it is not established here.
4. The dataset remains quarantined from AI/ML research, training, validation, benchmarking, and automated-system development unless a separately verified written authorization is produced and reviewed.

## 8. Minimal human follow-up

The smallest necessary next step is a human review to locate or request one of the following:

1. a separate Coinbase data-use agreement or written permission covering this exact artifact and the BTCognitive AI/ML use case; or
2. a written confirmation from Coinbase that the proposed use is authorized under a specific scope and terms.

Until that is obtained and reviewed, the practical decision remains: do not use the artifact for AI/ML research, model training, validation, benchmarking, or automated-system development.

## 9. Files inspected and created

**Inspected:**
- `research/v31_4_coinbase_terms_compatibility_report.md`
- `research/v31_4_coinbase15_data_use_decision.md`
- `data/raw/coinbase_15m.parquet`
- `data/raw/coinbase_15m_manifest.json`
- `engine/coinbase_15m_adapter.py`

**Created:**
- `research/v31_5_coinbase_terms_primary_source_verification.md`

No strategy logic, runtime manifests, collectors, protected ledgers, or executable behavior were modified.
