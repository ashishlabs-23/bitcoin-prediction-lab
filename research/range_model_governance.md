# 🛡️ BTCognitive: Range Model Governance & Promotion Protocol

## 1. Governance Principles
1. **Separation of Forecasting Quality vs Economic Execution**:
   - Range models are evaluated on statistical containment, pinball loss, coverage calibration, and width stability.
   - Live trading profitability is NOT a prerequisite for range forecasting because the product is a risk intelligence engine.
2. **Strict Point-in-Time Integrity**:
   - Zero future lookahead leakage permitted.
   - All quantile thresholds and conformal parameters must be estimated strictly from $t \le 0$ partitions.

---

## 2. 10-Point Promotion Gate for Range Models

A candidate range forecasting model may replace the production model only if:
1. **No Data Leakage**: Passes the automated temporal dependency audit.
2. **Walk-Forward OOS Validation**: Demonstrates stable calibration across at least 5 temporal folds.
3. **Independent Confirmation**: Evaluated on an untouched confirmation set with no hyperparameter tuning.
4. **Quantile Monotonicity**: Guarantees non-crossing quantiles ($P_{10} \le P_{25} \le P_{50} \le P_{75} \le P_{90}$).
5. **MFE Coverage**: Empirical $P_{90}$ coverage $\ge 88.0\%$.
6. **MAE Coverage**: Empirical $P_{90}$ coverage $\ge 88.0\%$.
7. **Joint Price Path Containment**: Full 24h path containment $\ge 75.0\%$.
8. **Interval Sharpness**: Mean interval width does not expand into economically uninformative bounds ($< 3.0\%$).
9. **Regime Robustness**: Validated across Bull, Bear, Sideways, and High Volatility states.
10. **Multiple-Testing Accounting**: Updates the cumulative trial ledger ($K \ge 1,099$).
