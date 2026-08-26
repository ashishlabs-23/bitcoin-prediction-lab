# Pre-Registration: MICRO-EVENT-01 — Volatility Ignition / Excursion Probability
**Document Status**: LOCKED & IMMUTABLE PRIOR TO MEIE ARENA INFERENCE  
**Pre-Registration ID**: MEIE-EVENT-01-v1.0  
**Locked At**: 2026-08-26T09:30:00Z  
**Author**: BTCognitive Research Protocol  
**Depends On**: None (first in MICRO-EVENT sequence)  
**Next Stage**: MEIE-DIRECTION-01 (only activated after N ≥ 100 IGNITION events observed)

---

## 1. Scientific Question

Does a detected **IGNITION event** (volatility acceleration from low-volatility compression) increase
the unconditional probability of a large 15m–30m price excursion?

$$H_1: P(|r_h| > k\sigma_h \mid \text{IGNITION}) > P(|r_h| > k\sigma_h \mid \text{NORMAL})$$

**No directional hypothesis is made at this stage.** This experiment tests movement magnitude
only. Direction is evaluated in MEIE-DIRECTION-01.

---

## 2. Definitions & Locked Parameters

### 2.1 State Vector (z-score normalization)

All six components are z-scored over a trailing **168-candle rolling window** (168 × 1-min candles = 2.8 hours).
$$\mathbf{s}_t = [z_{\text{hawkes}},\; z_{\text{ofi}},\; z_{\text{vpin}},\; z_{\text{depth}},\; z_{\text{spread}},\; z_{\text{impact}}]$$

Component definitions:

| Component | Raw Signal Source | Direction (high = stress) |
|:---|:---|:---|
| `z_hawkes` | `lambda_buy + lambda_sell` from `hawkes_shadow_session` | + |
| `z_ofi` | Buyer-initiated volume fraction from `vpin_true.py` aggTrades | + = buy pressure |
| `z_vpin` | Rolling VPIN (50 buckets) from `vpin_true.py` | + |
| `z_depth` | Candle volume as top-of-book depth proxy (aggTrades sum per minute) | − (thin = low volume) |
| `z_spread` | `(high - low) / close` per candle as spread proxy | + |
| `z_impact` | `|close - open| / volume` per candle as price-impact proxy | + |

> **Note on LOB data**: Full Level-2 order book data is not yet wired. The `z_depth`, `z_spread`,
> and `z_impact` components use aggTrades-derived proxies as defined above until L2 polling
> is integrated. This is a known approximation and is explicitly labeled in all outputs.

### 2.2 IGNITION Event Definition (LOCKED)

An IGNITION event occurs at time $t$ when **all three** of the following are true:

| Condition | Locked Threshold | Rationale |
|:---|:---|:---|
| Low preceding volatility | `z_spread < −0.5` over prior 15 candles (mean) | Confirms compression state |
| Hawkes acceleration | `z_hawkes > 1.5` | Self-excitation spike in event intensity |
| OFI deviation | `|z_ofi| > 1.0` | Order-flow imbalance in either direction |

Minimum gap between IGNITION events: **15 candles** (15 minutes). Overlapping events are
merged into a single event record.

### 2.3 Excursion Target (LOCKED)

- Horizon $h$: **15 candles** (15 minutes) and **30 candles** (30 minutes), tested separately.
- Threshold $k$: **1.5 × rolling 168-candle σ** of 1-minute returns.
- Realized excursion: `max(high, low) - open` / `open` over the $h$-candle window following detection.

### 2.4 Evaluation Window

- **Minimum events for inference**: N ≥ 50 detected IGNITION events.
- **Primary test**: Fisher's exact test or Chi-squared on 2×2 contingency table:
  (IGNITION / NORMAL) × (large excursion / small excursion).
- **Significance threshold**: $p < 0.05$ (two-sided).
- **Effect size**: Relative risk $RR = P(\text{large} | \text{IGNITION}) / P(\text{large} | \text{NORMAL})$.
- **Practical significance**: $RR > 1.3$ required alongside statistical significance.

---

## 3. Null Hypothesis

$$H_0: P(|r_h| > k\sigma_h \mid \text{IGNITION}) \leq P(|r_h| > k\sigma_h \mid \text{NORMAL})$$

If $H_0$ is not rejected at $p < 0.05$ with $RR > 1.3$ after $N \geq 50$ events,
the IGNITION event detector is **archived** and MEIE-DIRECTION-01 is not activated.

---

## 4. Data Source & Isolation Invariants

- All candle data from Binance live 1-minute OHLCV (same source as Arena runner).
- aggTrades from `data/raw/aggtrades/` (same as `vpin_true.py`).
- Hawkes intensities from `hawkes_shadow_session` in-memory output.
- **This experiment does NOT modify any existing Arena experiment state or Observatory records.**
- Results persist to a dedicated table `meie_events` in `results/meie_memory.db` (separate from `arena_memory.db`).

---

## 5. Threshold Mining Prohibition

> [!CAUTION]
> The thresholds above (`z_hawkes > 1.5`, `|z_ofi| > 1.0`, `z_spread < −0.5`) are
> **permanently locked at this pre-registration timestamp**. They may NOT be adjusted based
> on observed results. Any future parameter change requires a new pre-registration with a
> new version suffix (e.g., MEIE-EVENT-01-v2.0) and a full reset of the event counter.

---

## 6. Activation Conditions for MEIE-DIRECTION-01

MEIE-DIRECTION-01 is **not activated until**:
1. $N \geq 100$ IGNITION events are recorded in `meie_events`.
2. $H_1$ is not rejected ($p < 0.05$, $RR > 1.3$) for at least one horizon ($h = 15$ or $h = 30$).
3. The interim audit report is committed to `results/meie_event01_interim_report.md`.
