"""
research/live_forecast_scorecard.py — Live Paper Forecast Scorecard & Drift Monitor
==================================================================================
Evaluates live paper-forecast session quality:
1. Multi-Window Rolling Calibration: 25, 50, 100, 250 forecasts
2. Quality Metrics: MFE IC, MAE IC, P90 coverage, joint path coverage, absolute error, interval width
3. Benchmark Comparison: ATR, EWMA Volatility, Historical MFE Percentile vs Production Model
4. Statistical Drift Monitoring: NORMAL / WATCH / ALERT
"""

import numpy as np
import pandas as pd
from scipy import stats
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional


@dataclass
class LiveCalibrationWindowResult:
    window_size: int
    sample_count: int
    status: str  # CALIBRATION_OK, CALIBRATION_WARNING, CALIBRATION_CRITICAL, INSUFFICIENT_SAMPLE
    mfe_p90_coverage_pct: float
    mae_p90_coverage_pct: float
    joint_path_containment_pct: float
    mean_interval_width_pct: float
    mean_mfe_abs_error_pct: float
    mean_mae_abs_error_pct: float


class LiveForecastScorecard:
    """
    Computes rolling empirical calibration, benchmark comparisons, and drift detection.
    """

    def __init__(self, nominal_path_target: float = 78.87, nominal_p90_target: float = 90.0):
        self.nominal_path_target = nominal_path_target
        self.nominal_p90_target = nominal_p90_target

    def evaluate_rolling_windows(
        self,
        mfe_preds: np.ndarray,
        mae_preds: np.ndarray,
        actual_mfes: np.ndarray,
        actual_maes: np.ndarray,
        upper_covered_flags: np.ndarray,
        lower_covered_flags: np.ndarray,
        windows: List[int] = [25, 50, 100, 250]
    ) -> List[LiveCalibrationWindowResult]:
        """
        Calculates calibration across standard rolling observation windows.
        """
        n = len(actual_mfes)
        results = []

        for w in windows:
            if n < w:
                results.append(LiveCalibrationWindowResult(
                    window_size=w,
                    sample_count=n,
                    status="INSUFFICIENT_SAMPLE",
                    mfe_p90_coverage_pct=0.0,
                    mae_p90_coverage_pct=0.0,
                    joint_path_containment_pct=0.0,
                    mean_interval_width_pct=0.0,
                    mean_mfe_abs_error_pct=0.0,
                    mean_mae_abs_error_pct=0.0
                ))
                continue

            sub_mfe_p = mfe_preds[-w:]
            sub_mae_p = mae_preds[-w:]
            sub_mfe_a = actual_mfes[-w:]
            sub_mae_a = actual_maes[-w:]
            sub_up = upper_covered_flags[-w:]
            sub_low = lower_covered_flags[-w:]
            sub_path = sub_up & sub_low

            up_cov = float(np.mean(sub_up)) * 100.0
            low_cov = float(np.mean(sub_low)) * 100.0
            path_cov = float(np.mean(sub_path)) * 100.0
            avg_width = float(np.mean(sub_mfe_p + sub_mae_p)) * 100.0
            mfe_err = float(np.mean(np.abs(sub_mfe_a - sub_mfe_p))) * 100.0
            mae_err = float(np.mean(np.abs(sub_mae_a - sub_mae_p))) * 100.0

            if path_cov < 65.0 or up_cov < 75.0:
                status = "CALIBRATION_CRITICAL"
            elif path_cov < 73.0 or up_cov < 85.0:
                status = "CALIBRATION_WARNING"
            else:
                status = "CALIBRATION_OK"

            results.append(LiveCalibrationWindowResult(
                window_size=w,
                sample_count=len(sub_mfe_a),
                status=status,
                mfe_p90_coverage_pct=round(up_cov, 2),
                mae_p90_coverage_pct=round(low_cov, 2),
                joint_path_containment_pct=round(path_cov, 2),
                mean_interval_width_pct=round(avg_width, 2),
                mean_mfe_abs_error_pct=round(mfe_err, 4),
                mean_mae_abs_error_pct=round(mae_err, 4)
            ))

        return results

    def compare_benchmarks(
        self,
        actual_mfes: np.ndarray,
        pred_prod_mfe: np.ndarray,
        pred_atr_mfe: np.ndarray,
        pred_ewma_mfe: np.ndarray,
        pred_percentile_mfe: np.ndarray
    ) -> pd.DataFrame:
        """
        Benchmarks production forecast against ATR, EWMA, and Historical Percentile baselines.
        """
        def calc_metrics(name, preds):
            rho, p_val = stats.spearmanr(preds, actual_mfes)
            mae = float(np.mean(np.abs(actual_mfes - preds))) * 100.0
            rmse = float(np.sqrt(np.mean((actual_mfes - preds)**2))) * 100.0
            cov_p90 = float(np.mean(actual_mfes <= np.quantile(preds, 0.90))) * 100.0
            return {
                "Model / Baseline": name,
                "Spearman IC": round(float(rho), 4),
                "p-value": f"{p_val:.4e}" if p_val < 0.001 else f"{p_val:.4f}",
                "MAE %": round(mae, 4),
                "RMSE %": round(rmse, 4),
                "P90 Coverage %": round(cov_p90, 2),
                "Status": "Production Core" if "Production" in name else "Baseline Reference"
            }

        records = [
            calc_metrics("1. Production Ridge MFE Model", pred_prod_mfe),
            calc_metrics("2. Historical Percentile (168h)", pred_percentile_mfe),
            calc_metrics("3. EWMA Volatility Baseline", pred_ewma_mfe),
            calc_metrics("4. Average True Range (ATR)", pred_atr_mfe)
        ]
        return pd.DataFrame(records)

    def detect_distribution_drift(
        self,
        baseline_distribution: np.ndarray,
        current_distribution: np.ndarray
    ) -> Dict[str, Any]:
        """
        Runs Kolmogorov-Smirnov two-sample test to detect statistical drift.
        """
        if len(current_distribution) < 15 or len(baseline_distribution) < 15:
            return {"status": "NORMAL", "ks_statistic": 0.0, "p_value": 1.0, "message": "Insufficient sample for KS drift test."}

        ks_stat, p_val = stats.ks_2samp(baseline_distribution, current_distribution)

        if p_val < 0.01:
            status = "ALERT"
            msg = f"Severe distribution drift detected (KS stat={ks_stat:.4f}, p={p_val:.4e})."
        elif p_val < 0.05:
            status = "WATCH"
            msg = f"Moderate distribution shift observed (KS stat={ks_stat:.4f}, p={p_val:.4f})."
        else:
            status = "NORMAL"
            msg = "Distribution stable. No statistically significant drift."

        return {
            "status": status,
            "ks_statistic": round(float(ks_stat), 4),
            "p_value": round(float(p_val), 4),
            "message": msg
        }
