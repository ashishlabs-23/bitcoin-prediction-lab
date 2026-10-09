# Frontend Product Audit

**Scope:** Read-only inspection of the existing static frontend. No files were changed during audit.

## Findings

- Local-safe mode in `web/app.js` short-circuits the legacy dashboard and clearly separates application health, market availability, inference availability, research authorization, and historical/manifest status. It requests only `/health` and `/api/local/status`; the live rendering was verified previously.
- The normal application still has hard-coded fallback values in the what-if simulator, including a fallback spot and derived barrier/probability figures. Other components also substitute prices when market data is unavailable. These can make missing inputs appear to be real values.
- The what-if UI calls `/api/arena/what-if-scenario` and treats `SUCCESS` as normal output; it needs a distinct calculator label and truthful missing-input/result states. Scenario availability should not be controlled by research-run authorization, because a deterministic user-defined calculation is not model fitting or an experiment.
- Existing historical analog UI describes results as retrospective rather than a forecast, but should maintain explicit unverified provenance status.
- Existing quick-ticket UI is paper/external-position monitoring and contains no real order submission control. Keep order execution explicitly disabled in the restored research terminal.
- The existing dark palette and glass-card styles in `web/styles.css` can support the richer layout without introducing a framework.

## Product recommendation

Keep five visually distinct panels:

1. **Live market:** price, venue/source, source timestamp/freshness; unavailable rather than fallback values.
2. **Verified model inference:** show only after real inference and provenance checks; display exact failure/unavailable state otherwise.
3. **Hypothetical scenario calculator:** clearly identify user inputs and deterministic outputs, with `SCENARIO_CALCULATION — NOT A MODEL PREDICTION`.
4. **Historical evidence:** separate retrospective metrics and mark `UNVERIFIED` until evidence integrity is resolved.
5. **Execution state:** informational disabled state only; no buy/sell/order/broker actions.

The blocked experiment gate must remain visible but must not suppress a valid explicitly labelled calculator. Do not add model metrics or predicted values as UI constants.

## Evidence inspected

- `web/index.html`
- `web/app.js`
- `web/styles.css`
