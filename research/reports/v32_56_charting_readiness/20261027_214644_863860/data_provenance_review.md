# Data provenance and market-data rights review

## Release decision

**BLOCKED — Coinbase-backed public release.** No written license granting the intended public display, redistribution, derived analytics, caching/retention, commercial, or AI/ML use was found in the repository. Coinbase's official Market Data Terms, last updated 2026-08-07, restrict end-user applications, third-party display/dissemination of Market Data or Derived Works, and AI/ML development/training/validation/benchmarking absent prior express written consent. Source: https://www.coinbase.com/legal/market_data.

A public endpoint is not a public-display license. The allowed path is a written Coinbase agreement that expressly covers each intended use, or a provider whose executed license does. Legal review remains required.

## V32.55 data condition

- V2: 42,237 rows; 13 absent hourly candles in three gaps; `ACQUIRED_WITH_REVIEW_REQUIRED`.
- V3: `ACQUIRED_WITH_REVIEW_REQUIRED`; it is separate and immutable. Its manifest retains raw-response hashes and reproducible reconstruction evidence.
- The reported 56 later-candle overlap check is interval-scoped evidence only; it does not validate the historical file as a whole or resolve the 13 missing candles.
- No protected parquet or ledger was modified by this audit. No gaps were filled.

## Required provider-license evidence

Written permission must explicitly cover: end-user display, raw/derived redistribution, indicators/charts/research outputs, retention and caches, commercial/geographic scope, and model training/fine-tuning/testing/validation/benchmarking. Until then, deterministic fixture data remains isolated QA-only and unavailable to normal/public runtime.
