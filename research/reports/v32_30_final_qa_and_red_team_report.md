# BTCognitive — Master QA, Horizon Research & Red-Team Review Report (V32.30)

**Date:** 2026-10-25  
**Version:** V32.30  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY`  
**Live Execution Authorization:** `DISABLED` (Permanently fail-closed; zero live broker/order execution paths)  
**Lead Integrator:** Agent 0  
**Independent Red-Team Reviewer:** Agent 7  
**Dual Terminal State:**  
- **Software QA State:** `SOFTWARE_QA_PASS`  
- **Scientific / Economic State:** `NO_GO_NO_VALIDATED_EDGE`  

---

## 1. Multi-Agent Workstream Execution Summary

| Agent Workstream | Specialist Domain | Key Activities & Deliverables | Verdict |
| :--- | :--- | :--- | :---: |
| **Agent 0** | Coordinator & Integrator | Enforced phase order, preserved worktree integrity, verified protected file hashes, coordinated patch queue. | **PASS** |
| **Agent 1** | Forensics & Data Lineage | Audited Coinbase archive (33,424 bars), verified closed-bar semantics, confirmed 3 documented outage gaps, quarantined legacy data. | **PASS** |
| **Agent 2** | Strategy & Econometrics | Pre-registered and evaluated multi-horizon breakout strategies (24h, 72h, 168h). Proved gross edge increases with horizon, but net returns remain strictly negative. | **NO_GO_NO_VALIDATED_EDGE** |
| **Agent 3** | L2 Microstructure | Designed Coinbase L2 WebSocket architecture, Cont-Kukanov-Stoikov OFI math, and reconnect gap rules. Established horizon boundary (OFI is for entry timing, not macro direction). | **PASS (Dormant Design)** |
| **Agent 4** | Model Validity & Governance | Audited directional GBDTs (`PROVENANCE_LIMITED_RESEARCH_ONLY`) and Chronos-2 (`NOT_EXECUTED`). Established multi-horizon meta-model evaluation protocol. | **PASS** |
| **Agent 5** | Frontend UX Inventory | Mapped all UI routes, tabs, indicators, what-if tools, and governance badges in [web/app.js](file:///C:/Projects/BTCognitive/BTCognitive/web/app.js). | **PASS** |
| **Agent 6** | Independent Browser QA | Tested the live application in Chromium via [browser_subagent](file:///C:/Projects/BTCognitive/BTCognitive/research/reports/v32_30_frontend_browser_qa_matrix.md). Captured 9 screenshots, verified 14 UI feature areas, confirmed 0 console errors. | **BROWSER_QA_PASS** |
| **Agent 7** | Independent Red-Team | Challenged lookahead, cost accounting, gap handling, and UI claims. Falsified potential profitability claims. Confirmed fail-closed invariants. | **PASS** |

---

## 2. Multi-Horizon Strategy Research Findings (Pre-Registered Study)

Evaluated across all 33,424 hourly bars of the authenticated Coinbase BTC-USD dataset:

| Strategy Specification | Horizon ($H$) | Trades ($N$) | Win Rate (TP) | Gross Return | Net Return (27 bps) | 95% Bootstrap CI (27 bps) | Net Return (87 bps) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`TSMOM_DONCHIAN_24H_168H`** (Control) | 24h | 758 | 42.2% | $+0.0880\text{ R}$ | **$-0.2465\text{ R}$** | $[-0.3440, -0.1524]$ | **$-0.9898\text{ R}$** |
| **`TSMOM_DONCHIAN_72H_168H`** (Cand 1) | 72h | 477 | 43.8% | $+0.1016\text{ R}$ | **$-0.2383\text{ R}$** | $[-0.3570, -0.1087]$ | **$-0.9934\text{ R}$** |
| **`TSMOM_DONCHIAN_168H_336H`** (Cand 2) | 168h | 298 | 46.0% | $+0.1629\text{ R}$ | **$-0.1778\text{ R}$** | $[-0.3317, -0.0101]$ | **$-0.9349\text{ R}$** |

### Red-Team Scientific Assessment
1. **Gross Edge Increases with Horizon:** Slower breakout triggers with longer holding horizons capture larger price excursions, nearly doubling gross R from $+0.088\text{ R}$ to $+0.163\text{ R}$.
2. **Transaction Costs Remain Dominant:** Despite larger moves, exchange transaction friction (27 bps to 87 bps round-trip) erodes the entire gross edge. At 27 bps, the 95% bootstrap CI upper bound on the 168h macro horizon remains strictly negative ($-0.0101\text{ R}$).
3. **Pre-Registered Decision:** Under the pre-registered Economic Viability Gate ($EV_{\text{net}} > 0.0\text{ R}$), all three horizons fail. The scientific verdict is definitively **`NO_GO_NO_VALIDATED_EDGE`**.

---

## 3. Independent Browser QA Results & Visual Evidence

The independent browser subagent tested the live application at `http://127.0.0.1:8000/#/terminal`:
- **Interactive Views Tested:** Forecast view (1h, 4h, 24h), Market view (evidence router toggles), Strategies view (5 MEIE archetypes), Trades view (paper execution contracts), Research view (what-if scenario lab), Replay view (time machine), Arena view (virtual bankroll).
- **Responsive Layouts:** Desktop ($1536 \times 730$), Tablet ($1024 \times 768$), and Mobile/Narrow ($800 \times 600$). Zero horizontal body overflow.
- **Console & Network Health:** **0 uncaught exceptions, 0 warnings**.
- **Visual Artifacts:** 9 recorded screenshots and a full WebP session recording saved to artifact directory:
  - Desktop View: `desktop_terminal_initial_1792911705548.png`
  - Market View: `market_tab_view_1792911719450.png`
  - Strategies View: `strategies_tab_view_1792911731506.png`
  - Trades View: `trades_tab_view_1792911742520.png`
  - Research View: `research_tab_view_1792911754134.png`
  - Replay View: `replay_tab_view_1792911784505.png`
  - Arena View: `arena_tab_view_1792911798632.png`
  - Responsive 1024x768: `responsive_1024x768_1792911809107.png`
  - Responsive 800x600: `responsive_800x600_1792911823085.png`

---

## 4. Protected Files Bit-Identical Audit (Baseline vs. Post-QA)

| Protected File Path | Baseline SHA-256 (V32.30 Start) | Final SHA-256 (V32.30 Post-QA) | Integrity Status |
| :--- | :--- | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | `91c3aed984002f611a59c78a2eb4c342c0970baebbd2e3d6df7973be7acf1dd7` | **MATCH (Byte-Identical)** |
| `data/prospective_shadow_v1.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **MATCH (Byte-Identical)** |
| `data/prospective_entry_ledger_v2.jsonl` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | `e6e33e3c7beb4c255467e967fc819b85481b0afb1052c3ea7bd248c53f87b604` | **MATCH (Byte-Identical)** |
| `data/raw/ohlcv.parquet` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | `1e722f33734a89e74764c02fde0552752cc1ea2eff62ca9046c9d6edf2347d5c` | **MATCH (Byte-Identical)** |
| `data/raw/ohlcv_pre_backfill_backup.parquet` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | `c4949e5b5695ffa172677681b15af2ea6167e73317c3496546f2286a6730b1c8` | **MATCH (Byte-Identical)** |

---

## 5. Independent Red-Team Falsification Checklist

- [x] **Zero Live Trading Path:** All order routing calls throw `RuntimeError("Live execution permanently disabled")`.
- [x] **Point-in-Time Causality:** Entry filled strictly at $t+1$ Open; Donchian channel strictly excludes bar $t$ via `.shift(1)`.
- [x] **Conservative Collision Resolution:** Same-bar target/stop collision resolves strictly as `SL_FIRST`.
- [x] **Timeout Realized P&L:** Realized signed return $\frac{P_{\text{exit}} - P_{\text{entry}}}{1R}$ converted to R units; costs deducted exactly once.
- [x] **Zero Synthetic Fabrication:** 3 documented outage gaps excluded or preserved; zero synthetic bars interpolated.
- [x] **Isolated Socket Testing:** Real HTTP server cleanly started on dynamic ephemeral port and shut down with zero dangling listeners on port 8000.
- [x] **Clean Dependency Manifests:** Heavy research packages (`chronos-forecasting`, `torch`) isolated in [requirements-research.txt](file:///C:/Projects/BTCognitive/BTCognitive/requirements-research.txt). Untrusted pickle models (`tabicl_finetuned.pkl`) rejected.
- [x] **Truthful Status Reporting:** Chronos-2 labeled `INFERENCE NOT EXECUTED`; GBDTs labeled `PROVENANCE_LIMITED_RESEARCH_ONLY`.
- [x] **Preserved Protected Ledgers:** All five protected files verified bit-identical.

---

## 6. Final Dual Terminal State Declaration

### Software QA State: `SOFTWARE_QA_PASS`
All 73 backend unit/integration tests and frontend tests pass 100%. Real HTTP transport verification passes over loopback socket. The independent browser subagent validated 14 feature areas across multiple viewports with zero console errors. All protected file hashes match baseline.

### Scientific / Economic State: `NO_GO_NO_VALIDATED_EDGE`
Evaluated across 33,424 hourly Coinbase BTC-USD candles across 24h, 72h, and 168h horizons: gross edge improves from $+0.0880\text{ R}$ to $+0.1629\text{ R}$, but net returns after exchange friction remain strictly negative ($-0.2465\text{ R}$ at 24h, $-0.2383\text{ R}$ at 72h, $-0.1778\text{ R}$ at 168h under 27 bps). 95% bootstrap confidence interval upper bounds remain $< 0.0\text{ R}$. All research alerts remain muted.
