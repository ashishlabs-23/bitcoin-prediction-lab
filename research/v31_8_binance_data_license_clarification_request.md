# BTCognitive V31.8 — Binance Data License Clarification Request

**Date:** 2026-10-23  
**Scope:** research-only licensing clarification request for the separate Binance Vision Spot BTCUSDT 1-minute source contract defined in `research/v31_7_binance_btcusdt_1m_contract.md`. No dataset downloads, ingestion, experiments, backtests, or strategy changes were performed.

## 1. Official source basis

The request is based on the current official Binance Vision public-data terms and repository documentation:

- **Terms URL:** `https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md`
- **Repository URL:** `https://github.com/binance/binance-public-data`
- **Archive URL:** `https://data.binance.vision/`
- **Access date:** 2026-10-23
- **Last updated on page:** `August 26, 2026`

### Relevant official language
The retrieved current terms state:

- **Section 2.4:** "Use of any data derived from, calculated with, or extracted from the Datasets (including charts, models, and derivative analytical indicators) is strictly governed by these Vision Dataset Terms."
- **Section 3.1:** "Datasets are provided to you under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License (`CC BY-NC-SA 4.0`), incorporated herein by reference..."
- **Section 3.4:** "Commercial licensing is strictly excluded under this agreement; any commercial utilization requires a separate, written enterprise data license agreement executed with Binance."
- **Section 4.1:** permitted non-commercial uses are limited to academic research, non-monetized open educational projects, algorithmic historical backtesting for purely personal non-production research, and non-commercial open-source data science evaluations.
- **Sections 4.2-4.5:** express prohibitions include live proprietary trading execution, automated commercial order generation, compensation-based signal distribution, commercial product integration, and derivative redistribution that fails the attribution/share-alike obligations.

These clauses are the only direct source-language basis available to describe the bound of the current permission. The terms do not provide an express blanket authorization for private AI/ML development, training, or validation beyond the enumerated non-commercial research scope.

## 2. Requested use description

**Project:** BTCognitive  
**Nature:** Bitcoin quantitative research and market-risk intelligence system  
**Source proposed:** Binance Vision Spot BTCUSDT 1-minute historical klines  
**Research purpose:** non-commercial historical quantitative research, including feature engineering, analytical indicators, and potential private AI/ML model development, training, and evaluation  
**Explicit exclusions:** commercial product use, paid signal distribution, live trading, automated order generation, production activation, or any commercial exploitation  
**Scope boundary:** the project remains non-commercial and research-only unless the relevant permission is explicitly confirmed in writing

### Why clarification is necessary
The current terms support some non-commercial research activities, but they do not explicitly confirm that private AI/ML model development, training, validation, or benchmarking on the archive is permitted under the non-commercial research carve-out. This is precisely the area that needs written clarification.

## 3. Draft request to Binance

Subject: Clarification of authorized use of Binance Vision Spot BTCUSDT 1-minute historical data for BTCognitive research

Dear Binance Data Licensing / Support Team,

I am preparing a research-only data-use evaluation for BTCognitive, a Bitcoin quantitative research and market-risk intelligence project. The project proposes to use Binance Vision Spot BTCUSDT 1-minute historical klines from the official public archive for a non-commercial historical research scope.

The project intends to evaluate whether the data can support:

1. historical feature engineering and statistical analysis;
2. private internal research workflows and indicator derivation;
3. possible AI/ML model development, training, and evaluation for non-commercial research purposes;
4. internal, non-distributed analytical outputs derived from the dataset.

The project is not proposing the following:

- commercial product use;
- paid subscriptions or signal distribution;
- live execution or automated order generation;
- production deployment;
- any activity outside the strictly non-commercial research scope.

We are reviewing the current official terms at the public repository and archive:

- `https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md`
- `https://github.com/binance/binance-public-data`
- `https://data.binance.vision/`

The official terms state that the Datasets are governed by the Vision Dataset Terms and are provided under `CC BY-NC-SA 4.0` for non-commercial use, with commercial use requiring a separate written enterprise license. However, the terms do not explicitly answer the following questions in a project-specific way:

1. Does the listed non-commercial license permit private feature engineering and AI/ML model development, training, and evaluation on Binance Vision Spot BTCUSDT historical klines?
2. Are private, non-redistributed models, weights, metrics, and analytical indicators derived from this data permitted, and which terms govern those outputs?
3. Is internal use in a research prototype permitted when there is no commercial distribution, no compensation, no live execution, and no third-party signal distribution?
4. What attribution and CC BY-NC-SA 4.0 share-alike obligations apply to private results versus redistributed outputs?
5. Would any future commercial use require a separate written enterprise data license, even if the initial experiments are non-commercial?
6. Do these conditions apply to the exact public historical archive and access method proposed for BTCognitive?

Please clarify in writing the permitted scope for this specific use case, including any conditions or restrictions that apply to derived models, private outputs, and future commercial use. If a separate written approval is required for AI/ML development or broader analytical use, please advise the applicable process and any required license path.

Thank you for your clarification.

Sincerely,  
BTCognitive research team

## 4. Official contact route note

The current official public support route is:

- `https://www.binance.com/en/support`

This was accessed in the current environment, but the environment did not retrieve a direct licensing or enterprise-data-contact endpoint in the accessible response. Because no explicit, verifiable licensing contact path was identified in the reviewed official materials, the request is ready for manual submission through Binance’s official support or legal/licensing route, but no specific email, helpdesk, or licensing inbox was invented or assumed.

## 5. Decision gate status for this task

The current scope remains a written-clarification gate. Under the evidence available now:

- The source is a plausible non-commercial research candidate under the official public terms.
- The terms do not explicitly authorize private AI/ML model development or benchmarking beyond the enumerated non-commercial research scope.
- Because the intended use includes possible AI/ML model development, the current gate is not an approval.

The request should therefore be understood as a permission-clarification step, not a statement that the source is approved for experiments.
