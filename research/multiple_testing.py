"""
research/multiple_testing.py — Multiple Testing Control & Trial Accounting
==========================================================================
Tracks:
- n_total_features_tested
- n_configurations_tested
- n_horizons_tested
- n_models_tested
- n_successful_experiments
Computes rigorous Deflated Sharpe Ratio (DSR) using the actual research trial count K.
"""

import json
import numpy as np
from scipy import stats
from typing import Dict, Any


class ResearchTrialTracker:
    """Tracks research trial count across features, models, horizons, and configurations."""
    def __init__(self):
        self.trials = {
            "n_total_features_tested": 0,
            "n_configurations_tested": 0,
            "n_horizons_tested": 0,
            "n_models_tested": 0,
            "n_experiments": 0,
            "experiments_log": []
        }

    def record_feature_family(self, name: str, count: int):
        self.trials["n_total_features_tested"] += count

    def record_experiment(self, name: str, n_models: int, n_horizons: int, n_configs: int):
        self.trials["n_models_tested"] += n_models
        self.trials["n_horizons_tested"] = max(self.trials["n_horizons_tested"], n_horizons)
        self.trials["n_configurations_tested"] += n_configs
        self.trials["n_experiments"] += 1
        self.trials["experiments_log"].append({
            "name": name,
            "n_models": n_models,
            "n_horizons": n_horizons,
            "n_configs": n_configs
        })

    def total_trial_count_k(self) -> int:
        """Computes total effective research trial count K."""
        return max(1, self.trials["n_models_tested"] * max(1, self.trials["n_horizons_tested"]) + self.trials["n_configurations_tested"])

    def compute_deflated_sharpe_ratio(
        self,
        observed_sr: float,
        n_samples: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        sr_var: float = 0.0
    ) -> float:
        """
        Computes Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)
        using the actual research trial count K.
        """
        K = self.total_trial_count_k()
        euler_mascheroni = 0.5772156649
        z_k = (1.0 - euler_mascheroni) * stats.norm.ppf(1.0 - 1.0 / K) + euler_mascheroni * stats.norm.ppf(1.0 - 1.0 / (K * np.e))
        expected_max_sr = np.sqrt(sr_var) * z_k if sr_var > 0 else 0.0

        sr_std = np.sqrt((1.0 + 0.5 * (observed_sr ** 2) - skewness * observed_sr + ((kurtosis - 3.0) / 4.0) * (observed_sr ** 2)) / max(1, n_samples - 1))

        if sr_std <= 0:
            return 0.0

        z_score = (observed_sr - expected_max_sr) / sr_std
        return float(stats.norm.cdf(z_score))

    def export_manifest(self, filepath: str) -> None:
        manifest_data = {
            "trial_summary": {
                "n_total_features_tested": self.trials["n_total_features_tested"],
                "n_configurations_tested": self.trials["n_configurations_tested"],
                "n_horizons_tested": self.trials["n_horizons_tested"],
                "n_models_tested": self.trials["n_models_tested"],
                "total_effective_k": self.total_trial_count_k()
            },
            "experiments_log": self.trials["experiments_log"]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
