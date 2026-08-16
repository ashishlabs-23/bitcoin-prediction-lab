# BTCognitive — Adaptive Decision Intelligence Engine for BTCUSD

An experimentation and production platform for **BTCUSD decision optimization** under non-stationarity, regime shifts, and realistic execution constraints (fees, slippage, funding rates).

## The core philosophy: Decision Intelligence over Static Prediction

Don't frame this project as "which ML model predicts Bitcoin direction best." Frame it as:

> Given real-time information available strictly at time *t*, what is the optimal **trade execution and risk management decision** — and how do we quantify the four distinct layers of uncertainty (data, regime, model, market stress) before taking risk?

Profitable trading is a **decision optimization problem**, not a classification accuracy challenge. A model with 60% accuracy and a 2.0 Sharpe ratio under strict cost modeling beats a 74% AUC model with high turnover and a 0.2 Sharpe ratio.

BTCognitive evaluates decision quality under continuous multi-regime probabilities, leakage-resistant purged walk-forward validation, multiple-testing defense (Deflated Sharpe Ratio & Probability of Backtest Overfitting), and counterfactual strategy comparison.

---

## 1. Pipeline

```
Raw data (price, derivatives, on-chain, macro, sentiment)
      │
      ▼
Information-availability check (was this actually knowable at time t?)
      │
      ▼
Feature engineering (transform by statistical property, not by mechanical rule)
      │
      ▼
Target engine (fixed-horizon / triple-barrier / vol-normalized — compare, don't assume)
      │
      ▼
Purged & embargoed walk-forward split
      │
      ▼
Baseline ladder (no-skill → persistence → LogReg → RF → XGBoost → LSTM/GRU → Transformer → Ensemble)
      │
      ▼
Calibration (is "70% confidence" actually right 70% of the time?)
      │
      ▼
Meta-label gate (should I act on this signal at all?)
      │
      ▼
Position sizing → cost-aware execution simulator (fees, slippage, funding, latency)
      │
      ▼
Statistical validation (Deflated Sharpe, Probability of Backtest Overfitting, permutation tests)
      │
      ▼
Dashboard (predictions, validation, backtest, robustness, paper portfolio)
```

---

## 2. Data sources

| Category | Examples | Why it matters |
|---|---|---|
| **Price/OHLCV** | 1h/4h/1d candles | Baseline, but weakest signal alone — public and arbitraged fast |
| **Technical** | RSI, MACD, moving averages, realized volatility, volume deltas | Transform by statistical property (returns/ratios/z-scores usually beat raw levels), but don't force stationarity mechanically — some state variables carry economically meaningful information in levels |
| **Derivatives** | Funding rate, open interest, long/short ratio, liquidation volume | Reflects real capital flow and leveraged positioning; extreme funding has historically preceded reversals, though this relationship is time-varying, not permanent |
| **On-chain** | Exchange net flow, active addresses, MVRV / SOPR, whale wallet activity | Behavioral data with predictive value even where price alone lacks an intrinsic anchor |
| **Cross-asset / macro** | DXY, gold, SPX/Nasdaq correlation regime, rates | Recent work found gold-price relationships materially useful for BTC forecasting |
| **Sentiment** | Fear & Greed Index, news/headline NLP, social sentiment | Weak alone, useful as regime/context — treat with skepticism, easily noisy |

**Feature selection matters more than feature quantity.** Studies applying Boruta /
genetic-algorithm / LightGBM feature selection before modeling consistently beat
"throw in everything" approaches — large undifferentiated feature sets create a
curse-of-dimensionality problem, especially for deep models.

### Information-availability firewall (do this before anything else)

The most common invisible leak in a project like this isn't the train/test split —
it's using data that wasn't actually knowable at prediction time. On-chain metrics,
macro releases, and even some exchange data can be revised or published later than
their nominal timestamp implies.

Minimum implementation: every feature row needs, alongside its value, an
`available_time` — when the value was actually obtainable. Before training or
predicting at time `t`:

```python
assert available_time <= decision_time
```

You don't need a full multi-timestamp subsystem (event/exchange/ingestion/feature
time) to start — one `available_time` field and one assertion catches most of the
damage. Add finer-grained timestamps later only if a specific source turns out to
need it.

---

## 3. Labeling — compare targets, don't assume one is right

**Naive (avoid as the only target):**
```
y = (price[t+24] / price[t]) - 1
```
Ignores the path — treats a smooth +2% and a "-5% then recovers to +2%" identically.

**Run and compare three target formulations, not just one:**

- **A — Fixed horizon:** `r(t,H) = log(P[t+H] / P[t])` — simplest, still useful as
  a reference point.
- **B — Triple-barrier** (López de Prado): upper barrier (take-profit), lower
  barrier (stop-loss), vertical barrier (time limit) — whichever is hit first
  determines the label. Path-aware, mirrors how a real position resolves. Barriers
  should scale with recent volatility, not be fixed percentages.
- **C — Volatility-normalized return:** `r(t,H) / σ(t)` — useful for comparing
  signal strength across different volatility regimes.

Triple-barrier isn't automatically superior — it answers a different question
(how would a bounded trade resolve) than fixed-horizon (what's the return after
exactly H hours). Decide which matches what you're actually trying to build, and
justify it with the comparison rather than assuming it.

### Three separate prediction problems

Rather than one model doing everything, it's worth eventually splitting into:

- **Direction:** `P(R[t,H] > 0 | X_t)`
- **Magnitude:** `E[R[t,H] | X_t]`
- **Trade outcome:** `P(TP before SL | X_t)`

This is a good target architecture, but build it *after* your baseline ladder
proves there's a signal worth splitting — three untested models is not a better
starting point than one tested one.

---

## 4. Validation

### The precise leakage mechanism
Chronological walk-forward ordering, by itself, does not leak. The actual problem
is that **training observations whose label windows overlap the test window** can
transmit future information into training — this happens with both fixed-horizon
and triple-barrier labels, because both look forward from `t`.

### Purged & Embargoed Cross-Validation
```
Train ─────────╮ purge ╭──── Test ────╮ embargo ╭── (next fold starts here)
```
- **Purge**: remove training samples whose label window overlaps the test window.
- **Embargo**: buffer after the test window before resuming training data, to
  remove residual serial correlation.
- **Uniqueness weighting**: overlapping labels mean samples aren't equally
  informative — weight each by the inverse of how many other label windows
  overlap it.

### Combinatorial Purged CV (CPCV) — as a robustness check, not a replacement
CPCV generates multiple train/test path combinations instead of one linear split,
giving a distribution of outcomes rather than a single number. Use **walk-forward
as the primary evaluation** (it best represents "train on past → predict future,"
which is what live paper trading actually does), and **CPCV as a secondary
robustness check** on top of your best candidates.

### Sanity checks that catch what CV alone won't
- **Label permutation**: shuffle the target, retrain — performance should collapse
  to near-random. If it doesn't, you have leakage.
- **Timestamp perturbation**: break the temporal relationship — edge should
  disappear.
- **Feature permutation**: shuffle one feature at a time — performance should
  degrade in proportion to that feature's real importance.

These are cheap and should run automatically on every promoted model.

---

## 5. Models — baseline ladder

| Tier | Model | Purpose |
|---|---|---|
| 0 | No-skill (base rate) | Is the class balance itself informative? |
| 1 | Persistence (`sign(R[t])` momentum) | Is ML contributing anything beyond naive momentum? |
| 2 | Logistic Regression | Linear baseline |
| 3 | Random Forest | Nonlinear baseline, free feature importances |
| 4 | XGBoost / LightGBM | Usually the strongest tabular performer |
| 5 | LSTM / GRU | Sequential dependencies — needs more data, watch overfitting |
| 6 | Transformer | Only worth it with enough data; often ties or loses to boosted trees on tabular crypto features |
| 7 | Ensemble | Specify the method: simple average, stacked meta-learner, or regime-gated selection |

Don't assume XGBoost (or any model) wins — that's an empirical question the
ladder is designed to answer. Every tier should be evaluated on the **same**
feature set, target, and validation scheme; otherwise the comparison is meaningless.

### Meta-labeling (elevate this once tier 4+ shows a real signal)
A secondary model that learns whether to act on the primary directional signal:

```
Primary model → LONG / SHORT / NEUTRAL
                        │
                        ▼
              Meta-label model → TAKE / SKIP
                        │
                        ▼
                Position sizing
```

This is worth building earlier than "v2 polish" once you have a baseline that
beats the no-skill/persistence floor — but it's still a second model, so don't
start here.

---

## 6. Calibration & explainability

- **Calibration curve / reliability diagram**: among predictions where the model
  says "67% probability of positive return," does it happen ~67% of the time?
  If not, recalibrate (Platt scaling / isotonic regression) or use conformal
  prediction for a valid interval instead of a "Medium/High" label.
- **SHAP values** power the "what changed?" explanation — but label this
  **model attribution**, not causal explanation. SHAP shows how features
  contributed to *this model's* prediction, not that funding rate *caused* BTC
  to move. Keep that distinction visible in the UI copy.
- **Prediction history log**: every prediction vs. realized outcome, rolling
  accuracy/Brier score — doubles as your drift-detection surface.
- **Feature stability over time**: track feature importance by period. A feature
  that was #1 in 2023 and irrelevant in 2025 tells you something a single global
  SHAP plot won't.
- **Signal decay**: measure performance at 1h, 4h, 12h, 24h, 48h after a
  prediction to estimate the signal's "alpha half-life" — most edges aren't
  constant across horizons.

---

## 7. Backtest & execution realism

Minimum requirements:
- Fees + slippage modeled per trade
- Funding cost if simulating leveraged/short positions
- Turnover-aware — penalize models that flip direction constantly
- Cost-adjusted baseline, not just raw buy-and-hold
- Regime breakdown (bull/bear/sideways/high-vol), not one blended Sharpe number

### Position sizing — build in stages, don't jump to Kelly
1. Fixed notional (`position = ±1`)
2. Volatility targeting (`position ∝ target_vol / realized_vol`)
3. Probability-based (`position ∝ P(up) − 0.5`)
4. Risk-constrained (max position, max leverage, max daily loss, max drawdown)
5. Fractional Kelly — only after 1–4 are working and validated

### Cost-sensitivity grid
Instead of one fee/slippage assumption, run a small grid and report how the
strategy degrades:

```
               Slippage
             low   base   high
Fee low       X      X      X
Fee base      X      X      X
Fee high      X      X      X
```

A strategy whose Sharpe drops from 1.45 to 0.5 under realistic cost stress
is a very different result from one that holds up — report both.

### Execution latency (v2)
Decision time ≠ execution price. As the project matures, separate signal-generation
time, order-submission delay, and fill price rather than assuming instant execution
at the prediction candle's close.

---

## 8. Statistical validation — don't trust a single Sharpe number

You're testing multiple models × feature sets × horizons × hyperparameters —
some results will look good by chance.

- **Deflated Sharpe Ratio (DSR)**: corrects for the number of trials you ran
  before reporting the "best" result.
- **Probability of Backtest Overfitting (PBO)**: a related but distinct question
  — given how the strategy was selected, how likely is the apparent winner to be
  overfit rather than real?
- Report Sharpe with **confidence/bootstrap intervals and trade count** — a Sharpe
  of 1.5 from 37 trades means something very different from 1.5 from 8,000 trades.

To make DSR/PBO meaningful, keep a lightweight **experiment log** — even a CSV or
YAML per run (feature set, target, model, validation scheme, costs, result) is
enough to know how many trials you actually ran. This solves "researcher degrees
of freedom" — the tendency to forget how many things you tried before something
looked good.

---

## 9. Drift — more than one kind

- **Data drift**: `P(X)` changes (feature distributions shift)
- **Concept drift**: `P(Y|X)` changes (the relationship itself shifts)
- **Performance drift**: rolling accuracy/Brier score degrades
- **Economic drift**: the signal is statistically still there, but the expected
  move has shrunk relative to costs — the model can stay "accurate" while
  becoming unprofitable. This is easy to miss if you only track accuracy.

---

## 10. The flagship experiment: ablation by data source

This is the single most valuable experiment in the project — it turns "we got
67% accuracy" into an actual finding about *what information carries value*.

```
OHLCV only
   ↓
+ technical indicators
   ↓
+ derivatives (funding, OI)
   ↓
+ on-chain
   ↓
+ macro/cross-asset
   ↓
+ sentiment
```

For each step, hold model, target, and validation scheme fixed, and report:
AUC, Brier score, calibration error, net return, Sharpe, max drawdown, turnover,
DSR. Do the same sweep across models (fixed feature set) and across horizons
(1h/4h/12h/24h/48h/72h) — each is a controlled experiment answering one question
at a time, instead of one big result nobody can attribute to anything specific.

---

## 11. Dashboard

Structure it as five focused views rather than one crowded page:

1. **Market** — price, volatility, funding, OI, liquidity, current regime
2. **Prediction** — P(up), expected return, calibration, SHAP attribution ("what changed?")
3. **Validation** — walk-forward folds visualized (train/purge/test/embargo blocks), out-of-sample metrics
4. **Backtest & Robustness** — strategy comparison table, cost-sensitivity grid, regime breakdown, DSR/PBO
5. **Paper Portfolio** — capital, positions, entries, realized/unrealized P&L, exposure

Making the validation methodology visually inspectable (not just a final Sharpe
number) is what separates this from a typical prediction dashboard — it lets
someone check your work.

---

## 12. Before promoting a model, check (lightweight checklist, not a formal gate)

- [ ] Passes label/timestamp permutation sanity checks
- [ ] Beats no-skill and persistence baselines out-of-sample
- [ ] Calibrated (reliability diagram looks reasonable)
- [ ] Positive net Sharpe after realistic costs, holds up under the cost-sensitivity grid
- [ ] Reasonably stable across regimes (not only working in one bull run)
- [ ] DSR/PBO don't flag it as likely overfit given how many configs you tried

If a model fails several of these, that's a useful result — write it down and
move on, don't keep tuning until it passes by chance.

---

## 13. Build order

1. **Data + information-availability check** — ingest OHLCV/derivatives/on-chain,
   attach `available_time`, write the lookahead assertion early
2. **Target engine** — implement fixed-horizon, triple-barrier, vol-normalized;
   compare them on a toy baseline before committing to one
3. **Purged/embargoed walk-forward split** + sample uniqueness weighting
4. **Baseline ladder** — no-skill → persistence → LogReg → RF → XGBoost, with
   calibration and SHAP from the start
5. **Cost-aware backtester** — fees, slippage, funding, cost-sensitivity grid,
   regime breakdown
6. **Statistical validation** — DSR, PBO, permutation/placebo tests, experiment log
7. **Ablation study** (data sources, then models, then horizons) — your flagship result
8. **Dashboard v1** — the 5 views above
9. **Sequence models (LSTM/GRU), meta-labeling, ensemble methodology**
10. **Drift monitoring, feature stability tracking, signal decay, regime detector, execution latency modeling**

Do steps 1–7 properly before touching deep learning or sentiment NLP. A leaky
pipeline with a Transformer on top is still a leaky pipeline — validation
methodology is the actual hard part of this project, not model architecture.

---

## 14. Known limitations (state these explicitly)

- Crypto markets are efficient enough, and change structurally often enough (new
  derivatives products, regulation, macro regimes), that any edge found here
  should be assumed non-stationary — drift monitoring isn't optional polish.
- Funding-rate/on-chain predictability has been shown in the literature to be
  time-varying, not a permanent free lunch.
- High historical accuracy on illiquid or thin windows can hide unrealistic
  execution assumptions — always check against cost-adjusted, stress-tested returns.
- This project is for research/education, not a trading recommendation system.

---

## 15. Suggested tech stack

- **Data**: `ccxt` (exchange data), on-chain APIs (Glassnode/CryptoQuant-style),
  `pandas` / `polars`
- **Labeling/validation**: custom triple-barrier + purge/embargo (patterns from
  `mlfinlab`/`mlfin.py`-style libraries), or roll your own
- **Models**: `scikit-learn`, `xgboost`/`lightgbm`, `pytorch` (LSTM/GRU/Transformer)
- **Explainability**: `shap`
- **Backtesting**: `vectorbt` or a custom event-driven backtester (needed for
  realistic fee/slippage/funding modeling)
- **Experiment tracking**: a simple CSV/YAML log is enough to start; MLflow if it grows
- **Dashboard**: Streamlit/Dash for fast iteration, or custom React for a
  polished terminal-style UI

---

## 16. Full closed-loop architecture

This consolidates the pipeline in section 1 with the regime, ensemble, and
feedback components discussed throughout. Two structural rules govern this
diagram: predictions feed the gate in parallel with the uncertainty engine (not
through it sequentially), and **nothing changes the production model without
passing the validation gate** — including automated adaptation.

```
                    MARKET DATA (price, derivatives, on-chain, macro/news)
                          │
                          ▼
              FEATURE LAYER (availability firewall — section 2)
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
      MARKET STATE ENGINE        FEATURE / CONTEXT SNAPSHOT
      trend | vol | liquidity    (RSI, funding, OI, on-chain,
      | momentum | correlation    macro, sentiment, ...)
              │                        │
              ▼                        │
      REGIME DETECTOR                  │
      trending | ranging | breakout    │
      | high-vol | liquidation |event  │
              │                        │
      ┌───────┴────────┐               │
      │ (routes ensemble│               │
      │  weighting)      │  (joins as context feature) │
      ▼                 └───────────────┤
ADAPTIVE ENSEMBLE                       │
weighting by regime ◄───────────────────┘
      │
      ▼
   MODELS: LogReg/RF/XGBoost/LSTM
   (+ microstructure — v2+, only once order-flow/tick infra exists)
      │
┌─────┼─────────────┐
▼     ▼             ▼
Direction  Magnitude   Trade-outcome prediction
      │     │             │
      └─────┼─────────────┘
      ┌──────┴───────┐
      ▼              ▼
UNCERTAINTY ENGINE   META-LABEL GATE
calibration|interval|      TAKE / SKIP /
regime track record|       LOW-CONFIDENCE
drift|model agreement
      └──────┬───────┘
             ▼
      RISK / POSITION ENGINE
             │
             ▼
      COST-AWARE EXECUTION → PAPER PORTFOLIO
             │
             ▼
      ACTUAL OUTCOME
             │
             ▼
      MARKET MEMORY
      (what worked, by regime/feature/model)
             │
   ┌─────────┴──────────┐
   ▼                     ▼
SAFE STATE UPDATE   CANDIDATE MODEL/UPDATE
(see tier 2 below)         │
   │                       ▼
   │              ╔═══════════════════════╗
   │              ║   VALIDATION GATE     ║
   │              ║ purged WFO · CPCV ·   ║
   │              ║ DSR · PBO · permu-    ║
   │              ║ tation tests · cost   ║
   │              ║ stress · regime       ║
   │              ║ robustness            ║
   │              ╚═══════════╤═══════════╝
   │                    pass  │  fail → stays in research
   │                          ▼
   └─────────────────► PRODUCTION MODEL
```

### Three tiers of adaptation — this is what makes the gate enforceable

Not everything that touches the production system needs the full validation
gate, but everything that *changes what the system predicts or how* does. Draw
the line explicitly:

**Tier 1 — Online observation (always live, no gate needed)**
Market Memory recording each prediction/outcome, rolling metric updates, regime
statistics, drift statistics. Pure bookkeeping — nothing here changes behavior.

**Tier 2 — Safe online state updates (live, but with light guardrails)**
Calibration refits, regime-label updates, signal-quality recomputation. These
don't touch training data or introduce lookahead, but "no leakage" isn't the
same as "can't overfit to noise" — a calibration refit on 20 recent samples in a
thin regime can still drift somewhere bad. Guardrails: require a minimum sample
size before refitting, and check on a small holdout that the update actually
*improves* calibration error before applying it live. Cheap, but keeps tier 2
from becoming a side door around the gate.

**Tier 3 — Model adaptation (must pass the validation gate, no exceptions)**
Feature changes, retraining, ensemble-weight changes, hyperparameters, target
changes, regime-specific model changes. Every one of these becomes a
**candidate artifact** — it does not touch the production model until it clears
purged WFO, CPCV, DSR/PBO, permutation tests, cost-stress, and calibration
checks (section 12).

### The critical rule

> No observation, memory update, recalibration, feature change, model change,
> ensemble-weight change, or regime-policy change can directly modify the
> production model. Every candidate change must pass the same validation gate a
> manually-proposed model change would. Tier 1 and Tier 2 are the only paths
> that bypass the gate, and both are deliberately restricted to bookkeeping and
> lightly-guarded state — never to what the model predicts or how it's weighted.

This is the rule that keeps continuous adaptation from becoming continuous
overfitting with a better name.

## 17. Product/UI layer

The research architecture above answers *whether there's a real signal*. A
separate spec, `TERMINAL_UI_SPEC.md`, covers how that signal gets surfaced as a
live, chart-centric interface — including the uncertainty-awareness system
(calibration, prediction intervals, regime-conditional track record, drift
detection, model disagreement) that lets the system visibly flag when it
shouldn't be trusted, rather than presenting every prediction with the same
confident face. Build the research engine and that uncertainty system before
investing in real-time chart infrastructure — a trustworthy low-confidence flag
is worth more than a polished chart with a made-up confidence number.

## 18. Alpha Genome Evolutionary Subsystem

The **Alpha Genome** is an evolutionary research engine built to discover regime-specific exit policies and risk-management parameters (take-profit multipliers, stop-loss multipliers, max hold times, position sizing rules) without exploding the search space.

### Core Architectural Principles

1. **Separation of Direction & Risk**: Entry direction ($P(\text{up} \mid X_t)$) remains strictly owned by the `AdaptiveRegimeEnsemble`. Genomes compete exclusively on exit execution and sizing.
2. **Out-of-Band Batch Evolution**: The evolutionary loop (`genome/population.py`) runs asynchronously via CLI/cron jobs into a SQLite WAL-mode registry. The live inference path (`api/server.py`) remains 100% fast, stable, and read-only.
3. **Multi-Objective Pareto Fronts (NSGA-II)**: Avoids arbitrary weighted-sum fitness tuning. Genomes are sorted into Pareto fronts across 5 objectives:
   - Annualized Sharpe Ratio
   - Calmar Ratio
   - Win Rate
   - Max Drawdown (magnitude minimized)
   - Turnover (minimized)
4. **Statistical Overfitting Firewall**: Before any candidate genome reaches `quarantine` status, it must pass a dual statistical firewall:
   - **Deflated Sharpe Ratio (DSR > 0.5)**: López de Prado (2014) multiple-testing correction.
   - **Probability of Backtest Overfitting (PBO < 0.4)**: CSCV sub-period ranking consistency, guarded by a minimum of 30 trades per sub-period.
5. **Periodic Re-Validation**: Genomes marked `verified` undergo trailing 30-day re-evaluation against realized shadow trades (`[-0.5, +0.75]` Sharpe tolerance). Failed or over-performing genomes are demoted back to `candidate` for re-evolution.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                AdaptiveRegimeEnsemble (Direction)            │
       └──────────────────────────────┬──────────────────────────────┘
                                      │ (prob_up signals)
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                 Genome Exit & Risk Policy                    │
       │   TP = entry ± tp_mult * ATR │ SL = entry ∓ sl_mult * ATR   │
       │   Hold limit = max_hold_bars  │ Sizing = fixed|vol|prob     │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │            Purged & Embargoed CV Backtest Harness            │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
            Multi-Objective Pareto        Anti-Overfitting Gate
            (NSGA-II Non-Dominated)       DSR > 0.5  │  PBO < 0.4
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                      SQLite Registry (`genome_registry.db`)
                                      │
                                      ▼
                   FastAPI Read-Only REST API (`/genome/*`)
```

### CLI Operations

```bash
# Generate out-of-sample ensemble signals for feature matrix
python models/generate_ensemble_probs.py

# Run Generation 0 evolution for a market regime
python genome/population.py --generation 0 --population 30 --regime TRENDING_BULL

# Run next-generation evolution (mutates and crosses over prior survivors)
python genome/population.py --generation 1 --population 30 --regime TRENDING_BULL

# Run weekly verified genome re-validation
python genome/population.py --mode revalidate
```

---

## References / further reading

- López de Prado, *Advances in Financial Machine Learning* — triple-barrier
  labeling, purged/embargoed CV, meta-labeling, Deflated Sharpe Ratio
- Bailey & López de Prado (2014) — Deflated Sharpe Ratio; Bailey et al. (2017) —
  Combinatorial Symmetric Cross-Validation / Probability of Backtest Overfitting
- "Algorithmic crypto trading using information-driven bars, triple barrier
  labeling and deep learning" — *Financial Innovation*, 2025
- "Deep learning for Bitcoin price direction prediction: models and trading
  strategies empirically compared" — *Financial Innovation*, 2024
- "Using machine and deep learning models, on-chain data, and technical analysis
  for predicting bitcoin price direction and magnitude" — *ScienceDirect*, 2025
- "Predictability of Funding Rates" — SSRN, 2025

