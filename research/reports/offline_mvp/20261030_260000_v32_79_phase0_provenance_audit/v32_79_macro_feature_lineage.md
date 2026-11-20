# V32.79 Phase 0 — Macro Feature Lineage Audit (Workstream B)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream B (Macro Regime Lineage)  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!CAUTION]
> **CRITICAL FINDING: `data/processed/multi_regime_features.parquet` is built entirely from SYNTHETIC, SIMULATED price data. It does NOT contain real BTCUSD historical prices. Any research result derived from this file reflects simulated market dynamics, not empirical Bitcoin price history.**

---

## 1. Source Code Discovery

The generating code was identified via codebase-wide search. Files referencing `multi_regime_features`:

| File | Role |
|---|---|
| `research/multi_regime_dataset.py` | **Primary generator** — creates the parquet file |
| `research/macro_evaluation_harness.py` | Consumer — reads the file for evaluation |
| `research/multi_regime_purged_validation.py` | Consumer — cross-validation harness |
| `research/run_uncertainty_01_trial.py` | Consumer — uncertainty trial |
| `research/run_uncertainty_02_trial.py` | Consumer — uncertainty trial |
| `research/audit_iv_dataset.py` | Consumer — IV audit |
| `tests/test_multi_regime_deepening.py` | Test — validates the dataset |

---

## 2. Price Path Generation — Full Analysis

`research/multi_regime_dataset.py`, function `build_multi_regime_dataset()`:

### 2.1 Simulation Mechanism

```python
np.random.seed(42)               # Fixed seed — deterministic but simulated
dates = pd.date_range(start="2020-01-01", end="2026-08-23", freq="1h", tz="UTC")
# Regime-specific drift and volatility
mu[mask_r1] = 0.00015;   sigma[mask_r1] = 0.0065  # "Bull"
mu[mask_r2] = -0.00010;  sigma[mask_r2] = 0.0075  # "Bear"
mu[mask_r3] = 0.00008;   sigma[mask_r3] = 0.0040  # "Transition"
mu[mask_r4] = 0.00006;   sigma[mask_r4] = 0.0050  # "ETF Era"

ret = np.random.normal(mu, sigma)                  # SIMULATED returns
jumps = np.random.binomial(1, 0.005, N) * np.random.normal(0, 0.025, N)
close = 7200.0 * np.exp(np.cumsum(ret + jumps))    # SIMULATED price path
```

**This is a stochastic simulation with a fixed random seed.** The output parquet is a deterministic realization of a random walk calibrated to regime-appropriate drift/vol parameters, starting from \$7,200.

### 2.2 OHLCV Construction

```python
spread = np.abs(np.random.normal(0, sigma * 0.8))
high = close * (1.0 + spread)
low = close * (1.0 - spread)
open_p = close * (1.0 + np.random.normal(0, sigma * 0.2))
volume = np.random.lognormal(8.0, 1.0, size=N)
```

High, Low, Open, and Volume are **also simulated** from the same random seed cascade. They do not correspond to any real exchange data.

---

## 3. Regime Label Definition

```python
def assign_macro_regime(timestamp_series):
    conditions = [
        ts < "2021-11-10",
        (ts >= "2021-11-10") & (ts < "2023-01-01"),
        (ts >= "2023-01-01") & (ts < "2024-01-11"),
        ts >= "2024-01-11"
    ]
    choices = [
        "REGIME_1_HALVING_BULL",
        "REGIME_2_FED_HIKING_BEAR",
        "REGIME_3_TRANSITION_COMPRESSION",
        "REGIME_4_SPOT_ETF_INSTITUTIONAL"
    ]
```

**Regime labels are pure date-range assignments.** No market data, no lookahead, no learned thresholds. The regime for any bar is determined solely by its timestamp.

**Lookahead status:** ✅ **Zero lookahead in regime assignment.** Labels depend only on calendar dates, which are known at any past timestamp.

**However:** The regime boundary dates themselves encode retrospective knowledge about when macro regimes occurred (e.g., knowing that 2024-01-11 was the ETF approval date). These boundaries were set by the researcher after the fact and cannot be re-validated prospectively.

---

## 4. Feature Engineering Analysis

All features are computed from the simulated OHLCV in a rolling-window fashion:

| Feature | Computation | Lookahead? |
|---|---|---|
| `vol_1h` | 1-period log return std × √(24×365) | ✅ None |
| `vol_24h` | 24-period rolling log return std × √(24×365) | ✅ None |
| `vol_168h` | 168-period rolling log return std × √(24×365) | ✅ None |
| `parkinson_vol_24h` | 24-period rolling Parkinson H/L estimator | ✅ None |
| `rsi_14` | Wilder RSI(14) | ✅ None |
| `vol_ratio_1h_24h` | vol_1h / vol_24h | ✅ None |
| `vol_ratio_24h_168h` | vol_24h / vol_168h | ✅ None |
| `mfe_24h` | Maximum Favorable Excursion, 24-bar forward | ⚠️ **FORWARD-LOOKING TARGET** |
| `mae_24h` | Maximum Adverse Excursion, 24-bar forward | ⚠️ **FORWARD-LOOKING TARGET** |
| `macro_regime` | Date-range assignment | ✅ None |

**MFE/MAE are forward-looking outcome variables, not predictive features.** They are correctly used as targets in the validation harness. Their presence in the parquet does not constitute lookahead IF they are correctly treated as labels (not inputs).

The source is `research/purged_excursion_validation.py:compute_excursion_targets()` which computes forward excursions using `horizon_bars=24` — confirming MFE/MAE are 24-bar-forward outcomes.

---

## 5. Multi-Regime Validation Report Cross-Check

`experiments/results/multi_regime_validation_report.json` reports:

| Regime | N | Spearman IC (MFE) | Spearman IC (MAE) | Calibration |
|---|---|---|---|---|
| REGIME_2_FED_HIKING_BEAR | ~8,592 | −0.028 to −0.001 | +0.007 to +0.011 | DEGRADED_BELOW_TARGET |
| REGIME_3_TRANSITION_COMPRESSION | ~9,000 | −0.001 to 0.000 | +0.002 to +0.008 | CALIBRATED_NOMINAL |
| REGIME_4_SPOT_ETF_INSTITUTIONAL | ~3,386 | −0.025 to +0.001 | +0.003 to +0.011 | DEGRADED_BELOW_TARGET |

All Spearman ICs are near zero. **The volatility features computed from simulated data show no predictive relationship with simulated MFE/MAE.** This outcome is expected: the simulated returns are i.i.d. within each regime (plus jump diffusion), so rolling volatility metrics have no structural predictive relationship with 24-bar-forward excursions in a random walk.

**The validation experiment is self-consistent but the underlying dataset is synthetic.** This result tells us nothing about real BTC price predictability.

---

## 6. Impact Assessment on V32.79 Hypotheses

| Hypothesis | Impact of Synthetic Data |
|---|---|
| $H_{\text{Funding}}$ (Funding dislocation) | **Not affected** — funding analysis uses `binance_funding_2022_2026.parquet` (real data) merged with OHLCV checkpoint (real data). `multi_regime_features.parquet` not required. |
| $H_{\text{ETF}}$ (ETF flow conditioning) | **Not affected** — ETF data doesn't exist locally regardless. |
| $H_{\text{Macro}}$ (Fed regime conditioning) | **Directly affected** — regime labels from `multi_regime_features.parquet` cannot be used as ground truth for real BTC market regimes. Regime boundary dates (2021-11-10, 2023-01-01, 2024-01-11) would need to be re-applied directly to real OHLCV data. |
| $H_{\text{Macro\_Abstain}}$ (FOMC abstention) | **Not affected** — requires real event timestamps which don't exist locally. |

---

## 7. Determinations

| Question | Answer |
|---|---|
| Is `multi_regime_features.parquet` based on real BTC prices? | ❌ **NO — SYNTHETIC SIMULATION** |
| Is there lookahead in feature construction? | ✅ No lookahead in features; MFE/MAE are correctly identified as targets |
| Is there lookahead in regime labels? | ✅ No temporal lookahead; labels use historical boundary dates |
| Can regime labels from this file be used in V32.79 empirical research? | ❌ Labels must be recomputed by applying `assign_macro_regime()` to real OHLCV timestamps |
| Can any validation result from this file be used as empirical evidence? | ❌ Validation on synthetic data cannot substitute for real-data evaluation |
| Is the dataset legally usable for methodology testing (not evidence)? | ✅ Yes — acceptable for testing pipeline plumbing, not for evidence claims |

**Overall workstream B determination: BLOCKED_BY_PROVENANCE for evidential use**

The macro regime feature file cannot be used as empirical evidence. It may be used for software testing only. Any V32.79 regime-conditioned analysis must apply `assign_macro_regime()` directly to the real OHLCV checkpoint timestamps.

---

*No external data fetched. No datasets modified. No models trained.*

