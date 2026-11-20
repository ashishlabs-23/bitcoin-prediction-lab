# BTCognitive V32.71 — Priority 1: Analysis Engine Abstention Gate & Walk-Forward Manifest Remediation Report

**Milestone:** V32.71 Core Intelligence Remediation  
**Date:** 30 October 2026  
**Auditor:** Quantitative Research Engineer & Lead Orchestrator  
**Status:** COMPLETE — ROOT CAUSE ISOLATED & GOVERNANCE GATE CONFIRMED VALID  

---

## Executive Summary

During the V32.70 audit, the UI `Analyse` button was observed to return an `ABSTAIN` verdict on every live chart invocation. This deep-dive investigation evaluated the root cause in `engine/regime_strategy_tournament.py`, tracing the code path, checking historical evaluation manifests, analyzing the candidate strategy registry, and evaluating the safety implications of the gate.

**Key Finding:** The abstention gate in `regime_strategy_tournament.py` (lines 1162–1204) is **not a software bug or broken wire**. It is an intentional, rigorous **epistemic safety circuit**. It was introduced to prevent the runtime execution of legacy mock logic (`ai_filter_passed = (i % 3 != 0)` and hardcoded sample sizes) that would otherwise fabricate unvalidated signals and present synthetic performance metrics as empirical evidence. 

Bypassing or deleting this gate would constitute an unacceptable scientific violation. The gate must be maintained, and this report outlines the precise engineering roadmap to resolve it legitimately via reproducible, causal out-of-sample walk-forward manifests.

---

## 1. Trace of the Abstention Code Path

When an end-user clicks `Analyse` on the frontend, the call invokes `/api/regime/tournament` (or `/api/analysis`), which delegates to `RegimeStrategyTournament.run_tournament()`.

### The Decision Gate (lines 1162–1204)
```python
# Check whether we have a valid, verified walk-forward manifest
verified_manifest = self._load_verified_walk_forward_manifest()

if verified_manifest is None:
    logger.warning(
        "Tournament abstention gate triggered: No verified walk-forward manifest matches "
        "registered candidates and frozen protocol."
    )
    return TournamentResult(
        winner=None,
        action="ABSTAIN",
        confidence=0.0,
        rationale=(
            "No verified walk-forward manifest matches the registered candidate strategies "
            "and frozen protocol. A fresh three-arm evaluation is also unavailable because "
            "aligned point-in-time AI forecasts and a matched baseline series are not supplied. "
            "No arm metrics were computed or reused."
        ),
        arm_metrics={},
        gate_status="ABSTAIN_UNVERIFIED_MANIFEST",
        timestamp=pd.Timestamp.now(tz=timezone.utc).isoformat(),
    )
```

### Why `_load_verified_walk_forward_manifest()` Returns `None`
1. **Manifest File Absence/Mismatch:** The method looks for a serialized manifest JSON matching the hash of active strategies and configuration.
2. **Strategy Name Incompatibility:** The repository's historical manifest (`v26_canonical_strategy_manifest.json`) defines candidate strategies under legacy names:
   - `TS_MOM_TREND`
   - `VOL_COMPRESSION_BREAKOUT`
3. **Current Strategy Registry Divergence:** The active production strategy registry (`VersionedStrategyRegistry` in `engine/strategy_registry.py`) defines strategies as:
   - `TSMOM_DONCHIAN_24H_168H`
   - `ATR_VOLATILITY_BREAKOUT_12H`
4. Because the registry names and parameter schemas do not align with the historical V26 manifest, the loader rejects the legacy file as invalid/stale.

---

## 2. Legacy Evaluation Fallback & The "Mock Heuristic" Risk

Prior to the gate's introduction, lines 967–1061 of `regime_strategy_tournament.py` contained an inline three-arm evaluation fallback (`_evaluate_single_candidate_3_arms`). 

### The Flawed Fallback Implementation:
```python
# Historical code snippet from lines 975-995:
# Mock evaluation fallback when aligned AI forecast series is missing:
ai_filter_passed = (i % 3 != 0)  # Heuristic mock filter!
n_alone = 48
tp_alone = 28
n_ai = 32
tp_ai = 22
```
If the abstention gate were simply removed or bypassed, the tournament engine would fall back onto this hardcoded modulo arithmetic and fixed counts, generating fictitious "AI Advantage" metrics and recommending live directional trade setups based on pseudorandom bar index arithmetic!

**Conclusion:** The developer who implemented lines 1162–1204 acted correctly under scientific governance. The gate prevents catastrophic lookahead and unvalidated execution.

---

## 3. The 3-Arm Evaluation Protocol Requirements

To legally unlock the `Analyse` button without fabricating synthetic heuristics, the tournament engine requires a genuine 3-arm evaluation:

$$\text{Arm 1: Strategy Alone} \quad \text{vs.} \quad \text{Arm 2: Strategy + AI Gate} \quad \text{vs.} \quad \text{Arm 3: Matched Baseline}$$

### Protocol Requirements:
1. **Point-in-Time Alignment:** Features for bar $t$ must only use information available at closed candle $t-1$.
2. **Walk-Forward Splitting:** Purged k-fold cross-validation or expanding anchor walk-forward splits spanning historical regimes (2021–2026).
3. **Hypothesis Gate:** A candidate strategy + AI filter must demonstrate a statistically significant reduction in QLIKE / turnover friction or increase in Sharpe via Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) finite sample correction ($p < 0.05$).
4. **Execution Friction Deduction:** Performance metrics must incorporate the execution cost model (exchange fees + slippage) before declaring an arm superior.

---

## 4. Remediation Plan for V32.72

To replace the abstention gate with an authentic, verified evaluation:

1. **Manifest Alignment Script:** Construct an automated offline script (`scripts/generate_walk_forward_manifest.py`) that executes historical backtests across the active candidates (`TSMOM_DONCHIAN_24H_168H`, `ATR_VOLATILITY_BREAKOUT_12H`) using the canonical backfilled dataset (`data/raw/ohlcv_backfilled.parquet`).
2. **Offline Serialized Manifest:** Save the output as `engine/manifests/v32_canonical_walk_forward_manifest.json` with cryptographically verified checksums.
3. **Loader Binding:** Update `_load_verified_walk_forward_manifest()` to parse the new manifest schema, confirming that all candidate strategy names match `VersionedStrategyRegistry`.
4. **Graceful UI Feedback:** When live market conditions diverge from historical regime bounds or when required inputs are missing, display an informative diagnostic card rather than a generic opaque `ABSTAIN`.

---

## 5. Architectural Verdict

| Item | Finding | Action |
| :--- | :--- | :--- |
| **Abstention Gate** | Intentional epistemic safeguard | **RETAIN** (Do not bypass) |
| **Legacy Mock Logic** | Dangerous heuristic (`i % 3 != 0`) | **DEPRECATE & REMOVE** |
| **Strategy Manifest** | Stale / Name mismatch | **RE-GENERATE IN V32.72** |
| **Current Operational Status** | Research Only / Abstaining | **SAFE & GOVERNED** |

