# Independent Safety Review

**Reviewer:** Independent read-only review of the runtime, market-data, inference/API, and frontend audits

**Scope:** Source and contract review only. The reviewer did not run the app, contact market APIs, load models, run experiments, or inspect historical holdout values.

## Blocking findings

1. **The research authorization file is not an enforced application-wide training gate.** `run_authorization.json` remains `BLOCKED_AUDIT_FAILURE` / `authorized: false`, but production `api.server` starts `live_engine`, and `engine.inference_service` fits `AdaptiveRegimeEnsemble` from `make_dataset()` at startup. Do not launch production. The blocked state must prohibit training and report regeneration until B1/B2 are resolved, D5 is independently verified, and a new authorization is granted.
2. **The current manifest status is intentionally conservative, but the check is not a complete integrity verifier.** `local_safe_server.py` compares raw manifest bytes with embedded/registered hashes. The mismatch means those compared values differ; it does not, by itself, prove tampering, because the documented generation-time hash may be over canonicalized content excluding the self-hash field. The status path also does not recompute every artifact hash or dataset hash. Report the checked fields precisely; do not claim full contract integrity.
3. **The legacy dashboard has additional unverified/fallback values.** Beyond the what-if simulator, `web/app.js` contains fallback prices, volatility/funding values, default directions/probabilities, and fixed performance/evidence summaries. Keep the legacy dashboard excluded from the restored research terminal until those values are provenance-backed or explicitly marked as non-data demo content.
4. **The existing arena what-if path is not a standalone verified calculator.** It requires the observatory's volatility and conformal bounds in addition to user spot/TP/SL and returns probability-like and empirical-reference outputs. Do not treat those results as verified inference. A calculator must use explicit inputs and no hidden empirical dependency.

## Other safety requirements

- Continue using only the isolated `api.local_safe_server:app` on `127.0.0.1`. Do not register production routers.
- Keep paper-trade mutation endpoints out of the safe allowlist; production includes paper-trade and arena mutation paths even though no real broker-order path was found in the reviewed surfaces.
- Treat a status GET returning HTTP 200 with an explicit blocked/unavailable body as a successful status lookup. Use 422 for invalid calculator inputs and a 5xx response for actual internal/upstream failures; do not return an `ERROR` body with HTTP 200 for unexpected calculator exceptions.
- Make local-safe page injection fail closed if the safe-mode flag or local script is not inserted. Consider external fonts/styles explicitly if offline/network isolation is claimed.
- The generic exchange chain is not compatible with the frozen Bitstamp BTC/USD instrument. No source switch, cache substitution, perpetual product, or venue pooling may masquerade as research-compatible live data.
- Keep inference unavailable until artifact identity/hash, schema/preprocessing, input provenance and fresh data are verified. Never zero-fill missing model features.

## Reconciled go/no-go

**GO:** static/local-safe UI, truthful read-only status endpoints, and an isolated deterministic user-defined scenario calculation. The calculator may remain available while experiment authorization is blocked, if it uses explicit validated inputs, makes no network/persistence/training calls, and states:

`SCENARIO_CALCULATION — NOT A MODEL PREDICTION`

**NO-GO:** production startup, model training, performance report regeneration, verified-inference claims, market-feed promotion, and presentation of historical metrics as verified. These remain blocked until authorization and artifact verification requirements pass.

## Implementation acceptance gates

- Preserve the frozen contract files, trial ledger, and blocked authorization state.
- Implement any market adapter as public read-only Bitstamp BTC/USD only, with explicit event timestamps and freshness/provenance validation; fail closed without fallback.
- Keep the calculator pure and deterministic, with explicit units and registered barrier pair parameters. It must not depend on research authorization, observatory state, inferred probabilities, or live order code.
- Keep the current legacy dashboard out of the safe UI; remove numeric fallback presentation from the safe path.
- Add isolated tests for imports/side effects, malformed/stale/unavailable feed responses, deterministic formula, invalid/missing inputs, authorization separation, no order routes, and truthful failure handling.
