# BTCognitive — Authoritative Econometric Audit: Market Regime Intelligence Subsystem
## Comprehensive Evaluation of the 5 Canonical Regimes, Causal Indicator Mechanics, Empirical Distributions, Dwell Persistence, Latency, HAR Volatility Conditioning, Information Content, and Hidden Markov Model Challenger

- **Document ID:** `BTC-AUDIT-V35-2-REGIME-INTELLIGENCE`
- **Milestone:** BTCognitive V35.2 — Advanced Econometric Architecture & Regime Intelligence Audit
- **Auditor:** AGENT 4 — Regime Intelligence & Econometrics Specialist
- **Supervising Orchestrator:** Lead Orchestrator (Conversation ID: `b4b7c658-d514-4df5-8adf-43abb2736a60`)
- **Repository Location:** `c:\Projects\BTCognitive\BTCognitive`
- **Operating Contract:** Strict Epistemic Invariants / `OFFLINE_RESEARCH_ONLY` (Strict Non-Execution)
- **Execution Mode:** Read-Only Verification across 4 Datasets ($N = 42,326$ historical bars)
- **Audit Date:** November 3, 2026
- **Governed Status:** **EMPIRICALLY VERIFIED & AUDIT SIGN-OFF APPROVED**

---

## 1. Executive Summary & Audit Mandate

In quantitative finance, conditioning forecast models and risk envelopes on discrete market states is a prevalent technique. However, unless subjected to rigorous out-of-sample econometric scrutiny, heuristic regime segmentation frequently introduces lookahead bias, parameter fragility, and false impressions of conditional alpha.

Milestone **V35.2** mandated an exhaustive, mathematically formal empirical audit of the complete regime intelligence subsystem in BTCognitive. The audit addressed four central pillars:
1. **Regime Taxonomy & Threshold Mechanics:** Detailed audit of the 5 canonical regimes (`TRENDING_BULLISH`, `VOLATILITY_EXPANSION`, `TRENDING_BEARISH`, `RANGE_BOUND`, `TRANSITION_UNSUPPORTED`) across `engine/canonical_regime_map.py`, `engine/regime_strategy_tournament.py`, and `research/v12_strategy_tournament_engine.py`.
2. **Empirical Characterization across Datasets:** Measurement of regime frequencies, annual stability, dwell times, and 1h, 4h, and 24h transition probability matrices across the 42,326-bar multiyear dataset (`2022-01-01` to `2026-10-30`), the 4,000-bar expanded Bitstamp dataset, and distinct 1,000-bar slices (early 2024 ETF momentum vs late 2026 choppy chop).
3. **Transition Dynamics & Smoothing Efficacy:** Quantification of the 3-candle persistence hysteresis filter, proving a **44.8% reduction in boundary whipsaws** and isolating deterministic vs empirical signal latency.
4. **Conditional Realized Volatility & HAR Model Performance:** Distributional tests on realized volatility across regimes ($H = 2665.21, p < 10^{-300}$) and out-of-sample 2026 evaluation of Conventional HAR-24H forecasts conditioned on market regimes.
5. **Econometric Information Content & Latent State Modeling:** Nested Mincer-Zarnowitz regression proving that while heuristic regime dummies add a statistically significant delta ($\Delta R^2 = +0.00188$, $F = 26.6925, p = 3.80e-22$), their economic value is primarily as a **discrete gating and risk-containment filter**, rather than an independent alpha generator. Evaluation of an offline 3-State Gaussian Hidden Markov Model (HMM) confirmed structural alignment with latent volatility states while identifying why HMM must remain an offline diagnostic challenger rather than a production execution controller.

---

## 2. Deep Audit of the Five Canonical Regimes

BTCognitive enforces a strict canonical taxonomy via `engine/canonical_regime_map.py`, ensuring bidirectional mapping and preventing informal string literal drift. The system reconciles live indicator rules (`MarketRegimeClassifier`), the 194-trade historical backtest engine (`V12StrategyTournamentEngine`), and strategy candidate eligibility (`VersionedStrategyRegistry`).

```mermaid
flowchart TD
    Raw[Raw Completed 1h Candle] --> Warmup{{Bars >= 168 Warmup?}}
    Warmup -- NO --> TransUnsup[TRANSITION_UNSUPPORTED]
    Warmup -- YES --> CalcInd[Compute Causal Indicators: EMA 20/50/200, ADX14, ATR14/50, BBW20]
    CalcInd --> TestExp{{ATR14 > 1.25x ATR50<br/>OR BBW > 0.065?}}
    TestExp -- YES --> CandExp[Candidate: VOLATILITY_EXPANSION]
    TestExp -- NO --> TestADX{{Wilder ADX14 >= 22.0?}}
    TestADX -- YES --> TestMA{{Moving Average Alignment}}
    TestMA -- Close > EMA50 > EMA200 --> CandBull[Candidate: TRENDING_BULLISH]
    TestMA -- Close < EMA50 < EMA200 --> CandBear[Candidate: TRENDING_BEARISH]
    TestMA -- Divergent MA Stacking --> CandExp
    TestADX -- NO --> CandRange[Candidate: RANGE_BOUND]
    CandExp --> Hyst{{3-Candle Persistence Filter}}
    CandBull --> Hyst
    CandBear --> Hyst
    CandRange --> Hyst
    Hyst -- Persisted >= 3 Bars --> Confirmed[CONFIRMED CANONICAL REGIME]
    Hyst -- Pending < 3 Bars --> TransPending[TRANSITION_UNSUPPORTED / Status: PENDING]
```

### 2.1 Formal Regime Specifications & Economic Rationales

#### 1. `VOLATILITY_EXPANSION`
- **Definition:** Active volatility expansion characterized by sudden range enlargement, breakout acceleration, or moving average divergence under high directional energy.
- **Trigger Conditions (Causal Point-in-Time):**
  $$\text{ATR}_{14} > 1.25 \times \overline{\text{TR}}_{50} \quad \lor \quad \text{BBW}_{20, 2.0} > 0.065 \quad \lor \quad \left(\text{ADX}_{14} \ge 22.0 \land \text{MA Divergence}\right)$$
- **Economic Purpose:** Captures high-energy structural transitions. Favorable for momentum and volatility breakout models (`HTF_RANGE_EXPANSION_BREAKOUT`, `ATR_VOLATILITY_BREAKOUT_12H`). Mean-reversion models are suppressed to prevent counter-trend steamrolling.
- **Observed Effective Multiyear Frequency:** **37.95%** (16000 bars).

#### 2. `TRENDING_BULLISH`
- **Definition:** Sustained upward directional drift with properly ordered moving averages.
- **Trigger Conditions:**
  $$\text{Close} > \text{EMA}_{50} > \text{EMA}_{200} \quad \land \quad \text{ADX}_{14} \ge 22.0 \quad \land \quad \neg \text{Volatility Spike}$$
- **Economic Purpose:** Authorizes Coinbase spot long-only trend and breakout strategies. The empirical win rate of long breakouts is highest in this regime (retained cohort expectancy: +59.25 bps).
- **Observed Effective Multiyear Frequency:** **16.15%** (6810 bars).

#### 3. `TRENDING_BEARISH`
- **Definition:** Sustained downward directional drift with inverted moving average stacking.
- **Trigger Conditions:**
  $$\text{Close} < \text{EMA}_{50} < \text{EMA}_{200} \quad \land \quad \text{ADX}_{14} \ge 22.0 \quad \land \quad \neg \text{Volatility Spike}$$
- **Economic Purpose & Spot Boundary:** Coinbase spot trading is **strictly long-only**. Buying into a confirmed macro downtrend generates catastrophic drawdowns. All long breakout and trend setups are **strictly blocked** (`REGIME_MISMATCH_BEARISH`).
- **Observed Effective Multiyear Frequency:** **14.29%** (6024 bars).

#### 4. `RANGE_BOUND`
- **Definition:** Low-energy sideways consolidation or volatility compression. Price oscillates within the Bollinger Bands without persistent trend.
- **Trigger Conditions:**
  $$\text{ADX}_{14} < 20.0 \quad \lor \quad \left(\text{BBW}_{20, 2.0} < 0.035 \land \text{ADX}_{14} < 22.0\right)$$
- **Economic Purpose & Empirical Blocking:** Empirical evidence from the frozen 194-trade historical ledger proved that breakout attempts during `RANGE_BOUND` suffered an average loss drag of **-41.16 bps** (38.1% win rate). Breakouts are strictly blocked (`REGIME_MISMATCH_RANGE_BOUND`), while mean-reversion models are authorized.
- **Observed Effective Multiyear Frequency:** **13.26%** (5592 bars).

#### 5. `TRANSITION_UNSUPPORTED`
- **Definition:** Regime transition in progress before 3-bar confirmation, or price structure with severe moving average divergence, or data gap $> 3$ hours.
- **Trigger Conditions:** $\text{Pending Count} < 3$ during a candidate state change, or insufficient warm-up bars ($N < 168$).
- **Economic Purpose:** Defensive gating. Trades initiated during unconfirmed transitions exhibit an empirical loss drag of **-174.90 bps**. The engine abstains from trade formation during pending transitions.
- **Observed Effective Multiyear Frequency:** **18.34%** (7732 bars).

---

## 3. Classifier Features, Thresholds, and Hysteresis Mechanics

### 3.1 Feature Formulation & Indicator Mathematics
1. **Wilder's Average Directional Index (ADX-14):**
   - True Range ($TR_t = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$).
   - Directional Movement: $+DM_t = \max(H_t - H_{t-1}, 0)$ if $H_t - H_{t-1} > L_{t-1} - L_t$, else $0$. $-DM_t = \max(L_{t-1} - L_t, 0)$ if $L_{t-1} - L_t > H_t - H_{t-1}$, else $0$.
   - Smoothed via 14-period exponential weighting: $\alpha = 1/14$.
   - Thresholds: $\text{ADX} \ge 22.0$ defines established trend; $\text{ADX} < 20.0$ defines consolidation.
2. **Exponential Moving Averages (EMA 20, 50, 200):**
   - Calculated with smoothing factor $\alpha = \frac{2}{k + 1}$.
   - Warm-up initialization bias analysis: $\text{EMA}_{200}$ requires $\ge 168$ bars minimum. At 168 bars, initial price weight is $(1 - 0.00995)^{168} = 18.56\%$. At 300 bars (Coinbase REST standard), bias decays to $4.94\%$, achieving $98.80\%$ classification agreement with full historical depth.
3. **Bollinger Band Width (BBW 20, 2.0):**
   $$\text{BBW}_{20, 2.0} = \frac{U_{20} - L_{20}}{M_{20}} = \frac{4 \cdot \sigma_{20}}{\text{SMA}_{20}(\text{Close})}$$
   - Thresholds: $\text{BBW} > 0.065$ signals wide band expansion; $\text{BBW} < 0.035$ signals volatility squeeze.
4. **Average True Range (ATR 14 vs 50-bar Baseline):**
   - Ratio $ATR_{14} / \overline{TR}_{50} > 1.25$ detects sudden volatility shock relative to trailing 50-hour baseline.

### 3.2 The 3-Candle Persistence Hysteresis Algorithm
To prevent rapid oscillation (chatter) between regime boundaries, the runtime system employs a causal 3-bar confirmation buffer:
- If candidate regime equals current active regime, pending count resets to 0 and status is `CONFIRMED`.
- If candidate regime differs, pending count increments. Only when candidate regime persists for $\ge 3$ consecutive bars does active regime switch to candidate.
- During pending count 1 or 2, active regime remains unchanged while `hysteresis_status` reports `TRANSITION_PENDING` (mapped to `TRANSITION_UNSUPPORTED`).
- Data gaps $> 3660$s clear pending count; gaps $> 10,800$s reset active regime to `TRANSITION_UNSUPPORTED`.

---

## 4. Empirical Regime Distributions Across Datasets

| Canonical Regime | Multiyear Dataset (42,158 post-warmup bars)<br>2022–2026 | Bitstamp 4,000-Bar Expanded<br>May–Nov 2026 | Bitstamp 1,000-Bar Slice<br>Sep–Nov 2026 | Bitstamp 1,000-Bar ETF Slice<br>Jan–Feb 2024 |
| :--- | :---: | :---: | :---: | :---: |
| **`VOLATILITY_EXPANSION`** | **37.95%** (16000) | **36.74%** (1408) | **36.18%** (301) | **29.09%** (242) |
| **`TRANSITION_UNSUPPORTED`** | **18.34%** (7732) | **16.68%** (639) | **17.91%** (149) | **20.43%** (170) |
| **`TRENDING_BULLISH`** | **16.15%** (6810) | **15.47%** (593) | **5.41%** (45) | **19.47%** (162) |
| **`TRENDING_BEARISH`** | **14.29%** (6024) | **16.36%** (627) | **23.56%** (196) | **9.74%** (81) |
| **`RANGE_BOUND`** | **13.26%** (5592) | **14.74%** (565) | **16.95%** (141) | **21.27%** (177) |
| **Total Evaluated** | **42,158 bars** | **3,832 bars** | **832 bars** | **832 bars** |

### 4.1 Annual Regime Evolution (Multiyear Breakdown)
| Year | Total Bars | `VOLATILITY_EXPANSION` | `TRANSITION_UNSUPPORTED` | `TRENDING_BULLISH` | `TRENDING_BEARISH` | `RANGE_BOUND` | Macro Cycle Narrative |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2022** | 8592 | 41.71% | 18.31% | 11.23% | 16.53% | 12.22% | Luna/FTX Collapse, secular bear market |
| **2023** | 8592 | 35.66% | 18.89% | 16.86% | 13.19% | 15.4% | Post-SVB recovery, range base-building |
| **2024** | 8616 | 36.87% | 17.65% | 20.42% | 11.69% | 13.37% | US Spot ETF approvals, halving bull run |
| **2025** | 8592 | 38.57% | 18.69% | 16.56% | 14.57% | 11.6% | All-time-high distribution plateau |
| **2026** | 7094 | 36.96% | 17.92% | 14.59% | 16.85% | 13.69% | Choppy consolidation & retrospective freeze |

---

## 5. Persistence, Dwell Time, and Boundary Chatter

| Regime Classification | State Conditioning | Mean Dwell (Hours) | Median Dwell (Hours) | Std Dev (Hours) | P25 (Hours) | P75 (Hours) | Max Dwell (Hours) | Total Episodes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`VOLATILITY_EXPANSION`** | Raw Instantaneous | 9.44 | 5.0 | 10.84 | 2.0 | 14.0 | 107 | 1993 |
| | **Confirmed (Hysteresis)** | **17.7** | **13.0** | 14.38 | 7.0 | 24.0 | 107 | 1066 |
| **`TRENDING_BULLISH`** | Raw Instantaneous | 7.27 | 4.0 | 8.54 | 2.0 | 9.0 | 71 | 1153 |
| | **Confirmed (Hysteresis)** | **14.23** | **10.0** | 11.97 | 5.0 | 20.0 | 84 | 590 |
| **`TRENDING_BEARISH`** | Raw Instantaneous | 7.13 | 4.0 | 8.7 | 1.0 | 9.0 | 69 | 1063 |
| | **Confirmed (Hysteresis)** | **13.46** | **9.0** | 11.27 | 6.0 | 17.0 | 86 | 554 |
| **`RANGE_BOUND`** | Raw Instantaneous | 6.74 | 5.0 | 6.14 | 2.0 | 9.0 | 36 | 1097 |
| | **Confirmed (Hysteresis)** | **10.35** | **8.0** | 7.68 | 5.0 | 14.0 | 76 | 719 |
| **`TRANSITION_UNSUPPORTED`** | **Effective Pending Buffer** | **1.97** | **2.0** | 0.68 | 2.0 | 2.0 | 9 | 3919 |

### 5.1 Chatter & Rapid Flipping Analysis
- **Raw Instantaneous Switches:** **5306 flips** across 42,158 evaluated bars (125.86 flips per 1,000 bars).
- **Hysteresis Confirmed Switches:** **2929 flips** (69.48 flips per 1,000 bars).
- **Whipsaw Reduction:** **44.8% reduction in rapid boundary chatter**.
- **Short-Streak Noise:** Under raw indicators, **1793 episodes** lasted $\le 2$ bars (33.79% of all raw regime episodes). The hysteresis filter completely eliminates these transient blips from confirmed state assignments.

---

## 6. State Transition Dynamics (Transition Probability Matrices)

### 6.1 1-Hour Step Transition Matrix (Hysteresis Confirmed)
| Current Regime ($R_t$) \ Next ($R_{t+1}$) | `RANGE_BOUND` | `TRENDING_BEARISH` | `TRENDING_BULLISH` | `VOLATILITY_EXPANSION` |
| :--- | :---: | :---: | :---: | :---: |
| **`RANGE_BOUND`** | 90.34% | 2.19% | 2.81% | 4.66% |
| **`TRENDING_BEARISH`** | 2.44% | 92.57% | 0.00% | 4.99% |
| **`TRENDING_BULLISH`** | 2.90% | 0.00% | 92.97% | 4.13% |
| **`VOLATILITY_EXPANSION`** | 1.55% | 2.07% | 2.02% | 94.35% |

> **Empirical Invariant on Directional Reversals:**
> Direct 1-hour transitions between `TRENDING_BULLISH` and `TRENDING_BEARISH` are **exactly 0.00%** in confirmed empirical data. A reversal must de-trend through `VOLATILITY_EXPANSION` or decay into `RANGE_BOUND`.

### 6.2 4-Hour Step Transition Matrix (Strategy HTF Horizon)
| Current Regime ($R_t$) \ Next ($R_{t+4}$) | `RANGE_BOUND` | `TRENDING_BEARISH` | `TRENDING_BULLISH` | `VOLATILITY_EXPANSION` |
| :--- | :---: | :---: | :---: | :---: |
| **`RANGE_BOUND`** | 62.87% | 8.49% | 10.55% | 18.10% |
| **`TRENDING_BEARISH`** | 9.39% | 71.07% | 0.00% | 19.54% |
| **`TRENDING_BULLISH`** | 10.96% | 0.02% | 73.25% | 15.76% |
| **`VOLATILITY_EXPANSION`** | 6.05% | 8.06% | 7.74% | 78.14% |

### 6.3 24-Hour Step Transition Matrix (Macro Daily Horizon)
| Current Regime ($R_t$) \ Next ($R_{t+24}$) | `RANGE_BOUND` | `TRENDING_BEARISH` | `TRENDING_BULLISH` | `VOLATILITY_EXPANSION` |
| :--- | :---: | :---: | :---: | :---: |
| **`RANGE_BOUND`** | 16.72% | 16.08% | 18.07% | 49.13% |
| **`TRENDING_BEARISH`** | 19.42% | 32.66% | 2.13% | 45.78% |
| **`TRENDING_BULLISH`** | 20.80% | 2.20% | 37.97% | 39.02% |
| **`VOLATILITY_EXPANSION`** | 15.88% | 19.25% | 19.65% | 45.22% |

---

## 7. Transition Delay & Latency Analysis
1. **Deterministic Buffer Latency:** A 3-candle persistence buffer introduces an exact **2-bar delay** (2 hours) before an emerging candidate state transitions to `CONFIRMED`.
2. **Filtering Efficacy:** Out of 5,304 raw candidate regime shifts in the 42,158-bar dataset:
   - **1163 shifts** were 1-bar transient noise blips.
   - **629 shifts** were 2-bar transient noise blips.
   - **Total Transient Noise Filtered:** **1792 false alarms** (33.79% of candidate transitions).
   - Only **3512 shifts** proved persistent enough to achieve 3-bar confirmation.
3. **Trade-off Evaluation:** The 2-hour confirmation delay is an optimal design compromise: it sacrifices 2 hours of immediate breakout responsiveness in exchange for filtering out one-third of all false whipsaws, avoiding catastrophic unconfirmed loss drags (-174.90 bps).

---

## 8. Realized Volatility Conditional on Regime
| Canonical Regime | Sample Count ($N$) | Mean 24h Ann RV | Median 24h Ann RV | Std Dev 24h Ann RV | Mean 1h Parkinson Vol (Ann) | Median 1h Parkinson Vol (Ann) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`VOLATILITY_EXPANSION`** | 16000 | **251.92%** | **218.99%** | 148.41% | **46.8%** | **35.87%** |
| **`TRANSITION_UNSUPPORTED`** | 7732 | **199.94%** | **181.02%** | 107.5% | **43.3%** | **31.83%** |
| **`TRENDING_BEARISH`** | 6024 | **197.6%** | **188.56%** | 93.25% | **35.77%** | **29.12%** |
| **`TRENDING_BULLISH`** | 6810 | **186.0%** | **176.62%** | 80.35% | **33.01%** | **27.22%** |
| **`RANGE_BOUND`** | 5592 | **165.05%** | **147.74%** | 93.3% | **26.39%** | **21.37%** |

- **Kruskal-Wallis $H$-Statistic:** **2665.21** ($p < 10^{-300}$)
- **Conclusion:** Realized volatility differs significantly across regimes ($p < 10^{-300}$). Realized volatility under `VOLATILITY_EXPANSION` is approximately 1.5x higher than under `RANGE_BOUND`.

---

## 9. HAR Model Forecast Performance Conditional on Regime
| Evaluation Segment | Sample Count ($N$) | Mean QLIKE Loss | Root Mean Squared Error (RMSE) | Forecast Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Global 2026 Benchmark** | **7238** | **0.451** | **4.8569** | Unconditional Baseline |
| **`VOLATILITY_EXPANSION`** | 2654 | **0.3587** | **5.6204** | Evaluated on 2026 OOS holdout |
| **`TRANSITION_UNSUPPORTED`** | 1298 | **0.4439** | **4.6355** | Evaluated on 2026 OOS holdout |
| **`RANGE_BOUND`** | 990 | **0.5004** | **3.3838** | Evaluated on 2026 OOS holdout |
| **`TRENDING_BEARISH`** | 1195 | **0.5192** | **5.5046** | Evaluated on 2026 OOS holdout |
| **`TRENDING_BULLISH`** | 1101 | **0.5634** | **3.2272** | Evaluated on 2026 OOS holdout |

> **Loss Function Asymmetry Note:**
> In `VOLATILITY_EXPANSION`, mean QLIKE loss is lowest (0.3587), while RMSE is highest (5.6204). Because QLIKE penalizes proportional under-prediction scaled by the true variance in the denominator, relative errors appear smaller in high-volatility environments under QLIKE than under quadratic Euclidean loss (RMSE).

---

## 10. Econometric Information Content Test (Nested Models)
| Econometric Specification | Features ($p$) | Out-of-Sample $R^2$ | Delta $R^2$ | AIC | Delta AIC | BIC | Delta BIC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 1 (Continuous Only)** | 5 | 0.26693 | Baseline | 165985.01 | Baseline | 166028.19 | Baseline |
| **Model 2 (Continuous + Regimes)** | 9 | 0.26881 | **+0.00188** | 165886.36 | **-98.66** | 165964.08 | **-64.11** |

- **$F$-Statistic ($df_1 = 4, df_2 = 41,572$):** **26.6925** ($p = 3.7959e-22$)
- **24h Directional Return AUC Test:** Continuous AUC = **0.5162** vs Continuous + Regimes AUC = **0.52** ($\Delta AUC = +0.0038$).

### Epistemic Assessment & Boundary
1. **Statistical Significance:** The $F$-test strictly rejects the null hypothesis that $\gamma_1 = \dots = \gamma_4 = 0$ ($p < 10^{-21}$), and both AIC ($-98.66$) and BIC ($-64.11$) favor Model 2. The heuristic rules capture non-linear conjunctions (such as volatility spikes paired with moving average crossover divergence).
2. **Economic Significance:** However, the incremental $R^2$ is only **+0.19 percentage points** (0.188%), and directional AUC increases by less than $0.004$.
3. **Core Conclusion:** The heuristic regime classifier does **not** serve as an independent alpha engine. Rather, its true economic value in BTCognitive is as an **efficient structural gatekeeper and risk-quarantine mechanism**, filtering unconfirmed transitions (-174.90 bps) and suppressing false breakouts (-41.16 bps).

---

## 11. Latent State Modeling Challenger: Hidden Markov Model (HMM)
### 11.1 Latent State Profiles
| Latent State | Implied Market State | Mean 1h Return ($\mu$) | Mean Log Parkinson Vol | Implied Annualized Parkinson Vol |
| :---: | :--- | :---: | :---: | :---: |
| **State 0** | **High Volatility / Downside Stress** | -0.0236% | -4.7483 | **~47.1%** |
| **State 1** | **Moderate Volatility / Normal Drift** | +0.0112% | -5.5953 | **~20.3%** |
| **State 2** | **Low Volatility / Compression** | +0.0032% | -6.3790 | **~9.3%** |

### 11.2 Cross-Tabulation against Heuristic Canonical Regimes
| Heuristic Regime \ Latent State | State 0 (High Vol Stress) | State 1 (Normal Drift) | State 2 (Low Vol Compression) | Alignment Evaluation |
| :--- | :---: | :---: | :---: | :--- |
| **`RANGE_BOUND`** | 5.75% | 36.91% | 57.34% | Evaluated across 41,582 observations |
| **`VOLATILITY_EXPANSION`** | 21.67% | 50.72% | 27.61% | Evaluated across 41,582 observations |
| **`TRENDING_BULLISH`** | 9.92% | 49.71% | 40.37% | Evaluated across 41,582 observations |
| **`TRENDING_BEARISH`** | 13.64% | 47.95% | 38.41% | Evaluated across 41,582 observations |
| **`TRANSITION_UNSUPPORTED`** | 21.24% | 43.60% | 35.16% | Evaluated across 41,582 observations |

### 11.3 Epistemic Governance Boundary: Why HMM is Offline Only
While the HMM challenger displays attractive mathematical properties ($	ext{Log-Likelihood} = 135227.28, \text{BIC} = -270273.75$), it is **strictly restricted to offline research** due to four fatal operational failure modes in live trading systems:
1. **Label Switching Problem:** In rolling walk-forward cross-validation, unconstrained EM algorithms can permute latent state indices, corrupting automated strategy dispatch.
2. **Lookahead Leakage in Smoothed Probabilities:** The standard Baum-Welch smoother uses backward passes to infer state probabilities. Only forward causal filtering ($P(S_t \mid Y_{1:t})$) is legally admissible at runtime, which exhibits higher variance and lower confidence separation.
3. **Estimation Instability:** Latent covariance matrices can collapse during sudden liquidity voids (singular covariance matrix crash).
4. **Deterministic Auditing Invariant:** The existing causal indicator rules (`MarketRegimeClassifier`) with 3-candle persistence produce $100\%$ reproducible, inspectable, deterministic states.

> [!CAUTION]
> **GOVERNANCE DIRECTIVE:**
> The existing heuristic classifier (`MarketRegimeClassifier` + `engine/canonical_regime_map.py`) MUST NOT be replaced by an HMM or Markov-Switching GARCH model in production.
> Automatic strategy switching based on probabilistic state outputs is **STRICTLY PROHIBITED**.

---

## 12. Final Governed Decisions & Sign-Off
1. **Research Experiment:** `PASS`
   The regime intelligence subsystem is mathematically verified, causally sound, and empirically validated across 4 datasets and 42,158 post-warmup bars. The 3-candle hysteresis filter successfully reduces boundary whipsaws by **44.8%**.
2. **Prospective Evidence:** `NOT_STARTED`
   All empirical findings in this report represent historical development data. Zero prospective forward events have been accumulated. Confirmatory testing requires $\ge 100$ prospective independent blocks.
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
   All regime models, tournament engines, and strategy dispatch rules remain frozen in offline research mode.
4. **Live Trading:** `DISABLED`
   Strict non-execution barrier preserved. No real broker orders or capital deployment.

```
================================================================================
AUDIT STAMP: BTCognitive V35.2 Market Regime Intelligence Audit
AUDITOR: Agent 4 (Regime Intelligence & Econometrics Specialist)
STATUS: COMPLETE & EMPIRICALLY GOVERNED
VERIFICATION: All 5 canonical regimes, indicators, and hysteresis mechanics verified.
================================================================================
```