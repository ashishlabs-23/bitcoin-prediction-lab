# BTCognitive V31.8 — Binance Data Use Gate

**Date:** 2026-10-23  
**Scope:** evidence-based gate status for the selected Binance Vision Spot BTCUSDT 1-minute research candidate. No downloads, experiments, model training, runtime changes, or strategy work were performed.

## 1. Source under review

- **Venue:** Binance
- **Market:** Spot
- **Instrument:** BTCUSDT
- **Interval:** 1 minute
- **Source:** public Binance Vision archive and repository terms
- **Approved for future experiments:** not yet

## 2. Official evidence reviewed

### Primary-source terms
- `https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md`
- Access date: 2026-10-23
- Last updated: August 26, 2026

### Relevant clauses
- **Section 2.4:** all derived data and models are governed by the terms.
- **Section 3.1:** `CC BY-NC-SA 4.0` license for Datasets.
- **Section 3.4:** commercial use requires a separate written enterprise license.
- **Section 4.1:** enumerated permitted non-commercial uses.
- **Sections 4.2-4.5:** restrictions on live trading, commercial exploitation, commercial products, and redistribution obligations.

## 3. Current gate result

**Current status:** `BLOCKED — WRITTEN CLARIFICATION REQUIRED`

### Why it is blocked
The project’s intended use includes possible private AI/ML model development, training, evaluation, and feature engineering for a research prototype. The official terms clearly allow some non-commercial historical research, but they do not expressly and directly confirm that private AI/ML training, benchmarking, or evaluation on the public dataset is permitted under the listed non-commercial scope.

This is not a statement that such use is forbidden. It is a statement that the permission is not yet explicit enough to treat the candidate as approved for experiments.

## 4. Three possible outcomes

### 1) `APPROVED FOR SPECIFIED NON-COMMERCIAL SCOPE`
This would require explicit written confirmation or a sufficiently clear published term that specifically covers the intended model-development, training, and evaluation use on Binance Vision Spot BTCUSDT historical klines.

### 2) `BLOCKED — WRITTEN CLARIFICATION REQUIRED`
This is the current status. The data may still be a valid non-commercial historical source, but the AI/ML and private derivation scope remains ambiguous without written confirmation.

### 3) `REJECTED FOR INTENDED SCOPE`
This would apply if Binance confirms that the intended AI/ML or broader usage is excluded by the terms or requires a separate written enterprise license outside the current research scope.

## 5. Gate decision evidence

- The current public terms support a non-commercial research path.
- The current public terms restrict commercial use and require a separate written license for commercial utilization.
- The terms specifically govern derived data, charts, models, and analytical indicators.
- The current project’s planned AI/ML work is a broader use than simple visualization or purely descriptive historical analysis.
- Because the permission question remains unresolved in writing, the candidate is not approved for experimentation.

## 6. Human action required

The next required action is a written response from Binance or a verified licensing team representative confirming whether the project’s specific intended use is permitted under the official public terms, or whether a separate written enterprise license is required.

Until that written clarification is obtained and reviewed, the selected candidate remains a controlled non-commercial research candidate only, not an approved input for model training or AI/ML experimentation.

## 7. Files inspected or created

**Created:**
- `research/v31_8_binance_data_license_clarification_request.md`
- `research/v31_8_binance_data_use_gate.md`

**Inspected as evidence:**
- `research/v31_7_binance_btcusdt_1m_contract.md`
- official Binance Vision terms and repository documents

No strategy logic, experimental scripts, collectors, runtime manifests, or protected ledger files were modified.
