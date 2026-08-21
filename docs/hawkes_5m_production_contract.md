# 🦅 Hawkes 5-Minute Microstructure Candidate Production Contract

## 1. Scope & System Definition

* **Model Identifier:** `v1.0.0-challenger-hawkes-microstructure`
* **Target Horizon:** 5-Minute Maximum Favorable Excursion (MFE) & Maximum Adverse Excursion (MAE).
* **Role:** High-Frequency Microstructure Challenger.
* **Current Operational Status:** **`VALIDATED_SHADOW_MODEL`** (Non-executing; Ridge remains Production).

---

## 2. Input & Output Contract

### Inputs:
* Point-in-Time L2 Order Book & Trade Event Stream (Monotonic timestamp $t_i \le t_{i+1}$).
* 16 Microstructure Factors (Microprice, Depth/Top Imbalance, OFI, Signed Volume, Realized Volatility).

### Outputs:
* MFE Quantiles: $P_{10}, P_{50}, P_{90}$
* MAE Quantiles: $P_{10}, P_{50}, P_{90}$
* Hawkes Intensities: $\lambda_{\text{buy}}, \lambda_{\text{sell}}, \lambda_{\text{liq}}, \lambda_{\text{vol}}$, Event pressure.
* Secondary Directional Evidence: $P(\text{up}), P(\text{down})$ (Classified as `BULLISH`, `BEARISH`, or `NO_EDGE`).
* Uncertainty Score: Interval dispersion $(P_{90} - P_{10})_{\text{MFE}} + (P_{90} - P_{10})_{\text{MAE}}$.

---

## 3. Operational States & Safety Invariants

| State | Definition | Action |
| :--- | :--- | :--- |
| **`HEALTHY`** | Latency $< 5$ms, zero dropped events, coverage $\ge 90\%$ | Normal shadow forecast emission |
| **`WATCH`** | Latency in $[5, 10]$ms, PSI in $[0.10, 0.20]$ | Log telemetry warnings |
| **`DEGRADED`** | Stale feed ($> 1500$ms) or dropped events | Mark data quality DEGRADED |
| **`INVALID`** | Out-of-order timestamp or corrupted schema | Halt shadow emission |
| **`TRADING_NOT_ALLOWED`** | Execution invariant | Order placement strictly forbidden |
