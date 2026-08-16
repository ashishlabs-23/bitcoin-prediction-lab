# BTC AI Terminal — Product & UI Spec

This sits on top of the research engine in `README.md`. The research engine
decides *whether there's a real signal at all*; this spec covers how that signal
gets surfaced as something that behaves like a chart indicator — but one that
knows, and shows, when it's likely to be wrong.

## Why this is a different problem than "add a chart"

RSI and MACD are deterministic functions of price — recompute the same formula
on the same data and you always get the same line. An ML prediction is a
probabilistic estimate that is sometimes wrong, and *how* wrong it tends to be
changes by regime, by how far current conditions are from anything the model has
seen, and by how much your candidate models agree with each other. A prediction
overlay that doesn't surface that will get over-trusted exactly the way RSI
crossovers get over-trusted — except it'll look more authoritative because it
says "AI."

So the product requirement isn't "show a prediction on the chart." It's:
**show a prediction on the chart that visibly degrades its own presentation
when it doesn't trust itself.**

---

## 1. Layered information hierarchy

```
Layer 1 — What is happening      (price, volume, volatility, regime)
Layer 2 — What the model thinks  (direction, expected return, calibrated probability)
Layer 3 — Why                    (model attribution — SHAP-style factor breakdown)
Layer 4 — How much to trust it   (the uncertainty system — see below)
```

Layer 4 is the one most designs skip, and it's the one your question is actually
about.

---

## 2. The uncertainty-awareness system (core differentiator)

Don't build one "confidence" number. Build these four independent signals, show
them individually, and only then optionally combine them into a display score
with a visible formula.

### a. Calibrated probability, not raw model output
Raw classifier probabilities are usually not calibrated — a model saying "70%"
doesn't mean the event happens 70% of the time. Apply Platt scaling or isotonic
regression on held-out data before this number ever reaches the UI, and re-fit
calibration periodically as new data comes in. Track calibration **per regime**
separately (a model can be well-calibrated in trending markets and badly
calibrated in chop) — this is what feeds "regime coverage" below.

### b. Prediction intervals, not point estimates
For the expected-return number, use conformal prediction to produce an interval
with a coverage guarantee ("90% of the time, the actual return falls in this
range") instead of a single "+0.84%." This is what renders as the **prediction
zone / triple-barrier band** on the chart — the width of that band *is* the
model's odds of being wrong, made visual.

### c. Regime-conditional track record
Rather than one global accuracy number, the model should be able to say: "in
this specific regime (high-trend, medium-vol), over the last N predictions, I've
been right X% of the time." If current conditions fall into a regime with a thin
or poor historical track record, the UI should visibly downgrade — smaller
marker, muted color, or an explicit "low regime coverage" flag — rather than
showing the same confident LONG marker it would in a well-covered regime.

### d. Distributional distance / drift check
Before serving a prediction, compare the current feature vector's distance from
the training distribution (e.g. Mahalanobis distance, or a simple percentile
check per feature). If current conditions are far outside anything the model was
trained on, that's a direct, model-agnostic signal that the prediction is
unreliable — regardless of what probability the model outputs. This should be
able to override everything else and force a **NO-TRADE / LOW CONFIDENCE** state.

### e. Model disagreement as a native uncertainty signal
You're already building a ladder of models (LogReg → RF → XGBoost → LSTM →
Transformer). Their disagreement is free uncertainty information — if RF says
LONG at 71% and XGBoost says SHORT at 58%, that disagreement itself should
suppress the displayed confidence, independent of any single model's stated
probability. This is a good input to the meta-label gate, not just a debugging
tool.

### Combining these into a display score
If you want a single "Signal Quality" number for the UI, define it explicitly,
e.g.:

```
signal_quality = f(
    calibration_error,      # lower is better
    regime_track_record,    # sample size + historical accuracy in this regime
    distributional_distance,# lower is better
    model_agreement         # higher is better
)
```

Publish the formula in the UI (a small "how is this calculated?" link is enough)
— the point is that nothing about this number should be a mystery weight. If you
can't define it cleanly, show the four components separately instead of forcing
a composite.

---

## 3. What this looks like on the chart

Point estimate (avoid as the *only* visualization):
```
        ▲ LONG  72%
         │
─────────●────────
```

Prediction zone (prefer this — the band width communicates uncertainty directly):
```
$118,100 ─── upper bound (90% interval)
             ↑
$116,800 ─── current price / point estimate
             ↓
$115,900 ─── lower bound (90% interval)
```

Low-confidence state (visually distinct, not just a smaller number):
```
        ░ NO TRADE
        Low regime coverage — 12 historical samples
        Feature distance: 2.3σ from training distribution
```

The low-confidence state matters as much as the confident one — a system that
only ever shows sharp, confident-looking markers is lying by omission about how
often it doesn't know.

---

## 4. Prediction history & self-audit

Every prediction gets logged with: timestamp, model version, calibrated
probability, prediction interval, regime, distributional distance, and — once
the horizon resolves — the actual outcome and whether it fell inside the stated
interval. This closes the loop and answers the real question: **is the model's
stated uncertainty actually accurate**, not just "was the direction right."
A model that's right 55% of the time but honestly says so is more useful than
one that's right 60% of the time while claiming 85% confidence.

```
Time    Signal   P(up)   Interval          Regime         Actual   In interval?
10:00   LONG     68%     [+0.2%, +1.1%]    High-trend     +0.4%    ✓
11:00   LONG     71%     [+0.3%, +1.3%]    High-trend     +0.7%    ✓
12:00   SHORT    64%     [-0.9%, -0.1%]    Transitioning  +0.3%    ✕ (wrong side AND outside interval)
```

That last row is more informative than "wrong" — it tells you the model was
overconfident in a regime it doesn't handle well, which is exactly the kind of
thing the regime-conditional track record (2c) should start suppressing over
time.

---

## 5. Architecture (v1 scope — deliberately smaller than a full live terminal)

```
Candle-interval poll (not tick-level WebSocket for v1)
        │
        ▼
Feature snapshot (with information-availability check from README.md)
        │
        ▼
Model ladder → calibrated probability + conformal interval
        │
        ▼
Uncertainty checks: regime coverage, distributional distance, model agreement
        │
        ▼
Meta-label gate → TAKE / SKIP / LOW-CONFIDENCE
        │
        ▼
Chart overlay + attribution panel + prediction log
```

Single exchange feed, one canonical BTC/USDT source, prediction cadence matched
to the model's horizon (e.g. hourly model → hourly prediction, regardless of
whether the chart itself shows 15m candles). Full real-time tick streaming,
multi-exchange aggregation, and order-book depth are v2+ — they add UI polish
and latency realism but nothing to whether the model's uncertainty estimates are
honest, which is the harder and more important problem to solve first.

---

## 6. UI layout (v1)

```
┌─────────────────────────────────────────────┐
│  BTC/USDT   $116,842   +2.14%   1H  Binance  │
├─────────────────────────────────────────────┤
│  CHART — candles + prediction zone overlay   │
│  + historical prediction markers             │
├─────────────────────────────────────────────┤
│  AI FORECAST                                 │
│  Direction | Calibrated P(up) | Interval     │
│  | Horizon | Action (TAKE/SKIP/LOW-CONF)     │
├─────────────────────────────────────────────┤
│  MODEL ATTRIBUTION (labeled, not causal)     │
│  Top factors, "what changed since last tick" │
├─────────────────────────────────────────────┤
│  SIGNAL QUALITY (four components, not one    │
│  mystery number)                             │
│  Calibration | Regime coverage | Drift |     │
│  Model agreement                             │
├─────────────────────────────────────────────┤
│  PREDICTION HISTORY vs ACTUAL                │
│  (table above)                               │
├─────────────────────────────────────────────┤
│  PAPER PORTFOLIO                             │
└─────────────────────────────────────────────┘
```

This maps directly onto the 5-view dashboard already defined in `README.md`
section 11 — the chart is now the default landing surface, with Validation and
Backtest/Robustness reachable as secondary tabs rather than removed.

---

## Bottom line

The feature that actually answers "know the odds it's wrong" isn't a UI
component — it's calibration, prediction intervals, regime-conditional track
record, drift detection, and model disagreement, computed honestly and then
*visibly degrading the display* when they say the model shouldn't be trusted
right now. Build the four components in section 2 before building the chart
polish in section 3 — an honest-looking low-confidence flag on an ugly chart is
worth more than a beautiful chart with a fake confidence number on it.
