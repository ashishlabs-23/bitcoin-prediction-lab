# BTCognitive V25 — Governed Prospective Research & Operations Monitoring

**Specialist Role:** Agent C (Prospective Evidence & Monitoring Lead)  
**Date:** 19 October 2026  
**Status:** Protocol Frozen — Confirmatory Evidence Accumulation Active (`COLLECTING`)  
**Ledger Path:** `data/prospective_forecast_ledger.jsonl`  

---

## 1. Executive Summary & Epistemic Framework

Prospective forward validation eliminates the pervasive hazards of backtest overfitting, multiple hypothesis testing, and retrospective survivorship bias.

### Fundamental Operational Rules:
1. **Immutable Origins:** Forward predictions must be logged in `data/prospective_forecast_ledger.jsonl` at the exact point-in-time origin $t_{\text{origin}}$ prior to target maturity.
2. **Outcome Segregation:** Predictions and realized outcomes must remain physically and logically separated until $t_{\text{maturity}} = t_{\text{origin}} + h$ has elapsed.
3. **Zero Post-Hoc Tuning:** No model parameter, feature transformation, or target definition may be modified based on prospective observation results without registering a new, distinct protocol version.

---

## 2. Frozen Operational Horizon & Target Contracts

| Horizon Code | Span ($h$) | Target Metric | Target Formula | Reference Baseline | Authorized Challenger |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`1h`** | 1 Hour | Spot Price | $P_{t+1\text{h}}$ | Persistence: $\hat{P} = P_t$ | Ridge L2 ($\alpha=50.0$) |
| **`4h`** | 4 Hours | Spot Price | $P_{t+4\text{h}}$ | Persistence: $\hat{P} = P_t$ | Ridge L2 ($\alpha=50.0$) |
| **`24h`** | 24 Hours | Spot Price / Vol Proxy | $P_{t+24\text{h}}$ / `rv24h_var_ann` | Persistence / Rolling 30d | Ridge L2 / HAR-QLIKE-24h |
| **`168h`** | 168 Hours (7d) | Spot Price / Volatility | $P_{t+168\text{h}}$ / `rv7d_var_ann` | Persistence / Rolling 30d | Ridge L2 / HAR-RS-DOW |

*Target Isolation Note:* Volatility forecasting targets (`rv24h_var_ann`, `rv7d_var_ann`) serve market excursion and risk management. They are completely decoupled from future spot price level forecasts ($P_{t+h}$).

---

## 3. Census of Current Prospective Ledger Entries

An exhaustive inspection of `data/prospective_forecast_ledger.jsonl` yields:
- **Total Ledger Records:** 11 entries.
- **`24h` Target (`rv24h_var_ann`):**
  - Seed Entry: Aug 31, 2026 (resolved outcome: 0.098562)
  - Live Entry 1: Oct 15, 2026 (resolved outcome: 0.075116)
  - Overlapping Entries: 4 additional entries issued between Oct 15 and Oct 16 within the same 24-hour cycle.
  - **Clean Non-Overlapping Blocks ($|t_j - t_i| \ge 24\text{h}$):** **1 block** (Aug 31 to Oct 15).
- **`168h` Target (`rv7d_var_ann`):**
  - 5 entries issued between Oct 15 and Oct 16 scheduled to mature between Oct 22 and Oct 23.
  - **Mature Clean Blocks:** **0 blocks** (all pending scheduled maturity).
- **Current Operational Status:** **`COLLECTING`** (1 / 100 for 24h, 0 / 100 for 168h).

---

## 4. Governance Hurdle vs. Statistical Power Assessment

1. **Governance Hurdle (100 Clean Blocks):**
   - The requirement of 100 clean non-overlapping blocks is a governance hurdle designed to prevent premature release claims based on short-term lucky streaks.
   - It represents ~100 calendar days for 24-hour forecasts and ~700 calendar days for 168-hour forecasts.
2. **Statistical Power Reality:**
   - In financial time series with high noise-to-signal ratios, achieving 80% statistical power to detect small skill differentials ($\Delta \text{RMSE} < 0.5\%$) typically requires $N > 1,000$ independent blocks.
   - Reaching 100 blocks qualifies a model for formal statistical review, but does **not** automatically authorize promotion.

---

## 5. Ledger Integrity & Write Governance

- **Stable Keys & Idempotency:** Each forecast entry must carry a unique `forecast_id` UUID. Re-running the logging worker must never append duplicate records for the same timestamp and horizon.
- **Fail-Closed Resolution:** If an exchange API downtime causes missing data at $t_{\text{maturity}}$, the resolution state is marked `DEGRADED_UNRESOLVED` rather than interpolating synthetic prices.
