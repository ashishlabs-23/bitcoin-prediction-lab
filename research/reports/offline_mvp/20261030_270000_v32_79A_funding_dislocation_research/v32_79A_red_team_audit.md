# V32.79A — Independent Red-Team Audit (Workstream 6)
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Generated:** 2026-10-30  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

This report independently challenges the V32.79A experiment, its data, its results, and the inferences that could be drawn from them. The red-team role requires constructive adversarialism — finding the strongest objections that would invalidate the experiment or its conclusions.

---

## 2. Challenge 1: Is the Threshold Empirically Reasonable?

**Issue:** The ±25% annualized threshold sits at the **96.7th percentile** of positive funding rates. It was specified by the Manager as a fixed threshold, which is appropriate to prevent optimization. However, its empirical rarity has practical consequences.

**Finding:**
- Only 144 raw SHORT observations in 4.67 years = approximately 31 per year.
- After episode grouping: 64 distinct events in 4.67 years = approximately 14 per year.
- **At this frequency, collecting 100 non-overlapping clean prospective blocks would take approximately 7 years** — far beyond any practical research horizon without a lower threshold.

**Red-team verdict:** The ±25% ann threshold is sound conceptually (targeting genuinely extreme crowding) but is incompatible with achieving the 100-episode statistical minimum on the existing 4.67-year dataset. This is a structural impossibility, not a data-quality problem.

**Implication:** Any future investigation of $H_{\text{Funding}}$ must either (a) use a lower threshold (which requires Manager re-authorization as threshold optimization is prohibited at the current level), or (b) accumulate many more years of real data.

---

## 3. Challenge 2: Crowding → Mean-Reversion Causality

**Issue:** The hypothesis assumes that extreme positive funding causes crowded longs to unwind, producing downward price pressure. This causal chain has several weak links.

**Weak link 1: Causality direction.** High positive funding may persist for extended periods in trending markets (momentum carries longs). There is no guaranteed mechanism forcing mean-reversion within 24 hours.

**Weak link 2: Contemporaneity.** The funding rate at settlement $T$ reflects the positioning that was established BEFORE $T$. The settlement itself may have already partially triggered the rebalancing. The 1-hour causal lag applied in this experiment addresses this but does not eliminate the overlap.

**Weak link 3: Signal vs. cost conflation (for perp positions).** When funding rate is high (SHORT signal condition), short positions RECEIVE funding. A strategy that shorts perps at high funding is collecting carry AND betting on mean-reversion. These two mechanisms produce opposite risk profiles and should be separated. The current experiment avoids this by using BTCUSD spot prices as outcomes — but it means the carry benefit of a perp SHORT trade is not captured in the results.

**Red-team verdict:** The causal chain is plausible but not established in this dataset. The 24h results are consistent with both "weak mean-reversion effect" and "no effect with noise."

---

## 4. Challenge 3: Chronological Instability as a Structural Finding

**Issue:** The sign reversal between first-half (−0.39%) and second-half (+0.53%) net EV for the SHORT arm is the most important single finding in this experiment.

**Red-team analysis:** In a stable, repeatable market phenomenon, the first and second halves of the evaluation period should produce results with the same sign and comparable magnitudes. A sign reversal of this magnitude at N=32 per half has two competing explanations:

1. **Noise:** At N=32, the standard error of the mean net EV is approximately σ/√32 ≈ 2.2%/5.66 ≈ 0.39%. A difference of 0.915pp between halves is ~2.3 standard errors — it is NOT trivially noise. However, it is also not extraordinary at these sample sizes.

2. **Structural regime change:** The first half includes 2022 (LUNA/FTX crash — forced liquidation environments where funding spikes did NOT lead to immediate short-side profits because the price sometimes continued crashing). The second half is dominated by the post-ETF institutional regime. Different market structures create different funding dynamics.

**If the instability is structural:** No single fixed threshold can capture a reliable signal across regimes. The strategy would require regime-conditioning — but the Manager has blocked $H_{\text{Macro}}$ and regime labels contain hindsight problems.

**Red-team verdict:** The chronological instability is a genuine warning sign, not just noise. It suggests the funding signal, if it exists at all, is regime-dependent rather than universal. This further undermines the case for a single-threshold, regime-agnostic strategy.

---

## 5. Challenge 4: The SHORT TP Rate vs. Breakeven

**Issue:** The observed SHORT TP rate is 29.7%. The Binance breakeven TP rate for the 3%/1.5% barrier (simplified) is 38.7%.

**Red-team calculation:**

Using the full net-EV formula (NOT the simplified BEP):
$$\text{Net EV} = 0.297 \times 2.76\% + 0.453 \times (-1.74\%) + 0.250 \times (0.11\% - 0.24\%)$$
$$= 0.820\% - 0.788\% - 0.033\% = -0.001\% \approx 0\%$$

The simulation reports +0.068% because the mean EXPIRED P&L was approximately +0.24% gross (not +0.11% as used in the quick calculation above). Either way, the result is economically trivial and statistically indistinguishable from zero.

**The 38.7% BEP reference is a useful heuristic, but the primary endpoint is the full net EV calculation.** At +0.068% per trade with a 95% CI of [−0.415%, +0.563%], the result is consistent with zero.

**Red-team verdict:** Even taking the point estimate at face value, +0.068% per trade is not economically meaningful. Transaction costs, market-impact in real execution, and implementation friction would consume this and more.

---

## 6. Challenge 5: The LONG Arm — Is N=3 Meaningful at All?

**Issue:** The LONG arm's 66.7% TP rate and +1.26% net EV looks impressive. Should it be given any weight?

**Red-team analysis:** With N=3:
- A single outcome change (one SL → TP) would shift the TP rate from 66.7% to 33.3% — a complete sign reversal.
- The 95% bootstrap CI is [−1.74%, +2.76%] — a range of 4.5pp. This is not a measurement, it is a guess.
- Negative funding events (< −25% ann) occurred only 5 times in 4.67 years. Collecting 100 prospective episodes at this rate would require ~92 years.

**Red-team verdict:** N=3 is scientifically meaningless. Any apparent finding from the LONG arm — positive or negative — must be disregarded entirely. The LONG arm has `INSUFFICIENT_EVIDENCE` in the most extreme possible sense.

---

## 7. Challenge 6: Pre-Registration Compliance

**Was the experiment conducted per pre-registration?**

| Pre-registered element | Compliance |
|---|---|
| Threshold: ±25% ann | ✅ Applied exactly |
| Causal lag: +1 hour after settlement | ✅ Applied |
| Episode grouping: 24h cooldown | ✅ Applied |
| Barrier: 3%/1.5% | ✅ Applied |
| Horizon: 24h | ✅ Applied |
| Minimum 100 episodes | ✅ Checked — both arms fail |
| Long and short separately | ✅ Reported separately |
| Unconditional baseline | ✅ Computed |
| DM-HLN | ✅ Applied |
| Bootstrap CI | ✅ 2,000 replications |
| Chronological stability | ✅ First/second half |
| No threshold optimization | ✅ Fixed threshold used |
| No ML training | ✅ None |

**Pre-registration compliance: FULL**

No post-hoc changes were made to the experimental protocol. The stop condition (< 100 episodes) was applied as specified.

---

## 8. Summary Verdicts

| Challenge | Verdict |
|---|---|
| Threshold empirically reasonable? | Conceptually sound; practically incompatible with 100-episode minimum |
| Causal chain established? | Plausible but not demonstrated in this data |
| SHORT result reliable? | NO — N=64 (below minimum), p=0.269, CI straddles zero, sign reversal |
| LONG result reliable? | NO — N=3, statistically meaningless |
| Chronological stability? | FAIL — sign reversal between halves |
| Pre-registration compliance? | FULL — no protocol deviations |
| Appropriate final determination? | `INSUFFICIENT_EVIDENCE` |

---

*No external data fetched. No datasets modified. No models trained.*

