# BTCognitive V32.4 — Strategy Audit, Backtest Validation & Smart Entry Engine

**Date:** 2026-10-23  
**Repository:** `C:\Projects\BTCognitive\BTCognitive`  
**Status:** Research and audit only. No live trading, no data replacement, no protected-ledger changes.

## 1. Executive summary

This repository already contains a meaningful strategy and backtest architecture, but the project is still blocked at the data-governance gate before any legitimate comparative strategy evaluation can be treated as evidence.

The evidence in the repo shows:
- a strategy registry with several strategy archetypes,
- a multi-factor selection engine,
- a deterministic barrier resolver and entry-contract model,
- a realistic execution-cost model,
- and a tournament/simulator engine centered on BTC/USD-style research.

However, the local BTC/USD dataset remains blocked for formal research/AI-ML use because its exact provenance and rights chain are unresolved. That means a proper strategy-evaluation pass cannot be treated as final or trustworthy until the source gate is clarified in writing.

The correct final verdict under the prompt’s own rules is therefore:

`BLOCKED — REQUIRED DATA OR EVALUATION EVIDENCE UNAVAILABLE`

not a claim that the project is ready for production comparison or a new entry engine.

## 2. Actual strategy inventory found in the repo

### 2.1 Strategy registry and archetypes

The live code in `engine/strategy_registry.py` references strategy lifecycle states and strategy names, including:

- `MEIE-IGNITION`
- `MEIE-ABSORPTION`
- `MEIE-VACUUM`
- `MEIE-TOXICITY`
- `MEIE-COMBINED`

Those are treated as candidate/active/challenger strategy identities rather than free-form ideas.

### 2.2 Multi-factor strategy selection engine

The file `engine/strategy_selection.py` defines a canonical strategy-selection architecture with the following explicit archetypes:

- `MEIE-IGNITION`
- `MEIE-ABSORPTION`
- `MEIE-VACUUM`
- `MEIE-TOXICITY`
- `MEIE-COMBINED`

It evaluates both long and short hypotheses, applies eligibility gating, and computes a deterministic hash for the enabled indicator set. This is a strategy-ranking and selection engine, not a live trading engine.

### 2.3 Tournament-style research engine

The file `research/v12_strategy_tournament_engine.py` contains the stronger strategy / backtest simulation layer. It explicitly lists the following strategy families:

- `REGIME_ADAPTIVE_ROUTER`
- `MTF_MOMENTUM_TREND`
- `VOL_COMPRESSION_BREAKOUT`
- `HTF_RANGE_EXPANSION_BREAKOUT`
- `SHORT_HORIZON_MEAN_REVERSION`
- plus baselines including `NO_TRADE`, `BUY_AND_HOLD`, `VOL_TARGETED_BULL`, and `MATCHED_RANDOM_ENTRY`

This is the clearest evidence that the project already has multiple strategy baselines and a tournament framework.

### 2.4 Signal generation and risk contracts

The code also contains a valid risk and execution framework:

- `engine/entry_contracts.py`: immutable candidate setup and deterministic resolution contracts.
- `engine/barrier_resolver.py`: same-candle collision resolution, opening-gap handling, and conservative SL-first behavior.
- `engine/execution_cost_model.py`: venue-specific transaction cost assumptions.

These are not live execution code; they are research contracts and simulation components.

## 3. How the existing backtester actually works

### 3.1 Research engine assumptions

The tournament engine in `research/v12_strategy_tournament_engine.py` demonstrates that the project is built around:
- causal multi-timeframe indicators,
- next-bar or event-driven execution logic,
- barrier-based TP/SL resolution,
- cost-sensitive comparisons,
- and explicit risk-first selection rather than simple arbitrary profit maximization.

The engine calculates:
- ADX and trend features,
- EMA and Bollinger-band structures,
- volatility measures and compression heuristics,
- and uses explicit `ExecutionCostModel` assumptions.

### 3.2 Execution and cost logic

The file `engine/execution_cost_model.py` defines execution costs by venue and product type. It includes:
- Coinbase spot scenario,
- Binance futures scenario,
- per-side fees,
- spread and slippage terms,
- and funding cost logic for perpetual products.

This means the project already has a realistic cost model to use in backtests, but it must be applied consistently to the exact market contract being evaluated.

### 3.3 Candidate and barrier logic

The file `engine/entry_contracts.py` enforces strict geometry:
- long: TP > entry > SL,
- short: TP < entry < SL,
- and it refuses invalid or causally impossible setups.

The resolver in `engine/barrier_resolver.py` explicitly implements the required conservative rule for same-candle TP/SL collisions:
- if both barriers are touched in the same bar, it resolves to `SL_FIRST` and marks the event as ambiguous.

This is a solid research contract and is the right kind of discipline for a no-execution system.

## 4. Backtest reproducibility and reliability status

### 4.1 What is likely valid

The repository does contain a structured strategy-evaluation architecture and a defensible research framework. The core logic is not arbitrary; it includes:
- regime filters,
- cost-aware friction,
- deterministic TP/SL resolution,
- and multi-factor selection logic.

### 4.2 What is not yet trustworthy enough to claim a final result

The project has a severe unresolved source gate:

- the BTC/USD dataset is technically coherent,
- but exact version linkage and rights permission remain unresolved,
- and AI/ML use cannot be qualified without written permission from the dataset owner and the data source provider.

This is not a small issue; it invalidates the claim that backtest results are evidence-backed for the intended use.

A strategy result is only as good as the governing data contract. Without a clear, written rights chain and a verified version lineage, performance numbers are at best local simulation artifacts, not qualified research evidence.

## 5. What was actually resolved and what remains blocked

### Resolved
- The repository does contain legitimate strategy and backtest infrastructure.
- There are multiple existing strategy archetypes and a tournament engine.
- The application has deterministic entry and barrier logic.
- The execution-cost model is formalized and separated from live trading.
- The app is structurally designed to remain analysis-only.

### Blocked
- Exact public Kaggle version linkage for the local BTC/USD file.
- Rights to use the historical BTC/USD dataset for the intended project scope.
- Whether private AI/ML feature engineering, model development, and evaluation are permitted.
- Whether the local dataset can be used as a qualified evaluation input for production-grade strategy comparison.

Because of that, even a correct repo architecture does not justify a qualified comparative strategy result.

## 6. The 70–80% win-rate objective under the actual repo state

The objective is a valid research hypothesis, but not a promise. The actual repo state does not support a reliable claim that the target win rate is achieved or even meaningfully measurable because:

- the dataset rights gate is unresolved,
- the exact version linkage is unverifiable,
- the backtests are data-dependent and therefore cannot be treated as final evidence,
- and the prompt itself requires a proper data and rights gate before strategy comparison can be considered valid.

This means the most truthful statement is:

`The objective is a hypothesis, not a verified accomplishment.`

## 7. Recommended next step under the prompt’s rules

The safe path is:
1. preserve the existing strategies and backtest engine,
2. keep the data gate blocked until written permission is obtained,
3. complete software-level regression tests and architecture validation,
4. and only then perform offline comparative evaluation once the data-rights chain is cleared.

The repo is therefore not ready for final performance-based comparison or a new Smart Entry candidate under a qualified data contract. It is, however, ready for a documentable audit and architecture boundary review.

## 8. Final verdict

`BLOCKED — REQUIRED DATA OR EVALUATION EVIDENCE UNAVAILABLE`

This verdict is the correct completion state for the prompt as it stands in the repository, because the strategy and backtest architecture is real and structured, but the mandatory data provenance and permission gate remains unresolved.

## 9. Evidence inspected

- `engine/strategy_registry.py`
- `engine/strategy_selection.py`
- `research/v12_strategy_tournament_engine.py`
- `engine/entry_contracts.py`
- `engine/barrier_resolver.py`
- `engine/execution_cost_model.py`
- `research/v32_0_btcusd_license_provenance_decision.md`
- `research/v32_2_btcusd_dataset_resolution.md`
- `data/raw/btcusd_1-min_data.csv`

## 10. Compliance statement

- No live execution occurred.
- No strategy logic was replaced.
- No protected ledgers were modified.
- No new market data was downloaded.
- No comparison claims were made beyond what the available evidence supports.
