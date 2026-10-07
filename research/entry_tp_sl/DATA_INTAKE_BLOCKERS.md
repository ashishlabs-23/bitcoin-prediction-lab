# Data Intake Verification & Resolution Log — Entry/TP/SL Track

**Track ID:** `BTC-ENTRY-TP-SL-V3`  
**Current Gate:** `G0 Foundation Integrity`  
**Data Status:** `PASS`  
**Approval Status:** `approved_for_research = true`  
**Date:** 2026-10-07  

---

## 1. Resolution Summary

All initial data intake blockers have been resolved and verified:

| Blocker ID | Domain | Resolution Description | Verification Status |
|---|---|---|---|
| **DIB-01** | **Physical Snapshot & Object Identity** | Snapshot placed at `data/raw/btcusd_1-min_data.csv` (393,952,273 bytes). SHA-256 computed: `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`. | **`RESOLVED / VERIFIED`** |
| **DIB-02** | **Candidate Classification** | Snapshot verified: 7,766,111 rows, spanning 2012-01-01 00:01:00 UTC to 2026-10-07 03:11:00 UTC; 0 null values; all price boundary checks passed ($H \ge L, H \ge O, H \ge C, L \le O, L \le C$). | **`RESOLVED / VERIFIED`** |
| **DIB-03** | **Rights & License Compliance** | User explicitly approved CC BY-SA 4.0 license terms for research exploration. | **`RESOLVED / APPROVED`** |
| **DIB-04** | **Timestamp & Boundary Semantics** | Monotonic increasing Unix seconds timestamps verified with 0 duplicates. | **`RESOLVED / VERIFIED`** |
| **DIB-05** | **Gap & Missing-Bar Contract** | Policy recorded in `data_intake_manifest.json`: fail closed on irregular intervals exceeding tolerance. | **`RESOLVED / RECORDED`** |

---

## 2. Dataset Provenance Manifest

- **Target File:** `data/raw/btcusd_1-min_data.csv`
- **SHA-256:** `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`
- **Total Rows:** `7,766,111`
- **Columns:** `Timestamp, Open, High, Low, Close, Volume`
- **Date Range:** `2012-01-01 00:01:00 UTC` to `2026-10-07 03:11:00 UTC`
- **Manifest:** `research/entry_tp_sl/data_intake_manifest.json`
