#!/usr/bin/env python3
"""
BTCognitive CLI Tool
====================
Interactive command-line interface for querying real-time predictions,
market regimes, risk bounds, and SHAP explainability.
"""

import sys
import argparse
import urllib.request
import json


DEFAULT_API_URL = "http://localhost:8000"


def query_api(endpoint: str, base_url: str = DEFAULT_API_URL):
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-CLI/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"\033[91m[Error]\033[0m Failed to query {url}: {e}")
        return None


def cmd_health(args):
    print("\n\033[96m=== BTCognitive Engine Health ===\033[0m")
    data = query_api("/health", args.url)
    if data:
        status_color = "\033[92m" if data.get("status") == "live" else "\033[93m"
        print(f"Status:        {status_color}{data.get('status', 'unknown').upper()}\033[0m")
        print(f"Models Loaded: {data.get('models_loaded')}")
        print(f"Uptime:        {data.get('uptime', 0)} seconds")
        lat = data.get("latency", {})
        print(f"Latency:       Market: {lat.get('market_latency_ms', 0)}ms | Model: {lat.get('prediction_latency_ms', 0)}ms | WS: {lat.get('ws_latency_ms', 0)}ms")
    print()


def cmd_predict(args):
    print("\n\033[96m=== Latest AI Prediction & Uncertainty ===\033[0m")
    data = query_api("/prediction/latest", args.url)
    if data:
        dir_color = "\033[92m" if data.get("direction") == "LONG" else ("\033[91m" if data.get("direction") == "SHORT" else "\033[93m")
        print(f"Direction:       {dir_color}{data.get('direction')} ({data.get('probability_pct')}%\033[0m)")
        print(f"Expected Return: {data.get('expected_return_pct'):+.2f}%")
        print(f"Interval:        {data.get('prediction_interval_str', 'N/A')}")
        print(f"Action:          {data.get('action')}")
        print(f"Model:           {data.get('model')}")
        print(f"Confidence:      {data.get('confidence', 0)*100:.1f}%")
        print(f"Entry Price:     ${data.get('entry_price', 0):,.2f}")
        print(f"Take Profit:     ${data.get('tp', 0):,.2f}")
        print(f"Stop Loss:       ${data.get('sl', 0):,.2f}")
        print(f"\nNarrative: {data.get('uncertainty_narrative', 'N/A')}")
    print()


def cmd_regime(args):
    print("\n\033[96m=== Current Market Regime ===\033[0m")
    data = query_api("/regime/latest", args.url)
    if data:
        print(f"Regime:          {data.get('current_regime')}")
        print(f"Trend:           {data.get('trend_label')} (Score: {data.get('trend_score', 0):.3f})")
        print(f"Volatility:      {data.get('volatility_state')}")
        print(f"Momentum:        {data.get('momentum_state')}")
        print(f"Funding State:   {data.get('funding_state')}")
        print(f"Leverage State:  {data.get('leverage_state')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="BTCognitive CLI — Bitcoin Intelligence & Inference Tool")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="Backend Engine URL (default: http://localhost:8000)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("health", help="Check engine health and latency")
    subparsers.add_parser("predict", help="Get latest AI prediction, risk targets & uncertainty breakdown")
    subparsers.add_parser("regime", help="Get current market regime and macro state")

    args = parser.parse_args()

    if args.command == "health":
        cmd_health(args)
    elif args.command == "predict":
        cmd_predict(args)
    elif args.command == "regime":
        cmd_regime(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
