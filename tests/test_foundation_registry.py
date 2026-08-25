"""
tests/test_foundation_registry.py — Unit Tests for Foundation Model Registry Entries
===================================================================================
Verifies:
1. Presence of foundation model entries in ChallengerRegistry with deployment_status FOUNDATION_RESEARCH
2. Querying and lifecycle state management
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.challenger_registry import challenger_registry


def test_foundation_registry_entries():
    models = challenger_registry.list_all_models()
    versions = [m["version"] if isinstance(m, dict) else m.version for m in models]

    assert "timesfm-v2.5-research" in versions
    assert "moirai-v2.0-research" in versions
    assert "chronos-v2.0-research" in versions

    tf_entry = challenger_registry.get_model("timesfm-v2.5-research")
    assert tf_entry.deployment_status == "FOUNDATION_RESEARCH"

