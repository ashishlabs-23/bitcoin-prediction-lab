"""
tests/test_foundation_dataset.py — Unit Tests for Foundation Dataset Manifest
=============================================================================
Verifies:
1. Dataset manifest creation and schema properties
2. Presence of strict context windows (120h, 240h, 480h) and 24h purge/embargo
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.foundation_dataset import generate_foundation_dataset_manifest


def test_foundation_dataset_manifest_generation():
    manifest = generate_foundation_dataset_manifest()

    assert manifest["horizon"] == "24h"
    assert manifest["purge_hours"] == 24
    assert manifest["embargo_hours"] == 24
    assert 120 in manifest["context_windows_hours"]
    assert 240 in manifest["context_windows_hours"]
    assert 480 in manifest["context_windows_hours"]
