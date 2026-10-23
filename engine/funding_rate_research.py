"""
engine/funding_rate_research.py — Perpetual Funding Rate Research Engine & Collector
=====================================================================================
Manages normalized funding rate records across Bitcoin perpetual derivatives:
1. Linear USDT Perpetual: BTCUSDT (Linear settlement in USDT)
2. Inverse Coin-Margined Perpetual: BTCUSD_PERP (Inverse settlement in BTC)

GOVERNANCE CONTRACT:
- Separation of Spot vs Perpetual: Derivatives funding rates describe leverage and positioning;
  they do not constitute spot price observations.
- Threshold Semantics: Extreme funding flag (>0.03% per 8h) is an EXPLORATORY RESEARCH HYPOTHESIS only.
  It is not a validated market threshold, trade signal, or execution trigger.
- Feature Status: RESEARCH_FEATURE_EXPLORATORY (Non-execution, Analysis Only).
"""

from typing import Dict, Any, List, Optional
import datetime
import json
from pathlib import Path


class FundingRateResearchEngine:
    """Manages perpetual funding rate collection, schema validation, and diagnostics."""

    FEATURE_STATUS = "RESEARCH_FEATURE_EXPLORATORY"
    EXPLORATORY_THRESHOLD_8H = 0.0003  # 0.03% per 8 hours

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path(__file__).resolve().parent.parent / "data" / "research")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.storage_dir / "funding_rate_research_ledger.jsonl"

    def normalize_funding_record(
        self,
        instrument: str,
        funding_rate: float,
        funding_time_utc: str,
        interval_hours: int = 8,
        venue: str = "BINANCE",
        contract_type: str = "LINEAR_USDT"
    ) -> Dict[str, Any]:
        """
        Validate and normalize a perpetual funding rate observation.
        """
        annualized_rate = funding_rate * (8760.0 / interval_hours)
        is_exploratory_extreme = abs(funding_rate) >= self.EXPLORATORY_THRESHOLD_8H

        record = {
            "venue": venue,
            "instrument": instrument,
            "contract_type": contract_type,
            "funding_rate": round(funding_rate, 8),
            "funding_rate_bps": round(funding_rate * 10000.0, 4),
            "annualized_rate_pct": round(annualized_rate * 100.0, 2),
            "funding_time_utc": funding_time_utc,
            "interval_hours": interval_hours,
            "retrieval_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "exploratory_hypothesis": {
                "threshold_rate": self.EXPLORATORY_THRESHOLD_8H,
                "is_extreme_leverage_flag": is_exploratory_extreme,
                "scientific_status": "UNVALIDATED_EXPLORATORY_HYPOTHESIS_ONLY"
            },
            "feature_status": self.FEATURE_STATUS,
            "execution_authorization": "DISABLED"
        }
        return record

    def record_funding_observation(
        self,
        instrument: str,
        funding_rate: float,
        funding_time_utc: str,
        interval_hours: int = 8,
        venue: str = "BINANCE",
        contract_type: str = "LINEAR_USDT"
    ) -> Dict[str, Any]:
        """Normalize and append funding record to immutable research ledger."""
        record = self.normalize_funding_record(
            instrument=instrument,
            funding_rate=funding_rate,
            funding_time_utc=funding_time_utc,
            interval_hours=interval_hours,
            venue=venue,
            contract_type=contract_type
        )
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record


funding_research_engine = FundingRateResearchEngine()
