# V32.76 — Data Integrity & Forensic Provenance Audit Report

**Workstream:** Agent 1 — Data Integrity & Provenance Auditor  
**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** Forensic Data Integrity Specialist (Agent 1)  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Research Governance Authority Record  

---

## 1. Executive Summary & Incident Forensic Ruling

| Investigation Dimension | Forensic Finding | Governance Determination |
|---|---|---|
| **P0 Incident: Accidental Network Sync** | A mock mismatch in `tests/test_scenario_planner_and_inference_v6.py` (`requests.get` vs `urllib.request.urlopen`) caused live retrieval of Coinbase candles. | **ROOT CAUSE VERIFIED & REMEDIATED** via process-level socket isolation. |
| **Appended Bar Count** | Exactly 93 hourly candles appended (`2026-10-26 17:00 UTC` to `2026-10-30 13:00 UTC`). | **AUDITED & VALIDATED** against Coinbase Exchange API candle invariants. |
| **Dataset State Separation** | Two distinct datasets established on disk: `ohlcv_checkpoint_42233_bars.parquet` and `ohlcv_version_42326_bars.parquet`. | **PERMANENT PARTITION ESTABLISHED** — Hashes must never be treated as interchangeable. |
| **Integrity of Appended Candles** | 0 duplicates, 0 nulls, 0 missing hours, 100% OHLC ordering compliance ($L \le \min(O,C) \le \max(O,C) \le H$), volume $\ge 0$. | **LEGITIMATE EMPIRICAL DATA** — Non-synthetic, verified closed hourly candles. |
| **Historical Backup & Ledgers** | All 5 historical backups and prospective ledgers remain bit-identical. | **VERIFIED BIT-IDENTICAL**. |

---

## 2. Root Cause Analysis: The Accidental Coinbase Ingestion

### 2.1 The Code Defect
In `tests/test_scenario_planner_and_inference_v6.py::test_candle_sync_bounded_backoff`:
```python
# DEFECTIVE CODE:
with patch("engine.prospective_worker.requests.get") as mock_get:
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_get.return_value = mock_resp
    res = sync_live_candles(max_retries=2, base_backoff=0.01)
```
However, the implementation in `engine/prospective_worker.py` (lines 224–226) does not import or use `requests`:
```python
# ACTUAL IMPLEMENTATION:
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
    data = json.loads(resp.read().decode("utf-8"))
```

### 2.2 The Consequence
Because `requests.get` was patched instead of `urllib.request.urlopen`, the call bypassed the mock completely. The test issued a real HTTP GET request to:
`https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600`
Coinbase returned HTTP 200 with closed hourly candles. `sync_live_candles` validated the candles, identified 93 new candles newer than `max_existing_ts` (`2026-10-26 16:00 UTC`), concatenated them to `data/raw/ohlcv.parquet`, and atomically replaced the file on disk.

### 2.3 The Dual-Hash Test Workaround Rejection
During V32.75, a test assertion in `tests/test_v32_48_integrated_analyse_and_tournament.py` was altered to accept either `c007cd61...` or `ba06fb53...`.
**Agent 1 Forensic Ruling:** That workaround is **REJECTED**. A cryptographic hash is an immutable digest of a specific byte sequence. Treating multiple distinct hashes as valid for one immutable artifact creates silent dataset drift. The Product Manager's ruling is implemented: the two versions are permanently separated into distinct named files.

---

## 3. Forensic Reconstruction of the 93 Appended Candles

Forensic inspection of the 93 appended bars from index 42,233 through 42,325 confirms:

- **Row Count:** Exactly 93 closed hourly bars.
- **Start Bar (Index 42,233):**
  - Timestamp: `2026-10-26 17:00:00+00:00`
  - Open: `$80,099.58` | High: `$80,436.18` | Low: `$79,998.17` | Close: `$80,196.98` | Volume: `349.496658`
  - Available Time: `2026-10-26 18:00:00+00:00`
- **End Bar (Index 42,325):**
  - Timestamp: `2026-10-30 13:00:00+00:00`
  - Open: `$77,317.91` | High: `$77,317.91` | Low: `$76,409.00` | Close: `$76,985.40` | Volume: `1088.646561`
  - Available Time: `2026-10-30 14:00:00+00:00`
- **Data Hygiene:**
  - Duplicate Timestamps: `0`
  - Missing Hourly Intervals: `0` (diff is strictly `Timedelta('0 days 01:00:00')` throughout)
  - Null / NaN Values: `0` across all columns (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `available_time`)
  - OHLC Geometry Invariants: `True` ($L \le \min(O,C)$ and $H \ge \max(O,C)$ on 100% of rows)
  - Price Range: Low `$76,301.02` to High `$81,890.00`
- **Fabrication Check:** Negative. The candles match verifiable public Coinbase Exchange spot market history for BTC/USD over October 26–30, 2026. No synthetic metrics or fabricated rows exist.

---

## 4. Master Dataset Partition & Cryptographic Manifest

The repository datasets are partitioned and version-locked as follows:

| Version Identifier | File Path | Rows | SHA256 Hash | Governed Role |
|---|---|---|---|---|
| **Checkpoint 42,233** | `data/raw/ohlcv_checkpoint_42233_bars.parquet` | 42,233 | `f5c15cb11b9d51cf0077c8f8052086382deb1d8577749cbab8d0134842c7a94f` | **FROZEN CHECKPOINT** (Through 2026-10-26 16:00 UTC). Primary baseline for V32.73/V32.74 replays. |
| **Version 42,326** | `data/raw/ohlcv_version_42326_bars.parquet` | 42,326 | `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057` | **VERSIONED EXTENDED DATASET** (Through 2026-10-30 13:00 UTC). Validated historical data for V32.76 onwards. |
| **Continuous Backfill** | `data/raw/ohlcv_backfilled.parquet` | 42,177 | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **GAP-FREE EXPERIMENTAL SERIES** (Continuous hourly series for causal modeling). |
| **Pre-Backfill Backup** | `data/raw/ohlcv_pre_backfill_backup.parquet` | 41,434 | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **HISTORICAL ARCHIVE WITH GAPS** (Contains 2023 outage & Sept 2026 gap). |

### Protected Prospective Ledgers Verification:
- `data/prospective_entry_ledger.jsonl`: `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` (3,385 bytes — MATCH)
- `data/prospective_shadow_v1.jsonl`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes — MATCH)
- `data/prospective_entry_ledger_v2.jsonl`: `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` (12,744 bytes — MATCH)

---

## 5. Remediation & Process Guardrails

To prevent recurrence of accidental external network requests and dataset mutations:

1. **Process-Level Socket Interception:** Implemented in `tests/conftest.py`. Any socket connection to a non-loopback address raises `RuntimeError("OFFLINE_NETWORK_BLOCKED: ...")`.
2. **Protected Dataset Write Protection:** Implemented in `tests/conftest.py`. `pd.DataFrame.to_parquet` intercepts any attempt to write to `data/raw/` or `data/prospective_*.jsonl`, raising `RuntimeError("PROTECTED_DATASET_MUTATION_BLOCKED: ...")`.
3. **Corrected Test Mock:** In `tests/test_scenario_planner_and_inference_v6.py`, `urllib.request.urlopen` is patched with `side_effect = Exception("Coinbase 503")`, eliminating any reliance on unmocked transports.
4. **Permanent Separation:** All research experiments must explicitly document whether they use `ohlcv_checkpoint_42233_bars.parquet` or `ohlcv_version_42326_bars.parquet`. Mixing or silently aliasing hashes is strictly prohibited.

*Signed by Specialist Agent 1 (Data Integrity & Provenance Auditor)*

