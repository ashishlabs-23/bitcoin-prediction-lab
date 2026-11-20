# BTCognitive V32.20 — Execution-Cost Contract & Research Eligibility Gate Report

**Date:** October 2026  
**Status:** BLOCKED — EXECUTION-COST CONTRACT UNRESOLVED  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Forensic reconciliation of transaction-cost assumptions, primary source fee audit, dataset provenance boundaries, and research eligibility gate.  

---

## 1. Executive Summary & Gate Decision

### Governed Verdict: `BLOCKED — EXECUTION-COST CONTRACT UNRESOLVED`

A forensic investigation of transaction-cost assumptions across BTCognitive code, research scripts, and synthesis reports revealed severe, compounding contradictions:
1. **The 20x US Cost Divergence:** Historical directional evaluations in `research/evaluate_v5_directional_and_drift.py` assumed a **9.3 bps round-trip friction** for US trading, whereas the actual Coinbase US Retail schedule incurs **187.0 bps round-trip** (a 20.1x underestimation).
2. **The 8.2x EU/UK Cost Divergence:** The same evaluation script assumed a **13.0 bps round-trip friction** for EU/UK trading, whereas the actual Coinbase EU/UK Retail schedule incurs **107.0 bps round-trip** (an 8.2x underestimation).
3. **Cross-Product Venue Contamination:** The 9.3 bps and 13.0 bps figures were imported from **Binance USDT-M Perpetual Futures VIP 0 taker rates**, yet were applied to a spot BTC price series and mislabeled as "US" and "EU/UK" retail trading.
4. **Spot Shorting Non-Feasibility:** Both the generic 87.0 bps model and regional retail models evaluate short trade candidates on Coinbase Spot (`BTC-USD`), where retail accounts cannot borrow or short spot BTC.
5. **Dataset Provenance Contamination:** The primary dataset `data/raw/ohlcv.parquet` remains an unverified, mixed-source hybrid (historical Binance/Bitstamp concatenated with Coinbase Exchange spot backfills across a 742-hour gap).

Consequently, **no valid, empirically defensible cost contract currently exists that aligns the historical dataset with an executable market venue**. The research eligibility gate is formally set to **`BLOCKED`**. No strategy backtests, tournaments, or net expectancy claims are authorized until a unified dataset and matching execution venue contract are established.

---

## 2. Source-to-Code Cost Assumption Inventory

The following table traces every cost assumption identified across the repository:

| Cost Label / Value | Units | Primary Origin in Repository | Consuming Modules / Scripts | Reported Findings Dependent on Value | Forensic Discrepancy & Analysis |
|:---|:---:|:---|:---|:---|:---|
| **US: 9.3 bps** | bps (RT) | `research/evaluate_v5_directional_and_drift.py` (lines 7, 134, 138) | `research/evaluate_v5_directional_and_drift.py` | Reported break-even drift $\mu^* = +0.0637$ and $+0.046R$ net return on Variant V5. | **Mislabeled & Conflated.** Derived from Binance Futures VIP 0 taker with BNB discount (9.0 bps + spread) and conflated with Hawkes forecast error (9.30 bps MAE). Retail Coinbase US is 187 bps. |
| **EU/UK: 13.0 bps** | bps (RT) | `research/evaluate_v5_directional_and_drift.py` (lines 7, 133, 137) | `research/evaluate_v5_directional_and_drift.py` | Reported break-even drift $\mu^* = +0.0891$ and $+0.024R$ net return on Variant V5. | **Mislabeled Derivative Rate.** Derived from Binance Futures VIP 0 taker without BNB discount (10 bps + spread + slippage = 12-13 bps). Retail Coinbase EU/UK is 107 bps. |
| **India: 27.0 bps** | bps (RT) | `engine/execution_cost_model.py` (lines 62-74), `probabilistic_entry_engine.py` (lines 68-76) | `run_rigorous_replay_v2.py`, `v32_17_empirical_remediation_report.md` | Reported Net Expectancy of $-0.1656R$ per trade ($-404.0R$ cumulative, Sharpe $-3.97$). | **Empirical Spot Schedule.** Accurately reflects Coinbase International/India retail taker tier (0.10% each side = 20 bps + 7 bps spread/slip). Confirmed negative expectancy. |
| **Coinbase Advanced: 87.0 bps** | bps (RT) | `engine/execution_cost_model.py` (lines 75-87), `probabilistic_entry_engine.py` (lines 77-85) | `engine/smart_entry_engine.py`, `api/routes_research.py` | Smart Entry telemetry, CandidateSetup friction, break-even win rate ($>68\%$). | **Documented Spot Baseline.** Based on Coinbase Advanced Tier 1 (<$10k vol: 40 bps taker each side + 7 bps spread/slip). Shorting spot is impossible for retail. |
| **Coinbase US Retail: 187.0 bps** | bps (RT) | `engine/execution_cost_model.py` (lines 36-48), `probabilistic_entry_engine.py` (lines 50-58) | `run_rigorous_replay_v2.py`, `v32_17_empirical_remediation_report.md` | Reported Net Expectancy of $-1.1689R$ per trade ($-2,852.1R$ cumulative, Sharpe $-21.74$). | **Primary-Source Validated.** Reflects official Coinbase US retail schedule (0.90% taker each side = 180 bps + 7 bps spread/slip). Catastrophically negative expectancy. |
| **Coinbase EU/UK Retail: 107.0 bps** | bps (RT) | `engine/execution_cost_model.py` (lines 49-61), `probabilistic_entry_engine.py` (lines 59-67) | `run_rigorous_replay_v2.py`, `v32_17_empirical_remediation_report.md` | Reported Net Expectancy of $-0.6672R$ per trade ($-1,628.1R$ cumulative, Sharpe $-14.55$). | **Primary-Source Validated.** Reflects official Coinbase EU/UK retail schedule (0.50% taker each side = 100 bps + 7 bps spread/slip). Catastrophically negative expectancy. |
| **Legacy V30: 91.04 bps** | bps (RT) | `engine/execution_cost_model.py` (line 176), `probabilistic_entry_engine.py` (lines 113-120) | `prospective_entry_ledger.jsonl` | Produced the legacy $1.0877R$ friction entry in quarantined V1 ledger. | **Double-Counted Slippage.** Combined 80 bps commission + 3 bps spread + 8.04 bps slippage. Reconciled in V32.16 audit. |
| **Binance Futures: 12.0 bps** | bps (RT) | `engine/execution_cost_model.py` (lines 101-128), `probabilistic_entry_engine.py` (lines 104-112) | Sensitivity models only (`SENSITIVITY_ONLY_NON_SPOT`) | Hypothetical sensitivity testing. | **Perpetual Contract.** Valid for Binance USDT-M VIP 0, but inapplicable to spot `BTC-USD` series; funding rates and basis risk omitted. |

---

## 3. Primary Source Exchange Contract Verification

The following primary documentation was retrieved and verified on **2026-10-24**:

### 3.1 Coinbase Advanced Trade (Spot BTC-USD)
- **Primary Source:** Coinbase Advanced Trading Documentation  
  `https://help.coinbase.com/en-in/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees`
- **Product Type:** Centralized Spot Order Book (`BTC-USD`).
- **Fee Tier Structure (30-day trailing volume):**
  - **Tier 1 (<$10,000 volume):**
    - Maker Fee: **0.25%** (25.0 bps) per side.
    - Taker Fee: **0.40%** (40.0 bps) per side.
    - Two-sided Taker Commission: **80.0 bps**.
  - **Regional Retail Overrides (Sept 2026 Schedule):**
    - United States Retail: **0.50% maker / 0.90% taker** (180.0 bps two-sided taker).
    - European Union & UK Retail: **0.25% maker / 0.50% taker** (100.0 bps two-sided taker).
    - International / India Retail: **0.09% maker / 0.10% taker** (20.0 bps two-sided taker).
- **Microstructure Drag:**
  - Empirical Half-Spread: **1.5 bps** per side (3.0 bps round-trip).
  - Empirical Slippage: **2.0 bps** per side (4.0 bps round-trip).
- **Execution Feasibility:** Spot market only. **Retail accounts cannot execute short trades.**

### 3.2 Binance USDT-Margined Perpetual Futures (BTCUSDT)
- **Primary Source:** Binance Official Futures Fee Schedule  
  `https://www.binance.com/en/fee/futureFee`
- **Product Type:** Cash-Settled Perpetual Derivative (`BTCUSDT`).
- **Fee Tier Structure (VIP 0 Regular User):**
  - Standard Maker Fee: **0.020%** (2.0 bps) per side.
  - Standard Taker Fee: **0.050%** (5.0 bps) per side (10.0 bps round-trip).
  - With BNB 10% Discount: **0.018% maker / 0.045% taker** (9.0 bps round-trip).
- **Microstructure Drag:**
  - Half-Spread: **0.5 bps** per side (1.0 bps round-trip).
  - Slippage: **0.5 bps** per side (1.0 bps round-trip).
  - Round-trip Taker Total: **12.0 bps** (standard) or **9.3 bps** (with BNB discount and tight spread).
- **Holding Financing:**
  - 8-hour settlement funding rate: baseline average $\pm 1.0 \text{ bps}$ per 8 hours (adds $3.0 \text{ bps}$ across a 24-hour holding period).
- **Execution Feasibility:** Symmetric native long and short. **Ineligible for US retail traders** (CFTC regulatory exclusion).

---

## 4. Origin of the Discrepancies: Forensics

1. **Why was US cost listed as 9.3 bps in V5 research?**
   - In `research/evaluate_v5_directional_and_drift.py`, the directive requested testing "US 9.3 bps".
   - Forensic tracing revealed this number was derived by taking **Binance USDT-M Futures VIP 0 with BNB discount** ($4.5 \text{ bps} \times 2 = 9.0 \text{ bps} + 0.3 \text{ bps spread} = 9.3 \text{ bps}$), and confusing it with the Hawkes point-process error metric (where the 5-minute MFE Mean Absolute Error was reported as **9.30 bps** in `research/reports/hawkes_live_statistical_gate.md`).
   - Applying a 9.3 bps perpetual futures discount rate to a retail US trader on Coinbase Spot created an artificial 20x cost distortion, producing a spurious positive expectancy of $+0.046R$ that vanishes into a devastating **$-1.17R$ loss per trade** under actual Coinbase US fees.
2. **Why was EU/UK cost listed as 13 bps?**
   - In the same script, 13 bps was used for EU/UK. This was the standard **Binance USDT-M Futures VIP 0 taker rate** ($5.0 \text{ bps} \times 2 = 10.0 \text{ bps} + 1.0 \text{ bps spread} + 2.0 \text{ bps slippage/funding} = 13.0 \text{ bps}$).
   - On Coinbase EU/UK, the actual entry tier is 50 bps taker each side ($107.0 \text{ bps}$ total), turning the claimed $+0.024R$ profit into a **$-0.67R$ loss per trade**.

---

## 5. Dataset Provenance Boundary

The research dataset in `data/raw/ohlcv.parquet` ($N = 41,419$ hourly bars, 2022-01-01 to 2026-10-23) cannot serve as a valid execution baseline:
- **Mixed Origins:** Rows 0 to 40,901 were sourced from historical Binance BTCUSDT futures / Bitstamp spot ingestion, while rows 40,902 to 41,418 were backfilled from the Coinbase Exchange REST API.
- **The September 2026 Gap:** A total of **742 consecutive hours (30.92 calendar days)** are missing from `2026-09-01 06:00 UTC` to `2026-10-02 05:00 UTC`.
- **Semantic Mismatch:** The price series mixes USDT-denominated perpetual derivative prices with USD-denominated fiat spot prices. Applying a spot fee model to a futures price series (or vice versa) invalidates historical simulation integrity.

---

## 6. Win-Rate Claim Discipline & Mathematics

The aspirational target of a 70–80% win rate must be evaluated with mathematical precision:

### 6.1 Conditional vs. Unconditional Win Rates
- **Unconditional Outcome Distribution:** In a double-barrier geometry ($k_{\text{TP}} = 1.5\sigma_H, k_{\text{SL}} = 1.0\sigma_H, H = 24\text{h}$), there are three outcomes:
  $$P(\text{TP First}) + P(\text{SL First}) + P(\text{Timeout}) = 1.0$$
  Under driftless diffusion ($\mu = 0$):
  - $P(\text{TP First}) \approx 17.5\%$
  - $P(\text{SL First}) \approx 36.5\%$
  - $P(\text{Timeout}) \approx 46.0\%$
- **Conditional Win Rate (Among Resolved Trades Only):**
  $$P(\text{TP} \mid \text{Resolved}) = \frac{P(\text{TP First})}{P(\text{TP First}) + P(\text{SL First})} = \frac{0.1755}{0.1755 + 0.3650} \approx 32.5\%$$
  In empirical backtests on 2,440 non-overlapping trades, the observed conditional rate was **34.2%** (flat across all model deciles from 33.4% to 38.9%).

### 6.2 Evidentiary Discipline
- An unconditional 70–80% hit rate would require an immense directional drift ($\mu^* \gg 2.5$), which has no precedent in empirical liquid crypto markets.
- Even conditional on resolution, achieving a 70–80% win rate with an asymmetric 1.5 : 1.0 barrier requires predictive discrimination far beyond random noise.
- Current empirical evidence across 2022–2026 demonstrates that the meta-model entry probability signal has an AUC of **$0.5145 \pm 0.01$**, which is statistically indistinguishable from zero predictive skill.
- While a 70–80% win rate is not universally mathematically impossible under extreme exogenous regime shifts, it is **wholly unsupported by empirical data** and must remain strictly labeled as an **unvalidated research hypothesis**.

---

## 7. Execution-Cost Eligibility Gate Decision

To ensure scientific integrity, the research gate is formally set:

| Gate Component | Status | Required Resolution Action |
|:---|:---:|:---|
| **Execution Cost Contract** | `BLOCKED` | Must freeze one single venue schedule (Coinbase Advanced 87 bps or Binance Futures 12 bps) matching the data. |
| **Dataset Provenance** | `BLOCKED` | Must establish a single-origin, contiguous dataset with verified licensing and timestamp semantics. |
| **Directional Feasibility** | `BLOCKED` | Must disallow spot shorts or transition the research baseline to perpetual futures with explicit funding. |
| **Net Expectancy Claims** | `DISQUALIFIED` | No net expectancy or break-even win rate claims may be reported until all three gates are cleared. |

### Final Governed Decision:
`BLOCKED — EXECUTION-COST CONTRACT UNRESOLVED`
