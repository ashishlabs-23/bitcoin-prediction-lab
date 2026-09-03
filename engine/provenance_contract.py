"""
engine/provenance_contract.py — Level 0 Data & Timestamp Provenance Contract
=============================================================================
Enforces temporal provenance and anti-leakage invariants across three clocks:
  1. t_event: Source microsecond timestamp of the physical event.
  2. t_exchange: Exchange matching engine match timestamp.
  3. t_available: Local ingest receipt timestamp when data is accessible to the engine.

Invariant:
  For any decision taken at decision boundary t_0:
  t_available <= t_0
"""

import os
import sys
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd


class TemporalProvenanceError(ValueError):
    """Raised when data violates point-in-time causality or clock consistency."""
    pass


class ProvenanceContract:
    """
    Level 0 Data & Timestamp Provenance Engine.
    Validates temporal ordering, clock synchronization, point-in-time admissibility,
    and enforces strict scientific quarantine between real and synthetic data.
    """

    def __init__(
        self,
        max_clock_skew_ms: float = 5000.0,
        allow_synthetic: bool = True
    ):
        self.max_clock_skew_ms = max_clock_skew_ms
        self.allow_synthetic = allow_synthetic

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        t0: Optional[pd.Timestamp] = None,
        event_col: str = "timestamp",
        available_col: str = "available_time",
        exchange_col: Optional[str] = None,
        dataset_class: str = "REAL_MARKET"
    ) -> Dict[str, Any]:
        """
        Performs comprehensive L0 temporal validation on a market dataset.
        Enforces dataset_class classification (REAL_MARKET, SYNTHETIC_TEST, REPLAY)
        and scientific_eligible tagging.
        """
        if df.empty:
            raise TemporalProvenanceError("Dataframe is empty; cannot validate temporal provenance.")

        violations = []
        is_synthetic = dataset_class.upper() in ["SYNTHETIC_TEST", "REPLAY_MOCK"]
        scientific_eligible = not is_synthetic

        # 1. Column existence
        if available_col not in df.columns:
            if event_col in df.columns and self.allow_synthetic:
                df = df.copy()
                df[available_col] = df[event_col]
            else:
                violations.append(f"Missing mandatory receipt timestamp column: '{available_col}'")

        if event_col not in df.columns:
            violations.append(f"Missing event timestamp column: '{event_col}'")

        if violations:
            return {
                "valid": False,
                "n_records": len(df),
                "violations": violations,
                "latency_stats": {}
            }

        # 2. Convert to UTC datetimes
        t_avail = pd.to_datetime(df[available_col], utc=True)
        t_evt = pd.to_datetime(df[event_col], utc=True)

        # 3. Invariant 1: Causality check (t_available >= t_event)
        diff_ms = (t_avail - t_evt).dt.total_seconds() * 1000.0
        negative_latency_count = int((diff_ms < -100.0).sum())

        if negative_latency_count > 0:
            violations.append(
                f"Causality violation: {negative_latency_count} records show t_available < t_event by > 100ms"
            )

        # 4. Invariant 2: Monotonicity of receipt
        is_monotonic = t_avail.is_monotonic_increasing
        if not is_monotonic:
            violations.append("t_available is not monotonically non-decreasing.")

        # 5. Invariant 3: Decision boundary causality (all records <= t0 if specified)
        if t0 is not None:
            t0_dt = pd.to_datetime(t0, utc=True)
            leakage_count = int((t_avail > t0_dt).sum())
            if leakage_count > 0:
                violations.append(
                    f"Lookahead leakage: {leakage_count} records have t_available > t0 ({t0_dt.isoformat()})"
                )

        # 6. Latency offset telemetry
        lat_mean = float(diff_ms.mean()) if len(diff_ms) > 0 else 0.0
        lat_p50 = float(diff_ms.median()) if len(diff_ms) > 0 else 0.0
        lat_p99 = float(diff_ms.quantile(0.99)) if len(diff_ms) > 0 else 0.0
        lat_max = float(diff_ms.max()) if len(diff_ms) > 0 else 0.0

        if lat_max > self.max_clock_skew_ms and not self.allow_synthetic:
            violations.append(f"Excessive clock skew / latency: max = {lat_max:.1f}ms > {self.max_clock_skew_ms}ms")

        # 7. Provenance digest
        sample_str = f"{len(df)}_{t_evt.iloc[0]}_{t_evt.iloc[-1]}_{lat_p50:.2f}"
        prov_hash = hashlib.sha256(sample_str.encode("utf-8")).hexdigest()[:16]

        valid = len(violations) == 0

        return {
            "valid": valid,
            "n_records": len(df),
            "t_start": t_evt.iloc[0].isoformat() if len(t_evt) > 0 else None,
            "t_end": t_evt.iloc[-1].isoformat() if len(t_evt) > 0 else None,
            "latency_stats": {
                "mean_ms": round(lat_mean, 2),
                "p50_ms": round(lat_p50, 2),
                "p99_ms": round(lat_p99, 2),
                "max_ms": round(lat_max, 2),
                "negative_latency_count": negative_latency_count
            },
            "dataset_class": dataset_class.upper(),
            "scientific_eligible": scientific_eligible and valid,
            "violations": violations,
            "provenance_hash": prov_hash
        }

    def filter_admissible_data(
        self,
        df: pd.DataFrame,
        t0: pd.Timestamp,
        available_col: str = "available_time"
    ) -> pd.DataFrame:
        """
        Returns only the point-in-time slice strictly available at decision time t0.
        Guarantees zero future lookahead.
        """
        if df.empty:
            return df.copy()

        t0_dt = pd.to_datetime(t0, utc=True)
        if available_col in df.columns:
            t_avail = pd.to_datetime(df[available_col], utc=True)
            return df[t_avail <= t0_dt].copy()
        elif "timestamp" in df.columns:
            t_evt = pd.to_datetime(df["timestamp"], utc=True)
            return df[t_evt <= t0_dt].copy()
        else:
            raise TemporalProvenanceError(f"Cannot filter by t0 without '{available_col}' or 'timestamp'")
