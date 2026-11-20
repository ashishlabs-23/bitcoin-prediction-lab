"""
engine/data_mode.py — Authoritative Runtime Data-Lane Contract & Enforcement
=============================================================================
Enforces the single, authoritative three-lane data architecture for BTCognitive:
1. "fixture": Deterministic test/demo fixtures only. Strictly prohibited from reading
   empirical protected files or making external market data calls.
2. "offline_research": Local historical BTC-USD snapshots only (data/raw/ohlcv.parquet).
   Strictly prohibited from making external market data calls.
3. "provider": Staging / future licensed provider. Unconfigured and fail-closed in Phase 1.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Dict, Any, Optional, Set, Union


class DataMode(str, Enum):
    FIXTURE = "fixture"
    OFFLINE_RESEARCH = "offline_research"
    PROVIDER = "provider"

    @classmethod
    def from_string(cls, val: str) -> "DataMode":
        if not isinstance(val, str):
            raise InvalidDataModeError(f"Data mode must be string, got {type(val)}")
        clean = val.strip().lower().replace("-", "_")
        if clean not in SUPPORTED_DATA_MODES:
            raise InvalidDataModeError(
                f"Invalid data mode '{val}'. Supported values: {sorted(list(SUPPORTED_DATA_MODES))}"
            )
        return cls(clean)


SUPPORTED_DATA_MODES: Set[str] = {
    DataMode.FIXTURE.value,
    DataMode.OFFLINE_RESEARCH.value,
    DataMode.PROVIDER.value,
}

# The 6 protected research datasets and prospective ledgers
PROTECTED_EMPIRICAL_FILENAMES: Set[str] = {
    "ohlcv.parquet",
    "ohlcv_pre_backfill_backup.parquet",
    "ohlcv_backfilled.parquet",
    "prospective_entry_ledger.jsonl",
    "prospective_shadow_v1.jsonl",
    "prospective_entry_ledger_v2.jsonl",
}


class InvalidDataModeError(ValueError):
    """Raised when an unrecognized or malformed DATA_MODE is provided."""
    pass


class ExternalNetworkBlockedError(RuntimeError):
    """Raised when an outbound market data network connection is attempted in restricted modes."""
    pass


LOCAL_FIXTURE_FEED_ENV = "BTC_LOCAL_FIXTURE_FEED"
LOCAL_FIXTURE_LABEL = "LOCAL TEST FIXTURE ONLY — NOT MARKET DATA"


class ProtectedFileAccessBlockedError(PermissionError):
    """Raised when fixture mode attempts to read an empirical protected dataset."""
    pass


def get_data_mode() -> str:
    """
    Returns the active DATA_MODE string ("fixture", "offline_research", "provider").
    
    Validation & Defaults:
    1. If BTC_DATA_MODE or DATA_MODE environment variable is set:
       - Validates against supported modes.
       - If invalid, raises InvalidDataModeError immediately (fails closed).
       - Returns normalized mode.
    2. If not set:
       - In automated tests (pytest active), defaults explicitly to "fixture".
       - In local loopback execution, defaults explicitly to "offline_research".
    """
    raw_mode = os.environ.get("BTC_DATA_MODE") or os.environ.get("DATA_MODE")
    if raw_mode is not None:
        clean_mode = raw_mode.strip().lower().replace("-", "_")
        if clean_mode not in SUPPORTED_DATA_MODES:
            raise InvalidDataModeError(
                f"Invalid DATA_MODE '{raw_mode}'. Supported values are: "
                f"{sorted(list(SUPPORTED_DATA_MODES))}. Malformed modes fail closed."
            )
        return clean_mode

    # Auto-detect pytest environment
    if "PYTEST_CURRENT_TEST" in os.environ or sys.modules.get("pytest") is not None:
        return DataMode.FIXTURE.value

    # Default for local loopback development
    return DataMode.OFFLINE_RESEARCH.value


def is_external_network_permitted() -> bool:
    """
    Returns True only if the active mode contract permits outbound market-data network calls.
    In Phase 1, returns False for all modes because no licensed provider is configured.
    """
    mode = get_data_mode()
    if mode in (DataMode.FIXTURE.value, DataMode.OFFLINE_RESEARCH.value):
        return False
    
    # In Phase 1, no provider is licensed/cleared, so external network calls remain prohibited
    return False


def is_local_fixture_feed_enabled(mode: Optional[Union[str, DataMode]] = None) -> bool:
    """Return whether the explicitly opted-in, in-memory fixture feed may be exposed."""
    target_mode = (mode.value if isinstance(mode, DataMode) else mode) or get_data_mode()
    return (
        target_mode == DataMode.FIXTURE.value
        and os.environ.get(LOCAL_FIXTURE_FEED_ENV, "").strip() == "1"
    )


def assert_no_external_network(operation: str = "market_data_request") -> None:
    """
    Enforces that no external socket or HTTP request can be initiated in restricted modes.
    Raises ExternalNetworkBlockedError before any DNS lookup or socket creation.
    """
    if not is_external_network_permitted():
        mode = get_data_mode()
        raise ExternalNetworkBlockedError(
            f"External market-data network connection blocked for '{operation}'. "
            f"Active DATA_MODE='{mode}' strictly prohibits external network calls."
        )


def is_protected_file_access_permitted(path: str, mode: Optional[Union[str, DataMode]] = None) -> bool:
    """
    Returns False if fixture mode attempts to read any protected empirical dataset or ledger.
    """
    target_mode = (mode.value if isinstance(mode, DataMode) else mode) if mode is not None else get_data_mode()
    if target_mode == DataMode.FIXTURE.value:
        norm_path = os.path.normpath(path).replace("\\", "/")
        base_name = os.path.basename(norm_path)
        if base_name in PROTECTED_EMPIRICAL_FILENAMES:
            return False
        if "data/raw" in norm_path or "data/research" in norm_path:
            return False
    return True


def assert_protected_file_access_permitted(path: str, mode: Optional[Union[str, DataMode]] = None) -> None:
    """
    Enforces that fixture mode cannot silently read empirical protected files.
    """
    if not is_protected_file_access_permitted(path, mode=mode):
        raise ProtectedFileAccessBlockedError(
            f"Access to empirical protected file '{path}' is strictly prohibited under DATA_MODE='fixture'. "
            f"Automated tests in fixture mode must use deterministic fixtures."
        )


def get_data_mode_contract() -> Dict[str, Any]:
    """
    Emits the authoritative typed metadata for the active data lane.
    """
    mode = get_data_mode()
    return {
        "mode": mode,
        "data_mode": mode,
        "is_fixture": mode == DataMode.FIXTURE.value,
        "is_offline_research": mode == DataMode.OFFLINE_RESEARCH.value,
        "is_provider": mode == DataMode.PROVIDER.value,
        "external_network_allowed": is_external_network_permitted(),
        "local_fixture_feed_enabled": is_local_fixture_feed_enabled(mode),
        "local_fixture_feed_label": (
            LOCAL_FIXTURE_LABEL if is_local_fixture_feed_enabled(mode) else None
        ),
        "provider_configured": False,
        "provider_status": "PROVIDER_NOT_CONFIGURED" if mode == DataMode.PROVIDER.value else "DISABLED",
        "permitted_data_source": (
            "DETERMINISTIC_FIXTURE" if mode == DataMode.FIXTURE.value
            else ("LOCAL_HISTORICAL_SNAPSHOT" if mode == DataMode.OFFLINE_RESEARCH.value else "NONE")
        ),
        "permitted_rights_status": (
            "FIXTURE_ONLY" if mode == DataMode.FIXTURE.value
            else ("REVIEW_REQUIRED" if mode == DataMode.OFFLINE_RESEARCH.value else "UNAUTHORIZED")
        ),
        "canonical_symbol": "BTC-USD",
        "live_trading_enabled": False,
    }
