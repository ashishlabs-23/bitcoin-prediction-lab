# V32.80A — Multiple-Testing Reconciliation & Candidate Universe

**Milestone:** BTCognitive V32.80A — Audit Closure Addendum  
**Generated:** 2026-10-30T17:32:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report audits the pre-registered hypothesis family and reconciles the two significance thresholds cited across prior milestones:
1. **$K = 159$, $\alpha_{\text{Bonferroni}} \approx 0.000314$** (from V32.79 Phase 0 Statistical Protocol Review).
2. **$K = 2$, $\alpha_{\text{Bonferroni}} = 0.025$** (from V32.79A Pre-Registration).

---

## 2. Deconstruction of the Candidate Configuration Universe

### 2.1 The Full Programme-Wide Universe (V32.79 Phase 0)
In V32.79 Phase 0, the Lead Orchestrator audited the maximum possible candidate parameter space across the four exploratory hypotheses proposed for the macro research programme:

| Hypothesis | Parameter Dimensions | Combinatorial Count |
|---|---|---|
| **$H_{\text{Funding}}$** (Dislocation) | 5 quantiles $\times$ 3 lookbacks $\times$ 3 directions $\times$ 3 horizons | $5 \times 3 \times 3 \times 3 = 135$ |
| **$H_{\text{Macro}}$** (Regime Conditioning) | 4 regimes $\times$ 3 indicator thresholds $\times$ 2 horizons | $4 \times 3 \times 2 = 24$ |
| **$H_{\text{ETF}}$** (Flow Momentum) | Blocked in Phase 0 | $0$ |
| **$H_{\text{Macro\_Abstain}}$** (FOMC/CPI) | Blocked in Phase 0 | $0$ |
| **Total Possible Programme Universe** | | **$K = 159$ configurations** |

Under a strict Family-Wise Error Rate (FWER) control of $\alpha = 0.05$ across all possible explorations:
$$\alpha_{\text{programme}} = \frac{0.05}{159} \approx \mathbf{0.000314}$$

### 2.2 The Pre-Registered Experiment Universe (V32.79A Phase 1A)
When the Manager authorized V32.79 Phase 1A, the scope was restricted by executive fiat:
- All other hypotheses ($H_{\text{ETF}}$, $H_{\text{Macro}}$, $H_{\text{Macro\_Abstain}}$) were **BLOCKED**.
- In $H_{\text{Funding}}$, threshold optimization was **PROHIBITED**; the threshold was fixed at $\pm 25\%$ ann.
- Horizon was **FIXED** at 24 hours.
- Only two arms were authorized and pre-registered: `SHORT` and `LONG`.

Under this strictly pre-registered single experiment:
$$K_{\text{executed}} = 2 \implies \alpha_{\text{experiment}} = \frac{0.05}{2} = \mathbf{0.025}$$

---

## 3. Methodological Reconciliation & Governance Decision

| Level | Hypothesis Family Scope | $K$ | Critical $\alpha$ | Paired Short $p=0.0039$ | Verdict |
|---|---|---|---|---|---|
| **Experiment-Level** | Pre-registered V32.79A Arms (Short, Long) | 2 | **$0.025000$** | $p < 0.025$ | **Passes local threshold** |
| **Programme-Wide** | Total V32.79 Exploratory Search Space | 159 | **$0.000314$** | $p > 0.000314$ | **Fails programme threshold** |

### Manager Directive & Governance Ruling:
1. **No Post-Hoc Scope Definition:** The experiment executed exactly 2 configurations. Attempting to retroactively penalize V32.79A for 157 unexecuted experiments would be a post-hoc redefinition of the local test.
2. **Programme-Wide Governance Rule:** Conversely, accepting a local $p=0.025$ to justify model deployment or strategy promotion after a broader search space was conceived would violate rigorous financial econometrics (Harvey, Liu, & Zhu 2016).
3. **The Final Ruling:** Because the underlying sample failed the sample size gate ($N = 64 < 100$) and demonstrated temporal sign reversal, the strategy is rejected on **sample and economic grounds**. 
   - At the programme level ($K=159$), $p=0.0039$ fails.
   - At the local level ($K=2$), $p=0.0039$ is non-robust across bandwidths ($p=0.1685$ at $b=0$).
   
Under both standards, **NO STATISTICALLY DEFENDABLE EDGE EXISTS**.

