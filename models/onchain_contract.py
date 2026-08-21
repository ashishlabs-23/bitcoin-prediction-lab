"""
models/onchain_contract.py — Canonical On-Chain Data Contract
============================================================
Single source of truth for on-chain field definitions, data quality states,
and dataclass contracts across the BTCognitive system.

SCIENTIFIC SEMANTICS:
- 'mvrv_ratio': CoinMetrics CapMVRVFF ratio (Free-Float Market Cap / Realized Cap).
  Typical range: 0.7 - 4.5. This is NOT a Z-Score.
- 'nupl': Net Unrealized Profit/Loss ((Market Cap - Realized Cap) / Market Cap).
  Typical range: -0.2 - 0.85.
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

# Quality states
class OnchainQuality(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"
    MISSING = "MISSING"
    STALE = "STALE"
    WRONG_SCHEMA = "WRONG_SCHEMA"

SCHEMA_VERSION_CURRENT = "v1.0"

class OnchainContractError(ValueError):
    """Raised when on-chain data fails validation or violates canonical contract."""
    pass

@dataclass
class OnchainMetrics:
    mvrv_ratio: float
    nupl: float
    cycle_phase: str
    timestamp: str
    source: str
    is_live: bool
    is_degraded: bool
    influence_weight: float
    quality: OnchainQuality
    schema_version: str = SCHEMA_VERSION_CURRENT

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quality"] = self.quality.value
        # For backwards compatibility with consumers expecting 'mvrv'
        d["mvrv"] = self.mvrv_ratio
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], max_age_hours: float = 72.0) -> "OnchainMetrics":
        if not data or not isinstance(data, dict):
            raise OnchainContractError("Data must be a non-empty dictionary.")

        # Check required fields
        # Accept 'mvrv_ratio' or canonical 'mvrv'
        mvrv_val = data.get("mvrv_ratio")
        if mvrv_val is None:
            mvrv_val = data.get("mvrv")
            
        if mvrv_val is None:
            raise OnchainContractError("Missing required field 'mvrv_ratio' (or 'mvrv').")

        if "nupl" not in data:
            raise OnchainContractError("Missing required field 'nupl'.")

        try:
            mvrv_float = float(mvrv_val)
            nupl_float = float(data["nupl"])
        except (ValueError, TypeError):
            raise OnchainContractError("Numeric conversion error for mvrv/nupl.")

        cycle_phase = str(data.get("cycle_phase", "NEUTRAL"))
        source = str(data.get("source", "unknown"))
        is_live = bool(data.get("is_live", False))
        is_degraded = bool(data.get("is_degraded", True))
        influence_weight = float(data.get("influence_weight", 0.0))
        schema_ver = str(data.get("schema_version", SCHEMA_VERSION_CURRENT))
        ts_str = str(data.get("timestamp", data.get("updated_at", datetime.now(timezone.utc).isoformat())))

        # Evaluate Quality State
        quality = OnchainQuality.VALID
        if is_degraded or not is_live or influence_weight <= 0.0:
            quality = OnchainQuality.DEGRADED

        # Check for staleness
        try:
            # Parse ISO or standard string
            clean_ts = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now - dt > timedelta(hours=max_age_hours):
                quality = OnchainQuality.STALE
        except Exception:
            pass

        return cls(
            mvrv_ratio=mvrv_float,
            nupl=nupl_float,
            cycle_phase=cycle_phase,
            timestamp=ts_str,
            source=source,
            is_live=is_live,
            is_degraded=is_degraded,
            influence_weight=influence_weight,
            quality=quality,
            schema_version=schema_ver
        )

def assess_onchain_quality(data: Dict[str, Any]) -> OnchainQuality:
    """Helper to assess onchain dictionary quality without throwing."""
    if not data or not isinstance(data, dict):
        return OnchainQuality.MISSING
    
    if "mvrv" not in data and "mvrv_ratio" not in data:
        if "mvrv_zscore" in data and "mvrv" not in data:
            return OnchainQuality.WRONG_SCHEMA
        return OnchainQuality.MISSING

    try:
        metrics = OnchainMetrics.from_dict(data)
        return metrics.quality
    except OnchainContractError:
        return OnchainQuality.INVALID
    except Exception:
        return OnchainQuality.INVALID


if __name__ == "__main__":
    print("Running On-Chain Contract Verification Tests...")
    
    # 1. VALID
    valid_payload = {
        "mvrv_ratio": 2.15,
        "nupl": 0.45,
        "cycle_phase": "NEUTRAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "coinmetrics_api",
        "is_live": True,
        "is_degraded": False,
        "influence_weight": 1.0
    }
    m_valid = OnchainMetrics.from_dict(valid_payload)
    assert m_valid.quality == OnchainQuality.VALID, f"Expected VALID, got {m_valid.quality}"
    print("  [PASS] VALID test passed.")

    # 2. DEGRADED
    degraded_payload = {
        "mvrv": 1.85,
        "nupl": 0.42,
        "cycle_phase": "NEUTRAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "calibrated_proxy",
        "is_live": False,
        "is_degraded": True,
        "influence_weight": 0.0
    }
    m_degraded = OnchainMetrics.from_dict(degraded_payload)
    assert m_degraded.quality == OnchainQuality.DEGRADED, f"Expected DEGRADED, got {m_degraded.quality}"
    print("  [PASS] DEGRADED test passed.")

    # 3. INVALID (bad types)
    invalid_payload = {
        "mvrv": "NOT_A_FLOAT",
        "nupl": 0.42
    }
    assert assess_onchain_quality(invalid_payload) == OnchainQuality.INVALID
    print("  [PASS] INVALID test passed.")

    # 4. MISSING (empty dict)
    assert assess_onchain_quality({}) == OnchainQuality.MISSING
    print("  [PASS] MISSING test passed.")

    # 5. STALE (>72h old)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    stale_payload = {
        "mvrv": 2.10,
        "nupl": 0.45,
        "timestamp": old_ts,
        "is_live": True,
        "is_degraded": False,
        "influence_weight": 1.0
    }
    m_stale = OnchainMetrics.from_dict(stale_payload)
    assert m_stale.quality == OnchainQuality.STALE, f"Expected STALE, got {m_stale.quality}"
    print("  [PASS] STALE test passed.")

    # 6. WRONG_SCHEMA (using legacy mvrv_zscore without mvrv)
    wrong_schema_payload = {
        "mvrv_zscore": 2.15,
        "nupl": 0.45
    }
    assert assess_onchain_quality(wrong_schema_payload) == OnchainQuality.WRONG_SCHEMA
    print("  [PASS] WRONG_SCHEMA test passed.")

    print("\nALL ON-CHAIN CONTRACT TESTS PASSED.")
