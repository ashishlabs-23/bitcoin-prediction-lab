# BTCognitive V28 — Triple-Barrier Event Labeling & Methodology Report

**Version:** 28.0.0  
**Status:** VALIDATED RESEARCH METHODOLOGY  
**Resolver Version:** `ENTRY_TP_SL_RESOLVER_V1`  

---

## 1. Mathematical Formulation of Candidate Entry Events

In traditional time-series backtesting, positions are re-evaluated on fixed arbitrary time intervals (e.g. daily or hourly close). In **BTCognitive V28**, trade evaluation is modeled as discrete, event-based structural setups evaluated under the **Triple-Barrier Framework** (de Prado, 2018; Lopez de Prado & Bailey, 2014).

For any candidate event triggered at decision timestamp $t_0$, the trade outcome is bounded by three barriers:
1. **Upper Horizontal Barrier (Profit Target):** Reached when market price touches $P_{\text{TP}}$.
2. **Lower Horizontal Barrier (Stop Loss):** Reached when market price touches $P_{\text{SL}}$.
3. **Vertical Barrier (Holding Horizon Limit):** Time limit $t_{\text{timeout}} = t_0 + H$ (frozen at $H = 24\text{h}$ of closed hourly bars).

---

## 2. Causal Fill Model & Point-in-Time Timing

A common source of backtest inflation is assuming that a signal generated at candle close $C_{t_0}$ can be filled at $C_{t_0}$ without slippage.

In BTCognitive V28:
- **Signal Timestamp ($t_0$):** Candle close of bar $t_0$.
- **Fill Timestamp ($t_{\text{fill}} = t_0 + \Delta t$):** Open of candle $t_0 + 1$ ($O_{t_0 + 1}$).
- **Executable Price:**
  $$\begin{aligned}
  P_{\text{entry}}^{\text{LONG}} &= O_{t_0 + 1} \times \left(1 + \frac{\text{slippage\_bps}}{10000}\right) \\
  P_{\text{entry}}^{\text{SHORT}} &= O_{t_0 + 1} \times \left(1 - \frac{\text{slippage\_bps}}{10000}\right)
  \end{aligned}$$
Where base slippage is set to 2.0 bps ($0.02\%$).

---

## 3. Volatility-Scaled Barrier Geometry

Universal fixed-dollar barriers (e.g. "$500 stop") fail across changing regimes because Bitcoin's price has ranged from $10,000 to $90,000+. V28 scales barriers dynamically by trailing realized volatility $\sigma_{t_0}$ (or 24h Average True Range):

$$\begin{aligned}
P_{\text{TP}}^{\text{LONG}} &= P_{\text{entry}} \times (1 + k_{\text{TP}} \sigma_{t_0}) \\
P_{\text{SL}}^{\text{LONG}} &= P_{\text{entry}} \times (1 - k_{\text{SL}} \sigma_{t_0}) \\
P_{\text{TP}}^{\text{SHORT}} &= P_{\text{entry}} \times (1 - k_{\text{TP}} \sigma_{t_0}) \\
P_{\text{SL}}^{\text{SHORT}} &= P_{\text{entry}} \times (1 + k_{\text{SL}} \sigma_{t_0})
\end{aligned}$$

Where:
- $k_{\text{TP}} = 1.5$ (default profit multiple).
- $k_{\text{SL}} = 1.0$ (default stop multiple).
- $\sigma_{t_0} = \max(0.008, \text{Std}(\log r_{24\text{h}}) \times \sqrt{24})$.

---

## 4. Conservative Intrabar Collision Rule

When evaluating historical OHLC bars, it is possible for a single bar $t$ to span both barriers:
$$\text{High}_t \ge P_{\text{TP}} \quad \text{AND} \quad \text{Low}_t \le P_{\text{SL}}$$

### Epistemic Invariant:
Without sub-minute tick order books, it is physically impossible to know whether the high occurred before the low.
- Optimistic simulators assume the profit target was hit first, massively inflating backtest win rates.
- **BTCognitive V28 strictly enforces `SL_FIRST`**: whenever an intrabar collision occurs, the outcome is resolved as an adverse stop-loss touch.
- Zero optimistic tie-breaking is permitted.

In the verified Bitstamp 1m sample ($N=500$ pilot trades), 3 ambiguous collisions occurred; all 3 were resolved to `SL_FIRST`.

---

## 5. Excursion Analysis: MFE and MAE

For every candidate event, regardless of final outcome, the engine tracks excursions across its holding window:
- **Maximum Favourable Excursion (MFE):** The maximum peak unrealized gain in R-multiples achieved prior to exit.
- **Maximum Adverse Excursion (MAE):** The maximum peak unrealized loss in R-multiples sustained prior to exit.

Tracking MFE/MAE prevents "lucky wins" where price came within 1 bps of stopping out before reversing.

---

## 6. Purging, Embargoing & Overlapping Label Handling

Because trade outcomes can take up to 24 hours to resolve, consecutive candidate setups generate overlapping event windows. Evaluating overlapping trades as independent observations yields severe serial dependence and artificially narrow confidence intervals.

In V28:
- Overlapping holding periods are purged or embargoed during walk-forward training.
- Standard errors and confidence intervals are computed using dependence-aware stationary block bootstrapping.
