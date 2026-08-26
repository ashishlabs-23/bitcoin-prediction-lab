# Pre-Registration: MICRO-EXECUTION-01 — Positive Net Expected Value Gate
**Document Status**: LOCKED & IMMUTABLE  
**Pre-Registration ID**: MEIE-EXECUTION-01-v1.0  
**Locked At**: 2026-08-26T09:30:00Z  
**Activation Precondition**: MEIE-DIRECTION-01 must pass for at least one direction.  
**Depends On**: `results/meie_direction01_preregistration.md` (MEIE-DIRECTION-01)

---

## 1. Scientific Question

Can the observed microstructure state predict whether a theoretical signal can actually be
executed at **positive net expected value** after realistic execution costs?

$$H_1: E[EV_{\text{net}} \mid \text{directional IGNITION}] > 0$$

where:
$$EV_{\text{net}} = P(TP) \cdot R_{TP} - P(SL) \cdot R_{SL} - C_{\text{fee}} - C_{\text{spread}} - C_{\text{impact}}$$

---

## 2. Definitions & Locked Parameters

### 2.1 Gross Edge Estimation (LOCKED)

The gross edge per trade is derived from the existing `RangeForecastService` conformal envelopes:

- **TP distance**: `mfe_p50` (median favorable excursion) for 15m horizon.
- **SL distance**: `mae_p25` (25th percentile adverse excursion) — tighter than median to limit loss.
- **P(TP)**: Estimated as the empirical hit rate from MEIE-DIRECTION-01 (locked after that stage).
- **P(SL)**: `1 - P(TP)` (simplified; no timeout path in this first experiment).
- **Risk-reward ratio**: `TP_dist / SL_dist` — must be ≥ 1.5 for a trade to be considered.

### 2.2 Execution Cost Model (LOCKED)

Uses **existing `ExecutionSimulator`** from `backtest/execution_simulator.py`:

| Cost Component | Parameter | Value |
|:---|:---|:---|
| Taker fee | `taker_fee_bps` | 5.0 bps (0.05%) entry + exit = **10 bps total** |
| Slippage base | `base_slippage_bps` | 2.0 bps |
| VPIN toxicity multiplier | Live `z_vpin` at trade time | `1.0 + max(0, (vpin - 0.5) * 2.0)` |
| Size impact | `sqrt(size_usd / 100000)` factor | Applied from ExecutionSimulator formula |

Total execution friction budget: estimated **15–25 bps** depending on VPIN state.

### 2.3 Net EV Threshold (PRIMARY GATE — LOCKED)

A trade is **only considered** when:

$$EV_{\text{net}} > 0 \text{ bps}$$

This replaces DSR ≥ 0.95 as the primary execution gate for MEIE trades.
DSR is computed as a **secondary diagnostic only** after each batch of 50 trades.

### 2.4 Execution Risk Escalation (LOCKED)

The trade is **blocked** (overrides positive EV) when:

| Condition | Threshold |
|:---|:---|
| VPIN toxicity is extreme | `z_vpin > 2.5` at execution time |
| Spread proxy is extreme | `z_spread > 2.0` |
| Observable data quality | `data_quality == "INVALID"` from Observatory |

These conditions model the **hidden liquidity risk** identified in the 2026 SSRN study:
visible book depth becomes unreliable under stress, so execution is blocked when toxicity
or spread signals suggest hidden liquidity withdrawal.

---

## 3. Null Hypothesis

$$H_0: E[EV_{\text{net}} \mid \text{directional IGNITION}] \leq 0$$

Evaluated over **N ≥ 30 executed trades** (separate from IGNITION event count).
Primary test: one-sample t-test on realized `EV_net` series, $p < 0.05$ one-sided.

---

## 4. P&L Measurement (LOCKED)

Trades execute against real Binance 1-minute candle H/L/C using the existing
`check_position_closure_high_low` from `backtest/simulate.py`.

Outcomes recorded per trade:
- `gross_pnl_bps`: realized excursion / entry price × 10,000
- `fee_bps`: 10 bps flat
- `slippage_bps`: from ExecutionSimulator at execution VPIN
- `net_pnl_bps`: gross - fee - slippage
- `ev_predicted_bps`: EV_net predicted by payoff engine at t0
- `ev_error_bps`: net_pnl_bps - ev_predicted_bps (calibration tracking)

---

## 5. Isolation Invariant

> [!IMPORTANT]
> MEIE-EXECUTION-01 trades are recorded in **separate table `meie_trades`** in `results/meie_memory.db`.
> They do NOT affect the existing Arena experiment balance, win rate, equity curve, or model registry.
> The existing $N=720$ Observatory audit is completely isolated from MEIE execution.
> Promotion of a MEIE strategy to the main Arena requires a separate explicit decision
> after the $N=720$ audit concludes and MEIE-EXECUTION-01 reaches N ≥ 30 evaluated trades.

---

## 6. Threshold Mining Prohibition

> [!CAUTION]
> All thresholds above are permanently locked: `EV_net > 0`, `RR ≥ 1.5`, `z_vpin > 2.5`,
> `z_spread > 2.0`. No post-hoc adjustment is permitted.
