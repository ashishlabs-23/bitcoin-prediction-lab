"""
research/horizon_model_matrix.py — Model Architecture & Data Source Allocation Router
=====================================================================================
Defines the specialized allocation matrix matching horizons with optimal information families:
- 5m: Hawkes Point-Process + LOB
- 15m: LOB Depth / OFI Imbalance
- 1h: Technical Momentum + Microstructure Residuals
- 4h: Technical Mean Reversion + Derivatives Funding
- 12h: Multi-factor Ridge / Swing Volatility
- 24h: Production Ridge Conformal Regressor
- 48h: Historical Volatility Cone / High Uncertainty
"""

import os
import sys
import pandas as pd
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
REPORTS_DIR = os.path.join(ROOT_DIR, "research", "reports")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def df_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = [str(v) for v in row.values]
        lines.append("| " + " | ".join(row_str) + " |")
    return "\n".join(lines)


def generate_horizon_model_matrix() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    records = [
        {"Horizon": "5m", "Primary Information Family": "Event-Time Order Flow (LOB + Hawkes)", "Architecture Family": "Multivariate Hawkes + Quantile MLP", "Target Focus": "Transient Volatility & Direction", "Governance State": "VALIDATED_SHADOW_MODEL"},
        {"Horizon": "15m", "Primary Information Family": "Order Flow Imbalance (OFI) + Depth", "Architecture Family": "Linear Ridge / Quantile Regressor", "Target Focus": "Short-Term Order Book Liquidity", "Governance State": "RESEARCH"},
        {"Horizon": "1h", "Primary Information Family": "OHLCV Momentum + OFI Residuals", "Architecture Family": "Gradient Boosted Tree / Ridge", "Target Focus": "Intraday Momentum & Excursions", "Governance State": "RESEARCH"},
        {"Horizon": "4h", "Primary Information Family": "Perpetual Funding Rate + ATR", "Architecture Family": "Conditional Hurdle Regressor", "Target Focus": "Mean Reversion & Volatility Range", "Governance State": "RESEARCH"},
        {"Horizon": "12h", "Primary Information Family": "Multi-Factor Technical + Volatility", "Architecture Family": "Ridge Conformal Regressor", "Target Focus": "Intermediate Session Bounds", "Governance State": "RESEARCH"},
        {"Horizon": "24h", "Primary Information Family": "Macro Realized Volatility + 24h Structure", "Architecture Family": "Ridge Conformal Regressor v3.0.0", "Target Focus": "Daily Structural Risk Envelope", "Governance State": "PRODUCTION"},
        {"Horizon": "48h", "Primary Information Family": "Long-Term Macro Trend & Volatility", "Architecture Family": "Historical Volatility Cone", "Target Focus": "Multi-Day Regime Dispersion", "Governance State": "RESEARCH_EXPERIMENTAL"}
    ]
    df_matrix = pd.DataFrame(records)

    csv_path = os.path.join(RESULTS_DIR, "horizon_model_matrix.csv")
    df_matrix.to_csv(csv_path, index=False)

    report_path = os.path.join(REPORTS_DIR, "horizon_model_selection.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🧭 Horizon-Specific Model & Data Allocation Guide\n\n")
        f.write("## 1. Allocation Matrix\n\n")
        f.write(df_to_markdown(df_matrix))
        f.write("\n\n## 2. Decoupled Architecture Rationale\n\n")
        f.write("Attempting to force a single monolithic model across all horizons dilutes specialized predictive features. Decoupling high-frequency event dynamics (5m) from structural daily volatility (24h) maximizes signal retention.\n")

    return df_matrix, {"status": "ALLOCATION_MATRIX_GENERATED"}


if __name__ == "__main__":
    df_m, meta = generate_horizon_model_matrix()
    print("=== HORIZON MODEL ALLOCATION MATRIX ===")
    print(df_m.to_string(index=False))
