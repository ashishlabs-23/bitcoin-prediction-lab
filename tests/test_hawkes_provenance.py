"""
tests/test_hawkes_provenance.py — Unit Tests for Hawkes Data Provenance & Timestamp Integrity
=============================================================================================
Verifies:
1. Monotonic timestamp auditing
2. Rejection of out-of-order event streams (MICROSTRUCTURE_LEAKAGE_DETECTED)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.microstructure_dataset import generate_synthetic_l2_event_stream
from research.hawkes_data_provenance import audit_microstructure_data_provenance, MicrostructureProvenanceError


def test_hawkes_data_provenance_valid():
    df_events = generate_synthetic_l2_event_stream(n_events=200)
    df_audit, is_valid = audit_microstructure_data_provenance(df_events)

    assert is_valid is True
    assert len(df_audit) >= 10


def test_hawkes_provenance_rejects_out_of_order_stream():
    df_events = generate_synthetic_l2_event_stream(n_events=100)
    # Corrupt timestamps (inject out-of-order tick)
    df_events.loc[50, "timestamp_ms"] = df_events.loc[40, "timestamp_ms"] - 5000

    with pytest.raises(MicrostructureProvenanceError):
        audit_microstructure_data_provenance(df_events)
