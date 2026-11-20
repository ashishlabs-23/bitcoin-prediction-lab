# BTCognitive V30.9 — Statistical Gate Validity Audit Report

**Date:** October 23, 2026  
**HEAD Commit:** `24092a118bb4285cb2675cbc02694d34800d92d5`  
**Strategy Under Audit:** `HTF_RANGE_EXPANSION_BREAKOUT` (Spec Hash: `e1a3436a18ff992d`)  
**Operating Protocol:** `PROTOCOL-SHADOW-V1.1` + V30.5 Amendments  
**Final Governed Status:** `BLOCKED — PROTOCOL CLARIFICATION REQUIRED`  

---

## 1. Executive Summary

Milestone **V30.9** independently audits the econometric and statistical coherence of the frozen Protocol V1.1 statistical evaluation rules:
- The 50-observation interim review.
- The 100-block confirmatory gate.
- The Politis & Romano (1994) stationary bootstrap implementation.
- The Diebold–Mariano paired test with Harvey–Leybourne–Newbold (1997) correction.

### Principal Audit Finding:
A critical conceptual and mathematical ambiguity exists in the definition of the **"100-block confirmatory gate"** when applied to trade setup strategies:
1. **Provenance Mismatch:** The phrase *"100 non-overlapping clean blocks"* was inherited verbatim from `AGENTS.md` and V24 volatility forecasting protocols (`rv24h_var_ann`), where 1 clean block was defined as **one 24-hour calendar day**.
2. **Trade Setup Disconnect:** For Strategy D (`HTF_RANGE_EXPANSION_BREAKOUT`), trades occur sporadically (only upon a breakout of the 20-bar 4h high) and have stochastic holding periods ranging from 4 hours to 72 hours.
3. **The Unjustified 500-Trade Claim:** In V30.8, it was asserted that 100 blocks equals $100 \times 5 = 500\text{ completed trades}$ by multiplying the confirmatory blocks by the bootstrap expected block length ($E[L] = 5$). **This multiplication is mathematically and econometrically unsupported by bootstrap theory.**
4. **Governed Decision:** In accordance with the mandate (*"If the protocol is ambiguous or invalid, mark the gate `BLOCKED — PROTOCOL CLARIFICATION REQUIRED`. Do not silently reinterpret it"*), the confirmatory gate is formally marked **`BLOCKED — PROTOCOL CLARIFICATION REQUIRED`**.

---

## 2. Precise Sampling-Unit Definitions

To eliminate persistent confusion across historical reports, the sampling hierarchy is formally defined:

| Concept | Formal Definition | Operational Measurement | Statistical Properties |
| :--- | :--- | :--- | :--- |
| **Candle** | 1-hour closed market OHLCV bar | Timestamp, OHLC, Volume in `ohlcv.parquet` | Highly autocorrelated continuous price series; NOT an evaluation unit. |
| **Candidate Setup** | Breakout trigger condition met at closed 4h bar close ($t_0$) | Immutable `SHADOW_CANDIDATE` record | Unresolved decision point. Carries proposed fill ($t_0 + 1\text{h}$) and stop level. Zero realized return. |
| **Completed Outcome (Trade Unit)** | Closed excursion following stop-loss penetration or 18-bar (72h) horizon expiry | Immutable `SHADOW_OUTCOME` record | Discrete economic observation with realized net return (bps), net R, holding duration, and MFE/MAE. |
| **Non-Overlapping Interval** | Time span $[t_{\text{entry}, i}, t_{\text{exit}, i}]$ of trade $i$ | In-position gating suppresses subsequent signals until trade exit | Trade intervals do not overlap in time; however, flat periods create irregular temporal gaps between trades. |
| **Bootstrap Resampling Block** | Stochastically sampled slice of length $L \sim \text{Geometric}(p=0.20)$ with $E[L]=5$ | Politis & Romano (1994) stationary bootstrap loop | Computational device used during statistical simulation to preserve local dependence; NOT a data partitioning unit. |
| **Effective Information ($N_{\text{eff}}$)** | Independent information content under serial correlation: $N_{\text{eff}} \approx N \frac{1 - \rho}{1 + \rho}$ | Estimated via autocorrelation function of trade returns | Because volatility regimes cluster, $N$ sequential trades carry less information than $N$ independent observations ($N_{\text{eff}} < N$). |

---

## 3. Mathematical Assessment of the 100-Block vs. 500-Trade Claim

### 3.1 Traceability Analysis

1. **`AGENTS.md` (§5, Item 4):**
   > *"A minimum of 100 non-overlapping clean blocks is required before confirmatory prospective evaluation."*
2. **`research/protocol_v1_1.md` (§1, Row 3):**
   > *"Clarified that 1 observation = 1 candidate trade setup spanning up to 18 4h bars (72 hours)."*
3. **`research/protocol_v1_1.md` (§1, Row 4):**
   > *"Adjusted stationary bootstrap block length to $E[L] = 5$ trade observations (~15–20 calendar days)."*
4. **`research/protocol_v1_1.md` (§1, Row 6):**
   > *"The 100-block hurdle remains the confirmatory evidence gate."*

### 3.2 The Mathematical Flaw in Multiplying $100 \times 5 = 500$

In Politis & Romano (1994), the stationary bootstrap resamples a dataset of size $N$ using blocks of random length drawn from a geometric distribution with mean $E[L]$:
- The parameter $E[L] = 5$ is a **resampling bandwidth parameter**, analogous to the Newey–West lag truncation parameter $m$.
- The bootstrap takes a sample of size $N$ and resamples $N$ observations from it.
- **It does NOT partition the dataset into $N / 5$ non-overlapping blocks.**
- Stating that *"100 blocks requires $100 \times 5 = 500$ completed trades"* confuses the **target sample size** with the **resampling block length**.
- If the protocol intended $N = 500$, it should have stated $N = 500\text{ trades}$.
- If the protocol intended $N = 100\text{ trades}$, then each trade is a "block" of non-overlapping market exposure, and the sample size is $N = 100$.

### 3.3 Protocol Code Traceability Defect

An exhaustive search of `engine/prospective_shadow_collector.py` and `engine/shadow_feed_runner.py` revealed that **zero automated code exists to evaluate whether the confirmatory gate has been satisfied**:
- The code tracks `total_candidates`, `total_outcomes`, and `pending_resolution`.
- No function exists that evaluates $N \ge 100$ or computes the confirmatory stationary bootstrap gate.
- The gate exists solely in text documents (`AGENTS.md` and `protocol_v1_1.md`).

---

## 4. Bootstrap and DM-HLN Implementation Audit

### 4.1 Politis & Romano (1994) Stationary Bootstrap
- **Source Code:** `engine/stationary_bootstrap.py`.
- **Implementation:**
  - `generate_stationary_bootstrap_segment_indices()` draws geometric block lengths with $p = 1 / E[L] = 0.20$.
  - Resamples circularly strictly within contiguous segments, preventing cross-gap leakage.
- **Verdict:** **Mathematically Sound & Computationally Correct.** The algorithm faithfully implements Politis & Romano (1994).

### 4.2 Diebold–Mariano with Harvey–Leybourne–Newbold (1997) Correction
- **Source Code:** `models/challengers/har_qlike_24h_challenger.py` and `engine/price_forecast_engine.py`.
- **Implementation:**
  - Differential: $d_i = \text{Loss}(\text{Benchmark}) - \text{Loss}(\text{Strategy})$.
  - One-step finite-sample correction: $\text{HLN} = \text{DM} \times \sqrt{(T - 1) / T}$.
  - Reference distribution: Student's $t$ with $T - 1$ degrees of freedom.
- **Unresolved Horizon Alignment Ambiguity:**
  In Strategy D, trades have variable holding horizons (4h to 72h) and the strategy is flat between trades. Protocol V1.1 does not specify which economic comparison DM-HLN tests:
  - *Option 1 (Trade-Matched Excursion):* Compares strategy trade return to Buy & Hold return strictly over the holding window $[t_{\text{entry}, i}, t_{\text{exit}, i}]$.
  - *Option 2 (Full Calendar Time):* Compares strategy's overall equity curve (including 0% cash return during flat periods) against continuous Buy & Hold over calendar time.
  This must be explicitly resolved in Protocol V1.2.

### 4.3 Early Stopping Review (50 Observations)
- Evaluated when $N = 50$ completed trade outcomes accumulate.
- **Criteria:** Sample mean net expectancy $< 0$ bps under `COINBASE_RETAIL_87BPS` OR maximum equity drawdown $> 35\%$.
- **Verdict:** Logically coherent and implementable once 50 prospective outcomes exist. Currently, with 0 prospective outcomes, it remains unevaluable.

---

## 5. Timeline and Feasibility Recalculation

Trade accumulation duration estimates depend entirely on how the confirmatory gate is clarified:

| Interpretation | Required Trades ($N$) | Trade Frequency Estimate | Estimated Calendar Time | Feasibility Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Interpretation A (100 Trade Observations)** | 100 | ~1 trade every 3.5 days | **~350 calendar days** (~1.0 year) | **Feasible prospective research gate.** Provides $N_{\text{eff}} \approx 50$ under mild serial dependence. |
| **Interpretation B (100 Calendar Weeks)** | ~200 | ~1 trade every 3.5 days | **~700 calendar days** (~1.9 years) | **Feasible multi-year institutional validation.** |
| **Interpretation C (500 Trades from $100 \times 5$)** | 500 | ~1 trade every 3.5 days | **~1,750 calendar days** (~4.8 years) | **Impractical / Excessive for an initial shadow candidate.** Exceeds typical crypto market cycle (4 years). |

*Crucial Warning:* Trade frequency based on retrospective 2026 data is an **estimate**, not a guarantee. Breakout frequency varies dramatically across market volatility regimes.

---

## 6. Regression & Verification Test Results

### 6.1 Targeted Test Suite (59/59 Passed)

Executed across all shadow and verification test files:
```powershell
.venv_win\Scripts\python.exe -m pytest tests/test_entry_contracts_and_resolver.py tests/test_prospective_shadow_collector.py tests/test_shadow_feed_runner.py tests/test_v30_6_operational_proof.py tests/test_v30_7_shadow_burnin.py tests/test_v30_8_collection_integrity.py tests/test_v30_9_statistical_gate_audit.py -q
```

**Results:**
```
...........................................................              [100%]
59 passed in 5.64s
```

- `tests/test_v30_9_statistical_gate_audit.py` (5 tests):
  - `test_sampling_unit_variable_duration_vs_calendar_blocks`: PASSED
  - `test_audit_unjustified_500_trade_multiplication`: PASSED (proves $100 \times 5 = 500$ was an unverified claim)
  - `test_effective_sample_size_calculation`: PASSED ($N_{\text{eff}} = 53.8$ for $N=100, \rho=0.3$)
  - `test_dm_hln_aligned_trade_comparison`: PASSED
  - `test_early_stopping_drawdown_computation`: PASSED

### 6.2 Ledger Cryptographic Verification

| Ledger File | Record Count | SHA-256 Digest | Status |
| :--- | :---: | :--- | :---: |
| `data/prospective_entry_ledger.jsonl` | 5 | `91C3AED984002F611A59C78A2EB4C342C0970BAEBBD2E3D6DF7973BE7ACF1DD7` | ✅ **Untouched** |
| `data/prospective_shadow_v1.jsonl` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` | ✅ **Ready (0 records)** |

---

## 7. Proposed Protocol Amendments (For Future V1.2 Review)

The following amendments are proposed for formal governance review. In accordance with hard constraints, **these have NOT been applied to the frozen Protocol V1.1**:

### Proposed Amendment 1: Disambiguate Confirmatory Gate Sample Size
- **Proposal:** Amend Protocol V1.1 §1 Row 6 to explicitly define the confirmatory gate as **$N = 100$ completed non-overlapping trade setup outcomes** (rather than the ambiguous term "100 blocks").
- **Rationale:** Because in-position gating enforces that trades cannot overlap in time, each trade setup represents a non-overlapping segment of market exposure. Requiring $N = 100$ completed trades provides adequate power ($N_{\text{eff}} \approx 40\text{--}60$ under regime persistence) over ~1 calendar year.

### Proposed Amendment 2: Clarify Bootstrap Resampling Role
- **Proposal:** Clarify that $E[L] = 5$ is strictly the **resampling parameter** of the Politis & Romano (1994) stationary bootstrap algorithm, used to construct empirical 95% confidence intervals from the $N = 100$ sample, and does not multiply or expand the required sample size.

### Proposed Amendment 3: Specify DM-HLN Benchmark Horizon Matching
- **Proposal:** Explicitly mandate **Trade-Matched Excursion Matching** for the DM-HLN test: for each trade setup $i$, the Buy & Hold loss/return is computed over $[t_{\text{entry}, i}, t_{\text{exit}, i}]$.

---

## 8. Final Governed Milestone Decision

### Explicit Final Milestone Decision:
$$\mathbf{BLOCKED\ —\ PROTOCOL\ CLARIFICATION\ REQUIRED}$$

### Formal Justification:
1. **The "100-block hurdle" in Protocol V1.1 is mathematically ambiguous** when applied to trade setup strategies: it conflates calendar blocks inherited from volatility forecasting with trade setup units and the bootstrap resampling parameter $E[L]=5$.
2. Multiplying 100 blocks by 5 to claim a 500-trade requirement ($4.8\text{ years}$) is econometrically unsupported by the protocol text.
3. The benchmark alignment for the DM-HLN test on variable-duration trades lacks an explicit definition in Protocol V1.1.
4. Per prompt instructions (*"If the protocol is ambiguous or invalid, mark the gate `BLOCKED — PROTOCOL CLARIFICATION REQUIRED`. Do not silently reinterpret it"*), this decision formally halts confirmatory gate claims until a governed Protocol V1.2 amendment is formally approved.
5. **Ongoing shadow collection is unaffected:** The background collection loop continues safely accumulating genuine market data.
