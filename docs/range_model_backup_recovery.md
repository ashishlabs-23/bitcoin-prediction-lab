# 🛡️ Range Model Backup, Disaster Recovery & Provenance Protocol

## 1. Backup Hierarchy

1. **Model Weights & Metadata**:
   - Primary: `models/registry/<version>/`
   - Checksum: SHA-256 fingerprint verified against `results/production_lock.json`.
2. **SQLite Database in WAL Mode**:
   - `backtest/market_memory.db` backed up via SQLite online backup API (`VACUUM INTO`).
   - Forecast snapshots, resolution outcomes, and shadow comparisons preserved.
3. **Parquet Time-Series Cache**:
   - `data/features.parquet` immutable cache.

---

## 2. Disaster Recovery & Rollback Procedure

When a promoted candidate demonstrates operational degradation:
1. Trigger `challenger_registry.rollback()`.
2. Target version restores to `PRODUCTION` status with zero data mutation.
3. All past forecasts, resolution outcomes, and provenance hashes remain intact in SQLite WAL memory.
