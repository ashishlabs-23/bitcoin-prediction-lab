"""
engine/realized_semi_variance.py — Hourly-Sampled Realized Semi-Variance & Asymmetry Engine
=============================================================================================
Computes causal, point-in-time realized semi-variance metrics from closed hourly candles:
1. r_t = ln(C_t / C_{t-1})
2. Realized Variance: RV_W = sum_{i=0}^{W-1} r_{t-i}^2
3. Upside Realized Semi-Variance: RS_W^+ = sum_{i=0}^{W-1} r_{t-i}^2 * I(r_{t-i} > 0)
4. Downside Realized Semi-Variance: RS_W^- = sum_{i=0}^{W-1} r_{t-i}^2 * I(r_{t-i} < 0)
5. Asymmetry Ratio: A_W = (RS_W^+ - RS_W^-) / (RS_W^+ + RS_W^- + eps)

GOVERNANCE STATUS:
- Feature Status: HOURLY_SAMPLED_RESEARCH_FEATURE
- Disclaimers: Hourly-sampled proxy. Does NOT implement high-frequency (e.g. 5-minute)
  bipower variation or continuous/jump decomposition. Does NOT alter authorized HAR-RS-DOW-v1.0 model.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


class RealizedSemiVarianceEngine:
    """Computes hourly-sampled realized semi-variance components."""

    FEATURE_STATUS = "HOURLY_SAMPLED_RESEARCH_FEATURE"

    def __init__(self, eps: float = 1e-12):
        self.eps = eps

    def compute_returns(self, closes: np.ndarray) -> np.ndarray:
        """Compute point-in-time log returns r_t = ln(C_t / C_{t-1})."""
        if len(closes) < 2:
            return np.array([])
        return np.diff(np.log(closes))

    def compute_semi_variance_components(
        self,
        returns_window: np.ndarray,
        annualize: bool = True
    ) -> Dict[str, float]:
        """
        Compute realized variance, upside semi-variance, downside semi-variance,
        and asymmetry ratio over a single window of log returns.
        """
        W = len(returns_window)
        if W == 0:
            return {
                "rv": 0.0,
                "rs_plus": 0.0,
                "rs_minus": 0.0,
                "asymmetry_ratio": 0.0,
                "window_size": 0,
                "status": "INSUFFICIENT_DATA"
            }

        pos_mask = returns_window > 0
        neg_mask = returns_window < 0

        # Raw sum of squares
        ss_rv = float(np.sum(returns_window ** 2))
        ss_pos = float(np.sum((returns_window[pos_mask]) ** 2)) if np.any(pos_mask) else 0.0
        ss_neg = float(np.sum((returns_window[neg_mask]) ** 2)) if np.any(neg_mask) else 0.0

        # Exact algebraic identity: RV == RS+ + RS-
        assert abs(ss_rv - (ss_pos + ss_neg)) < 1e-12, "RV must equal RS+ + RS- algebraically."

        annualization_factor = (8760.0 / W) if annualize else 1.0

        rv_ann = ss_rv * annualization_factor
        rs_pos_ann = ss_pos * annualization_factor
        rs_neg_ann = ss_neg * annualization_factor

        denom = ss_pos + ss_neg + self.eps
        asym = (ss_pos - ss_neg) / denom

        return {
            "rv": round(rv_ann, 6),
            "rs_plus": round(rs_pos_ann, 6),
            "rs_minus": round(rs_neg_ann, 6),
            "asymmetry_ratio": round(asym, 6),
            "window_size": W,
            "status": self.FEATURE_STATUS
        }

    def compute_rolling_semi_variance(
        self,
        closes: np.ndarray,
        window: int = 24,
        annualize: bool = True
    ) -> pd.DataFrame:
        """
        Compute rolling semi-variance components across a time series of closes.
        Only relies on historical data up to index t (strictly causal).
        """
        if len(closes) < window + 1:
            return pd.DataFrame()

        rets = self.compute_returns(closes)
        T = len(rets)

        rv_series = np.full(len(closes), np.nan)
        rs_pos_series = np.full(len(closes), np.nan)
        rs_neg_series = np.full(len(closes), np.nan)
        asym_series = np.full(len(closes), np.nan)

        for t in range(window - 1, T):
            window_slice = rets[t - window + 1 : t + 1]
            metrics = self.compute_semi_variance_components(window_slice, annualize=annualize)
            # Closes index is t + 1 because returns are length T = N - 1
            close_idx = t + 1
            rv_series[close_idx] = metrics["rv"]
            rs_pos_series[close_idx] = metrics["rs_plus"]
            rs_neg_series[close_idx] = metrics["rs_minus"]
            asym_series[close_idx] = metrics["asymmetry_ratio"]

        return pd.DataFrame({
            f"rv_{window}h": rv_series,
            f"rs_plus_{window}h": rs_pos_series,
            f"rs_minus_{window}h": rs_neg_series,
            f"asymmetry_{window}h": asym_series
        })


semi_variance_engine = RealizedSemiVarianceEngine()
