# V32.80 — Independent Red-Team Audit (Workstream 8)
**Milestone:** BTCognitive V32.80 — Research Integrity & Reproducibility Audit  
**Generated:** 2026-10-30T17:18:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Adversarial Scope & Objectives

The Red-Team mandate for V32.80 is to independently challenge the complete evidence package generated during the V32.79–V32.80 cycle, specifically scrutinizing:
1. The discovery of the paired DM-HLN p-value ($p = 0.0039$) versus the original unpaired ($p = 0.269$).
2. The risk of treating the paired p-value as a validated edge despite failing the 100-episode sample gate.
3. The severe chronological instability (H1 vs. H2 sign reversal).
4. The retail fee barrier (Coinbase 87 bps deficit).
5. The systemic risk posed by the synthetic dataset `multi_regime_features.parquet` and how governance must insulate the repository going forward.

---

## 2. Red-Team Challenge 1: The Paired DM-HLN $p = 0.0039$ — Genuine Signal or False Hope?

**The Finding:** V32.80 discovered that pairing the 64 SHORT episodes with their contemporaneous 24h baseline blocks yields a paired HLN statistic of $2.9998$ ($p = 0.0039$). At a local $K=2$ Bonferroni threshold ($\alpha = 0.025$), this appears nominally statistically significant.

### Red-Team Objections:
1. **The Post-Hoc Alignment Hazard:**
   While paired comparison is econometrically superior to unpaired sampling, applying it post-hoc after observing the dataset introduces selection confirmation risk. 
2. **Failure of the Programme-Wide Multiple Testing Hurdle:**
   Under the full V32.79 research scope ($K \le 159$, $\alpha_{\text{Bonf}} \approx 0.000314$), $p = 0.0039$ **fails by more than an order of magnitude**. Claiming that $K=2$ applies because only two arms were executed ignores the broader hypothesis exploration that preceded it.
3. **Severe Temporal Concentration:**
   The positive performance is entirely concentrated in H2 (March–December 2024, post-ETF approval). During H1 (January 2023–March 2024), the strategy generated **$-39.02\text{ bps}$ net loss**. If a paired DM test is run on H1 alone, the statistic is negative and non-significant.
4. **Sample Size Disqualification:**
   The pre-registered protocol mandated at least **100 distinct qualifying episodes** before any confirmatory inference could be drawn. Achieving $N=64$ means the sample gate was breached. A significant p-value on an underpowered sample is classic Type I error risk (the "Winner's Curse" in small-sample quantitative finance).

**Red-Team Verdict:** The $p = 0.0039$ paired result is a valuable methodological correction of an earlier calculation error, but it **MUST NOT** be used to claim an empirical trading edge.

---

## 3. Red-Team Challenge 2: Chronological Instability & Regime Dependence

**The Finding:**
- **H1 (First 32 episodes):** Net EV = $-39.02\text{ bps}$, TP Rate = $18.8\%$.
- **H2 (Last 32 episodes):** Net EV = $+52.62\text{ bps}$, TP Rate = $40.6\%$.

### Red-Team Analysis:
A 21.8 percentage-point swing in hit rate and a sign reversal from negative to positive across contiguous chronological halves is direct empirical evidence of **non-stationarity**.
- In H1 (2023 recovery / compression), extreme positive funding was frequently punished as price continued grinding upward against crowded shorts.
- In H2 (2024 ETF era), structural market-making and institutional basis arbitrage caused sharp mean-reversions after funding spikes.

A strategy whose positive expectation depends entirely on a post-2024 market structure shift cannot be considered robust. If market conditions revert to H1 dynamics, the strategy will incur persistent drawdown.

---

## 4. Red-Team Challenge 3: Retail Execution Infeasibility

| Venue / Tier | Round-Trip Cost | Net Realized EV | Realized Outcome |
|---|---|---|---|
| **Binance VIP0** | 24 bps | **+6.8 bps** | Marginal / Unstable |
| **Coinbase Advanced** | 87 bps | **−56.2 bps** | **Severe Loss** |

Even if Binance VIP0 institutional fees yield $+6.8\text{ bps}$, Coinbase Advanced retail users lose $56.2\text{ bps}$ per trade. A strategy with a $-56.2\text{ bps}$ retail expectation cannot be deployed or promoted for general execution.

Furthermore, if market impact and adverse selection at execution are modeled (resting limit orders filled during adverse wicks), even the $6.8\text{ bps}$ margin would be fully erased.

---

## 5. Red-Team Challenge 4: Systemic Exposure to Synthetic Data

**The Finding:** `data/processed/multi_regime_features.parquet` was constructed from `np.random.normal()` price paths with a fixed seed (`np.random.seed(42)`).

### Root Cause Analysis:
Why was this not caught immediately upon file generation?
1. The code in `research/multi_regime_dataset.py` lacked explicit header warnings indicating that the generator produced synthetic/simulated test vectors.
2. The file was saved directly into `data/processed/`, an area usually reserved for ingested empirical data transforms.
3. Downstream scripts (`research/macro_evaluation_harness.py`, `research/multi_regime_purged_validation.py`) ingested the file without checking metadata assertions.

### Safeguards Required:
- Any script generating synthetic or simulated fixtures must write to `data/synthetic/` or `tests/fixtures/`, never `data/processed/` or `data/raw/`.
- All generated fixtures must contain a mandatory metadata flag `dataset_type: "SYNTHETIC"` in parquet schema metadata or accompanying JSON sidecars.
- All downstream empirical loaders must assert `dataset_type != "SYNTHETIC"`.

---

## 6. Synthesis and Final Red-Team Ruling

| Red-Team Question | Assessment | Red-Team Verdict |
|---|---|---|
| Does V32.79A reproduce mathematically? | Yes, counts and decompositions verified | **REPRODUCIBLE** |
| Was the original DM-HLN correctly calculated? | No, unpaired comparison was misspecified | **CALCULATION_DISCREPANCY** |
| Does the corrected paired $p=0.0039$ prove an edge? | No, sample size $N=64 < 100$, H1/H2 unstable | **REJECTED AS AN EDGE** |
| Is there a viable retail trading strategy? | No, Coinbase net EV is $-56.2\text{ bps}$ | **NO_ECONOMIC_EDGE** |
| Are prior OHLCV barrier milestones invalidated? | No, independent lineage from real OHLCV | **ISOLATED & SOUND** |

**Recommended Formal Milestone Determination:**
`REPRODUCIBLE_INSUFFICIENT_EVIDENCE` with an explicit audit note recording the `CALCULATION_DISCREPANCY` in the earlier unpaired DM test.

