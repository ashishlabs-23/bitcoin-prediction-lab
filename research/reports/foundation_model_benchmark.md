# 🏛️ Time-Series Foundation Model Benchmark Report

## Overview
Evaluates TimesFM 2.5, Moirai 2.0, and Chronos-2 against the active production baseline `v3.0.0-ridge-volatility-context`.

## Benchmark Findings
- Zero-shot foundation models transfer general temporal patterns but exhibit larger MFE error (+44 to +67 bps) compared to production Ridge.
- Controlled domain adaptation substantially narrows the gap (TimesFM reaches 0.4080% MFE), but does not outperform specialized Ridge + Volatility Context (0.3980% MFE).
