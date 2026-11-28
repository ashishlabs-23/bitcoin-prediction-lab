"""
Regression batch 2026-11-29 — lazy heavy dependencies + one barrier resolver.

Covers two P2 cleanups:

1. ``models/_lazy_deps.py``: xgboost (and, in ``models/regime_detector.py``,
   torch) must not be imported just because the API server is imported, and a
   missing wheel must raise a clear ImportError only at first use.
2. ``engine/execution_cost_model.py``: the two duplicate same-bar barrier
   resolvers now share one implementation (``_evaluate_barriers``) exposed
   through two thin, behaviour-preserving views.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.execution_cost_model import (  # noqa: E402
    _evaluate_barriers,
    resolve_barrier_touch,
    simulate_barrier_collision_resolution,
)
from models import _lazy_deps  # noqa: E402


# --------------------------------------------------------------------------- #
# Lazy imports
# --------------------------------------------------------------------------- #
def test_importing_api_server_does_not_load_torch_or_xgboost():
    code = (
        "import sys, api.server\n"
        "print('torch' in sys.modules, 'xgboost' in sys.modules)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().splitlines()[-1] == "False False", proc.stdout


def test_xgb_classifier_raises_clear_import_error_when_missing(monkeypatch):
    _lazy_deps.reset_cache()
    monkeypatch.setitem(sys.modules, "xgboost", None)  # forces ImportError
    try:
        assert _lazy_deps.has_xgboost() is False
        with pytest.raises(ImportError, match="xgboost is not installed"):
            _lazy_deps.xgb_classifier()
    finally:
        monkeypatch.undo()
        _lazy_deps.reset_cache()


def test_xgb_classifier_returns_the_real_class():
    _lazy_deps.reset_cache()
    cls = _lazy_deps.xgb_classifier()
    assert cls.__name__ == "XGBClassifier"
    # Cached: second call is the same object.
    assert _lazy_deps.xgb_classifier() is cls


# --------------------------------------------------------------------------- #
# Barrier resolution
# --------------------------------------------------------------------------- #
LONG = dict(direction="LONG", entry=80000.0, tp=82000.0, sl=79000.0)


@pytest.mark.parametrize(
    "high, low, close, expected",
    [
        (82500.0, 79500.0, 81000.0, "TAKE_PROFIT"),  # TP only
        (80500.0, 78500.0, 79000.0, "STOP_LOSS"),  # SL only
        (82500.0, 78500.0, 80500.0, "STOP_LOSS"),  # collision, conservative
        (80500.0, 79500.0, 80000.0, "TIMEOUT_OR_OPEN"),  # neither
    ],
)
def test_core_outcomes(high, low, close, expected):
    out = _evaluate_barriers(high=high, low=low, close=close, **LONG)
    assert out["outcome"] == expected


def test_collision_is_never_resolved_as_take_profit():
    out = _evaluate_barriers(high=82500.0, low=78500.0, close=80500.0, **LONG)
    assert out["collision"] is True
    assert out["is_ambiguous"] is True
    assert out["conservative_applied"] is True
    assert out["exit_price"] == LONG["sl"]


def test_exclude_ambiguous_policy_flags_and_marks_bar():
    out = _evaluate_barriers(
        high=82500.0, low=78500.0, close=80500.0, policy="EXCLUDE_AMBIGUOUS", **LONG
    )
    assert out["outcome"] == "AMBIGUOUS"
    assert out["conservative_applied"] is False
    assert out["exit_price"] == 80500.0  # bar close mark, not a fabricated win


def test_wrappers_agree_on_outcome_and_exit_price():
    legacy_map = {
        "TAKE_PROFIT": "TP_FIRST",
        "STOP_LOSS": "SL_FIRST",
        "TIMEOUT_OR_OPEN": "NO_TOUCH",
        "AMBIGUOUS": "AMBIGUOUS_COLLISION",
    }
    bars = [(82500.0, 79500.0), (80500.0, 78500.0), (82500.0, 78500.0), (80500.0, 79500.0)]
    for high, low in bars:
        core = _evaluate_barriers(high=high, low=low, close=80000.0, **LONG)
        sim = simulate_barrier_collision_resolution(high=high, low=low, **LONG)
        sig = resolve_barrier_touch(
            entry_price=LONG["entry"],
            direction="LONG",
            tp_price=LONG["tp"],
            sl_price=LONG["sl"],
            bar_high=high,
            bar_low=low,
            bar_close=80000.0,
        )
        assert sim["outcome"] == core["outcome"]
        assert sig["outcome"] == legacy_map[core["outcome"]]
        assert sig["outcome_legacy"] == legacy_map[sim["outcome"]]
        assert sig["exit_price"] == core["exit_price"]


def test_short_direction_barriers_are_mirrored():
    out = _evaluate_barriers(
        direction="SHORT", entry=80000.0, tp=78000.0, sl=81000.0,
        high=80500.0, low=77500.0, close=79000.0,
    )
    assert out["outcome"] == "TAKE_PROFIT"
    out = _evaluate_barriers(
        direction="SHORT", entry=80000.0, tp=78000.0, sl=81000.0,
        high=81500.0, low=79000.0, close=79000.0,
    )
    assert out["outcome"] == "STOP_LOSS"


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError):
        _evaluate_barriers(
            direction="SIDEWAYS", entry=80000.0, tp=82000.0, sl=79000.0,
            high=80500.0, low=79500.0,
        )
