# BTCognitive V32.66 — Repository State Audit (Before / After)

**Audit Timestamp:** 30 October 2026  
**Repository Branch:** `main` (single branch, preserved throughout execution)  
**Baseline Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  
**Current HEAD Commit SHA:** `25d483f4c3646661b57311de9d0b53d2be881adb`  

---

## 1. Non-Negotiable Git Invariants Audit

- **Branch Operations:** Zero branches created, checked out, or deleted.
- **Commit History:** Zero commits performed (`HEAD` remains strictly `25d483f4c3646661b57311de9d0b53d2be881adb`).
- **Push Operations:** Zero remote network pushes attempted.
- **Destructive Operations:** Zero git resets (`git reset --hard`), checkouts (`git checkout .`), stashes, or cleans executed.
- **User Modification Preservation:** All pre-existing modified files in working tree remain intact and untouched.

---

## 2. Protected Empirical Artifacts Invariance Audit

All six protected empirical datasets and prospective ledgers were verified before and after task execution using SHA-256 cryptographic hashes. All six exhibit 100% bit-level invariance:

| Dataset / Ledger Path | Canonical Baseline SHA-256 | Post-Execution SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `data/raw/ohlcv.parquet` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | `c007cd613bec3012fa427d047b466d5e250bd4451b5062d311f387e8afd0ce3f` | **BIT-IDENTICAL** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **BIT-IDENTICAL** |
| `data/raw/ohlcv_backfilled.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **BIT-IDENTICAL** |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **BIT-IDENTICAL** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **BIT-IDENTICAL** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **BIT-IDENTICAL** |

---

## 3. Newly Created Audit & Verification Files (Untracked)

The following files were created specifically for V32.66 verification and audit evidence:
1. `tests/test_v32_66_provider_contract.py` — Provider-neutral contract test suite (8/8 passed).
2. `engine/run_v32_66_browser_acceptance.py` — Real-browser CDP acceptance runner (8/8 passed).
3. `research/reports/offline_mvp/20261030_150000_v32_66_rights_closure_and_mvp_gates/` — Governed deliverable directory containing reports, matrices, and hashes.
4. `research/reports/artifacts/browser_qa/v32_66/` — Browser evidence artifacts (8 PNG screenshots, console.log, network_requests.json, browser_acceptance_results.json).

