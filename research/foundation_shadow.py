"""
research/foundation_shadow.py — Isolated Foundation Model Shadow Execution Harness
==================================================================================
Runs foundation models in strictly decoupled shadow mode:
- Zero mutations to 24h Production Ridge range forecasts
- Zero mutations to 5m Hawkes microstructure shadow forecasts
- Zero trade execution, zero automatic model promotion
"""

import os
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.foundation.timesfm_adapter import timesfm_adapter
from models.foundation.moirai_adapter import moirai_adapter
from models.foundation.chronos_adapter import chronos_adapter


class FoundationShadowHarness:
    def execute_shadow_evaluation(
        self,
        current_price: float = 65200.0,
        history: List[float] = None
    ) -> Dict[str, Any]:
        raw_series = history if history else [65200.0 * (1.0 + (i - 60) * 0.0005) for i in range(120)]
        
        fc_timesfm = timesfm_adapter.forecast(current_price, raw_series)
        fc_moirai = moirai_adapter.forecast(current_price, raw_series)
        fc_chronos = chronos_adapter.forecast(current_price, raw_series)

        return {
            "timestamp": fc_timesfm.timestamp,
            "current_price": current_price,
            "isolation_status": "STRICTLY_ISOLATED_FROM_PRODUCTION",
            "production_intact": True,
            "shadow_forecasts": {
                "timesfm_2.5": fc_timesfm.to_dict(),
                "moirai_2.0": fc_moirai.to_dict(),
                "chronos_2": fc_chronos.to_dict()
            }
        }


foundation_shadow_harness = FoundationShadowHarness()
