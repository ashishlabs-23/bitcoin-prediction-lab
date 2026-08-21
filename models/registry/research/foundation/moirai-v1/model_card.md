# 📄 Foundation Model Card: Salesforce Moirai 2.0

## Model Overview
* **Model Name:** Salesforce Moirai 2.0
* **Architecture:** Any-Variate Masked Encoder-Decoder Transformer
* **Pretraining Data:** LOTSA (Large-scale Open Time Series Archive) dataset (27B observations)
* **Input Representation:** Multi-resolution tokenized price & volatility sequences (120h, 240h, 480h)
* **Horizon:** 24 Hours
* **Role in BTCognitive:** `FOUNDATION_RESEARCH` (Research Challenger Only)
* **BTCUSD Performance:** Zero-shot MFE Error: `0.4580%`, Adapted MFE Error: `0.4190%` (vs Production Ridge `0.3980%`).
* **Governance Status:** **`NOT_PROMOTED`** — Generalist representation lacks specialized cryptocurrency microstructure handling.
