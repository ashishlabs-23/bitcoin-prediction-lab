# BTCognitive API Reference

Comprehensive specification of all REST endpoints and WebSocket channels exposed by the **BTCognitive** inference engine.

---

## 1. Engine & Health Endpoints

### `GET /health`
Returns the operational health, models initialization state, and round-trip subsystem latency.

**Response:**
```json
{
  "status": "live",
  "models_loaded": true,
  "websocket": true,
  "uptime": 120,
  "latency": {
    "market_latency_ms": 12,
    "prediction_latency_ms": 85,
    "ws_latency_ms": 7
  }
}
```

---

## 2. Quantitative Inference Endpoints

### `GET /prediction/latest`
Fetches the latest ensemble prediction, expected returns, quantile risk intervals, Take-Profit / Stop-Loss targets, and uncertainty breakdown.

**Response:**
```json
{
  "symbol": "BTC/USD",
  "direction": "LONG",
  "probability_pct": 79.8,
  "expected_return_pct": 2.78,
  "prediction_interval": [-0.007, 0.035],
  "tp": 66578.0,
  "sl": 61312.0,
  "confidence": 0.812,
  "action": "TAKE_LONG",
  "uncertainty_breakdown": {
    "data_reliability": 1.0,
    "regime_certainty": 0.74,
    "model_agreement": 0.98,
    "volatility_stress": 0.91,
    "composite_quality_score": 0.88
  }
}
```

---

## 3. Market Regime Endpoints

### `GET /regime/latest`
Returns current macro classification, trend strength score, and volatility indicators.
