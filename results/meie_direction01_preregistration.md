# Pre-Registration: MICRO-DIRECTION-01 — Conditional Direction After Ignition
**Document Status**: LOCKED & IMMUTABLE  
**Pre-Registration ID**: MEIE-DIRECTION-01-v1.0  
**Locked At**: 2026-08-26T09:30:00Z  
**Activation Precondition**: MEIE-EVENT-01 must reach N ≥ 100 events with H₁ not rejected.  
**Depends On**: `results/meie_event01_preregistration.md` (MEIE-EVENT-01)

---

## 1. Scientific Question

Conditional on an IGNITION event (as defined in MEIE-EVENT-01), can the **sign of OFI** and
**Hawkes directionality** predict the direction of the subsequent excursion?

$$H_1: P(\text{sign}(r_h) = +1 \mid \text{IGNITION},\; z_{\text{ofi}} > 0,\; \lambda_{\text{buy}} > \lambda_{\text{sell}}) > 0.55$$
$$H_1: P(\text{sign}(r_h) = -1 \mid \text{IGNITION},\; z_{\text{ofi}} < 0,\; \lambda_{\text{sell}} > \lambda_{\text{buy}}) > 0.55$$

This is a **conditional classification problem**, not unconditional BTC price prediction.

---

## 2. Definitions & Locked Parameters

### 2.1 Directional Signal (LOCKED)

The directional signal at IGNITION time $t$ is:

| Signal | Definition | Long Signal | Short Signal |
|:---|:---|:---|:---|
| **OFI sign** | `sign(z_ofi)` at event time | `z_ofi > 0.5` | `z_ofi < −0.5` |
| **Hawkes sign** | `lambda_buy > lambda_sell` from shadow session | buy > sell | sell > buy |

A **directional IGNITION** requires both signals to agree:
- **LONG-IGNITION**: `z_ofi > 0.5` AND `lambda_buy > lambda_sell`
- **SHORT-IGNITION**: `z_ofi < −0.5` AND `lambda_sell > lambda_buy`
- **AMBIGUOUS**: signals disagree → classify as `NO_DIRECTION`, not traded.

### 2.2 Outcome Definition (LOCKED)

- Horizon $h$: **15 and 30 candles** (same as EVENT-01 for comparability).
- Positive outcome: close at $t + h$ > open at $t + 1$ (for LONG-IGNITION).
- Negative outcome: close at $t + h$ < open at $t + 1$ (for SHORT-IGNITION).
- AMBIGUOUS events are recorded but excluded from directional accuracy calculation.

### 2.3 Evaluation Criteria (LOCKED)

- **Minimum sample**: N ≥ 60 directional IGNITION events (≥30 LONG, ≥30 SHORT).
- **Primary statistic**: Hit rate (directional accuracy).
- **Significance**: Binomial test against 50% null, $p < 0.05$ (one-sided).
- **Practical significance**: Hit rate ≥ 55%.
- **Both** sides (LONG and SHORT) must meet criteria independently, or the directional
  hypothesis is rejected for that side.

---

## 3. Null Hypothesis

$$H_0: P(\text{correct direction} \mid \text{directional IGNITION}) \leq 0.50$$

Rejection requires: binomial $p < 0.05$ AND empirical hit rate ≥ 55% for $N \geq 60$ events.

---

## 4. Activation Conditions for MEIE-EXECUTION-01

MEIE-EXECUTION-01 is **not activated until**:
1. MEIE-DIRECTION-01 H₁ is not rejected for at least one direction (LONG or SHORT).
2. N ≥ 60 directional IGNITION events are recorded.
3. The interim audit report `results/meie_direction01_interim_report.md` is committed.

---

## 5. Threshold Mining Prohibition

> [!CAUTION]
> The directional thresholds (`z_ofi > 0.5`, `z_ofi < -0.5`) are permanently locked.
> No adjustment is permitted based on observed data. Any change requires a new pre-registration
> version (MEIE-DIRECTION-01-v2.0) with full event counter reset.
