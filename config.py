"""
Global configuration shim for bitcoin-prediction-lab.

Fix (2026-11-28):
    This module and the ``config/`` package shared one importable name, and the
    package's docstring claimed that ``from config import RESULTS_DIR`` worked
    "because config.py re-exports from here". It did not: this module defined
    its own *CWD-relative* strings ("experiments/results", "data/raw") while
    ``config/paths.py`` defines *absolute* paths rooted at the project. The same
    name therefore resolved to two different directories depending on which
    object the interpreter picked.

    This module now derives the same absolute paths as ``config/paths.py``, so
    both import routes agree, and it warns so callers migrate to
    ``config.paths``. The collision itself (module vs package) is still latent
    -- rename this file to ``legacy_config.py`` when call sites are migrated.
"""

from __future__ import annotations

import os
import warnings

warnings.warn(
    "The root-level 'config' module is deprecated and collides with the 'config/' "
    "package. Import from 'config.paths' (paths) or 'config.security' (security).",
    DeprecationWarning,
    stacklevel=2,
)

PROJECT_ROOT: str = os.path.abspath(os.path.dirname(__file__))
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")
DATA_RAW_DIR: str = os.path.join(DATA_DIR, "raw")
DATA_PROCESSED_DIR: str = os.path.join(DATA_DIR, "processed")
RESULTS_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "results")
LOGS_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "logs")
MODEL_REGISTRY_DIR: str = os.path.join(PROJECT_ROOT, "models", "checkpoints")
GENOME_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "genome")

SYMBOL: str = "BTC/USD"
EXCHANGE: str = "binance"
TIMEFRAME: str = "1h"
DATA_START: str = "2022-01-01T00:00:00Z"
