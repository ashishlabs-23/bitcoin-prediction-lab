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
    def test_cmd_predict(self, mock_urlopen):
        mock_res = MagicMock()
        mock_res.read.return_value = b'{"direction": "LONG", "probability_pct": 80.5, "expected_return_pct": 2.1, "action": "TAKE_LONG", "confidence": 0.85}'
        mock_urlopen.return_value.__enter__.return_value = mock_res

        args = MagicMock()
        args.url = "http://localhost:8000"
        
        cli.cmd_predict(args)


if __name__ == "__main__":
    unittest.main()
