"""
research/leaderboard.py — BTCognitive V3 Quantitative Leaderboard Generator
==========================================================================
Ranks all V3 forecasting models, specialized experts, router, and meta labeler
strictly by Deflated Sharpe Ratio (DSR), exporting to CSV, Parquet, and Markdown.
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESULTS_DIR
from research.evaluator import evaluate_models

logger = logging.getLogger("btcognitive.leaderboard")

LEADERBOARD_CSV_PATH = os.path.join(RESULTS_DIR, "leaderboard.csv")
LEADERBOARD_PARQUET_PATH = os.path.join(RESULTS_DIR, "leaderboard.parquet")
LEADERBOARD_MD_PATH = os.path.join(RESULTS_DIR, "leaderboard.md")


class ModelLeaderboard:
    """
    Ranks models strictly using Deflated Sharpe Ratio (DSR) and exports reports.
    """

    def __init__(self, results_dir: str = RESULTS_DIR):
        self.results_dir = results_dir
        os.makedirs(self.results_dir, exist_ok=True)

    def generate_leaderboard(
        self,
        evaluation_results: Optional[List[Dict[str, Any]]] = None,
        tensors: Optional[np.ndarray] = None,
        y_true: Optional[np.ndarray] = None,
        returns: Optional[np.ndarray] = None
    ) -> pd.DataFrame:
        """
        Builds the ranked leaderboard DataFrame sorted strictly by DSR descending.
        """
        if evaluation_results is None:
            if tensors is None or y_true is None or returns is None:
                # Generate synthetic benchmarking set if no test set passed
                np.random.seed(42)
                n = 100
                tensors = np.random.randn(n, 120, 32).astype(np.float32)
                y_true = np.random.choice([0, 1, 2], size=n, p=[0.45, 0.45, 0.10])
                returns = np.random.normal(loc=0.004, scale=0.015, size=n).astype(np.float32)

            evaluation_results = evaluate_models(tensors, y_true, returns)

        df = pd.DataFrame(evaluation_results)

        # Ensure required columns exist
        expected_cols = ["model", "dsr", "sharpe", "profit_factor", "accuracy", "precision", "recall", "roc_auc"]
        for c in expected_cols:
            if c not in df.columns:
                df[c] = 0.0

        # Strict DSR Ranking: Sort by DSR descending
        df = df.sort_values(by="dsr", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "Rank"

        # Rename columns for professional reporting
        display_df = df.rename(columns={
            "model": "Model",
            "dsr": "DSR",
            "sharpe": "Sharpe",
            "profit_factor": "Profit Factor",
            "accuracy": "Accuracy",
            "precision": "Precision",
            "recall": "Recall",
            "roc_auc": "ROC AUC"
        })

        return display_df

    def export_all(
        self,
        df: pd.DataFrame,
        csv_path: Optional[str] = None,
        parquet_path: Optional[str] = None,
        md_path: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Exports the ranked leaderboard to CSV, Parquet, and Markdown.
        """
        c_path = csv_path or LEADERBOARD_CSV_PATH
        p_path = parquet_path or LEADERBOARD_PARQUET_PATH
        m_path = md_path or LEADERBOARD_MD_PATH

        os.makedirs(os.path.dirname(c_path), exist_ok=True)
        os.makedirs(os.path.dirname(p_path), exist_ok=True)
        os.makedirs(os.path.dirname(m_path), exist_ok=True)

        # 1. Export CSV
        df.to_csv(c_path, index=True)

        # 2. Export Parquet
        # Reset index to store Rank as a column in Parquet
        df.reset_index().to_parquet(p_path, index=False)

        # 3. Export Markdown
        md_table = self._format_markdown_report(df)
        with open(m_path, "w", encoding="utf-8") as f:
            f.write(md_table)

        logger.info(f"Exported leaderboards to {c_path}, {p_path}, {m_path}")

        return {
            "csv": c_path,
            "parquet": p_path,
            "markdown": m_path
        }

    def _format_markdown_report(self, df: pd.DataFrame) -> str:
        """Constructs a clean Markdown table representation."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# BTCognitive V3 — Quantitative Model Leaderboard",
            f"Generated: `{now_str}`",
            "",
            "> [!NOTE]",
            "> Models are strictly ranked by **Deflated Sharpe Ratio (DSR)** to correct for multiple-testing bias and data snooping.",
            "",
            "| Rank | Model | DSR | Sharpe | Profit Factor | Accuracy | Precision | Recall | ROC AUC |",
            "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        ]

        for rank, row in df.iterrows():
            lines.append(
                f"| **#{rank}** | {row['Model']} | **{row['DSR']:.4f}** | {row['Sharpe']:.2f} | "
                f"{row['Profit Factor']:.2f} | {row['Accuracy']*100:.1f}% | {row['Precision']*100:.1f}% | "
                f"{row['Recall']*100:.1f}% | {row['ROC AUC']:.3f} |"
            )

        lines.append("")
        return "\n".join(lines)


# Global Singleton Leaderboard
leaderboard_engine = ModelLeaderboard()


def generate_and_export_leaderboard(
    tensors: Optional[np.ndarray] = None,
    y_true: Optional[np.ndarray] = None,
    returns: Optional[np.ndarray] = None
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Runs evaluation, ranks models by DSR, and exports to CSV, Parquet, and Markdown."""
    df = leaderboard_engine.generate_leaderboard(tensors=tensors, y_true=y_true, returns=returns)
    exports = leaderboard_engine.export_all(df)
    return df, exports
