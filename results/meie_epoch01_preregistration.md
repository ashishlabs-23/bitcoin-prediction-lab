# Pre-Registration: MEIE-EPOCH-01 — Live Paper-Trading Evaluation & 7-Level Research Ladder
**Document Status**: LOCKED & IMMUTABLE PRIOR TO EPOCH 01 EVALUATION  
**Pre-Registration ID**: MEIE-EPOCH-01-v1.0  
**Locked At**: 2026-08-26T10:40:00Z  
**Protocol Philosophy**: Controlled Autonomy + Isolated Experimentation + Continuous Evidence Collection  
**Depends On**: `results/meie_event01_preregistration.md`, `results/meie_direction01_preregistration.md`, `results/meie_execution01_preregistration.md`

---

## 1. Epistemic Baseline & Core Invariant

> [!IMPORTANT]
> **Architecture is Promising $\neq$ Strategy is Empirically Proven.**  
> At initialization, zero strategies hold a validated edge or "champion" status.  
> All archetypes start strictly categorized by their epistemic candidate status:
> - `MEIE-IGNITION-v1.0`: **CANDIDATE**
> - `MEIE-ABSORPTION-v1.0`: **CANDIDATE**
> - `MEIE-VACUUM-v1.0`: **CANDIDATE**
> - `MEIE-TOXICITY-v1.0`: **DEFENSIVE_FILTER** (Risk / Liquidity Blocker)
> - `MEIE-COMBINED-v1.0`: **PORTFOLIO_CHALLENGER** (Correlation-Aware Allocator)

The frozen scientific core (`HAR-RS-DOW + C2 + Observatory` $N=720$ prospective audit) remains completely untouched and isolated in `results/arena_memory.db`. All MEIE prospective execution lives in `results/meie_memory.db`.

---

## 2. The 7-Level Microstructure Research Ladder

Every strategy archetype must ascend the 7-level research ladder sequentially. No promotion occurs without clearing each gate on out-of-sample prospective paper data:

```
Level 1: Event Validity        ── Does the event alter future return/vol distribution? P(Y|E) != P(Y)
   ↓
Level 2: Conditional Direction ── Does order flow (OFI) + state predict direction? P(UP|E,S) != P(DOWN|E,S)
   ↓
Level 3: Path Prediction       ── Quantile bounds on MFE, MAE, T_TP, T_SL (RangeForecastService)
   ↓
Level 4: Execution Realism     ── Does edge survive full friction (10 bps fee + VPIN slippage + latency)?
   ↓
Level 5: Economic Yield        ── EV_net > 0 bps after all costs (Primary execution gate)
   ↓
Level 6: Prospective Stability ── Survives N=100 trade epoch without drawdown breach (MDD < 5%)
   ↓
Level 7: Champion Promotion    ── Challenger defeats incumbent on (EV_net, Sharpe, MDD, Profit Factor) triad
```

---

## 3. Opportunity Quality ($OQ$) Metric

Trade execution is conditioned not on signal presence alone, but on Opportunity Quality ($OQ$):

$$OQ = \frac{\max(0, EV_{\text{net}})}{\text{Expected MAE} + \epsilon} - \sum \text{Penalties}$$

### 3.1 Penalties
- **Data Quality Penalty**: $-0.15$ if feature feed is `DEGRADED`.
- **Spread / Liquidity Penalty**: $-0.10$ if $|z_{\text{spread}}| > 1.0$.
- **Directional Ambiguity Penalty**: $-0.25$ if Hawkes intensity and OFI sign disagree.

### 3.2 Gate Tiers (LOCKED)
| $OQ$ Range | Action Tier | Description |
|:---|:---|:---|
| **$0.00 \le OQ < 0.25$** | **IGNORE** | Edge insufficient to justify friction $\rightarrow$ Mandatory **ABSTAIN** |
| **$0.25 \le OQ < 0.50$** | **WATCH** | Marginal edge; monitored in shadow telemetry |
| **$0.50 \le OQ < 1.00$** | **PAPER_CANDIDATE** | Validated risk-reward $\rightarrow$ eligible for paper execution |
| **$OQ \ge 1.00$** | **HIGH_QUALITY_CANDIDATE** | High asymmetric payout vs. expected adverse excursion |

---

## 4. C2 Risk Conditioning & Macro Scaling

The frozen C2 / Observatory system serves as the master **risk conditioner** for the Arena:

| C2 / Observatory Environment | Calibration State | C2 Risk Multiplier | Arena Action |
|:---|:---|:---|:---|
| **CALIBRATED / COMPRESSION** | Normal confidence | **$1.0$** | Standard $0.50\%$ daily NAV risk budget |
| **DEGRADED / ELEVATED VOL** | Moderate uncertainty | **$0.5$** | $50\%$ risk budget reduction; half position sizing |
| **CRISIS / HIGH UNCERTAINTY** | Extreme risk | **$0.0$** | Mandatory **ABSTAIN** (Zero new paper positions) |

---

## 5. Turn-of-15m Candle Boundary Anomaly Hypothesis

Replicating the published 2023 15-minute boundary anomaly in modern microstructure:

$$H_1: P(\text{Excursion} > k\sigma \mid t \in \{00, 15, 30, 45\}\text{m},\; \text{IGNITION}) > P(\text{Excursion} > k\sigma \mid t \notin \{00, 15, 30, 45\}\text{m},\; \text{IGNITION})$$

Conditioned on:
1. Volatility regime ($\text{COMPRESSION} \rightarrow \text{EXPANSION}$)
2. Liquidity state ($z_{\text{depth}}, z_{\text{spread}}$)
3. Hawkes self-excitation intensity ($\lambda_{\text{buy}} + \lambda_{\text{sell}}$)

---

## 6. Epoch 01 Governance & Promotion Rules

- **Epoch Length**: Exactly $N = 100$ resolved closed paper trades per strategy account.
- **Starting Virtual NAV**: $\$10,000.00$ USD per isolated account.
- **Daily Risk Budget**: $0.50\%$ of account NAV per UTC day.
- **Max Single-Trade Loss**: $0.20\%$ of account NAV.
- **Daily Drawdown Halt**: $0.75\%$ loss in 24h halts account until UTC midnight.
- **Promotion Thresholds**:
  - Realized $\overline{EV}_{\text{net}} > 0\text{ bps}$
  - Realized $\text{MDD} < 5.0\%$
  - Realized $\text{Profit Factor} > 1.0$
  - $\text{Score} = \frac{EV}{\sigma} \times \text{Reliability} - \lambda \cdot \text{CVaR}_{95}$ must exceed current incumbent.

---

## 7. Epoch 01 Audit Methodology & Immutability Protocol

### 7.1 Selection Quality Decomposition (Filter Quality vs. Opportunity Preservation)
To evaluate whether the risk gate and filters improve capital deployment without causing execution paralysis:

- **5A: Filter Quality (Downside Elimination)**:
  $$\Delta EV_{\text{filter}} = EV_{\text{executed}} - EV_{\text{counterfactual all-trades}}$$
  *Measures how effectively the gate removed loss-making candidate trades.*

- **5B: Opportunity Preservation (Inertia & Type II Error Prevention)**:
  $$P(\text{profitable} \mid \text{abstained}), \quad EV_{\text{abstained counterfactual}}$$
  *Measures whether the gate accidentally blocked high-alpha opportunities.*

- **Opportunity Capture Rate ($OCR$)**:
  $$OCR = \frac{\text{Profitable opportunities actually executed}}{\text{Total profitable candidate opportunities available}} \times 100\%$$
  *Point-in-Time Invariant: Candidate eligibility is determined strictly by information available at $t_0$. A candidate is counted in the denominator if and only if it met all $t_0$ eligibility rules and its point-in-time contract resolves with positive net EV at $t_{\text{exit}}$. Zero retrospective or lookahead selection is permitted.*

### 7.2 Empirical Path & Directional Verification Standards
- **Path Impact**: Beyond mean comparison $P(Y \mid E) \neq P(Y)$, the audit evaluates $\Delta P$ and the full empirical conditional distribution of:
  $$\{ \text{Forward Return}, \; |\text{Return}|, \; \text{Realized Volatility}, \; \text{MFE}, \; \text{MAE} \}$$
- **Directional Significance**: Requires $\Delta_{\text{direction}} = P(\text{UP} \mid E, S) - P(\text{DOWN} \mid E, S)$ to survive formal confidence bounds rather than nominal superiority.

### 7.3 Failure Mode Cross-Tabulation
Every unprofitable resolved trade ($N_{\text{loss}}$) is categorized into the 8-class taxonomy and conditioned on macro state:
$$P(\text{Failure Class } k \mid \text{Market Regime}), \quad P(\text{Failure Class } k \mid \text{C2 Risk State})$$

### 7.4 Dual Allocation Benchmarks for `MEIE-COMBINED`
`MEIE-COMBINED` must demonstrate true portfolio marginal utility against two benchmarks:
1. **Dominance over Single Best Archetype**:
   $$\Delta EV_{\text{best}} = EV_{\text{Combined}} - EV_{\text{best single archetype}}$$
2. **Dominance over Equal-Weight ($1/N$) Static Allocation**:
   $$\Delta EV_{1/N} = EV_{\text{Combined}} - EV_{\text{equal-weight portfolio}}$$

### 7.5 Sample Size Invariant ($N_{\text{resolved}} = 100$)
- The epoch boundary is reached strictly when $N_{\text{resolved}} = 100$ closed trades have completed their full lifecycle (TP, SL, Timeout, or Invalidation) per candidate archetype.
- Raw signals and abstentions are recorded continuously as supplementary decision evidence.

### 7.6 Mid-Epoch Parameter Immutability
- **Strict Prohibition**: Strategy thresholds, TP/SL geometry, holding horizons, risk budget caps, allocator weights, and event definitions may **NOT** be tuned or mutated mid-epoch based on partial outcomes.
- Scientific behavior remains fixed; modifications must strictly wait for the formal Epoch 01 boundary review.

### 7.7 The 10-Point Forensic Report Questions
At the $N_{\text{resolved}} = 100$ boundary, the formal forensic report will answer:
1. Did the event occur often enough in live market conditions?
2. Did the event statistically alter the future path distribution ($\Delta P$, MFE, MAE distributions)?
3. Did conditional direction add significant value ($\Delta_{\text{direction}} = P(\text{UP}) - P(\text{DOWN})$)?
4. Did the TP/SL asymmetric geometry survive fees, slippage, and impact?
5. Did the execution gate improve capital selection (5A: Filter Quality) while preserving alpha (5B: Opportunity Preservation & $OCR$)?
6. Which market regimes caused failures (Cross-tabulated $P(\text{Failure} \mid \text{Regime})$)?
7. Did the strategy beat both the SKIP ($0.00$) baseline and OPPOSITE-action counterfactuals?
8. Did the edge survive across independent time and regime slices?
9. Did the Combined allocator outperform both the best single archetype and an equal-weight $1/N$ baseline?
10. Which rung of the 7-level research ladder blocked each candidate from champion promotion?
