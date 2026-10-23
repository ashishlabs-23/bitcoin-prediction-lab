# BTCognitive Research Source Quality Register (V12)

**Version:** 1.0.0  
**Effective Date:** October 2026  
**Status:** AUDITED & GOVERNED  
**Orchestration:** Agent A (Research Governance & Epistemic Boundaries)  

---

## 1. Classification Taxonomy

Sources are classified into four evidence tiers:
1. **TIER 1: PEER_REVIEWED_LITERATURE** — Published academic papers in quantitative finance, statistics, and econometrics.
2. **TIER 2: ESTABLISHED_QUANT_METHODOLOGY** — Published technical treatises, exchange rulebooks, and standard market microstructure specifications.
3. **TIER 3: REPRODUCIBLE_CODE_IMPLEMENTATION** — Open-source or verifiable algorithmic frameworks with test fixtures and explicit assumptions.
4. **TIER 4: ANECDOTAL_OR_VENDOR_CLAIM** — Vendor marketing backtests, social media claims, and un-replicated YouTube trading systems. Classified as **UNVERIFIED HYPOTHESES** until independently replicated on genuine exchange data.

---

## 2. Research Source Inventory & Reconciled Verdicts

| Source ID | Citation / Reference | Type | Declared Claim | BTCUSD Empirical Verification | V13 Governed Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SRC-01** | Wilder, J. W. (1978). *New Concepts in Technical Trading Systems*. Trend Research. | TIER 2 | ADX(14) > 25 indicates persistent trend strength; ATR measures true market volatility. | Verified on Coinbase BTC-USD hourly series; ADX separates high and low directional drift regimes. | `ACCEPTED_AS_HYPOTHESIS_FILTER` |
| **SRC-02** | Bollinger, J. (2001). *Bollinger on Bollinger Bands*. McGraw-Hill. | TIER 2 | Bandwidth compression ($\text{BBW}$) precedes volatility expansion; standard deviation touches indicate mean reversion. | Verified on BTC-USD 15m/1h; bandwidth percentile isolates volatility coiling, but gross edges degrade under retail fees. | `ACCEPTED_WITH_COST_HURDLE` |
| **SRC-03** | Donchian, R. (1960). *High-Low Channel Breakout Methodology*. | TIER 2 | N-period price channel breakouts capture sustained momentum. | Verified on BTC-USD; prone to false breakouts in choppy regimes, requiring HTF trend and volatility filters. | `ACCEPTED_AS_CANDIDATE_BRANCH` |
| **SRC-04** | Politis, D. N., & Romano, J. P. (1994). *The Stationary Bootstrap*. JASA, 89(428), 1303-1313. DOI: 10.1080/01621459.1994.10476870. | TIER 1 | Resampling dependent time series with random geometric block lengths preserves serial correlation. | Implemented and verified in `v11_strategy_discovery_engine.py` and `v12_strategy_tournament_engine.py`. | `AUTHORIZED_STATISTICAL_CORE` |
| **SRC-05** | Harvey, D., Leybourne, S., & Newbold, P. (1997). *Testing the equality of prediction mean squared errors*. IJF, 13(2), 281-291. | TIER 1 | Small-sample correction for Diebold-Mariano test under serial dependence. | Implemented and verified in loss function and baseline comparison tests. | `AUTHORIZED_STATISTICAL_CORE` |
| **SRC-06** | Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017). *The Probability of Backtest Overfitting*. Journal of Computational Finance, 20(4), 39-69. DOI: 10.21314/JCF.2016.322. | TIER 1 | Quantifies probability that in-sample best strategy was selected by chance via CSCV. | Verified across 5 strategy candidates; confirms multi-trial penalization requirement. | `AUTHORIZED_DIAGNOSTIC_CORE` |
| **SRC-07** | Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Non-Normality and Memory*. Journal of Portfolio Management, 40(5), 94-107. DOI: 10.3905/jpm.2014.40.5.094. | TIER 1 | Corrects observed Sharpe ratio for multiple testing, skewness, kurtosis, and sample length. | Applied to tournament leaderboards to discount inflated nominal Sharpe ratios. | `AUTHORIZED_STATISTICAL_CORE` |
| **SRC-08** | Deprez, C., & Frömmel, M. (2024). *Are simple technical trading rules profitable in bitcoin markets?*. International Review of Economics & Finance, 93, 786-801. DOI: 10.1016/j.iref.2024.05.003. | TIER 1 | Comprehensive empirical evaluation of 7,000+ technical rules in BTC markets; demonstrates gross profitability disappears once realistic transaction costs and snooping adjustments are applied. | **EMPIRICALLY CONFIRMED IN BTCognitive V12/V13**: Unleveraged technical strategies show positive gross expectancy that collapses under 87 bps retail friction. | `CONFIRMATORY_LITERATURE_BASELINE` |
| **SRC-09** | Vendor / Retail Trading Systems (Various, 2024–2026). *“90% Win-Rate Trend Following with Breakeven Stops”*. | TIER 4 | Moving stop to entry price guarantees zero risk; partial exits at 1R yield 90% win rates. | **REPRODUCED & FALSIFIED**: On Coinbase BTC-USD spot with 87 bps retail friction, breakeven stops incur execution costs on fills, and partial exits reduce right-tail profit factor. | `REJECTED_AS_UNREALISTIC_CLAIM` |
| **SRC-10** | Vendor Crypto Delta-Neutral Yield Claims (2025). *“Risk-Free Perpetual Funding Carry”*. | TIER 4 | Basis/funding arbitrage provides guaranteed 15–30% APR with zero liquidation risk. | **DEFERRED**: Requires verified derivatives order-book execution, liquidation risk models, and collateral contracts. Not simulated on spot. | `DEFERRED_PENDING_CONTRACTS` |

---

## 3. Epistemic Verification Rules
1. **No Cherry-Picked Metrics:** Never report gross return without net return after documented transaction friction.
2. **Breakeven Stop Realism:** Fills at entry price after moving stop to breakeven MUST account for two-sided exchange commission, bid-ask spread, and slippage.
3. **Negative Results Preserved:** Unsuccessful experiments and falsified hypotheses are permanently retained in tournament manifests to track the total trial count ($N_{\text{trials}}$).
