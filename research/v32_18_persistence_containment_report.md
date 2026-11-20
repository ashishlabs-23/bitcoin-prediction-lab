# BTCognitive V32.18 — Smart Entry Persistence Containment Report

**Date:** October 2026  
**Status:** CONTAINMENT VERIFIED  
**Repository:** https://github.com/ashishlabs-23/bitcoin-prediction-lab  
**Scope:** Strict persistence containment for Smart Entry evaluation, API routes, and test suites.  

---

## 1. Executive Summary

During the post-commit forensic audit of V32.17, an operational defect was identified in `SmartEntryDecisionEngine.evaluate_market()`: an unconditional invocation of `self.entry_engine.log_prospective_decision(decision)` inside a blind `try...except pass` block. This defect resulted in automatic, silent appends to `data/prospective_entry_ledger_v2.jsonl` whenever market evaluation was triggered, including during unit testing, Live Terminal UI polling, and research API queries.

In V32.18, a surgical containment patch was implemented to enforce strict, default-disabled persistence boundaries. Market evaluation, API endpoints, and UI rendering are now **100% write-free by default**. Persistence requires an explicit opt-in parameter, tests are redirected to isolated temporary storage, failures are handled fail-closed and logged honestly without converting `ABSTAIN` into trade acceptance, and all five protected forensic data artifacts retain their exact byte-for-byte SHA-256 digests.

---

## 2. Persistence Boundary Remediation

### 2.1 Engine Remediation (`engine/smart_entry_engine.py`)
- **Default-Disabled Signature:** Added `persist: bool = False` and `ledger_path: Optional[Union[Path, str]] = None` to `SmartEntryDecisionEngine.evaluate_market()`.
- **Elimination of Unconditional Writes:** Removed the unconditional write block. Persistence is now guarded behind `if persist:`.
- **Honest Status & Error Reporting:** If `persist=True` is supplied, success is recorded via `persisted: True` and `persisted_timestamp_utc`. If an I/O exception occurs, it is captured with `persisted: False` and `persistence_error: str(e)`. The engine fails closed, retaining `status: ABSTAIN` and `decision_action: ABSTAIN`.
- **Safe Early Exits:** All early validation exits (`live_price <= 0` and unselected strategy) return `"persisted": False`.

### 2.2 Destination Isolation (`engine/probabilistic_entry_engine.py`)
- **Target Path Parameter:** Extended `ProbabilisticEntryEngine.log_prospective_decision()` to accept `ledger_path: Optional[Union[Path, str]] = None`. When specified, writes target the isolated path rather than `self.ledger_file` (`data/prospective_entry_ledger_v2.jsonl`).

### 2.3 Research API Hardening (`api/routes_research.py`)
- **POST `/api/research/smart-entry`:** Explicitly passes `persist=False` to `evaluate_market()`. Ordinary API calls and Live Terminal UI refreshes cannot write to the prospective ledger. The response envelope returns `"persisted": False` and `"persisted_timestamp_utc": None`.
- **GET `/api/research/entry-quality`:** The `persist` query parameter defaults to `False`. When `persist=True` is explicitly passed, write operations are wrapped in an isolated exception handler. Any persistence failure is logged and surfaced via `"persisted": False` and `"persistence_error": str(e)` without altering the underlying entry decision or converting `ABSTAIN` into acceptance.
- **Abstain Payload Contract:** Updated `_smart_entry_abstain_response()` to include `"persisted": False` and `"first_passage_geometry_baseline": None`.

---

## 3. Isolated Regression Verification

A dedicated regression test suite, `tests/test_v32_18_persistence_containment.py`, was created to verify all seven containment properties.

### 3.1 Test Execution & Evidence

**Command:**  
`python -m pytest tests/test_v32_18_persistence_containment.py -v`

**Results:**  
`7 passed, 1 warning in 13.06s`

| Test Name | Verified Property | Status |
|:---|:---|:---:|
| `test_1_normal_engine_evaluation_performs_no_ledger_write` | Standard engine evaluation performs zero writes; `persisted=False`. | PASSED |
| `test_2_ordinary_api_request_performs_no_ledger_write` | Calling `/api/research/smart-entry` writes zero records. | PASSED |
| `test_3_repeated_evaluation_and_ui_refresh_do_not_append_records` | 10 rapid repeated evaluations and UI refresh requests append zero records. | PASSED |
| `test_4_persistence_disabled_when_opt_in_flag_omitted` | Default parameters omit persistence in both engine and API endpoints. | PASSED |
| `test_5_explicitly_enabled_persistence_isolated_destination` | Explicit opt-in (`persist=True`) writes only to isolated temporary fixture (`tmp_path`). | PASSED |
| `test_6_persistence_failure_fail_closed_honest_representation` | I/O failure reports `persisted=False`, attaches error, and never alters `ABSTAIN`. | PASSED |
| `test_7_existing_decision_and_api_response_contracts_intact` | All required API response fields and backwards compatibility preserved. | PASSED |

**Existing Smart Entry Test Suite Verification:**  
`python -m pytest tests/test_smart_entry_engine.py tests/test_smart_entry_api.py -v`  
`9 passed, 1 warning in 12.62s` (zero writes to production ledgers).

---

## 4. Forensic Evidence & Protected Artifact Integrity

All five protected forensic artifacts were verified before and after test execution. SHA-256 digests and file sizes remain completely unchanged:

| File Path | SHA-256 Digest | Size (Bytes) | Integrity Status |
|:---|:---|:---:|:---:|
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | 3,385 | UNCHANGED |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | UNCHANGED |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | 12,744 | UNCHANGED |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | 2,326,699 | UNCHANGED |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | 2,284,681 | UNCHANGED |

> [!NOTE]
> The nine existing records in `data/prospective_entry_ledger_v2.jsonl` originate from prior test execution runs before containment. They are preserved intact as forensic evidence and are not treated as genuine empirical market observations.

---

## 5. Unresolved Research Blockers

Containment of prospective writes addresses operational safety. The following fundamental scientific and econometric blockers remain open and must not be bypassed:

1. **Regional & Fee Structure Inconsistencies:**
   - The current baseline assumes an 87 bps round-trip transaction drag calibrated to retail Coinbase spot. In retail spot markets, shorting is impossible without perpetual futures or margin borrowing.
   - For institutional or lower-tier fee schedules, drag is reduced, but net expectancy remains negative across all evaluated tiers under realistic slippage and spread assumptions.

2. **Mixed-Source Dataset Provenance:**
   - The primary dataset in `data/raw/ohlcv.parquet` contains mixed-source data with unresolved historical backfill provenance and licensing terms (see audits in V31.1 through V31.8).
   - Confirmatory out-of-sample testing cannot proceed until a clean, single-origin dataset with verified provenance is established.

3. **Statistical Infeasibility of the 70–80% Win-Rate Objective:**
   - Under driftless Brownian motion with barrier geometry $K_{\text{TP}} = 1.5\sigma_H$ and $K_{\text{SL}} = 1.0\sigma_H$ over a 24-hour horizon, the theoretical first-passage null rate is approximately 17–19% TP-first, with ~50% timeouts.
   - Empirical evaluation across 2,440 non-overlapping 24h blocks yielded an 18.6% TP-first rate vs. 17.6% random null ($p = 0.34$, statistically indistinguishable from noise).
   - The meta-model entry probability signal (`p_tp`) exhibits an AUC of ~0.51, possessing no practical discriminatory skill.
   - Demanding a 70–80% win rate under these barrier economics is mathematically incompatible with unconditional market dynamics and represents an unproven aspirational hypothesis.

---

## 6. Governed Decision

| Dimension | Governed Verdict |
|:---|:---|
| **Containment Verification** | `CONTAINMENT VERIFIED` |
| **Prospective Ledger Writes** | Write-free by default; opt-in isolated to temporary test paths. |
| **Protected Files** | 100% byte-for-byte preserved; zero modification or deletion. |
| **Model Authorization** | `OFFLINE_RESEARCH_ONLY` |
| **Live Trading** | `DISABLED` |
