# BTCognitive PRD Amendment V12 — Regime-Adaptive Strategy Tournament, Risk-First Selection & Live Terminal Integration

**Document Version:** 12.0.0  
**Effective Date:** October 2026  
**Status:** APPROVED & GOVERNED  
**Supersedes:** PRD V11 Amendments (preserved in historical records)  
**Parent PRD:** `docs/BTCognitive_Master_PRD.md`, `docs/BTCognitive_Master_PRD_v2_Continuation.md`  

---

## 1. Executive Summary & Operational Scope

This amendment extends BTCognitive from an uncertainty-estimation and exploratory discovery platform into an **evidence-driven BTCUSD Strategy Tournament and Risk-First Selection System**.

BTCognitive continuously monitors the observed market regime of BTCUSD, determines which strategy hypotheses are structurally compatible with current conditions, compares their independently validated historical risk and cost metrics, and projects the Top-5 most relevant candidates within the Live Terminal.

### Non-Negotiable Operational Boundaries
1. **Research & Paper Milestones Only:** Live trading remains strictly **DISABLED**. No real capital, broker API, or automated order placement is authorized.
2. **Directional Null & Epistemic Boundaries:** Directional prediction remains gated at Tier 2 (`OFFLINE_RESEARCH_ONLY`). System directional advice remains strictly `ABSTAIN`.
3. **No Assumed Winners:** The proposed regime-adaptive router is treated as an unverified experimental hypothesis, evaluated strictly against its component strategies and independent baselines (`NO_TRADE`, `BUY_AND_HOLD`, `VOL_TARGETED_BULL`, and `MATCHED_RANDOM_ENTRY`).
4. **Risk-First Pareto Ranking:** Selection prioritizes capital preservation, low maximum drawdown, downside Sortino, and positive net expectancy after transaction costs. Large nominal win rates without downside control are disqualified.

---

## 2. Market Regime Taxonomy & Hysteresis Contract

Market regime classification operates strictly on **completed higher-timeframe bars** (1-hour and 4-hour) to prevent intra-bar lookahead leakage.

### 2.1 Formal Regime Taxonomy
| Regime Code | Primary Identifying Indicator Rules | Compatible Strategy Families |
| :--- | :--- | :--- |
| `TRENDING_BULL` | $P_t > \text{EMA}_{200, \text{1h}}$ AND $\text{ADX}_{14, \text{1h}} \ge 25$ AND $\text{EMA}_{20, \text{1h}} > \text{EMA}_{50, \text{1h}}$ | Multi-Timeframe Momentum Trend Following (`MTF_MOMENTUM_TREND`) |
| `TRENDING_BEAR` | $P_t < \text{EMA}_{200, \text{1h}}$ AND $\text{ADX}_{14, \text{1h}} \ge 25$ AND $\text{EMA}_{20, \text{1h}} < \text{EMA}_{50, \text{1h}}$ | Multi-Timeframe Momentum Trend Following (`MTF_MOMENTUM_TREND` short branch) |
| `VOL_COMPRESSION_RANGE` | $\text{ADX}_{14, \text{1h}} < 20$ AND $\text{BBW}_{20, \text{1h}} \le \text{Percentile}_{20}(\text{BBW}_{100})$ | Volatility-Compression Breakout (`VOL_COMPRESSION_BREAKOUT`) |
| `CONSOLIDATION_RANGE` | $20 \le \text{ADX}_{14, \text{1h}} < 25$ OR ($|\text{Z-Score}(P_t, \text{EMA}_{50})| \le 1.5$ AND $\text{ADX} < 25$) | Short-Horizon Mean Reversion (`SHORT_HORIZON_MEAN_REVERSION`) |
| `TRANSITION_UNSUPPORTED` | Conflicting indicators, high parameter volatility, or missing/stale inputs | `ABSTAIN` (No candidate qualified) |

### 2.2 Hysteresis and Persistence Rule
To prevent destructive churn and excessive turnover costs:
- A new regime state must persist for at least **3 consecutive completed hourly candles** before the router switches strategy allocation.
- In-flight positions are governed by their original exit and trailing-stop rules; a regime switch cancels un-triggered entry orders immediately.

---

## 3. Tournament Strategy Specifications & Predeclared Contracts

The tournament evaluates five distinct hypotheses alongside four quantitative baselines:

### Candidate 1: `REGIME_ADAPTIVE_ROUTER` (Strategy A)
- **Hypothesis:** Dynamically routing to the compatible strategy archetype conditioned on causal ADX/EMA regime classification produces superior Sortino and lower drawdown than static single-strategy allocation.
- **Contract:** Monitors completed 1h ADX, EMA200, and Bollinger Bandwidth. Routes to `MTF_MOMENTUM_TREND` during confirmed trends, `SHORT_HORIZON_MEAN_REVERSION` during consolidation, and `VOL_COMPRESSION_BREAKOUT` during low-volatility coiling. Emits `ABSTAIN` during transitions.
- **Switching Cost Friction:** Debits full round-trip friction upon each branch switch.

### Candidate 2: `MTF_MOMENTUM_TREND` (Strategy B)
- **Hypothesis:** Multi-timeframe trend filtering with 50% partial exit at 1R, moving the remaining stop toward breakeven, and trailing with 3× ATR limits tail losses while locking in gains.
- **Entry:** Completed bar close above 20-period Donchian channel upper band with $P_t > \text{EMA}_{200, \text{1h}}$.
- **Risk Management:** Initial Stop Loss $= P_{\text{entry}} - 2 \times \text{ATR}_{14}$. 
- **Partial Exit:** 50% closed at $1R = P_{\text{entry}} + 2 \times \text{ATR}_{14}$. Remaining stop moved to entry price $+ \text{round-trip cost friction}$.
- **Trailing Stop:** Trailing 3× ATR applied to remaining 50% position.

### Candidate 3: `VOL_COMPRESSION_BREAKOUT` (Strategy C)
- **Hypothesis:** Volatility compression identified by 20-period Bollinger Bandwidth in the bottom quintile followed by an expansion bar yields asymmetric right-tail moves.
- **Entry:** Compression identified when $\text{BBW} < \text{quantile}_{0.20}(\text{BBW}_{100})$. Breakout triggered when close exceeds previous 12-bar high.
- **Risk Management:** Stop Loss at opposite band or 1.5× ATR. Max holding horizon: 24 bars.

### Candidate 4: `HTF_RANGE_EXPANSION_BREAKOUT` (Strategy D)
- **Hypothesis:** Breakouts beyond 4-hour consolidation ranges capture institutional liquidity pushes.
- **Entry:** Close exceeds 4h highest high of past 20 bars.
- **Stop Loss:** Opposite boundary of the 4h consolidation channel. Modeled slippage increased by 50% during high-volatility expansions.

### Candidate 5: `SHORT_HORIZON_MEAN_REVERSION` (Strategy E)
- **Hypothesis:** Standardized price deviations ($Z > 2.0$) on 15m/1h bars in range regimes revert to the 20-period moving average.
- **Entry:** $P_t < \text{Lower Bollinger Band}(20, 2.0)$ with $\text{ADX} < 20$.
- **Adverse Selection Gate:** Gated when hourly volume $> 2.5\times$ rolling average (preventing knife-catching).
- **Exit:** Touch of middle band (SMA 20) or max hold 12 bars. Stop Loss $= 1.5\times$ band distance.

### Independent Baselines
1. `NO_TRADE`: 100% Cash / Treasury proxy (Expectancy = 0 bps, Max DD = 0.0%).
2. `BUY_AND_HOLD`: Unhedged passive long exposure across identical timestamps.
3. `VOL_TARGETED_BULL`: Continuous exposure scaled inversely to realized volatility (10% annualized target).
4. `MATCHED_RANDOM_ENTRY`: Monte Carlo random entries (N=1,000) with identical holding periods and ATR stop rules.

---

## 4. Execution Cost Reconciliations

All candidate strategies are evaluated across three explicit, verified cost schedules:

| Cost Scenario Key | Two-Sided Comm | Spread | Slippage | Funding/Hold | Total Round-Trip | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `COINBASE_RETAIL_87BPS` | 80.0 bps | 3.0 bps | 4.0 bps | 0.0 bps | **87.0 bps** | Verified Empirical Baseline (Retail Tier 1) |
| `COINBASE_INSTITUTIONAL_18BPS`| 11.6 bps | 3.0 bps | 4.0 bps | 0.0 bps | **18.6 bps** | Verified Empirical Baseline (High Volume) |
| `BINANCE_PERP_15BPS` | 10.0 bps | 1.0 bps | 2.0 bps | 2.0 bps | **15.0 bps** | Hypothetical Derivatives Reference |

**Breakeven Cost ($\text{BPS}_{\text{BE}}$):** The exact round-trip friction at which net expectancy equals 0.0 bps.

---

## 5. Event-Driven Simulator & Conservative Invariants

1. **Next-Bar-Open Execution:** Signals generated on completed candle $t$ execute at the open of bar $t+1$.
2. **Adverse Simultaneous Touch:** If both Take Profit and Stop Loss price levels are breached within the same bar's $[L, H]$ range, the simulator strictly records the **Stop Loss (loss)** first.
3. **Imperfect Breakeven Realization:** Moving a stop to entry price does not eliminate loss: exchange commission, bid-ask spread, and slippage apply upon execution.
4. **Purged Walk-Forward Splitting:** 
   - Train / Dev: 60%
   - Validation: 20%
   - Untouched Holdout: 20%
   - Embargo: $\max(\text{holding horizon})$ purged between splits to prevent causal information leakage.

---

## 6. Live Terminal Strategy Intelligence Dashboard Requirements

The Live Terminal sidebar replaces the legacy `"Strategy evaluation unavailable"` card with the **Strategy Tournament Intelligence Dashboard**:

1. **Market Context Header:**
   - Instrument (`BTC-USD`), Venue (`Coinbase Spot`), Current Completed Price & Timestamp.
   - Active Market Regime, HTF ADX value, Hysteresis Status (`CONFIRMED` / `TRANSITION`).
   - Overall Selection Verdict (`ABSTAIN` / `RESEARCH_ONLY`).
   - Execution Status (`DISABLED`).
2. **Top-5 Tournament Leaderboard Table & Cards:**
   - Strategy Name & Family.
   - Regime Compatibility (`MATCH`, `INCOMPATIBLE`, `NEUTRAL`).
   - Current Setup State (`SETUP_AVAILABLE`, `NO_SETUP`, `INELIGIBLE`, `BLOCKED`, `ABSTAIN`).
   - Historical Evidence: Net Expectancy (bps) with 95% Bootstrap CI, Wilson Win Rate CI, Max Drawdown %, Sortino Ratio, Sharpe Ratio, Profit Factor, Break-even Cost bps.
   - Status Badge: `VALIDATED_RESEARCH_CANDIDATE`, `INCONCLUSIVE`, `UNPROFITABLE_AFTER_COSTS`, `REGIME_DEPENDENT`, `BLOCKED_BY_DATA`, `ABSTAIN`.
3. **Current Setup Inspection Modal / View:**
   - Real-time setup levels: Hypothetical Entry, TP, SL, R:R, and Invalidation Reason.
   - If no trigger exists: Explicit `NO_SETUP` with diagnostic failure reason.
4. **Baselines Comparison View:**
   - Immediate toggle to compare candidates against `NO_TRADE`, `BUY_AND_HOLD`, `VOL_TARGETED_BULL`, and `MATCHED_RANDOM_ENTRY`.

---

## 7. Governed Approval
- **Lead Orchestrator:** Antigravity Research Orchestrator
- **Epistemic Invariant:** Live execution disabled; research transparency maintained.
