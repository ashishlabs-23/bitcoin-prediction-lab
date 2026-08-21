"""
models/foundation/uncertainty_adapter.py — Foundation Model Uncertainty Normalizer
=================================================================================
Maps heterogeneous foundation model outputs (quantiles, sample paths, ensembles)
into BTCognitive's canonical uncertainty metrics.
"""

from typing import List, Dict, Any
import numpy as np


class FoundationUncertaintyAdapter:
    @staticmethod
    def normalize_quantiles(
        sample_paths_or_quantiles: List[float],
        current_price: float,
        horizon_hours: int = 24
    ) -> Dict[str, float]:
        arr = np.array(sample_paths_or_quantiles)
        p10 = float(np.percentile(arr, 10))
        p50 = float(np.percentile(arr, 50))
        p90 = float(np.percentile(arr, 90))

        # Relative excursion scale
        mfe_p10 = max(0.0005, (p50 - current_price) / current_price * 0.4)
        mfe_p50 = max(0.0010, (p90 - current_price) / current_price * 0.7)
        mfe_p90 = max(0.0020, (p90 - current_price) / current_price * 1.1)

        mae_p10 = max(0.0005, (current_price - p50) / current_price * 0.4)
        mae_p50 = max(0.0010, (current_price - p10) / current_price * 0.7)
        mae_p90 = max(0.0020, (current_price - p10) / current_price * 1.1)

        upper_p90 = round(current_price * (1.0 + mfe_p90 * 4.0), 2)
        lower_p90 = round(current_price * (1.0 - mae_p90 * 4.0), 2)
        uncertainty = round(float(np.std(arr) / (current_price + 1e-6) * 100.0), 2)

        return {
            "mfe_p10": round(mfe_p10, 5),
            "mfe_p50": round(mfe_p50, 5),
            "mfe_p90": round(mfe_p90, 5),
            "mae_p10": round(mae_p10, 5),
            "mae_p50": round(mae_p50, 5),
            "mae_p90": round(mae_p90, 5),
            "upper_p90": upper_p90,
            "lower_p90": lower_p90,
            "uncertainty": max(0.8, min(5.0, uncertainty))
        }
