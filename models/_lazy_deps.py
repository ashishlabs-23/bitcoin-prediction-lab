"""
models/_lazy_deps.py — Lazily imported optional heavy dependencies
==================================================================
xgboost and torch cost seconds of import time and hundreds of MB of RSS, and
neither is needed to serve the API: xgboost is only touched when an ensemble is
actually fitted, and torch only when a neural refinement path runs.

Importing them at module scope made `import api.server` pay for both, and made
the whole application fail to start when either wheel was missing. These
helpers defer the import to first use and cache the outcome (success or the
ImportError) so a missing package degrades one code path instead of the process.
"""

from typing import Any, Dict, Optional

__all__ = ["xgb_classifier", "has_xgboost", "reset_cache"]

_XGB: Dict[str, Any] = {"loaded": False, "cls": Optional[type], "error": Optional[BaseException]}
_XGB.update({"cls": None, "error": None})


def xgb_classifier() -> type:
    """Return ``xgboost.XGBClassifier``, importing xgboost on first use.

    Raises:
        ImportError: when xgboost is not installed. The original exception is
            chained so the caller can see the real reason.
    """
    state = _XGB
    if not state["loaded"]:
        try:
            from xgboost import XGBClassifier

            state.update(loaded=True, cls=XGBClassifier, error=None)
        except ImportError as exc:  # pragma: no cover - depends on the environment
            state.update(loaded=True, cls=None, error=exc)
    if state["cls"] is None:
        raise ImportError("xgboost is not installed in this environment") from state["error"]
    return state["cls"]


def has_xgboost() -> bool:
    """True when xgboost can be imported (cheap after the first call)."""
    try:
        xgb_classifier()
        return True
    except ImportError:
        return False


def reset_cache() -> None:
    """Forget cached import outcomes (used by tests)."""
    _XGB.update(loaded=False, cls=None, error=None)
