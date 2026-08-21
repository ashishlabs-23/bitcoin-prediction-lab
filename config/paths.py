"""
config/paths.py — Canonical Filesystem Paths for BTCognitive
=============================================================
Single source of truth for all project path constants.
All production, research, and engine modules must import from here.
Do NOT redefine these paths locally in individual scripts.

Backwards-compatible: existing `from config import RESULTS_DIR` still works
because config.py re-exports from here.
"""

import os

# ---------------------------------------------------------------------------
# Auto-detect project root (works regardless of CWD)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT: str = os.path.abspath(os.path.join(_HERE, ".."))

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")
DATA_RAW_DIR: str = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED_DIR: str = os.path.join(PROJECT_ROOT, "data", "processed")

# ---------------------------------------------------------------------------
# Results / Outputs  (ONE canonical location: experiments/results/)
# ---------------------------------------------------------------------------
RESULTS_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "results")
RESEARCH_RESULTS_DIR: str = RESULTS_DIR   # alias — same directory
LOGS_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "logs")

# ---------------------------------------------------------------------------
# Model artefacts
# ---------------------------------------------------------------------------
MODEL_REGISTRY_DIR: str = os.path.join(PROJECT_ROOT, "models", "checkpoints")
GENOME_DIR: str = os.path.join(PROJECT_ROOT, "experiments", "genome")

# ---------------------------------------------------------------------------
# Ensure critical output directories exist at import time
# ---------------------------------------------------------------------------
for _d in (RESULTS_DIR, LOGS_DIR, DATA_RAW_DIR, DATA_PROCESSED_DIR, MODEL_REGISTRY_DIR, GENOME_DIR):
    os.makedirs(_d, exist_ok=True)


if __name__ == "__main__":
    print("BTCognitive Canonical Paths")
    print(f"  PROJECT_ROOT      = {PROJECT_ROOT}")
    print(f"  DATA_RAW_DIR      = {DATA_RAW_DIR}")
    print(f"  DATA_PROCESSED_DIR= {DATA_PROCESSED_DIR}")
    print(f"  RESULTS_DIR       = {RESULTS_DIR}")
    print(f"  MODEL_REGISTRY_DIR= {MODEL_REGISTRY_DIR}")
    print(f"  GENOME_DIR        = {GENOME_DIR}")
    print("PASS: all paths resolved")
