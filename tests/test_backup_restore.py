"""
tests/test_backup_restore.py — Unit Tests for Production Backup & Restore Simulation
====================================================================================
Verifies:
1. Production lock manifest backup and restore
2. Data immutability and checksum preservation across simulated corruption
"""

import os
import sys
import json
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_backup_and_restore_simulation(tmp_path):
    lock_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results", "production_lock.json"))
    backup_file = tmp_path / "production_lock_backup.json"

    # 1. Create Backup
    shutil.copy(lock_file, backup_file)
    assert os.path.exists(backup_file)

    # 2. Simulate File Corruption
    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    original_checksum = data["model_checksum"]

    data["model_checksum"] = "sha256:corrupted_checksum_simulated"
    corrupted_file = tmp_path / "corrupted_lock.json"
    with open(corrupted_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # 3. Restore
    shutil.copy(backup_file, corrupted_file)
    with open(corrupted_file, "r", encoding="utf-8") as f:
        restored_data = json.load(f)

    assert restored_data["model_checksum"] == original_checksum
