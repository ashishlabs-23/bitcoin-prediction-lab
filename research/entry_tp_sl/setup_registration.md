# Structural Setup Registration Document (Phase 6C)

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Registration Date:** `2026-10-07`  
**Status:** `FROZEN_DETECTOR_REGISTRATION`  

---

## 1. Setup Family Inventory

The research track authorizes exactly two causal structural setup detectors:

| Setup ID | Name | Core Structural Thesis | Parameters (Locked) | Side Determination |
|---|---|---|---|---|
| **`A1_SWEEP_RECLAIM`** | Liquidity Sweep / Reclaim | False breakout beyond recent swing extremum followed by immediate mean-reverting candle close inside range. | `swing_lookback_bars = 24` (6h), `sweep_min_pct = 0.05%`, `sweep_max_pct = 2.0%`, `cooldown_bars = 4` (1h). | **LONG** on low sweep/reclaim; **SHORT** on high sweep/reclaim. |
| **`A2_RANGE_RECLAIM`** | Range Reclaim | Compression boundary breakout failure returning to 12-hour value area. | `range_lookback_bars = 48` (12h), `range_quantile_low = 0.15`, `range_quantile_high = 0.85`, `reclaim_buffer_pct = 0.10%`. | **LONG** on lower boundary reclaim; **SHORT** on upper boundary reclaim. |

---

## 2. Direction Ownership Invariant
- The setup detector exclusively determines trade direction (`Side.LONG` or `Side.SHORT`).
- Downstream meta-models (Logistic / LightGBM) possess strictly binary action choices: `ACCEPT` or `ABSTAIN`.
- The meta-model is **PROHIBITED** from flipping direction (`LONG -> SHORT` or `SHORT -> LONG`).
