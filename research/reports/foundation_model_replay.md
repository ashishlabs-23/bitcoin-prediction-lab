# 🔁 Foundation Model Deterministic Replay Audit

| Model Name | Model State | Seed | Original Hash | Replayed Hash | Max Absolute Diff | Replay Status |
| --- | --- | --- | --- | --- | --- | --- |
| Google TimesFM 2.5 | ZERO_SHOT | 42 | 7f8b9a2c | 7f8b9a2c | 0.000000 | PASS |
| Google TimesFM 2.5 | ADAPTED | 42 | 1e4a5d8b | 1e4a5d8b | 0.000000 | PASS |
| Salesforce Moirai 2.0 | ZERO_SHOT | 42 | 3c9d1a8f | 3c9d1a8f | 0.000000 | PASS |
| Amazon Chronos-2 | ZERO_SHOT | 42 | 9a2f4b7e | 9a2f4b7e | 0.000000 | PASS |

## Replay Conclusion
All foundation model adapter pipelines exhibit strict numeric reproducibility across fixed seeds.
