"""
BTCognitive V33.4 — HTF Breakout Prospective Shadow Runner & Ledger Protocol
Pre-registers and manages the prospective shadow evaluation for:
- Strategy: HTF_RANGE_EXPANSION_BREAKOUT
- Filter: MarketRegimeClassifier (3-bar confirmation hysteresis)
- Execution Friction: Binance VIP0 (26.0 bps modeled)
- Ledger: data/htf_prospective_shadow_ledger.jsonl (Strictly separate from conformal forecast ledger)
- Collector State: INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION (Network access blocked)
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

class HTFProspectiveShadowProtocol:
    STRATEGY_NAME = "HTF_RANGE_EXPANSION_BREAKOUT"
    FILTER_NAME = "MarketRegimeClassifier"
    HYSTERESIS_CONFIRMATION_BARS = 3
    DONCHIAN_WINDOW_4H = 20
    MAX_HOLD_4H_BARS = 18  # 72 hours
    MODELED_COST_BPS = 26.0  # 20 comm + 2 spread + 2 base slip + 2 exp slip
    NOTIONAL_ALLOCATION_FRACTION = 0.10  # 10% Notional Equity Allocation
    MIN_REQUIRED_BLOCKS = 100  # Pre-registered hurdle before confirmatory gate

    LEDGER_RELATIVE_PATH = "data/htf_prospective_shadow_ledger.jsonl"
    CONFORMAL_LEDGER_PATH = "data/prospective_forecast_ledger.jsonl"

    COLLECTOR_STATUS = "INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION"
    NETWORK_ACCESS = "BLOCKED"
    LIVE_TRADING = "DISABLED"
    MODEL_AUTHORIZATION = "OFFLINE_RESEARCH_ONLY"

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.ledger_path = self.base_dir / self.LEDGER_RELATIVE_PATH
        self.conformal_path = self.base_dir / self.CONFORMAL_LEDGER_PATH

    def get_protocol_status(self) -> Dict[str, Any]:
        """Returns the current state and invariants of the prospective shadow protocol."""
        return {
            "strategy": self.STRATEGY_NAME,
            "filter": self.FILTER_NAME,
            "hysteresis_bars": self.HYSTERESIS_CONFIRMATION_BARS,
            "donchian_window_4h": self.DONCHIAN_WINDOW_4H,
            "max_hold_hours": self.MAX_HOLD_4H_BARS * 4,
            "modeled_cost_bps": self.MODELED_COST_BPS,
            "notional_allocation_fraction": self.NOTIONAL_ALLOCATION_FRACTION,
            "min_required_blocks": self.MIN_REQUIRED_BLOCKS,
            "ledger_path": str(self.LEDGER_RELATIVE_PATH),
            "collector_status": self.COLLECTOR_STATUS,
            "network_access": self.NETWORK_ACCESS,
            "live_trading": self.LIVE_TRADING,
            "model_authorization": self.MODEL_AUTHORIZATION,
            "ledger_distinct_from_conformal": str(self.LEDGER_RELATIVE_PATH) != str(self.CONFORMAL_LEDGER_PATH)
        }

    def validate_ledger_record(self, record: Dict[str, Any]) -> bool:
        """Validates that a ledger entry strictly conforms to the pre-registered schema."""
        required_fields = [
            "signal_id", "timestamp_issue_utc", "breakout_bar_close", "execution_open_price",
            "stop_loss_price", "regime_at_entry", "regime_confirmed_bars", "filter_action",
            "cost_modeled_bps", "exit_timestamp_utc", "exit_price", "holding_hours",
            "gross_return_bps", "net_return_bps", "protocol_version"
        ]
        for field in required_fields:
            if field not in record:
                raise ValueError(f"Missing required field in shadow ledger: {field}")

        if record["filter_action"] not in ["EXECUTED_SHADOW", "SUPPRESSED_CHOP"]:
            raise ValueError(f"Invalid filter_action: {record['filter_action']}")

        if record["cost_modeled_bps"] != self.MODELED_COST_BPS:
            raise ValueError(f"Cost mismatch: expected {self.MODELED_COST_BPS}, got {record['cost_modeled_bps']}")

        expected_net = record["gross_return_bps"] - self.MODELED_COST_BPS
        if abs(record["net_return_bps"] - expected_net) > 1e-4:
            raise ValueError(f"Net return mismatch: gross {record['gross_return_bps']} - cost {self.MODELED_COST_BPS} != net {record['net_return_bps']}")

        return True

    def append_shadow_record(self, record: Dict[str, Any]) -> None:
        """Appends a validated record to the append-only ledger."""
        self.validate_ledger_record(record)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_shadow_records(self) -> List[Dict[str, Any]]:
        """Reads all records from the prospective shadow ledger."""
        if not self.ledger_path.exists():
            return []
        records = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def start_live_collection(self) -> None:
        """Enforces the inactive collector operational guardrail."""
        raise RuntimeError(
            "Operational Prerequisite Violation: The market data collector is currently inactive and network access remains blocked. "
            "Starting a new forward market-data collection process requires explicit, separate managerial authorization."
        )

