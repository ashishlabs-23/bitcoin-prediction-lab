"""
Unit Tests for BTCognitive CLI Tool
==================================
Tests argument parsing and mock query routing for terminal commands.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cli


class TestCLI(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_cmd_health(self, mock_urlopen):
        mock_res = MagicMock()
        mock_res.read.return_value = b'{"status": "live", "models_loaded": true, "uptime": 50, "latency": {"market_latency_ms": 10}}'
        mock_urlopen.return_value.__enter__.return_value = mock_res

        args = MagicMock()
        args.url = "http://localhost:8000"
        
        # Should execute without throwing
        cli.cmd_health(args)

    @patch("urllib.request.urlopen")
    def test_cmd_terminal(self, mock_urlopen):
        mock_res = MagicMock()
        mock_res.read.return_value = b'{"four_questions": {"1_expected_volatility": {"point_forecast_har_rs_dow": 0.12}, "2_uncertainty_risk_envelope": {"lower_bound_variance": 0.04, "upper_bound_variance": 0.22}, "3_current_regime": {"macro_epoch": "SPOT_ETF_ERA"}, "4_operational_calibration_trust": {"calibration_health_status": "STABLE"}}}'
        mock_urlopen.return_value.__enter__.return_value = mock_res

        args = MagicMock()
        args.url = "http://localhost:8000"
        
        cli.cmd_terminal(args)

    @patch("urllib.request.urlopen")
    def test_cmd_observatory(self, mock_urlopen):
        mock_res = MagicMock()
        mock_res.read.return_value = b'{"status": "STABLE", "status_rationale": "Normal operation", "total_resolved_forecasts": 10, "pending_unresolved_forecasts": 5, "coverage_30d_pct": 91.5, "coverage_90d_pct": 92.0, "coverage_all_pct": 92.5, "upper_breach_30d_pct": 4.0, "lower_breach_30d_pct": 4.5, "tail_asymmetry_30d_pct": 0.5, "mean_winkler_30d": 0.20, "valid_N": 10, "pending_N": 5, "data_invalid_N": 0, "hash_failures": 0, "abstained_N": 0, "census_verified": true, "prospective_experiment_id": "EXP-PROSPECTIVE-HAR-RS-DOW-2026-v1.0", "prospective_epoch_id": "EPOCH-2026-08-PROSPECTIVE-01", "prospective_audit_status": "ACCUMULATING"}'
        mock_urlopen.return_value.__enter__.return_value = mock_res

        args = MagicMock()
        args.url = "http://localhost:8000"
        
        cli.cmd_observatory(args)


if __name__ == "__main__":
    unittest.main()
