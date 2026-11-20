# BTCognitive V32.70 — Quantitative Trading Intelligence Audit

**Audit Date:** 30 October 2026  
**Milestone:** V32.70  
**Target:** Quantitative Engines, Indicator Libraries, Microstructure & Payoff Logic  

---

## 1. Quantitative Capability Assessment Matrix

We audited every quantitative capability against actual source code to distinguish genuine, functioning implementations from theoretical or disconnected code:

| Quantitative Capability | Implemented File Path | Actual Mechanism in Code | Status | Integration Level |
| :--- | :--- | :--- | :--- | :--- |
| **Market Regime Identification** | `engine/regime_strategy_tournament.py` | Causal logic on EMA50, EMA200, ADX(14), ATR(14), BBW. Classifies 4 discrete regimes. | **WORKING** | Core dependency of Analysis button. |
| **Volatility Forecasting** | `engine/realized_semi_variance.py`, `models/authoritative_model_registry.py` | Decomposes variance into upside/downside semi-variances; HAR OLS and QLIKE models. | **WORKING** | Verified mathematically; offline research only. |
| **Volatility Term Structure** | `engine/volatility_bridge.py` | Deterministic cross-horizon volatility mapping across 5m, 15m, 1h, 4h, 24h. | **WORKING** | Available via API; verified in unit tests. |
| **Trend Identification** | `engine/regime_strategy_tournament.py` | Causal moving average stack ($\text{Close} > \text{EMA}_{50} > \text{EMA}_{200}$) with ADX $\ge 22.0$. | **WORKING** | Active in 1-click analysis workflow. |
| **Momentum Indicators** | `features/build_features.py` | Wilder 14-period RSI, Donchian 24h/168h channel breakouts. | **WORKING** | Causal and mathematically verified. |
| **Order Book Imbalance (OBI)** | `engine/l2_microstructure_features.py` | $\text{OBI} = \frac{V_{\text{bid}} - V_{\text{ask}}}{V_{\text{bid}} + V_{\text{ask}}}$ across top $K=5$ book levels. | **WORKING** | Requires live L2 socket; idle in fixture mode. |
| **Order Flow Imbalance (OFI)** | `engine/l2_microstructure_features.py` | Cont, Kukanov & Stoikov (2014) event-based top-of-book order flow tracking. | **WORKING** | High-frequency logic implemented; needs live feed. |
| **Liquidity & Impact Proxies** | `engine/l2_microstructure_features.py` | Kyle's Lambda price impact proxy and Amihud illiquidity proxy. | **WORKING** | Microstructure module; standalone. |
| **Funding Rate Analysis** | `engine/funding_rate_research.py` | Normalizes perpetual funding rates; computes 8h holding cost drag. | **PARTIAL** | Historical parquet ends Sept 2026; live feed offline. |
| **Price Excursion Forecasting** | `engine/price_forecast_engine.py` | Parametric MFE / MAE quantile boundaries. | **PARTIAL** | Legacy ridge model blocked; conformal bands active. |
| **Expected Value (EV) Modeling** | `engine/payoff_engine.py` | Calculates net EV in basis points after venue fees (60/87 bps) and adverse slippage. | **WORKING** | Active; blocks setups if net $EV \le 0$. |
| **Risk/Reward & Geometry** | `engine/regime_strategy_tournament.py` | ATR-proportional Take-Profit and Stop-Loss (1.5x to 2.25x ATR). | **WORKING** | Frozen immutably upon proposal generation. |
| **Trade Invalidation Rules** | `engine/regime_strategy_tournament.py` | Explicit anomaly exit policies (e.g. 3 consecutive closes below EMA50, volume spikes). | **WORKING** | Active in simulation monitor loop. |
| **Uncertainty Estimation** | `engine/uncertainty_service.py` | Decomposes uncertainty into data reliability, regime certainty, and model agreement. | **WORKING** | Computes Shannon entropy and composite risk score. |

---

## 2. In-Depth Evaluation: Entry Opportunity Identification & Ranking

### 2.1 How Opportunities Are Currently Identified
When the user clicks "Analyse Setup", candidate strategies are screened via a 2-stage funnel:

1. **Stage 1: Regime Compatibility Filter**
   The current regime is classified (e.g., `VOLATILITY_EXPANSION`). Strategies in `VersionedStrategyRegistry` that do not support this regime are filtered out with explicit rejection reasons (e.g. `Regime mismatch: requires ['RANGE_BOUND']`). Quarantined strategies are immediately dropped.

2. **Stage 2: The 7/10 Preliminary Screen (`evaluate_7_of_10_screen`)**
   - The strategy must have **at least 7 Take-Profit hits out of the last 10 completed eligible attempts**.
   - Completed attempts are checked first from the prospective simulated ledger (`smart_entry_attempts.jsonl`).
   - If fewer than 10 prospective attempts exist, it falls back to verified historical walk-forward records.
   - If fewer than 10 total eligible records exist, the strategy is rejected with `INSUFFICIENT_EVIDENCE`.

### 2.2 Critical Product Flaw: The Tournament Abstention Deadlock
Once candidates pass the 7/10 screen, they are passed to `run_strategy_tournament_backtest()`.
As discovered in our architectural audit, lines 1162–1204 of `engine/regime_strategy_tournament.py` execute an unconditional early return:
```python
unavailable_reason = (
    "No verified walk-forward manifest matches the registered candidate strategies and frozen protocol. "
    "A fresh three-arm evaluation is also unavailable because aligned point-in-time AI forecasts and "
    "a matched baseline series are not supplied. No arm metrics were computed or reused."
)
return { ... "final_verdict": "ABSTAIN", ... }
```
**Consequence:**
- In the existing production codebase, **the tournament backtest ALWAYS abstains**.
- This means `#btn-analyse-setup` will **NEVER** output `SMART_ENTRY_AVAILABLE` under normal operating conditions; it will always conclude with `status: "ABSTAIN"`.
- **Verdict on Opportunity Ranking:** While the sorting and screening logic is mathematically implemented, **the end-to-end recommendation pipeline is intentionally blocked fail-closed** by governance rules pending fresh prospective validation data.

---

## 3. Epistemic Assessment: Can BTCognitive Predict Market Direction?

- **Unconditional Return Predictability:** Empirically audited LightGBM 4-lag return model achieves **53.28%** out-of-sample accuracy across 33,919 evaluations.
- **Economic Viability:** With an average gross excursion of ~15 bps per hour and roundtrip transaction costs of 14–20 bps (Coinbase 60–87 bps tier), a 53.28% hit rate yields a **negative net expectancy of -13.07 bps per bar**.
- **The 90% Win Rate Claim:** The application documentation correctly notes that any claim of a 90% directional win rate is an **unsupported research hypothesis**. The application's true quantitative strength lies in **volatility risk envelope containment**, NOT directional market timing.

