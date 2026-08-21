# 📄 Foundation Model Card: Amazon Chronos-2

## Model Overview
* **Model Name:** Amazon Chronos-2
* **Architecture:** T5-based Autoregressive Language Model Tokenized for Time-Series
* **Pretraining Data:** Synthetic time-series + TSlib benchmark datasets
* **Input Representation:** Quantized and tokenized price trajectories (120h, 240h, 480h)
* **Horizon:** 24 Hours
* **Role in BTCognitive:** `FOUNDATION_RESEARCH` (Research Challenger Only)
* **BTCUSD Performance:** Zero-shot MFE Error: `0.4650%`, Adapted MFE Error: `0.4250%` (vs Production Ridge `0.3980%`).
* **Governance Status:** **`NOT_PROMOTED`** — Heavy tokenization latency (220ms) without statistical outperformance.
