# 🌐 BTCUSD Multiscale Dual-Horizon Forecast Contract

## 1. Architectural Philosophy

BTCognitive provides decoupled, dual-horizon intelligence without probability blending:
1. **Short-Horizon Subsystem (5m):** High-frequency order flow and Hawkes self-excitation capturing transient volatility and market pressure (`VALIDATED_SHADOW_MODEL`).
2. **Long-Horizon Subsystem (24h):** Structural macro features and Production Ridge Conformal Regressor predicting daily risk envelopes (`PRODUCTION`).

---

## 2. API Contract Specification (`GET /prediction/multiscale`)

```json
{
  "symbol": "BTCUSD",
  "timestamp": "2026-08-21T15:24:00Z",
  "current_price": 65200.0,
  "short_horizon": {
    "horizon": "5m",
    "current_price": 65200.0,
    "mfe_p50": 0.00093,
    "mae_p50": 0.00099,
    "upper_p90": 65326.16,
    "lower_p90": 65075.73,
    "direction_state": "BEARISH",
    "uncertainty": 0.1,
    "model_version": "v1.0.0-challenger-hawkes-microstructure",
    "data_quality": "VALID"
  },
  "long_horizon": {
    "horizon": "24h",
    "current_price": 65200.0,
    "mfe_p50": 0.00412,
    "mae_p50": 0.00581,
    "upper_p90": 66911.50,
    "lower_p90": 63048.40,
    "direction_state": "NO_DIRECTIONAL_EDGE",
    "uncertainty": 1.6,
    "model_version": "v3.0.0-excursion-ridge-conformal",
    "data_quality": "VALID"
  },
  "overall_data_quality": "VALID",
  "production_model_version": "v3.0.0-excursion-ridge-conformal",
  "shadow_model_version": "v1.0.0-challenger-hawkes-microstructure",
  "shadow_health": "SHADOW_HEALTHY",
  "status": "RESEARCH_MULTISCALE_READY"
}
```

---

## 3. Product Display & Chart Semantics

* **Next 5 Minutes Panel:** Explicitly labeled **`RESEARCH SHADOW`** / **`VALIDATED SHADOW`**.
* **Next 24 Hours Panel:** Explicitly labeled **`PRODUCTION`**.
* **Zero Probability Blending:** Never averages or combines probabilities into a single number.
