# V32.80 — Research Lineage Audit (Workstream 5)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

Classify each prior milestone conclusion according to its actual input data lineage. Do not invalidate independent OHLCV research merely because the macro-regime dataset was synthetic.

---

## 2. Data Source Classification

| Dataset | Classification | Empirical Status |
|---|---|---|
| `ohlcv_checkpoint_42233_bars.parquet` | Real Coinbase BTCUSD hourly prices | ✅ VALID |
| `binance_funding_2022_2026.parquet` | Real Binance BTCUSDT funding rates | ✅ VALID (instrument distinction documented) |
| `multi_regime_features.parquet` | Synthetic simulation (`np.random.seed(42)`) | ❌ INVALID for empirical claims |
| `experiments/results/multi_regime_validation_report.json` | Derived from synthetic data | ❌ SYNTHETIC_DATA_DERIVED |
| Execution cost parameters (24/87 bps) | Fixed, documented derivation | ✅ VALID |
| Barrier mechanics (TP/SL/EXPIRED) | Deterministic calculation on real prices | ✅ VALID |

---

## 3. Milestone-by-Milestone Lineage

### V32.74 — Conditional Entry Research
**Determination:** `BLOCKED_BY_COST_ECONOMICS`

| Component | Data source | Valid? |
|---|---|---|
| Entry-filter barrier backtest | Real OHLCV checkpoint | ✅ |
| RSI/vol entry filters | Computed from real OHLCV | ✅ |
| Cost economics | Fixed 24/87 bps parameters | ✅ |
| Regime features | None referenced in barrier P&L | ✅ |
| **Determination lineage** | | **✅ VALID — real data throughout** |

---

### V32.75 — (Data Governance Incident Recovery)
**Determination:** Addressed the 93-candle incident. Not a strategy milestone.

| Component | Data source | Valid? |
|---|---|---|
| OHLCV checkpoint creation | Real Coinbase data | ✅ |
| Hash-mismatch remediation | Real file operations | ✅ |
| Network isolation tests | Code changes only | ✅ |
| **Determination lineage** | | **✅ VALID** |

---

### V32.76 — Governance and Test Infrastructure
**Determination:** 79/79 tests passing.

| Component | Data source | Valid? |
|---|---|---|
| Test infrastructure | Code only | ✅ |
| Protected dataset checksums | Real file hashes | ✅ |
| `test_multi_regime_deepening.py` | Synthetic data (pipeline test only) | ✅ (software test) |
| **Determination lineage** | | **✅ VALID** |

---

### V32.77 — Volatility-Adaptive Entry Research
**Determination:** `BLOCKED_BY_COST_ECONOMICS`

| Component | Data source | Valid? |
|---|---|---|
| ATR-scaled barrier backtest | Real OHLCV checkpoint | ✅ |
| 72h/168h horizon evaluation | Real OHLCV checkpoint | ✅ |
| Cost economics | Fixed 24/87 bps | ✅ |
| Regime features | Not used in barrier P&L computation | ✅ |
| **Determination lineage** | | **✅ VALID — real data throughout** |

---

### V32.78 — Asymmetric Regime-Conditioned Entry Research
**Determination:** `BLOCKED_BY_COST_ECONOMICS`

| Component | Data source | Valid? |
|---|---|---|
| Barrier P&L calculation | Real OHLCV checkpoint | ✅ |
| Regime labels (date-range) | Applied to real OHLCV timestamps | ✅ (date-range function, not synthetic features) |
| Cost economics | Fixed 24/87 bps | ✅ |
| Multi-regime validation IC | **Synthetic `multi_regime_features.parquet`** | ❌ SYNTHETIC_DATA_DERIVED |
| Spearman IC ≈ 0 claim | Synthetic data artifact | ❌ Not valid as real-BTC evidence |
| **Determination lineage** | | **⚠️ PARTIALLY VALID** |

**V32.78 nuance:** The `BLOCKED_BY_COST_ECONOMICS` determination is based on real-data P&L calculations and is correct. The near-zero Spearman IC finding (from synthetic data) was used as supporting context, not as the primary determination criterion. The determination itself is unaffected. The IC claims require reclassification as SYNTHETIC_DATA_DERIVED.

---

### V32.79 Phase 0 — Data Provenance Audit
**Determination:** `BLOCKED_BY_PROVENANCE`

| Component | Data source | Valid? |
|---|---|---|
| Dataset inventory | Direct file inspection | ✅ |
| Funding provenance | Real funding parquet | ✅ |
| **Synthetic data discovery** | Code inspection of `multi_regime_dataset.py` | ✅ |
| ETF/FOMC absence finding | File system search | ✅ |
| Cost reconciliation | Document audit | ✅ |
| **Determination lineage** | | **✅ VALID — this milestone discovered the synthetic data** |

---

### V32.79A Phase 1A — Funding Dislocation Research
**Determination:** `INSUFFICIENT_EVIDENCE`

| Component | Data source | Valid? |
|---|---|---|
| Funding signal | Real BTCUSDT funding parquet | ✅ |
| Price outcomes | Real OHLCV checkpoint | ✅ |
| Episode detection | Deterministic algorithm | ✅ |
| Barrier simulation | Real price data | ✅ |
| DM-HLN (original) | Unpaired comparison | ❌ CALCULATION_DISCREPANCY |
| DM-HLN (V32.80 corrected) | Paired comparison (p=0.0039) | ✅ |
| **Determination lineage** | | **✅ VALID — INSUFFICIENT_EVIDENCE confirmed by V32.80** |

---

## 4. Conclusions Requiring Reclassification

| Finding | Original report | Required reclassification |
|---|---|---|
| "Near-zero Spearman IC for macro regime features" | V32.78, V32.79 | Reclassify as `SYNTHETIC_DATA_DERIVED — not informative about real BTC` |
| `multi_regime_validation_report.json` | experiments/results | Annotate as `SYNTHETIC_DATA_DERIVED` |
| "Volatility features show no predictive relationship with MFE/MAE" | V32.78/V32.79 | Reclassify — result is expected for i.i.d. simulated returns |

**No determination label (BLOCKED_BY_COST_ECONOMICS, INSUFFICIENT_EVIDENCE, etc.) requires revision.** The determinations were reached via real-data calculations.

---

## 5. Research Record Integrity Assessment

| Milestone | Determination | Data Lineage Valid? | Determination Stands? |
|---|---|---|---|
| V32.74 | BLOCKED_BY_COST_ECONOMICS | ✅ Real OHLCV | ✅ YES |
| V32.75 | Governance recovery | ✅ Real files | ✅ YES |
| V32.76 | 79 tests passing | ✅ Real/pipeline | ✅ YES |
| V32.77 | BLOCKED_BY_COST_ECONOMICS | ✅ Real OHLCV | ✅ YES |
| V32.78 | BLOCKED_BY_COST_ECONOMICS | ⚠️ P&L real; IC synthetic | ✅ YES (P&L basis) |
| V32.79 Ph0 | BLOCKED_BY_PROVENANCE | ✅ Real | ✅ YES |
| V32.79A | INSUFFICIENT_EVIDENCE | ✅ Real + corrected DM | ✅ YES |

**All milestone determinations stand. The synthetic data discovery affects supporting context in V32.78, not the primary determination basis.**

---

*No datasets modified. No conclusions retroactively rewritten. Amendments are dated and auditable.*

