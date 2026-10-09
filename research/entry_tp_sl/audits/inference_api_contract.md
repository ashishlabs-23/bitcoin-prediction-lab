# Research Inference and Scenario API Audit

**Scope:** Read-only API/model/contract inspection. No model artifact was loaded, no training or research run was performed, and no holdout values were inspected.

## Current state

- `run_authorization.json` is `BLOCKED_AUDIT_FAILURE`, `authorized: false`, with B1, B2, and D5 unresolved. Its reason prohibits fitting models or regenerating performance tables.
- `/prediction/latest` and `/api/research/entry-tp-sl` currently fail closed with unavailable/blocked responses and no signal payload.
- Production startup does not load a verified model artifact: `live_engine` calls `make_dataset(horizon_bars=24)` and fits `AdaptiveRegimeEnsemble`. Its feature preparation can zero-fill missing columns. This is not a validated, provenance-bound inference contract.
- The standard `/api/research/entry-tp-sl` route reads the authorization state but does not verify manifest hashes. The local-safe status path does compare raw, embedded, and registered manifest hashes and reports `PROVENANCE_FAILURE` on mismatch.
- The arena what-if route is a simulation, not model inference. It now requires explicit spot/TP/SL, but also depends on observatory volatility and conformal bounds. A stand-alone calculator should take all numerical assumptions explicitly and must not imply that the resulting scenario is a recommendation.
- Frozen barrier pairs and costs are defined by `research/entry_tp_sl/barrier_contract.py`; the freeze itself does not authorize model fitting or experiment execution.

## Separate capability contracts

### Verified research inference

Return an inference only after verifying an approved model artifact identity/hash, model and feature-schema versions, exact feature names/order/types/units and preprocessing, and fresh input provenance. Do not zero-fill missing features. Bind outputs to artifact and input snapshot, and preserve the setup-owned side (LONG/SHORT) while the meta-model only accepts or abstains. Otherwise return the accurate unavailable/provenance/model failure state and no numeric signal.

The existing authorization gate continues to block training and report regeneration. No validated current inference artifact was established in this audit; current runtime inference state remains `MODEL_UNAVAILABLE`/`DATA_UNAVAILABLE` as applicable.

### Hypothetical scenario calculation

Keep a pure deterministic calculator separate from the inference route and research-run authorization. Require explicit finite inputs and units, including reference price, volatility assumption, side, registered barrier pair, and horizon. Validate input relationships and return the calculation timestamp, source/provenance, formula version and disclaimer:

`SCENARIO_CALCULATION — NOT A MODEL PREDICTION`

Missing or invalid inputs must not yield numeric fallbacks. Neither capability may create or submit orders.

## Evidence inspected

- `api/routes_prediction.py`
- `api/routes_arena.py`
- `api/local_safe_server.py`
- `api/server.py`
- `engine/inference_service.py`
- `models/router.py`
- `models/tft_model.py`
- `research/entry_tp_sl/run_authorization.json`
- `research/entry_tp_sl/AMENDMENT_REQUIRED.md`
- `research/entry_tp_sl/barrier_contract.py`
- `research/entry_tp_sl/contract_freeze_manifest.json`
