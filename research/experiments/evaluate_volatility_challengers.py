"""
research/experiments/evaluate_volatility_challengers.py
=========================================================
Preregistered evaluation of Bitcoin volatility forecasting models:
1. 168-Hour Horizon (rv7d_var_ann): Persistence, Rolling 30D, HAR-RS-DOW-v1.0, Rolling 720h HAR-RS
2. 24-Hour Horizon (rv24h_var_ann): Persistence, Rolling 30D, HAR-OLS-24H, HAR-QLIKE-24H-v1.0, Rolling 720h HAR-24H

Statistical Standards:
- Loss: Patton (2011) QLIKE loss family & RMSE
- Pairwise: Diebold-Mariano (1995) with Harvey-Leybourne-Newbold (1997) correction, Student's t_{T-1}
- Multi-Model: Hansen, Lunde, Nason (2011) Model Confidence Set (MCS) at alpha = 0.05
- Evaluation: Strictly non-overlapping chronological blocks on 2026 development replay holdout

Harness integrity (E1, 2026-11-28)
----------------------------------
This module was hardened after the research audit of 2026-11-28 found four harness defects:

1. The rolling challengers fitted Ridge on the RAW variance level and emitted the linear
   prediction directly as a variance, without an exp link or any positivity constraint. 35 of
   331 rolling 24H predictions were negative (min = -0.2961); the QLIKE clamp turned each into a
   loss of ~369,061 and inflated the reported mean QLIKE of "Rolling-720h HAR-24H" to 9436.8193.
   All rolling fits now happen in log space, exp() is guarded against overflow, and every forecast
   is floored at `max(pred, 0.05 * rolling_30d_var)`. `ensure_positive_variance()` raises
   ValueError if any forecast is still non-positive or non-finite, so a regression fails loudly.
2. The training window admitted rows whose 24H target matured up to 23h after the forecast origin
   (a target-maturity / look-ahead leak). `causal_window_mask()` now ends every window at
   `idx_ts - embargo_hours` (24h for the 24H contract, 168h for the 168H contract).
3. The emitted report hard-coded the string "SURVIVES (In MCS)" for models that the stored MCS
   computation had eliminated, and hard-coded the evaluation date range. Both are now computed.
4. The persistence fallback was indexed by position rather than by timestamp; it is now a
   timestamp lookup.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Callable, Optional

import numpy as np
import pandas as pd
from scipy import stats
import joblib
from sklearn.linear_model import Ridge

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.har_rs_dow_features import prepare_har_rs_dow_dataset, get_har_rs_dow_features
from engine.har_24h_features import prepare_har_24h_dataset, get_har_24h_feature_matrix
from validation.startup_gate import MODEL_ARTIFACT_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_volatility_challengers")

OHLCV_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
MANIFEST_PATH = os.path.join(REPO_ROOT, "research", "experiments", "manifest_exp_vol_challenger_2026.json")
REPORT_PATH = os.path.join(REPO_ROOT, "research", "reports", "volatility_challenger_evaluation_report.md")
QLIKE_24H_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_qlike_24h_v1.joblib")
OLS_24H_PATH = os.path.join(REPO_ROOT, "experiments", "results", "research_improvement", "har_ols_24h_v1.joblib")

# The committed historical report (research/reports/volatility_challenger_evaluation_report.md) is
# a frozen artifact and must not be silently overwritten by a re-run. Set this environment variable
# to redirect the generated report to a scratch path; the default keeps the legacy behaviour.
REPORT_PATH_ENV = "VOL_CHALLENGER_REPORT_PATH"

# ---------------------------------------------------------------------------
# Forecast admissibility guards (E1 defect 1)
# ---------------------------------------------------------------------------
# Floor as a fraction of the trailing 30-day realized variance: scale-aware and never negative.
MIN_FORECAST_FLOOR_FRACTION = 0.05
# exp(x) overflows float64 around x ~= 709.78; clip the linear predictor well below that.
EXP_LINEAR_CLIP = 700.0
# Any variance strictly below this is treated as non-admissible for a positive target.
MIN_ABSOLUTE_VARIANCE = 1e-12


class NonPositiveForecastError(ValueError):
    """Raised when a variance forecast is non-positive or non-finite after all guards."""


def ensure_positive_variance(
    forecast: Any,
    floor_reference: Any,
    model_name: str = "<unnamed>",
    floor_fraction: float = MIN_FORECAST_FLOOR_FRACTION,
) -> np.ndarray:
    """Return ``forecast`` as a strictly positive, finite variance array.

    ``floor_reference`` is the trailing 30-day realized variance at each forecast origin; the
    admissible floor is ``floor_fraction * floor_reference`` (0.05 by default), matching the
    preregistered guard ``max(pred, 0.05 * rolling_30d_var)``. Negative or zero forecasts are
    raised to the floor; non-finite forecasts (NaN/inf) are treated as harness bugs and raise
    immediately. The guarded array is validated once more, so a future regression cannot silently
    produce a 9436-style QLIKE blow-up.
    """
    pred = np.asarray(forecast, dtype=float).reshape(-1)
    ref = np.asarray(floor_reference, dtype=float).reshape(-1)
    if pred.size == 0:
        raise NonPositiveForecastError(f"{model_name}: empty forecast vector")
    if ref.size == 1:
        ref = np.full(pred.shape, ref[0], dtype=float)
    if ref.shape != pred.shape:
        raise ValueError(
            f"{model_name}: floor reference shape {ref.shape} does not match forecast shape {pred.shape}"
        )

    usable_ref = np.where(np.isfinite(ref) & (ref > 0.0), ref, MIN_ABSOLUTE_VARIANCE)
    floor = np.maximum(floor_fraction * usable_ref, MIN_ABSOLUTE_VARIANCE)

    non_finite = ~np.isfinite(pred)
    if np.any(non_finite):
        first = int(np.argmax(non_finite))
        raise NonPositiveForecastError(
            f"{model_name}: {int(np.sum(non_finite))} non-finite variance forecast(s) before the "
            f"guard (first index {first}, value {pred[first]!r}); refusing to score"
        )
    guarded = np.maximum(pred, floor)

    bad = ~np.isfinite(guarded) | (guarded <= 0.0)
    if np.any(bad):
        first = int(np.argmax(bad))
        raise NonPositiveForecastError(
            f"{model_name}: {int(np.sum(bad))} non-positive/non-finite variance forecast(s) after "
            f"guard (first index {first}, value {guarded[first]!r}); refusing to score"
        )
    return guarded


def validate_positive_variance(forecast: Any, model_name: str = "<unnamed>") -> np.ndarray:
    """Assertion-only variant of :func:`ensure_positive_variance` (no flooring).

    Used for trailing realized-variance benchmarks (persistence, rolling 30D), which are positive
    by construction and must not be modified by a guard: flooring a benchmark would silently move
    the baseline it defines. Any non-positive/non-finite value raises ValueError.
    """
    pred = np.asarray(forecast, dtype=float).reshape(-1)
    bad = ~np.isfinite(pred) | (pred <= 0.0)
    if pred.size == 0 or np.any(bad):
        first = int(np.argmax(bad)) if pred.size else -1
        raise NonPositiveForecastError(
            f"{model_name}: {int(np.sum(bad))} non-positive/non-finite benchmark variance(s) "
            f"(first index {first}); refusing to score"
        )
    return pred


def log_space_variance_fit(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_predict: np.ndarray,
    floor_reference: Any,
    alpha: float = 1.0,
    model_name: str = "<unnamed>",
    floor_fraction: float = MIN_FORECAST_FLOOR_FRACTION,
) -> np.ndarray:
    """Fit Ridge on log-variance (HAR convention) and return admissible positive variances.

    The target is floored at ``MIN_ABSOLUTE_VARIANCE`` before the log transform, the linear
    predictor is clipped to ``[-EXP_LINEAR_CLIP, EXP_LINEAR_CLIP]`` to guard exp() overflow, and
    the exponentiated prediction passes through :func:`ensure_positive_variance`.
    """
    y = np.asarray(y_train, dtype=float)
    y_log = np.log(np.maximum(y, MIN_ABSOLUTE_VARIANCE))
    model = Ridge(alpha=alpha).fit(X_train, y_log)
    linear = np.clip(np.asarray(model.predict(X_predict), dtype=float), -EXP_LINEAR_CLIP, EXP_LINEAR_CLIP)
    return ensure_positive_variance(
        np.exp(linear), floor_reference, model_name=model_name, floor_fraction=floor_fraction
    )


# ---------------------------------------------------------------------------
# Causal training-window helper (E1 defect 2)
# ---------------------------------------------------------------------------
def causal_window_mask(
    index: pd.DatetimeIndex,
    idx_ts: pd.Timestamp,
    window_hours: int = 720,
    embargo_hours: int = 24,
) -> np.ndarray:
    """Boolean mask of training rows usable at forecast origin ``idx_ts``.

    The window is the half-open interval ``(idx_ts - window_hours, idx_ts - embargo_hours)``. ``embargo_hours`` must be at
    least the target horizon: a row stamped ``t`` carries a target computed from returns over
    ``(t, t + horizon]``, so it is only fully observed at ``t + horizon``. With the 24H contract
    the window therefore ends at ``idx_ts - 24h``; admitting rows up to ``idx_ts - 1h`` leaks up to
    23 hours of the evaluation target into the training set.
    """
    index = pd.DatetimeIndex(index)
    lower = idx_ts - pd.Timedelta(hours=window_hours)
    upper = idx_ts - pd.Timedelta(hours=embargo_hours)
    return (index > lower) & (index < upper)


def rolling_predictions(
    df: pd.DataFrame,
    eval_index: pd.DatetimeIndex,
    feature_fn: Callable[[pd.DataFrame], np.ndarray],
    floor_col: str,
    target_col: str,
    fallback_col: str,
    window_hours: int = 720,
    embargo_hours: int = 24,
    min_train_rows: int = 120,
    alpha: float = 1.0,
    model_name: str = "Rolling-720h",
) -> np.ndarray:
    """Expanding-by-window rolling HAR challenger with causal windows and positive forecasts.

    Fits in log space on the training window, falls back (by timestamp, not position) to the
    persistence column when the window is too short, and returns guarded positive variances.
    """
    index = df.index
    preds: List[float] = []
    n_fallback = 0
    for idx_ts in eval_index:
        mask = causal_window_mask(index, idx_ts, window_hours=window_hours, embargo_hours=embargo_hours)
        train_window = df.loc[mask].dropna(subset=[target_col])
        floor_ref = float(df.at[idx_ts, floor_col])
        if len(train_window) >= min_train_rows:
            X_w = feature_fn(train_window)
            y_w = train_window[target_col].values
            X_p = feature_fn(df.loc[[idx_ts]])
            preds.append(
                float(
                    log_space_variance_fit(
                        X_w, y_w, X_p, floor_ref, alpha=alpha, model_name=model_name
                    )[0]
                )
            )
        else:
            n_fallback += 1
            preds.append(float(df.at[idx_ts, fallback_col]))
    if n_fallback:
        logger.info("%s: %d/%d blocks used the persistence fallback", model_name, n_fallback, len(eval_index))
    floor_refs = df.loc[eval_index, floor_col].values.astype(float)
    return ensure_positive_variance(np.array(preds), floor_refs, model_name=model_name)


def qlike_loss(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """Patton (2011) QLIKE loss: L(y, y_hat) = y / y_hat - ln(y / y_hat) - 1 >= 0."""
    eps = 1e-6
    y = np.maximum(y_true, eps)
    y_hat = np.maximum(y_pred, eps)
    ratio = y / y_hat
    return ratio - np.log(ratio) - 1.0


def dm_hln_test(loss_baseline: np.ndarray, loss_challenger: np.ndarray, h: int = 1) -> Dict[str, float]:
    """Diebold-Mariano test with Harvey-Leybourne-Newbold (1997) correction and Student's t_{T-1}."""
    d = loss_baseline - loss_challenger
    T = len(d)
    if T < 5:
        return {"dm_stat": 0.0, "hln_stat": 0.0, "p_value": 1.0, "mean_diff": 0.0}

    d_bar = float(np.mean(d))
    # Autocovariance up to lag h-1 with Bartlett weights
    gamma_0 = float(np.var(d, ddof=0))
    gamma_sum = 0.0
    for k in range(1, h):
        w_k = 1.0 - (k / h)
        cov_k = float(np.mean((d[k:] - d_bar) * (d[:-k] - d_bar)))
        gamma_sum += 2.0 * w_k * cov_k

    lr_var = max(1e-12, (gamma_0 + gamma_sum) / T)
    dm = d_bar / np.sqrt(lr_var)
    hln_factor = np.sqrt(max(0.01, (T + 1 - 2 * h + h * (h - 1) / T) / T))
    hln_stat = float(dm * hln_factor)
    p_val = float(2.0 * (1.0 - stats.t.cdf(abs(hln_stat), df=T - 1)))

    return {
        "dm_stat": round(dm, 4),
        "hln_stat": round(hln_stat, 4),
        "p_value": round(p_val, 4),
        "mean_diff": round(d_bar, 6)
    }


def model_confidence_set(losses_dict: Dict[str, np.ndarray], alpha: float = 0.05, B: int = 500) -> List[str]:
    """
    Hansen, Lunde, Nason (2011) Model Confidence Set (MCS) procedure using T_max statistic.
    Returns the surviving set of superior models at confidence level 1 - alpha.
    """
    model_names = list(losses_dict.keys())
    surviving = list(model_names)
    T = len(next(iter(losses_dict.values())))

    while len(surviving) > 1:
        M = len(surviving)
        loss_matrix = np.column_stack([losses_dict[m] for m in surviving])  # T x M
        d_bar_all = np.zeros((M, M))
        t_stats = np.zeros(M)

        for i in range(M):
            d_i = loss_matrix[:, i:i+1] - loss_matrix  # T x M
            d_bar_i = np.mean(d_i, axis=0)  # M
            var_i = np.var(d_i, axis=0, ddof=1) / T
            var_i = np.maximum(var_i, 1e-12)
            t_ij = d_bar_i / np.sqrt(var_i)
            t_stats[i] = np.max(t_ij)

        t_max = np.max(t_stats)
        worst_idx = np.argmax(t_stats)

        # Stationary bootstrap for p-value
        rng = np.random.default_rng(42)
        boot_max = np.zeros(B)
        centered_loss = loss_matrix - np.mean(loss_matrix, axis=0)

        for b in range(B):
            idx = rng.choice(T, size=T, replace=True)
            boot_mat = centered_loss[idx]
            b_tstats = np.zeros(M)
            for i in range(M):
                b_di = boot_mat[:, i:i+1] - boot_mat
                b_var = np.maximum(np.var(b_di, axis=0, ddof=1) / T, 1e-12)
                b_tstats[i] = np.max(np.mean(b_di, axis=0) / np.sqrt(b_var))
            boot_max[b] = np.max(b_tstats)

        p_val = np.mean(boot_max > t_max)
        if p_val < alpha:
            # Reject worst model
            eliminated = surviving.pop(worst_idx)
            logger.info("MCS eliminated model '%s' (p-val = %.4f < alpha = %.2f)", eliminated, p_val, alpha)
        else:
            break

    return surviving


def mcs_status(model_key: str, mcs: List[str]) -> str:
    """Report cell for a model's 95% Model Confidence Set membership (computed, never hard-coded)."""
    return "**SURVIVES (In MCS)**" if model_key in mcs else "Eliminated"


def render_table(rows: List[Dict[str, Any]], mcs: List[str]) -> str:
    """Render a markdown scorecard where MCS membership comes from the stored MCS result."""
    lines = [
        "| Model Candidate | Model Role | Mean QLIKE | RMSE | MAE | 95% MCS Status |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for r in rows:
        qlike_cell = f"**{r['mean_qlike']:.5f}**" if r.get("emphasis") else f"{r['mean_qlike']:.5f}"
        lines.append(
            f"| **{r['display']}** | {r['role']} | {qlike_cell} | {r['rmse']:.5f} | "
            f"{r['mae']:.5f} | {mcs_status(r['key'], mcs)} |"
        )
    return "\n".join(lines)


def evaluation_span(index: pd.DatetimeIndex, horizon_hours: int) -> Tuple[str, str]:
    """Span of the evaluated blocks (computed from the data, never hard-coded).

    Returns ``(first_issue_timestamp, last_target_maturity)``: the first block's issue timestamp and
    the maturity of the final block's target (last issue + horizon).
    """
    first = pd.Timestamp(index.min())
    last = pd.Timestamp(index.max())
    maturity = last + pd.Timedelta(hours=horizon_hours)
    return first.strftime("%Y-%m-%d"), maturity.strftime("%Y-%m-%d")


def run_experiment() -> Dict[str, Any]:
    logger.info("Loading dataset and models...")
    df_ohlcv = pd.read_parquet(OHLCV_PATH)
    if "timestamp" in df_ohlcv.columns:
        df_ohlcv["timestamp"] = pd.to_datetime(df_ohlcv["timestamp"], utc=True)
        df_ohlcv.set_index("timestamp", inplace=True)
    df_ohlcv.sort_index(inplace=True)

    holdout_start = pd.to_datetime("2026-01-01T00:00:00Z")

    # =========================================================================
    # PART 1: 168-Hour Horizon (rv7d_var_ann) Evaluation
    # =========================================================================
    logger.info("Evaluating 168-Hour Models on Non-Overlapping Blocks...")
    df_168 = prepare_har_rs_dow_dataset(OHLCV_PATH, drop_target_na=True)
    df_168_oos = df_168[df_168.index >= holdout_start].copy()

    # Sample strictly non-overlapping blocks (every 168 hours)
    step_168 = 168
    df_168_eval = df_168_oos.iloc[::step_168].dropna(subset=["rv7d_var_ann"]).copy()
    y_168 = df_168_eval["rv7d_var_ann"].values

    # Models:
    # 1. Persistence: rv7d_var_ann lagged
    pred_persist_168 = df_168_eval["rv7d_var_ann_lag"].values
    # 2. Rolling 30D
    pred_roll30d_168 = df_168_eval["rv30d_var_ann"].values
    # 3. Canonical HAR-RS-DOW-v1.0 (Frozen)
    pipe_canonical = joblib.load(MODEL_ARTIFACT_PATH)
    X_168 = get_har_rs_dow_features(df_168_eval)
    pred_canonical = np.exp(np.clip(pipe_canonical.predict(X_168), -EXP_LINEAR_CLIP, EXP_LINEAR_CLIP))
    # 4. Rolling-720h OLS HAR-RS Challenger (log-space fit, causal window ending at idx_ts - 168h)
    pred_rolling_168 = rolling_predictions(
        df_168,
        df_168_eval.index,
        feature_fn=get_har_rs_dow_features,
        floor_col="rv30d_var_ann",
        target_col="rv7d_var_ann",
        fallback_col="rv7d_var_ann_lag",
        window_hours=720,
        embargo_hours=168,
        min_train_rows=168,
        alpha=10.0,
        model_name="Rolling-720h HAR-RS (Challenger)",
    )

    floor_168 = df_168_eval["rv30d_var_ann"].values
    models_168 = {
        "Persistence (168h)": validate_positive_variance(pred_persist_168, "Persistence (168h)"),
        "Rolling 30D (168h)": validate_positive_variance(pred_roll30d_168, "Rolling 30D (168h)"),
        "HAR-RS-DOW-v1.0 (Canonical)": ensure_positive_variance(pred_canonical, floor_168, "HAR-RS-DOW-v1.0"),
        "Rolling-720h HAR-RS (Challenger)": pred_rolling_168
    }

    losses_qlike_168 = {m: qlike_loss(y_168, pred) for m, pred in models_168.items()}
    losses_rmse_168 = {m: float(np.sqrt(np.mean((y_168 - pred)**2))) for m, pred in models_168.items()}
    losses_mae_168 = {m: float(np.mean(np.abs(y_168 - pred))) for m, pred in models_168.items()}
    mean_qlike_168 = {m: float(np.mean(loss)) for m, loss in losses_qlike_168.items()}

    mcs_168 = model_confidence_set(losses_qlike_168, alpha=0.05)
    dm_canon_vs_persist = dm_hln_test(losses_qlike_168["Persistence (168h)"], losses_qlike_168["HAR-RS-DOW-v1.0 (Canonical)"], h=1)
    dm_roll_vs_canon = dm_hln_test(losses_qlike_168["HAR-RS-DOW-v1.0 (Canonical)"], losses_qlike_168["Rolling-720h HAR-RS (Challenger)"], h=1)

    # =========================================================================
    # PART 2: 24-Hour Horizon (rv24h_var_ann) Evaluation
    # =========================================================================
    logger.info("Evaluating 24-Hour Models on Non-Overlapping Blocks...")
    df_24 = prepare_har_24h_dataset(df_ohlcv, dropna=True)
    df_24_oos = df_24[df_24.index >= holdout_start].copy()

    # Sample strictly non-overlapping blocks (every 24 hours)
    step_24 = 24
    df_24_eval = df_24_oos.iloc[::step_24].dropna(subset=["rv24h_var_ann"]).copy()
    y_24 = df_24_eval["rv24h_var_ann"].values

    pred_persist_24 = df_24_eval["rv1d_var_ann"].values
    pred_roll30d_24 = df_24_eval["rv30d_var_ann"].values

    m_ols_24 = joblib.load(OLS_24H_PATH)
    m_qlike_24 = joblib.load(QLIKE_24H_PATH)
    X_24_eval, _ = get_har_24h_feature_matrix(df_24_eval)
    # NOTE: both stored artifacts carry their own inverse link and emit variances directly
    # (ConventionalHAR24H / HARQLIKE24HChallenger); they must NOT be exponentiated here.
    pred_ols_24 = m_ols_24.predict(X_24_eval)
    pred_qlike_24 = m_qlike_24.predict(X_24_eval)

    # Rolling-720h OLS HAR 24h candidate (log-space fit, causal window ending at idx_ts - 24h)
    pred_rolling_24 = rolling_predictions(
        df_24,
        df_24_eval.index,
        feature_fn=lambda d: get_har_24h_feature_matrix(d)[0],
        floor_col="rv30d_var_ann",
        target_col="rv24h_var_ann",
        fallback_col="rv1d_var_ann",
        window_hours=720,
        embargo_hours=24,
        min_train_rows=120,
        alpha=1.0,
        model_name="Rolling-720h HAR-24H (Challenger)",
    )

    floor_24 = df_24_eval["rv30d_var_ann"].values
    models_24 = {
        "Persistence (24h)": validate_positive_variance(pred_persist_24, "Persistence (24h)"),
        "Rolling 30D (24h)": validate_positive_variance(pred_roll30d_24, "Rolling 30D (24h)"),
        "HAR-OLS-24H (Conventional)": ensure_positive_variance(pred_ols_24, floor_24, "HAR-OLS-24H"),
        "HAR-QLIKE-24H-v1.0 (Challenger)": ensure_positive_variance(pred_qlike_24, floor_24, "HAR-QLIKE-24H"),
        "Rolling-720h HAR-24H (Challenger)": pred_rolling_24
    }

    losses_qlike_24 = {m: qlike_loss(y_24, pred) for m, pred in models_24.items()}
    losses_rmse_24 = {m: float(np.sqrt(np.mean((y_24 - pred)**2))) for m, pred in models_24.items()}
    losses_mae_24 = {m: float(np.mean(np.abs(y_24 - pred))) for m, pred in models_24.items()}
    mean_qlike_24 = {m: float(np.mean(loss)) for m, loss in losses_qlike_24.items()}

    mcs_24 = model_confidence_set(losses_qlike_24, alpha=0.05)
    dm_qlike_vs_ols_24 = dm_hln_test(losses_qlike_24["HAR-OLS-24H (Conventional)"], losses_qlike_24["HAR-QLIKE-24H-v1.0 (Challenger)"], h=1)
    dm_roll_vs_ols_24 = dm_hln_test(losses_qlike_24["HAR-OLS-24H (Conventional)"], losses_qlike_24["Rolling-720h HAR-24H (Challenger)"], h=1)
    dm_roll_vs_persist_24 = dm_hln_test(losses_qlike_24["Persistence (24h)"], losses_qlike_24["Rolling-720h HAR-24H (Challenger)"], h=1)
    dm_qlike_vs_persist_24 = dm_hln_test(losses_qlike_24["Persistence (24h)"], losses_qlike_24["HAR-QLIKE-24H-v1.0 (Challenger)"], h=1)

    span_168_start, span_168_end = evaluation_span(df_168_eval.index, 168)
    span_24_start, span_24_end = evaluation_span(df_24_eval.index, 24)

    rows_168 = [
        {"key": "HAR-RS-DOW-v1.0 (Canonical)", "display": "HAR-RS-DOW-v1.0", "role": "Canonical Production Baseline",
         "mean_qlike": mean_qlike_168["HAR-RS-DOW-v1.0 (Canonical)"], "rmse": losses_rmse_168["HAR-RS-DOW-v1.0 (Canonical)"],
         "mae": losses_mae_168["HAR-RS-DOW-v1.0 (Canonical)"], "emphasis": True},
        {"key": "Rolling-720h HAR-RS (Challenger)", "display": "Rolling-720h HAR-RS", "role": "Research Challenger",
         "mean_qlike": mean_qlike_168["Rolling-720h HAR-RS (Challenger)"], "rmse": losses_rmse_168["Rolling-720h HAR-RS (Challenger)"],
         "mae": losses_mae_168["Rolling-720h HAR-RS (Challenger)"]},
        {"key": "Persistence (168h)", "display": "Persistence (168h)", "role": "Naive Baseline",
         "mean_qlike": mean_qlike_168["Persistence (168h)"], "rmse": losses_rmse_168["Persistence (168h)"],
         "mae": losses_mae_168["Persistence (168h)"]},
        {"key": "Rolling 30D (168h)", "display": "Rolling 30D (168h)", "role": "Naive Benchmark",
         "mean_qlike": mean_qlike_168["Rolling 30D (168h)"], "rmse": losses_rmse_168["Rolling 30D (168h)"],
         "mae": losses_mae_168["Rolling 30D (168h)"]},
    ]
    rows_24 = [
        {"key": "HAR-QLIKE-24H-v1.0 (Challenger)", "display": "HAR-QLIKE-24H-v1.0", "role": "Research Challenger",
         "mean_qlike": mean_qlike_24["HAR-QLIKE-24H-v1.0 (Challenger)"], "rmse": losses_rmse_24["HAR-QLIKE-24H-v1.0 (Challenger)"],
         "mae": losses_mae_24["HAR-QLIKE-24H-v1.0 (Challenger)"], "emphasis": True},
        {"key": "HAR-OLS-24H (Conventional)", "display": "HAR-OLS-24H", "role": "Conventional Baseline",
         "mean_qlike": mean_qlike_24["HAR-OLS-24H (Conventional)"], "rmse": losses_rmse_24["HAR-OLS-24H (Conventional)"],
         "mae": losses_mae_24["HAR-OLS-24H (Conventional)"]},
        {"key": "Rolling-720h HAR-24H (Challenger)", "display": "Rolling-720h HAR-24H", "role": "Research Challenger",
         "mean_qlike": mean_qlike_24["Rolling-720h HAR-24H (Challenger)"], "rmse": losses_rmse_24["Rolling-720h HAR-24H (Challenger)"],
         "mae": losses_mae_24["Rolling-720h HAR-24H (Challenger)"]},
        {"key": "Persistence (24h)", "display": "Persistence (24h)", "role": "Naive Baseline",
         "mean_qlike": mean_qlike_24["Persistence (24h)"], "rmse": losses_rmse_24["Persistence (24h)"],
         "mae": losses_mae_24["Persistence (24h)"]},
        {"key": "Rolling 30D (24h)", "display": "Rolling 30D (24h)", "role": "Naive Benchmark",
         "mean_qlike": mean_qlike_24["Rolling 30D (24h)"], "rmse": losses_rmse_24["Rolling 30D (24h)"],
         "mae": losses_mae_24["Rolling 30D (24h)"]},
    ]

    qlike_in_mcs_24 = "HAR-QLIKE-24H-v1.0 (Challenger)" in mcs_24
    qlike_mcs_phrase = (
        "It is retained in the 95% Model Confidence Set."
        if qlike_in_mcs_24
        else "It is **not** retained in the 95% Model Confidence Set."
    )

    # =========================================================================
    # PART 3: Format and Save Structured Research Report
    # =========================================================================
    report = f"""# BTCognitive — Quantitative Research & Challenger Evaluation Report

**Experiment ID:** EXP-VOL-CHALLENGER-2026-01  
**Execution Date:** {datetime.now(timezone.utc).isoformat()}  
**Epistemic Standard:** Development Replay Holdout (Non-Overlapping Blocks) + Pre-Registered Prospective Challengers  
**Primary Loss Metric:** Patton (2011) Homogeneous Bregman QLIKE Loss  
**Harness:** causal training windows (24H window ends at `idx_ts - 24h`, 168H at `idx_ts - 168h`); log-space fits with positivity guard `max(pred, 0.05 * rolling_30d_var)`  

---

## 1. Executive Summary & Epistemic Boundary
This report executes the preregistered research experiment evaluating candidate volatility forecasting models against frozen baselines across two decoupled horizons:
1. **168-Hour Horizon (Annualized 7-Day Realized Variance, `rv7d_var_ann`):** N = {len(y_168)} non-overlapping 7-day blocks.
2. **24-Hour Horizon (Annualized 24-Hour Realized Variance Proxy, `rv24h_var_ann`):** N = {len(y_24)} non-overlapping 1-day blocks.

**Key Findings:**
- **168H Canonical Baseline (`HAR-RS-DOW-v1.0`):** QLIKE {mean_qlike_168['HAR-RS-DOW-v1.0 (Canonical)']:.5f} vs persistence {mean_qlike_168['Persistence (168h)']:.5f} (HLN t-stat = {dm_canon_vs_persist['hln_stat']}, p = {dm_canon_vs_persist['p_value']}); {"retained in" if "HAR-RS-DOW-v1.0 (Canonical)" in mcs_168 else "not retained in"} the 95% Model Confidence Set.
- **24H QLIKE Challenger (`HAR-QLIKE-24H-v1.0`):** QLIKE {mean_qlike_24['HAR-QLIKE-24H-v1.0 (Challenger)']:.5f} vs conventional OLS-HAR {mean_qlike_24['HAR-OLS-24H (Conventional)']:.5f} (HLN t-stat = {dm_qlike_vs_ols_24['hln_stat']}, p = {dm_qlike_vs_ols_24['p_value']}). {qlike_mcs_phrase}
- **24H Rolling-720h Challenger:** QLIKE {mean_qlike_24['Rolling-720h HAR-24H (Challenger)']:.5f} vs persistence {mean_qlike_24['Persistence (24h)']:.5f} (HLN = {dm_roll_vs_persist_24['hln_stat']}, p = {dm_roll_vs_persist_24['p_value']}); {"retained in" if "Rolling-720h HAR-24H (Challenger)" in mcs_24 else "eliminated from"} the 95% Model Confidence Set.
- **Confirmatory Research Boundary:** Because this dataset represents historical development replay, no challenger is granted automatic production authorization. All challengers remain `OFFLINE_RESEARCH_ONLY` pending $\\ge 100$ clean prospective blocks in the append-only ledger.

---

## 2. 168-Hour Horizon Evaluation (`rv7d_var_ann`)

**Dataset:** {len(y_168)} strictly non-overlapping 168-hour blocks (issue timestamps {span_168_start} to {span_168_end} where the end date is the last target's maturity).

{render_table(rows_168, mcs_168)}

### Statistical Comparison:
- **HAR-RS-DOW-v1.0 vs. Persistence:** HLN = {dm_canon_vs_persist['hln_stat']}, p-value = {dm_canon_vs_persist['p_value']}, Mean Diff = {dm_canon_vs_persist['mean_diff']}
- **Rolling-720h vs. HAR-RS-DOW-v1.0:** HLN = {dm_roll_vs_canon['hln_stat']}, p-value = {dm_roll_vs_canon['p_value']}, Mean Diff = {dm_roll_vs_canon['mean_diff']}
- **95% Model Confidence Set:** {mcs_168}

---

## 3. 24-Hour Horizon Evaluation (`rv24h_var_ann`)

**Dataset:** {len(y_24)} strictly non-overlapping 24-hour blocks (issue timestamps {span_24_start} to {span_24_end} where the end date is the last target's maturity).

{render_table(rows_24, mcs_24)}

### Statistical Comparison:
- **HAR-QLIKE-24H vs. HAR-OLS-24H:** HLN = {dm_qlike_vs_ols_24['hln_stat']}, p-value = {dm_qlike_vs_ols_24['p_value']}, Mean Diff = {dm_qlike_vs_ols_24['mean_diff']}
- **Rolling-720h vs. HAR-OLS-24H:** HLN = {dm_roll_vs_ols_24['hln_stat']}, p-value = {dm_roll_vs_ols_24['p_value']}, Mean Diff = {dm_roll_vs_ols_24['mean_diff']}
- **Rolling-720h vs. Persistence (24h):** HLN = {dm_roll_vs_persist_24['hln_stat']}, p-value = {dm_roll_vs_persist_24['p_value']}, Mean Diff = {dm_roll_vs_persist_24['mean_diff']}
- **HAR-QLIKE-24H vs. Persistence (24h):** HLN = {dm_qlike_vs_persist_24['hln_stat']}, p-value = {dm_qlike_vs_persist_24['p_value']}, Mean Diff = {dm_qlike_vs_persist_24['mean_diff']}
- **95% Model Confidence Set:** {mcs_24}

---

## 4. Governed Governance Verdict
1. **Canonical Production Model:** `HAR-RS-DOW-v1.0` remains the sole authorized production model for 168-hour volatility risk.
2. **Challenger Models:** `HAR-QLIKE-24H-v1.0`, `Rolling-720h HAR-RS` and `Rolling-720h HAR-24H` remain strictly `OFFLINE_RESEARCH_ONLY`.
3. **Prospective Hurdle:** Confirmatory evaluation requires accumulation of >= 100 clean non-overlapping blocks in `data/prospective_forecast_ledger.jsonl`.
"""

    report_path = os.environ.get(REPORT_PATH_ENV) or REPORT_PATH
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("Evaluation report successfully written to: %s", report_path)
    print(report)

    return {
        "n_168": len(y_168),
        "n_24": len(y_24),
        "mean_qlike_168": mean_qlike_168,
        "mean_qlike_24": mean_qlike_24,
        "mcs_168": mcs_168,
        "mcs_24": mcs_24,
        "dm_qlike_vs_ols_24": dm_qlike_vs_ols_24,
        "dm_roll_vs_persist_24": dm_roll_vs_persist_24,
        "dm_qlike_vs_persist_24": dm_qlike_vs_persist_24,
        "report_path": report_path,
    }


if __name__ == "__main__":
    run_experiment()
