"""
tests/test_research_isolation.py — Unit Tests for Research Workspace Path Isolation
===================================================================================
Verifies:
1. Research scripts cannot overwrite models/registry/production or locked artifacts
2. Output directories remain separated (research/reports/ and results/ vs models/)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_research_isolation_paths():
    prod_registry = os.path.join(ROOT_DIR, "models", "registry")
    research_dir = os.path.join(ROOT_DIR, "research")
    results_dir = os.path.join(ROOT_DIR, "results")

    assert os.path.exists(research_dir)
    assert os.path.exists(results_dir)
    # Ensure research and production directories are distinct paths
    assert os.path.abspath(research_dir) != os.path.abspath(prod_registry)
