"""
tests/test_volatility_harness_guards_2026_11_28.py
==================================================
Red-team regression suite for the volatility challenger evaluation harness (E1, 2026-11-28).

The 2026-11-28 audit of `research/experiments/evaluate_volatility_challengers.py` found:

1. The rolling challengers fitted Ridge on the RAW variance level and emitted the linear
   prediction as a variance with no exp link / positivity constraint. 35 of 331 rolling 24H
   predictions were negative (min -0.2961); the QLIKE clamp converted each into a loss of
   ~369,061, inflating the reported mean QLIKE of "Rolling-720h HAR-24H" to 9436.8193.
2. The training window admitted rows whose 24H target matured up to 23h after the forecast
   origin, leaking future returns into the fit.
3. The emitted markdown report hard-coded "SURVIVES (In MCS)" for models the stored MCS had
   eliminated, and hard-coded the evaluation date range.
4. The persistence fallback was indexed by position, not timestamp.

Each test below pins one of those fixes so a regression fails loudly instead of silently
producing a 9436-style QLIKE.
"""

import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.experiments import evaluate_volatility_challengers as ev  # noqa: E402

EVALUATOR_PATH = PROJECT_ROOT / "research" / "experiments" / "evaluate_volatility_challengers.py"
OHLCV_PATH = PROJECT_ROOT / "data" / "raw" / "ohlcv.parquet"


# ---------------------------------------------------------------------------
# Defect 1: negative / non-finite variance forecasts must be impossible to score
# ---------------------------------------------------------------------------
class TestPositiveVarianceGuard:
    def test_negative_forecasts_are_floored_at_scale_aware_value(self):
        pred = np.array([-0.2961, -1e-6, 0.0, 0.5])
        ref = np.array([0.25, 0.25, 0.25, 0.25])
        out = ev.ensure_positive_variance(pred, ref, "unit")
        assert np.all(np.isfinite(out))
        assert np.all(out > 0)
        assert out[0] == pytest.approx(0.05 * 0.25)
        assert out[3] == pytest.approx(0.5)  # admissible forecasts pass through untouched

    def test_floor_is_scale_aware_not_global(self):
        pred = np.array([-1.0, -1.0])
        ref = np.array([0.04, 4.0])
        out = ev.ensure_positive_variance(pred, ref, "unit")
        assert out[0] == pytest.approx(0.002)
        assert out[1] == pytest.approx(0.2)

    def test_scalar_floor_reference_is_broadcast(self):
        out = ev.ensure_positive_variance(np.array([-1.0, -2.0]), 0.3, "unit")
        assert out == pytest.approx(np.array([0.015, 0.015]))

    def test_shape_mismatch_is_rejected(self):
        with pytest.raises(ValueError):
            ev.ensure_positive_variance(np.array([1.0, 2.0]), np.array([0.1, 0.2, 0.3]), "unit")

    def test_non_finite_forecast_raises(self):
        for bad in (np.nan, np.inf, -np.inf):
            with pytest.raises(ValueError):
                ev.ensure_positive_variance(np.array([0.2, bad]), 0.2, "unit")

    def test_empty_forecast_raises(self):
        with pytest.raises(ValueError):
            ev.ensure_positive_variance(np.array([]), 0.2, "unit")

    def test_post_guard_assertion_path_raises(self, monkeypatch):
        """With no floor at all a non-positive forecast must raise, not score."""
        monkeypatch.setattr(ev, "MIN_ABSOLUTE_VARIANCE", 0.0)
        with pytest.raises(ValueError):
            ev.ensure_positive_variance(np.array([-1.0]), 0.2, "unit", floor_fraction=0.0)

    def test_reproduction_fixture_negative_prediction_explodes_qlike_without_guard(self):
        """The audit's failure mode: one negative variance -> a ~369,061 QLIKE loss."""
        y = np.array([0.2, 0.3, 0.1])
        raw = np.array([0.2, -0.2961, 0.1])
        unguarded = ev.qlike_loss(y, raw)
        assert unguarded[1] > 1e5  # y / 1e-6 - ln(...) - 1 ~ 369,061
        guarded = ev.ensure_positive_variance(raw, 0.25, "unit")
        assert np.all(ev.qlike_loss(y, guarded) < 50.0)

    def test_log_space_fit_never_returns_non_positive_and_survives_overflow(self):
        rng = np.random.default_rng(0)
        X_train = rng.normal(size=(50, 3))
        y_train = np.exp(2.0 * X_train[:, 0])  # wide dynamic range, all positive
        X_predict = rng.normal(size=(7, 3)) * 50.0  # deliberately extreme extrapolation
        out = ev.log_space_variance_fit(X_train, y_train, X_predict, 0.2, alpha=1.0, model_name="unit")
        assert np.all(np.isfinite(out))
        assert np.all(out > 0)

    def test_log_space_fit_handles_zero_target_rows(self):
        X_train = np.ones((10, 1))
        y_train = np.array([0.0, 0.0, 0.1, 0.2, 0.1, 0.3, 0.2, 0.1, 0.2, 0.3])
        out = ev.log_space_variance_fit(X_train, y_train, np.ones((1, 1)), 0.25, model_name="unit")
        assert np.all(np.isfinite(out)) and np.all(out > 0)

    def test_benchmark_validator_does_not_move_the_baseline(self):
        pred = np.array([0.001, 0.2])
        out = ev.validate_positive_variance(pred, "Persistence")
        assert out == pytest.approx(pred)  # no flooring: the benchmark stays where it was
        with pytest.raises(ValueError):
            ev.validate_positive_variance(np.array([0.1, 0.0]), "Persistence")


# ---------------------------------------------------------------------------
# Defect 2: target-maturity (look-ahead) leak in the rolling training window
# ---------------------------------------------------------------------------
def _hourly_index(n: int = 1200, start: str = "2026-03-01T00:00:00Z") -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=n, freq="h")


class TestCausalWindow:
    def test_window_ends_at_idx_ts_minus_horizon(self):
        idx = _hourly_index(400)
        idx_ts = idx[300]
        mask = ev.causal_window_mask(idx, idx_ts, window_hours=720, embargo_hours=24)
        selected = idx[mask]
        assert len(selected) > 0
        # No training row may carry a target that matures after the forecast origin.
        assert selected.max() < idx_ts - pd.Timedelta(hours=24)
        assert selected.min() > idx_ts - pd.Timedelta(hours=720)
        # Nothing at or after the origin is ever admitted.
        assert selected.max() < idx_ts

    def test_leaky_mask_would_admit_unmatured_targets(self):
        idx = _hourly_index(400)
        idx_ts = idx[300]
        leaky = ev.causal_window_mask(idx, idx_ts, window_hours=720, embargo_hours=0)
        leaking_rows = idx[leaky]
        immmature = [t for t in leaking_rows if t + pd.Timedelta(hours=24) > idx_ts]
        assert len(immmature) == 23  # rows t-23h .. t-1h leak 1..23h of the evaluation target

    def test_168h_contract_uses_168h_embargo(self):
        idx = _hourly_index(1200)
        idx_ts = idx[1000]
        mask = ev.causal_window_mask(idx, idx_ts, window_hours=720, embargo_hours=168)
        assert idx[mask].max() < idx_ts - pd.Timedelta(hours=168)


def _synthetic_df_with_target_spike(n: int = 900, idx_pos: int = 800) -> pd.DataFrame:
    """Intercept-only HAR dataset where the evaluation target is a volatility spike.

    Rows ``idx_pos-23 .. idx_pos-1`` carry the same forward window as the evaluation target
    (5.0), so a window that ends at ``idx_ts - 1h`` sees the spike in-sample; a window ending at
    ``idx_ts - 24h`` cannot.
    """
    idx = _hourly_index(n)
    target = np.full(n, 0.1)
    target[idx_pos - 23:idx_pos] = 5.0
    target[idx_pos] = 5.0
    df = pd.DataFrame(
        {
            "rv24h_var_ann": target,
            "rv1d_var_ann": np.full(n, 0.1),
            "rv30d_var_ann": np.full(n, 0.1),
            "const": np.ones(n),
        },
        index=idx,
    )
    return df


class TestLeakClosureRegression:
    def test_shifting_window_end_by_24h_changes_the_score(self):
        df = _synthetic_df_with_target_spike()
        eval_index = df.index[[700, 800, 850]]
        feature_fn = lambda d: d[["const"]].values  # noqa: E731

        leaky = ev.rolling_predictions(
            df, eval_index, feature_fn, floor_col="rv30d_var_ann",
            target_col="rv24h_var_ann", fallback_col="rv1d_var_ann",
            window_hours=720, embargo_hours=0, min_train_rows=10, model_name="leaky",
        )
        causal = ev.rolling_predictions(
            df, eval_index, feature_fn, floor_col="rv30d_var_ann",
            target_col="rv24h_var_ann", fallback_col="rv1d_var_ann",
            window_hours=720, embargo_hours=24, min_train_rows=10, model_name="causal",
        )

        y = df.loc[eval_index, "rv24h_var_ann"].values
        leaky_q = float(np.mean(ev.qlike_loss(y, leaky)))
        causal_q = float(np.mean(ev.qlike_loss(y, causal)))

        assert not np.allclose(leaky, causal), "shifting the window end by 24h must change predictions"
        assert abs(leaky_q - causal_q) > 1e-3, "shifting the window end by 24h must change the score"
        # The leak flatters the challenger: in-sample access to the spike lowers its loss.
        assert leaky_q < causal_q
        assert causal[1] == pytest.approx(0.1)  # causal window never sees the 5.0 spike

    def test_default_embargo_matches_the_24h_horizon(self):
        import inspect

        sig = inspect.signature(ev.rolling_predictions)
        assert sig.parameters["embargo_hours"].default == 24


# ---------------------------------------------------------------------------
# Defect 4: persistence fallback must be a timestamp lookup
# ---------------------------------------------------------------------------
class TestFallbackIndexing:
    def test_fallback_is_indexed_by_timestamp(self):
        df = _synthetic_df_with_target_spike()
        df["rv1d_var_ann"] = np.arange(len(df)) / 1000.0 + 0.01  # unique persistence per row
        eval_index = df.index[[10, 400, 899]]
        # min_train_rows above the window size forces the fallback path on every block.
        preds = ev.rolling_predictions(
            df, eval_index, lambda d: d[["const"]].values, floor_col="rv30d_var_ann",
            target_col="rv24h_var_ann", fallback_col="rv1d_var_ann",
            window_hours=720, embargo_hours=24, min_train_rows=10_000, model_name="fallback",
        )
        assert preds == pytest.approx(df.loc[eval_index, "rv1d_var_ann"].values)

    def test_eval_index_not_starting_at_zero_still_maps_correctly(self):
        """The old positional fallback (`pred_persist_24[len(preds)]`) is only right if the
        evaluation index starts at row 0 of the persistence vector; here it does not."""
        df = _synthetic_df_with_target_spike()
        df["rv1d_var_ann"] = np.linspace(0.05, 0.5, len(df))
        eval_index = df.index[[500, 501, 600]]
        preds = ev.rolling_predictions(
            df, eval_index, lambda d: d[["const"]].values, floor_col="rv30d_var_ann",
            target_col="rv24h_var_ann", fallback_col="rv1d_var_ann",
            window_hours=720, embargo_hours=24, min_train_rows=10_000, model_name="fallback",
        )
        positional = df["rv1d_var_ann"].values[: len(eval_index)]
        assert not np.allclose(preds, positional)


# ---------------------------------------------------------------------------
# Defect 3: MCS status and date ranges must be computed, never hard-coded
# ---------------------------------------------------------------------------
class TestComputedReportFields:
    def test_mcs_status_reflects_the_stored_mcs_result(self):
        mcs = ["HAR-OLS-24H (Conventional)", "HAR-QLIKE-24H-v1.0 (Challenger)"]
        assert "SURVIVES" in ev.mcs_status("HAR-QLIKE-24H-v1.0 (Challenger)", mcs)
        assert ev.mcs_status("Rolling-720h HAR-24H (Challenger)", mcs) == "Eliminated"

    def test_render_table_marks_eliminated_models(self):
        rows = [
            {"key": "A", "display": "A", "role": "r", "mean_qlike": 0.1, "rmse": 0.1, "mae": 0.1},
            {"key": "B", "display": "B", "role": "r", "mean_qlike": 9.0, "rmse": 1.0, "mae": 1.0},
        ]
        table = ev.render_table(rows, ["A"])
        line_a = next(l for l in table.splitlines() if "| **A** |" in l)
        line_b = next(l for l in table.splitlines() if "| **B** |" in l)
        assert "SURVIVES (In MCS)" in line_a
        assert "Eliminated" in line_b

    def test_evaluation_span_is_derived_from_the_data(self):
        idx = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-11-28T00:00:00Z"])
        start, end = ev.evaluation_span(idx, 24)
        assert start == "2026-01-01"
        assert end == "2026-11-29"  # last issue + 24h target maturity

    def test_source_has_no_hard_coded_mcs_strings_or_date_ranges(self):
        src = EVALUATOR_PATH.read_text(encoding="utf-8")
        code = src.split('"""', 2)[2]  # drop the module docstring, which quotes the audit finding
        assert code.count("SURVIVES (In MCS)") == 1, "the MCS string may only exist inside mcs_status()"
        assert "2026-10-16" not in src, "evaluation date range must be computed, not hard-coded"
        mcs_fn = code.split("def mcs_status")[1].split("def render_table")[0]
        assert "SURVIVES (In MCS)" in mcs_fn and "Eliminated" in mcs_fn

    def test_report_template_cells_come_from_render_table(self):
        src = EVALUATOR_PATH.read_text(encoding="utf-8")
        report_block = src.split('report = f"""', 1)[1]
        assert "{render_table(rows_168, mcs_168)}" in report_block
        assert "{render_table(rows_24, mcs_24)}" in report_block


# ---------------------------------------------------------------------------
# End-to-end harness reproduction on the committed dataset
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not OHLCV_PATH.exists(), reason="OHLCV dataset not available")
class TestEndToEndHarness:
    def test_rerun_scores_finite_and_rolling_challenger_loses_to_persistence(self, tmp_path, monkeypatch):
        out_path = tmp_path / "report.md"
        monkeypatch.setenv(ev.REPORT_PATH_ENV, str(out_path))
        results = ev.run_experiment()

        report = out_path.read_text(encoding="utf-8")
        assert out_path.exists()
        # No 9436-style blow-up survives anywhere in the 24H scorecard.
        q24 = results["mean_qlike_24"]
        assert all(np.isfinite(v) and v < 50.0 for v in q24.values())
        rolling = q24["Rolling-720h HAR-24H (Challenger)"]
        persistence = q24["Persistence (24h)"]
        assert rolling == pytest.approx(0.95567, abs=5e-3)
        assert persistence == pytest.approx(0.81175, abs=5e-3)
        assert rolling > persistence, "Rolling-720h HAR-24H must remain worse than persistence"
        # The QLIKE challenger's headline numbers are unchanged by the harness fix.
        assert q24["HAR-QLIKE-24H-v1.0 (Challenger)"] == pytest.approx(0.33920, abs=5e-3)
        assert q24["HAR-OLS-24H (Conventional)"] == pytest.approx(0.41537, abs=5e-3)
        # Every "SURVIVES" claim in the emitted report is backed by the stored MCS.
        assert "SURVIVES" in report
        for model in results["mcs_24"]:
            assert model in report
