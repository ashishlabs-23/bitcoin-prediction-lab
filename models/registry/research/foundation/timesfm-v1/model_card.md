# 📄 Foundation Model Card: Google TimesFM 2.5

## Model Overview
* **Model Name:** Google TimesFM 2.5
* **Architecture:** Decoder-only Temporal Transformer with Patch Masking
* **Pretraining Data:** ~100B real-world time points across retail, energy, and traffic benchmarks
* **Input Representation:** Univariate Normalized OHLCV Time-Series (120h, 240h, 480h Context)
* **Horizon:** 24 Hours
* **Role in BTCognitive:** `FOUNDATION_RESEARCH` (Research Challenger Only)
* **Status:** Zero-shot evaluation complete; domain adaptation evaluated.
* **BTCUSD Performance:** Zero-shot MFE Error: `0.4420%`, Adapted MFE Error: `0.4080%` (vs Production Ridge `0.3980%`).
* **Governance Status:** **`NOT_PROMOTED`** — Local Ridge + Volatility Context remains superior with 400x lower latency.
