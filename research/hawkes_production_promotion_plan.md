# 📜 Hawkes Microstructure Production Promotion Plan (Governance Draft)

## 1. Overview & Guardrails

* **Challenger Identifier:** `v1.0.0-challenger-hawkes-microstructure`
* **Current Status:** **`VALIDATED_SHADOW_MODEL`** (Non-executing; Ridge remains Production).
* **Target Horizon:** 5-minute probabilistic excursions ($P_{10}, P_{50}, P_{90}$).
* **Strict Rule:** **Zero Automatic Promotion.** Any production transition requires manual governance review and complete statistical gate clearance.

---

## 2. Mandatory Promotion Gates

A future promotion to active production requires satisfying all 7 gates:

1. **Independent Sample Scale:** Minimum **500 non-overlapping 5-minute blocks** ($N_{\text{eff}} \ge 250$).
2. **Error Advantage:** Live 5m MFE MAE $\le 9.50\text{ bps}$ with statistically significant lead over static LOB ($p_{\text{adj}} < 0.01$).
3. **Calibration & Coverage:** Live P90 coverage within $[88.0\%, 95.0\%]$; Winkler sharpness score $\le 100.0$.
4. **Latency Budget:** Total per-event pipeline latency $p_{99} \le 5.0\text{ ms}$; peak burst latency $\le 10.0\text{ ms}$.
5. **Data Quality Integrity:** Stale order book percentage $\le 0.05\%$; zero out-of-order event occurrences.
6. **Regime Robustness:** Verified stability across volatile, sideways, and trend regimes.
7. **Rollback & Safety:** Automatic fallback to Production Ridge upon feed degradation.

---

## 3. Manual Sign-Off & Governance Workflow

* Lead Quantitative Auditor Approval: Required.
* Model Risk Officer Review: Required.
* Replay Audit & SHA-256 Hash Verification: Required.
