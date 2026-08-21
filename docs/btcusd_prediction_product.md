# 🌐 BTCognitive Product Specification: Probabilistic BTCUSD Range Engine

## 1. Product Identity & Purpose

**BTCognitive** is an AI-driven market intelligence platform providing probabilistic 24-hour **BTCUSD price range, excursion magnitude, volatility envelope, and uncertainty forecasts**.

> [!IMPORTANT]
> **Core Value Proposition**: Rather than emitting brittle, unvalidated binary BUY/SELL trading signals, BTCognitive equips analysts, risk managers, and market participants with statistically calibrated price boundaries ($P_{10}$, $P_{50}$, $P_{90}$) and excursion boundaries ($\text{MFE}$, $\text{MAE}$).

---

## 2. Core Prediction Components

For every 1-hour bar, the Range Engine emits:
1. **Spot Reference Price ($P_t$)**: Current BTCUSD price at forecast creation.
2. **24H Maximum Favorable Excursion (MFE)**: Predicted potential upward price expansion ($P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$).
3. **24H Maximum Adverse Excursion (MAE)**: Predicted potential downward drawdown risk ($P_{10}, P_{25}, P_{50}, P_{75}, P_{90}$).
4. **Nominal 90% Price Range Envelope**:
   - $\text{Upper}_{P90} = P_t \times (1 + \text{MFE}_{P90})$
   - $\text{Lower}_{P90} = P_t \times (1 - \text{MAE}_{P90})$
5. **Conformal Uncertainty & Coverage Confidence**: Quantifies dispersion across regimes (`HIGH`, `MODERATE`, `LOW_CONFIDENCE`).
6. **Market Regime Classification**: Trending Bull, Trending Bear, Sideways, Breakout, High Volatility.
7. **Secondary Directional Evidence**: Experimental conditional overlay (`NO_DIRECTIONAL_EDGE` default).
8. **Tradeability Research Score**: Non-execution informational metric (`RESEARCH ONLY`).

---

## 3. Product Safety & Non-Execution Guarantees

* **Zero Automated Execution**: No broker API credentials, no automated order placement, zero real capital execution.
* **Point-in-Time Integrity**: All features and forecasts strictly utilize information timestamped $t \le 0$.
* **Immutable Provenance**: Every forecast is stored with cryptographic SHA-256 hashes in SQLite WAL mode.
