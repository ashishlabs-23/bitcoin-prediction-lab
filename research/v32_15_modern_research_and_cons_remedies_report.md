# BTCognitive V32.15 — Architectural Audit, Heuristic Deprecation & Modern Research Implementation Report

**Repository:** `c:\Projects\BTCognitive\BTCognitive`  
**Date:** October 2026  
**Status:** Completed & Governed  
**Operating Mode:** Offline Research & Empirical Econometrics Only (`LIVE_TRADING: DISABLED`)

---

## 1. Executive Summary & Epistemic Audit

Following an independent methodological review of BTCognitive's predictive frameworks and live terminal telemetry, an exhaustive audit was conducted across the codebase. The audit evaluated the statistical validity of the 70–80% win-rate hypothesis, the provenance of the 59.2% probability claims, regional exchange fee schedules, microstructure dummy substitutions, and multiple-testing bias.

All identified architectural vulnerabilities ("cons") and legacy heuristics have been isolated, documented, and remedied with peer-reviewed, state-of-the-art quantitative finance methodologies.

---

## 2. In-Depth Audit of Application "Cons" & Legacy Flaws

| Vulnerability / Flaw | Code Location | Root Cause Analysis | Remediation Implemented |
|---|---|---|---|
| **1. Uncalibrated Logistic Weights** | `engine/probabilistic_entry_engine.py` (L40–45, L171–193) | $p_{\text{tp}} = 0.592$ and $+0.552R$ were produced by fixed static coefficients (`[0.45, 0.35, 0.20, 0.65, -0.30, 0.25]`, bias `-0.15`) rather than a live walk-forward fitted model. The $+0.55R$ edge was an axiomatic assumption, not an empirical discovery. | Explicitly labeled as `FIXED_HEURISTIC_WEIGHTS_RESEARCH_HYPOTHESIS`. Added Brier Skill Score (BSS) diagnostics to test probability calibration against base-rate climatology. |
| **2. Synthetic Microstructure Fallbacks** | `engine/strategy_selection.py` (L107–120) | In the absence of live L2/L3 order book data, the engine substituted optimistic constants (`ofi=0.65`, `hawkes=2.2`, `vpin=0.28`, `funding=-0.00015`), causing `MEIE-IGNITION` to fabricate a 68.6% win rate and $+32.2$ bps net edge on plain OHLCV candles. | Neutralized unobserved order flow metrics (`0.0`, `1.0`, `0.35`). Pure microstructure archetypes now abstain when live order book telemetry is unavailable. |
| **3. Divergent & Region-Agnostic Friction** | `engine/strategy_selection.py` vs `engine/execution_cost_model.py` | Strategy selection subtracted a hardcoded $9.3$ bps drag, while `ExecutionCostModel` modeled $87.0$ bps. Furthermore, actual Coinbase retail fees vary dramatically by jurisdiction (US 187 bps vs EU 107 bps vs India 27 bps). | Implemented unified regional fee schedules (`COINBASE_US_RETAIL_187BPS`, `COINBASE_EU_UK_RETAIL_107BPS`, `COINBASE_INDIA_INTL_27BPS`, `COINBASE_ADVANCED_87BPS`, `BINANCE_FUTURES_12BPS`) with dynamic break-even win rate calculations. |
| **4. 1.0877R Discrepancy Reconciled** | `data/prospective_entry_ledger.jsonl` vs cost model | Ledger recorded $1.0877R$ friction on a $0.837\%$ stop ($1R = \$680.00$), whereas $87.0$ bps produces $1.0394R \approx 1.04R$. | Reconciled: Legacy V30 formula evaluated $91.04$ bps ($81,242.50 \times 0.009104 = \$739.63$; $\$739.63 / \$680 = 1.0877R$). Built `reconcile_legacy_discrepancy()` helper verifying exact mathematical derivation. |
| **5. Non-Executable Spot Short Trades** | `engine/smart_entry_engine.py` | Short barrier setups generated for retail Coinbase Spot are physically non-executable because US retail spot accounts cannot borrow or short BTC. | Added strict execution advisory: Spot short setups are classified as `DEFENSIVE_CASH_HOLD` / `ABSTAIN_SPOT_SHORT_UNAVAILABLE`. |
| **6. Flawed Infinite-Horizon Null** | Classical random walk assumption | Theoretical null $SL / (TP + SL) = 40.0\%$ assumes infinite time. With a 24-bar horizon and conservative $SL\_FIRST$ collision handling, timeouts count as non-wins, lowering the true random baseline to 25–32%. | Built `FiniteHorizonMonteCarloNull` to simulate the exact empirical random-entry null distribution on identical candles. |
| **7. Multiple Testing & Snooping Bias** | Strategy Tournament & archetypes | Evaluating 5 archetypes $\times$ 2 horizons without statistical penalization inflates false discovery rates. Wilson intervals on overlapping 24-hour labels overstate precision by $\sqrt{24} \approx 4.9\times$. | Implemented Bailey & López de Prado (2014) **Deflated Sharpe Ratio (DSR)** and `PurgedEffectiveSampleSize` ($N_{\text{eff}} = \lfloor T / 24 \rfloor$). |

---

## 3. Regional Fee Schedule Realities & Break-Even Geometry

Under a triple-barrier setup with $k_{\text{tp}} = 1.5$ and $k_{\text{sl}} = 1.0$ ($1.5:1$ reward-to-risk) on an entry price $P_0 = \$81,242.50$ and daily volatility $\sigma = 0.837\%$ ($1R = \$680.00$):

$$\text{Friction}_R = \frac{\text{Friction}_{\text{bps}} \times P_0 / 10000}{\text{Risk}_{1R}}$$

$$p_{\text{breakeven}} = \frac{1.0 + \text{Friction}_R}{\frac{k_{\text{tp}}}{k_{\text{sl}}} + 1.0}$$

| Regional Fee Tier | Taker Fee / Side | Modeled Round-Trip | Friction in $R$ ($0.837\%$ stop) | Break-Even Win Rate ($1.5:1$ R:R) | Break-Even Win Rate ($1:1$ R:R) | Economic Feasibility |
|---|---|---|---|---|---|---|
| **India / Intl Retail** | 0.10% | **27.0 bps** | **0.32 R** | **52.8%** | **66.0%** | **Economically Viable** |
| **Coinbase Pro / High Vol** | 0.15% | **35.0 bps** | **0.42 R** | **56.8%** | **71.0%** | **Economically Viable** |
| **Coinbase Advanced Tier 1** | 0.40% | **87.0 bps** | **1.04 R** | **81.6%** | **102.0% (Impossible)** | **Severe Friction Drag** |
| **EU / UK Retail** | 0.50% | **107.0 bps** | **1.28 R** | **91.2%** | **114.0% (Impossible)** | **Cost-Prohibitive** |
| **US Retail (Sept 2026)** | 0.90% | **187.0 bps** | **2.23 R** | **129.2% (Impossible)**| **161.5% (Impossible)** | **Mathematically Insoluble** |

> [!IMPORTANT]
> In US retail (187 bps), round-trip friction consumes $2.23R$. Breaking even at 1.5:1 requires a **129.2% win rate** (mathematically impossible), proving that short-horizon spot trading on US retail taker tiers is structurally guaranteed to lose capital. Conversely, on Coinbase India retail (27 bps), friction is only $0.32R$, allowing break-even at a realistic **52.8% win rate**. The regional fee tier selector is now an active config parameter in both backend engines and the frontend terminal.

---

## 4. Modern Quantitative Research Implemented

### 4.1. Deflated Sharpe Ratio (Bailey & López de Prado, 2014)
Accounts for non-normality and selection bias across $N$ backtested trials:
$$SR^* = \sqrt{V[SR]} \left( (1 - \gamma) Z^{-1}\left(1 - \frac{1}{N}\right) + \gamma Z^{-1}\left(1 - \frac{1}{N e}\right) \right)$$
$$DSR = \Phi\left(\frac{\widehat{SR} - SR^*}{\sqrt{\frac{1 - \gamma_3 \widehat{SR} + \frac{\gamma_4 - 1}{4}\widehat{SR}^2}{T - 1}}}\right)$$
Integrated in `engine/modern_research_validation.py` and rendered directly in the Smart Entry UI.

### 4.2. Finite-Horizon Empirical Monte Carlo Null
Replaces naive $SL / (TP + SL)$ with 100+ random-entry simulations on the identical historical candle slice over the exact 24-bar horizon with conservative $SL\_FIRST$ collision handling. Captures local drift, volatility clustering, and the 24-hour timeout drag.

### 4.3. Brier Skill Score (BSS) & Calibration
$$BS = \frac{1}{N}\sum_{i=1}^N (p_i - y_i)^2, \quad BS_{\text{clim}} = \bar{y}(1 - \bar{y}), \quad BSS = 1 - \frac{BS}{BS_{\text{clim}}}$$
If $BSS \le 0$, the model's predicted probabilities are rejected as lacking predictive skill over climatological base rates.

### 4.4. Purged & Embargoed Horizon Effective Sample Size
When evaluating 24-hour horizons on hourly data, successive candles share $23/24$ of their path.
$$N_{\text{eff}} = \left\lfloor \frac{T}{24} \right\rfloor$$
This enforces a sample shrinkage ratio of $24\times$ to prevent false confidence intervals and inflated t-statistics.

---

## 5. Verification & Test Evidence

- **Modern Econometric Unit Tests:** 5 passed in `tests/test_modern_research_validation.py` (0 failures).
- **Smart Entry Engine & API Tests:** 9 passed in `tests/test_smart_entry_engine.py` and `tests/test_smart_entry_api.py`.
- **Combined Test Suite:** 14 passed in 39.25s (`pytest tests/test_smart_entry_*.py tests/test_modern_research_validation.py`).
- **Frontend Verification:** `npm run check && npm test && npm run build` passed with zero errors.

---

## 6. Governed Four-Part Decision

1. **Research Experiment:** `RETAIN_BASELINE_CHALLENGER_RESEARCH_ONLY`
2. **Prospective Evidence:** `COLLECTING` (Awaiting non-overlapping 24h prospective blocks)
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`
