# BTCognitive V31.6 — Alternative Data Source Qualification

**Date of assessment:** 2026-10-23  
**Scope:** Read-only source qualification for a separate alternative market-data path. No strategy logic, replay, backtest, model training, or live behavior was run.

## 1. Purpose

This report qualifies an alternative market-data source only under a strict research-only, evidence-first standard. The Coinbase 15-minute artifact remains quarantined from AI/ML use until explicit written authorization is verified. This task does not relabel that source or bypass its restriction.

## 2. Primary-source evidence reviewed

### Binance Vision dataset terms and documentation
- **Dataset terms:** `https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md`
- **Dataset repo:** `https://github.com/binance/binance-public-data`
- **Dataset portal:** `https://data.binance.vision/`
- **Access date:** 2026-10-23
- **Revision date stated on page:** `Last Updated: August 26, 2026`
- **Relevant clause references:** Vision Dataset Terms, Section 3 (non-commercial license grant), Section 4 (scope of non-commercial use and express prohibitions)

### Evidence summary
The official Binance Vision terms are clear and directly usable for source screening:

- The Datasets are provided under the `CC BY-NC-SA 4.0` license, with a non-commercial restriction expressly stated.
- The terms state: "Commercial licensing is strictly excluded under this agreement; any commercial utilization requires a separate, written enterprise data license agreement executed with Binance."
- The permitted non-commercial uses are limited to: academic research, non-monetized open educational projects, algorithmic historical backtesting for purely personal non-production research, and non-commercial open-source data science evaluations.
- The terms also say the Datasets may not be used for live proprietary trading execution, signal distribution for compensation, or commercial financial products.
- The repository description confirms that all symbols are supported and that both 1-minute and 15-minute and other intervals are available in the public archive, including Spot and USD-M / COIN-M futures datasets.

### Keywords and interpretation
The key point is that the Binance terms are not silent on research permission. They expressly provide a non-commercial research path, but not a commercial or broad AI/ML production path.

This matters because the current BTCognitive work is a research prototype and not a commercial or production trading platform. The terms may support a separate non-commercial research use, but that still requires a separate human decision on scope and any future commercial expansion.

## 3. Important note on the V31.5 exchange-doc retrieval

The V31.5 report explicitly noted that the earlier Exchange API documentation retrieval did not include the sentence that appears on the currently published Coinbase page: "Accessing the Exchange Market Data API means agreeing to the Market Data Terms of Use."

That omission is not a basis to claim the Coinbase API is permission-free. The historical V31.5 report remains intact and is not altered in this task. The important legal point is that the official Coinbase Market Data page is the controlling source for current market-data use restrictions, and the exchange welcome page alone is not enough to establish legal permission.

## 4. Candidate comparison

| Candidate | Provider / venue | Instrument / contract | Granularity / archive | Official-term evidence | Status | Key limitation |
|---|---|---|---|---|---|---|
| Binance Vision public data | Binance | BTCUSDT (Spot) and other symbols | 1m, 15m, hourly and other intervals in public archive | Official repo terms, `CC BY-NC-SA 4.0`, non-commercial research carve-out | `ELIGIBLE FOR HUMAN REVIEW — NON-COMMERCIAL RESEARCH SCOPE` | Not a BTC-USD substitute; future commercial use requires separate license |
| Coinbase 15m local artifact | Coinbase | BTC-USD | 15m Parquet | Current Coinbase Market Data Terms prohibit AI/ML use without prior express written consent | `BLOCKED — RIGHTS OR TERMS UNRESOLVED` | Legal permission unresolved; dataset remains quarantined |
| BTCUSDT as a direct BTC-USD replacement | Binance | BTCUSDT | Any interval, but instrument mismatch | Official Binance terms do not convert BTCUSDT into BTC-USD legal equivalence | `REJECTED — INSTRUMENT, GRANULARITY, OR LICENSE MISMATCH` | Different instrument and market identity cannot be treated as equivalent |
| Other free providers | Unverified / not source-first reviewed | Variable | Variable | No clear open terms identified in the reviewed source path | `BLOCKED — RIGHTS OR TERMS UNRESOLVED` | No canonical free research licence established in this task |

## 5. Evidence-led assessment of the strongest candidate

### Candidate A — Binance Vision historical market data

**Provider:** Binance Vision  
**Instrument:** BTCUSDT (Spot), not BTC-USD  
**Granularity:** 1-minute, 15-minute, hourly, and other public intervals documented by the dataset repo  
**Location:** `https://data.binance.vision/` and `https://github.com/binance/binance-public-data`  
**Terms:** `https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md`  
**Access date:** 2026-10-23  
**Revision date:** August 26, 2026

**Why it is the strongest candidate:**
- It is a public, free, documented archive with clear coverage and interval support.
- It has primary-source licensing language that expressly permits non-commercial research activities.
- It is a valid free-tier candidate for a research-only dataset path.

**Why it still does not qualify as a general replacement:**
- It is a BTCUSDT dataset, not a BTC-USD market-data contract.
- The project must not silently substitute BTCUSDT for BTC-USD when the existing research architecture and source requirements are BTC-USD-specific.
- The terms limit use to non-commercial research and exclude commercial use unless separate written enterprise licensing is obtained.
- The file or archive cannot be treated as interchangeable with a Coinbase BTC-USD 15-minute dataset without a separate instrument contract and source-proof review.

**Conservative conclusion:**
This candidate is the best available free-tier source for a clearly separate, non-commercial historical research study, but only as a distinct BTCUSDT contract and not as a direct BTC-USD replacement.

## 6. Recommended status assignments

### `ELIGIBLE FOR HUMAN REVIEW — NON-COMMERCIAL RESEARCH SCOPE`
- **Binance Vision Spot BTCUSDT historical archive**
- Rationale: primary-source terms expressly support academic and non-commercial historical research, algorithmic backtesting for personal non-production research, and non-commercial open-source data science evaluations.

### `REJECTED — INSTRUMENT, GRANULARITY, OR LICENSE MISMATCH`
- **BTCUSDT used as a direct BTC-USD replacement**
- Rationale: instrument mismatch and a different contract; not equivalent to the Coinbase BTC-USD or any BTC-USD-specific downstream requirement.

### `BLOCKED — RIGHTS OR TERMS UNRESOLVED`
- **Coinbase local 15m artifact**
- Rationale: the source restriction is clear in the current Coinbase Market Data Terms, and no proof of express written authorization for this project’s AI/ML use was found.

## 7. Best next candidate for human review

The strongest candidate for a separately scoped non-commercial research path is:

- **Binance Vision BTCUSDT Spot historical archive (1m / 15m / hourly)**

This is the best free-tier source because it has public data, clear archive coverage, and official terms explicitly permitting academic and non-commercial research. The main remaining decision is not technical; it is a human scope decision:

1. Is BTCognitive comfortable treating this as a separate BTCUSDT historical research dataset, not a BTC-USD replacement?
2. Does the project remain strictly non-commercial and research-only?
3. Are future commercial, production, or AI/ML use cases excluded from the current scope?

If the answer to all three is yes, then the dataset may merit a separate, explicit contract. If not, the project should keep it out of the active path.

## 8. Exact permission and scope questions still needing human review

The remaining decisions are:

- Is the project using Binance Vision under the non-commercial research scope only, or is it intending broader model-development, commercial analytics, or production research?
- Does the project accept a separate BTCUSDT research contract rather than a BTC-USD-equivalent market-data contract?
- Is the project willing to keep the license and attribution obligations under the `CC BY-NC-SA 4.0` framework and the Binance Vision non-commercial terms?
- Is the project prepared to exclude future commercial use and maintain a strict research-only boundary?

## 9. Final decision

**Best supported candidate:** Binance Vision public dataset as a separate, non-commercial BTCUSDT research contract.

**Not approved as a direct replacement for Coinbase BTC-USD:** no instrument equivalence is established.

**Current operational posture:** do not let any alternative source bypass the Coinbase legal hold. The strongest alternative is a separate, explicit non-commercial research path, not a general “free replacement” for the quarantined Coinbase contract.

## 10. Files inspected or created

**Created:**
- `research/v31_6_alternative_data_source_qualification.md`

**Inspected as evidence:**
- `research/v31_5_coinbase_terms_primary_source_verification.md`
- `research/v31_4_coinbase_terms_compatibility_report.md`
- `research/v31_4_coinbase15_data_use_decision.md`
- `research/v31_2_dataset_options_assessment.md`
- Official Binance Vision data terms and repository pages

No strategy logic, replay, model-training workflow, collector configuration, or protected ledger was modified.
