# V26 Prioritized Implementation Roadmap

**Date:** October 2026  
**Status:** APPROVED FOR RESEARCH PLANNING  
**Ranking Framework:** Ranked objectively across 6 PRD dimensions:
1. Correctness & safety dependency
2. Probable incremental research value (alpha / risk intelligence)
3. Data availability & licensing (free public vs paid/restricted)
4. Empirical validation cost (computational & engineering effort)
5. CPU / storage / latency burden (laptop-first constraint)
6. User value & interpretability

---

## 1. Prioritized Feature Backlog

| Rank | Feature Specification | Category | Data Provider & Cost | CPU / Storage Burden | Valuation Score (1–10) | Phase Target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Statistical HAC Inference & Dependence Engine** | Correctness (P0) | Internal OHLCV (Zero Cost) | Negligible (<100ms) | **10.0** | **V26 (Delivered)** |
| **2** | **Dual-EMA / Strategy Nomenclature & Cost Reconciliation** | Correctness (P0) | Internal Engine (Zero Cost) | Negligible | **10.0** | **V26 (Delivered)** |
| **3** | **PRD Traceability & Test Census Disambiguation** | Governance (P0) | Internal Repo (Zero Cost) | Zero | **10.0** | **V26 (Delivered)** |
| **4** | **Cross-Exchange Spot Divergence & Stale Source Detection** | Market Data (P1) | Binance, Kraken REST (Free) | Low (<1MB/day, 20ms sync) | **9.2** | **V27** |
| **5** | **Perpetual Funding Rate & Annualized Basis (8h step)** | Market Data (P1) | Binance Public Futures (Free) | Minimal (<100KB/day) | **9.0** | **V27** |
| **6** | **Realized Semi-Variance & Continuous/Jump Decomposition** | Volatility (P1) | Internal OHLCV (Zero Cost) | Low (<2s per batch) | **8.8** | **V27** |
| **7** | **Open Interest (OI) & OI Delta Prospective Collector** | Market Data (P1) | Binance Public REST (Free) | Minimal | **8.2** | **V28** |
| **8** | **Conformal Winkler Score & Interval Sharpness Dashboard** | Uncertainty (P1) | Internal Engine (Zero Cost) | Low | **8.0** | **V28** |
| **9** | **Order Book Microstructure (Spread, Depth Imbalance)** | Microstructure (P2) | Coinbase / Binance L2 Stream | High (requires WS capture) | **6.5** | **V29 (Prospective only)** |
| **10** | **Options Implied Volatility (Deribit DVOL Index)** | Derivatives (P2) | Deribit Public API (Free) | Minimal | **6.0** | **V29** |
| **11** | **Macro / Cross-Market Context (DXY, Yields, SPX)** | Macro (P3) | FRED API / Yahoo Finance | Moderate (holiday alignment) | **4.5** | **V30 (Deferred)** |
| **12** | **On-Chain Active Addresses & Exchange Net Flows** | On-Chain (P3) | Requires Glassnode/CryptoQuant | High ($$$ paid API) | **3.0** | **DEFERRED (Paid API)** |

---

## 2. Phased Roadmap Details

### Phase V27: Core Market Data & Asymmetric Volatility (Immediate Next Sprint)
1. **Cross-Exchange Spot Arbitrage & Divergence:**
   - Ingest Binance BTC-USDT and Kraken BTC-USD hourly closes.
   - Compute pairwise basis $\Delta_{t} = \ln(P_{\text{Coinbase}, t}) - \ln(P_{\text{Binance}, t})$.
   - Ablation test: Does $\Delta_t$ reduce QLIKE loss on 24h realized variance?
2. **Perpetual Futures Funding Rate:**
   - Ingest 8-hour funding rates from Binance Futures public archive.
   - Evaluate predictive power for directional excursions following extreme leverage buildup (>0.03% per 8h).
3. **HAR-RS Semi-Variance Decomposition:**
   - Decompose hourly squared returns into $RS_t^+ = \sum r_i^2 \mathbb{I}(r_i > 0)$ and $RS_t^- = \sum r_i^2 \mathbb{I}(r_i < 0)$.
   - Test whether downside semi-variance improves 168h conformal interval calibration.

### Phase V28: Microstructure & Sharpness Calibration
1. **Prospective Open Interest Collector:**
   - Append-only recording of hourly aggregate Bitcoin open interest.
2. **Winkler Score Interval Optimization:**
   - Integrate interval sharpness scoring directly into model selection routines.

### Phase V29: Prospective Microstructure & Options Context
1. **L2 Order Book Imbalance:**
   - Collect prospective top-5 level bid/ask imbalance.
2. **Deribit DVOL Ingestion:**
   - Optional non-blocking feed for cross-validation against realized volatility forecasts.

---

## 3. Epistemic Gates for Roadmap Promotion

- **Ablation Hurdle:** No new feature family will be retained unless a point-in-time ablation study demonstrates a statistically significant out-of-sample error reduction ($p < 0.05$ via DM-HAC or CW-HAC) over the frozen baseline.
- **Laptop-First Constraint:** Cumulative RAM usage must remain under 1.5 GB; daily feature extraction must complete in under 30 seconds on a standard modern CPU.
