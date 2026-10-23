# V26 Prospective Evaluation & Multiple Testing Audit

**Agent:** Agent F (Prospective Evidence, Ledgers & Multiple Testing Governance)  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  
**Governing Rule:** A minimum of 100 non-overlapping clean blocks is required before confirmatory prospective evaluation. Retrospective backtests cannot replace prospective proof.

---

## 1. Prospective Ledger Audit

The prospective evaluation system operates on an append-only JSONL ledger located at `data/prospective_forecast_ledger.jsonl`.

### 1.1 Ledger Census & Integrity
- **Total Ledger Records Logged:** 11 records.
- **Append-Only Immutability:** Verified. Issue timestamps ($t_{\text{issue}}$) are strictly monotonic and recorded in UTC before target maturity ($t_{\text{maturity}}$).
- **Mature 24-Hour Blocks:** Exactly **1 clean mature 24-hour block** has reached maturity and resolved against closed empirical market candles.
- **Mature 168-Hour (7-Day) Blocks:** Exactly **0 mature 168-hour blocks** have resolved.
- **Governance Hurdle:** 100 non-overlapping clean mature blocks.
- **Hurdle Attainment:** $1 / 100$ ($1.0\%$).
- **Current Operational Status:** **`COLLECTING`** (Under no circumstances may this status be accelerated, simulated, or promoted to `CONFIRMATORY_GATE`).

---

## 2. Retrospective vs Prospective Separation

A fundamental epistemic principle of BTCognitive is the strict firewall between retrospective development data and untouched prospective data:
1. **Retrospective Replay (Development):** The 2021–2026 historical dataset (`ohlcv.parquet`) has been repeatedly analyzed, inspected, and backtested. Regardless of whether train/test splits are used, repeated experimentation introduces selection bias and overfitting.
2. **Prospective Ledger (Validation):** Only forecasts logged in real time prior to candle formation qualify as prospective evidence. Synthetic backfilling or post-hoc generation is strictly prohibited by governance rules.

---

## 3. Multiple Testing & Selection Bias Analysis

When multiple model specifications (e.g., Ridge, Lasso, ElasticNet, LightGBM, Random Forests, HAR variants) and strategy rules (Dual-EMA, RSI, Bollinger Squeeze, Regime Router) are evaluated on the same historical dataset, standard significance thresholds are invalid.

### 3.1 Deflated Sharpe Ratio (DSR) & PBO Framework
Following Bailey & López de Prado (2014) and Harvey, Liu, & Zhu (2016):
- **Multiple Trials Adjusted Hurdle:** In a tournament with $M \ge 4$ candidate strategies, the expected maximum Sharpe ratio under the null hypothesis of zero true skill is:
  $$\mathbb{E}[\max_m \mathrm{SR}_m] \approx \sqrt{2 \ln M} \cdot \sigma_{\mathrm{SR}}$$
- With $M=4$ and 9,975 hourly observations, any apparent gross Sharpe ratio below $1.5$ is statistically indistinguishable from selection bias.
- Because all active strategies evaluated produce negative net returns after transaction costs, the Probability of Backtest Overfitting (PBO) for active strategies is effectively **100%**.
- **No strategy may be promoted.**

---

## 4. Governance Decision & Prospective Roadmap

1. **Protocol Preservation:** The 100-block hurdle remains strictly frozen and uncompromised.
2. **Automated Accumulation:** The background worker continues issuing prospective forecasts hourly.
3. **Status:** **`COLLECTING`** ($1 / 100$ mature blocks).
