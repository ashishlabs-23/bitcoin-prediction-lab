# V32.76 — Research Decision Record & Multi-Agent Synthesis

**Milestone:** BTCognitive V32.76 — Multi-Agent Research Integrity & Conditional Entry Investigation  
**Date:** 2026-10-30  
**Evaluator:** Lead Quantitative Research Director & Integration Owner  
**Governing Repo:** `https://github.com/ashishlabs-23/bitcoin-prediction-lab`  
**Classification:** Governing Decision Record (Phase 2 Synthesis)  

---

## 1. Synthesis of Specialist Workstreams

The Lead Research Director has reviewed and reconciled all seven specialist reports (Agents 1 through 7). The table below formalizes the classification of every finding in accordance with research governance standards:

| # | Investigation Topic | Specialist Finding | Red-Team Challenge | Lead Synthesis & Governing Classification |
|---|---|---|---|---|
| **1** | **P0 Accidental Network Call** | Test mocked `requests.get` while code used `urllib.request.urlopen`. 93 candles appended to `ohlcv.parquet`. | Accidental dataset mutation is a serious data provenance failure that could contaminate historical replays. | **`VERIFIED`** — Remediated via process-level socket interception in `tests/conftest.py`. Network access is permanently blocked during test runs. |
| **2** | **Dataset Version Separation** | 42,233-bar checkpoint and 42,326-bar live feed separated into distinct files. | Dual-hash test assertion was an unacceptable workaround. | **`VERIFIED`** — `ohlcv_checkpoint_42233_bars.parquet` (`f5c15cb1...`) and `ohlcv_version_42326_bars.parquet` (`ba06fb53...`) are permanent distinct assets. Hashes are never aliased. |
| **3** | **Appended 93 Candles Quality** | 93 hourly bars from Coinbase (Oct 26 17:00 to Oct 30 13:00 UTC) with 0 gaps, 0 nulls, valid OHLC. | Are the candles legitimate empirical data or synthetic? | **`VERIFIED`** — Legitimate empirical closed hourly bars from Coinbase Exchange. Non-synthetic. Quarantined to version 42,326. |
| **4** | **Causal Entry Filter Edge** | Tested 4 filters (Trend Pullback, Donchian Breakout, Vol-Filtered, Trend Following). None achieved positive net EV. | Win rates of 29–34% are below or equal to zero-drift random walk expectation. No predictive alpha exists. | **`REJECTED`** (as candidate strategies) / **`VERIFIED`** (as an empirical finding: technical indicators fail to beat fee hurdle). |
| **5** | **0.75% Stop-Loss Geometry** | Stop-loss is narrower than 24h market noise ($0.75\% < 2.14\%$). Stop-out rates exceed 60%. | Slower trends are wiped out by random intraday wicks. | **`VERIFIED`** — Static 0.75% stop-loss on 1h BTC bars is structurally flawed. Future milestones must use ATR-scaled dynamic barriers. |
| **6** | **Passive Maker Friction** | SCEN_3 assumes 4 bps round-trip friction with 100% fill rate. | Limit orders suffer adverse selection and non-execution during fast breakouts. | **`REJECTED`** — SCEN_3 is reclassified as `UNVERIFIED_AND_UNREALISTIC`. Only verified taker tiers (Binance 24 bps, Coinbase 87 bps) are valid for economic gates. |
| **7** | **Multiple Testing & Overfitting** | Evaluating multiple filters without DSR/PBO leads to false discoveries. | Backtest selection bias guarantees finding a lucky strategy among dozens of attempts. | **`VERIFIED`** — Pre-registered DSR and PBO criteria adopted. Since all V32.74/V32.76 filters produced negative net Sharpe, PBO is 0. |
| **8** | **Active Test Health vs Legacy** | 79 / 79 core tests pass cleanly in 38.88s. | Repository contains 348 test files; running `pytest tests/` was killed due to legacy test timeouts. | **`PARTIALLY_VERIFIED`** — Core active regression suite is 100% passing (79/79). The remaining ~338 files are historical milestone artifacts requiring formal archiving. |
| **9** | **ML Readiness** | 4 targets and 8 features audited. Zero leakage. | ML on lagging OHLCV indicators will simply overfit historical noise. | **`VERIFIED`** — No models trained, tuned, or promoted. System remains strictly `OFFLINE_RESEARCH_ONLY`. |
| **10** | **Analysis Button State** | Fail-closed gate in `engine/regime_strategy_tournament.py` outputs `ABSTAIN`. | Enabling BUY/SELL would guarantee negative expected return for users. | **`VERIFIED`** — Abstention gate must remain permanently active until a statistically verified positive net EV strategy is proven. |

---

## 2. Definitive Governing Decisions

1. **Governed Milestone Determination:**
   **`BLOCKED_BY_RESEARCH_VALIDITY`**  
   While test reliability, software architecture, data provenance, and process-level network isolation are fully resolved, **no causal entry filter has demonstrated positive net expected value after verified execution costs**.

2. **Dataset Lineage Policy:**
   - `ohlcv_checkpoint_42233_bars.parquet` is the immutable reference dataset for all historical replays through October 26, 2026 16:00 UTC.
   - `ohlcv_version_42326_bars.parquet` is the extended reference dataset through October 30, 2026 13:00 UTC.
   - The dual-hash test workaround is permanently abolished.

3. **Software & Test Isolation Standards:**
   - Process-level socket interception in `tests/conftest.py` is permanently established.
   - In-memory/filesystem dataset write protection in `tests/conftest.py` is permanently established.
   - The 79-test suite is established as the Authoritative Core CI Suite.

4. **Analysis Button Gate:**
   - Permanent fail-closed `ABSTAIN` preserved in `engine/regime_strategy_tournament.py` (lines 1162–1204).

5. **Live Trading Gate:**
   - Permanent `DISABLED`. Zero broker execution, zero capital deployment.

*Signed by Lead Quantitative Research Director & Integration Owner*

