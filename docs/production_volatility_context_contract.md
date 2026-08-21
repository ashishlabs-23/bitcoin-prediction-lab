# 🌐 Production Volatility Context Contract

## 1. Scope & System Definition

* **Model Pipeline:** `v3.0.0-excursion-ridge-conformal` + `v1.0.0-volatility-bridge-context`
* **Target Horizon:** 24-Hour Maximum Favorable Excursion (MFE) & Maximum Adverse Excursion (MAE).
* **Role:** Production Probabilistic Range & Risk Envelope Conditioner.
* **Governance Status:** **`PRODUCTION`** (Safe, decoupled context layer).

---

## 2. Input Specification & Mathematical Formulas

### Point-in-Time Inputs:
* Historical close prices $P_{t-k}$ across 5m, 15m, 1h, 4h, 12h, and 24h windows.

### Term-Structure Ratios:
$$r_{5\text{m}} = \frac{\sigma_{5\text{m}} \cdot \sqrt{288}}{\sigma_{24\text{h}}}, \quad r_{1\text{h}} = \frac{\sigma_{1\text{h}} \cdot \sqrt{24}}{\sigma_{24\text{h}}}, \quad r_{4\text{h}} = \frac{\sigma_{4\text{h}} \cdot \sqrt{6}}{\sigma_{24\text{h}}}$$

### Deterministic Regime Derivation:
* `VOL_EXPANDING`: $r_{1\text{h}} > 1.30 \text{ or } r_{5\text{m}} > 1.40$
* `VOL_COMPRESSION`: $r_{1\text{h}} < 0.75$
* `PEAK_VOLATILITY`: $r_{4\text{h}} > 1.50$
* `NORMAL`: Default equilibrium state

---

## 3. Production Safety & Independence Invariants

1. **Zero Shadow Coupling:** The 24h production forecast uses ONLY historical prices and deterministic volatility formulas. It has ZERO runtime dependency on the shadow Hawkes model or intermediate research models.
2. **Purge & Embargo:** Strict 24-hour purge and embargo enforced across all walk-forward evaluation cycles.
3. **Rollback Policy:** In the event of missing multi-timeframe feeds, the engine gracefully falls back to baseline `realized_vol_24h` without downtime.
