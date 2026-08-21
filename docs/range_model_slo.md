# 🎯 Range Model Service Level Objectives (SLOs) & Reliability Contract

## 1. Operational Service Level Objectives

| Metric | Target SLO | Measurement Window | Action on Violation |
| :--- | :---: | :---: | :--- |
| **Forecast Generation Availability** | $\ge 99.9\%$ | Rolling 30 Days | Alert on-call |
| **Forecast Resolution Completeness** | $\ge 99.9\%$ | 24h Forward Horizon | Log resolution retry |
| **Database Write Success (WAL)** | $\ge 99.99\%$ | Continuous | Degrade to in-memory fallback |
| **Model Checksum Integrity** | **$100.0\%$** | On every request | Block inference / raise `MODEL_INVALID` |
| **Joint Path Containment Calibration** | $\ge 78.87\%$ | 30 Independent Blocks | Set health state to `MODEL_WATCH` |
| **Zero-Fabrication Invariant** | **$100.0\%$** | Permanent | Return `DEGRADED` on failure, never fake prices |

---

## 2. Point-in-Time & Provenance Guarantees

* **Zero Lookahead Leakage**: Only data timestamped $t \le 0$ may enter feature calculation.
* **Cryptographic Hashes**: Every prediction emitted contains a SHA-256 hash of its input features and calibration parameters.
