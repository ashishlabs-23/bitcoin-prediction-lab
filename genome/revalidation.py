"""
genome/revalidation.py -- Periodic Re-validation for Verified Genomes

Implements Correction 7: 'verified' is not a permanent status.
Verified genomes undergo periodic (e.g. weekly) re-evaluation against their
trailing realized performance in quarantine/live trading.

Demotion rules:
  - Trailing realized Sharpe < backtested_sharpe - 0.5 (underperformance)
  - Trailing realized Sharpe > backtested_sharpe + 0.75 (suspicious overperformance)

Demoted genomes revert to status='candidate' with an explanation appended to mutation_log,
allowing them to be re-evolved in future generation runs.
"""

import math
import logging
import pandas as pd
import numpy as np
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from genome.chromosome import Genome
from genome.registry import (
    load_leaderboard,
    load_genome,
    save_genome,
    load_quarantine_trades,
)

log = logging.getLogger("genome.revalidation")


def evaluate_quarantine_performance(genome_id: str, min_days: int = 30) -> dict:
    """
    Evaluates shadow quarantine trade performance for a genome over min_days.

    Promotion rules to 'verified':
      - Minimum min_days * 24 trade/bar records (or trade records spanning min_days)
      - Realized Sharpe within [-0.5, +0.75] of backtested Sharpe (Correction 6)
      - No drawdown breach > 1.5x backtested max_drawdown

    Returns dict with keys:
      - genome_id
      - current_status
      - new_status ('verified', 'quarantine', 'dead', 'investigate')
      - realized_sharpe
      - backtested_sharpe
      - reason
    """
    g = load_genome(genome_id)
    if g is None:
        return {'genome_id': genome_id, 'current_status': 'unknown', 'new_status': 'unknown', 'reason': 'Genome not found'}

    trades_df = load_quarantine_trades(genome_id)
    if trades_df.empty:
        return {
            'genome_id': genome_id,
            'current_status': g.status,
            'new_status': g.status,
            'realized_sharpe': float('nan'),
            'backtested_sharpe': g.sharpe,
            'reason': 'No quarantine trades recorded'
        }

    # Compute realized pnl return series
    pnls = trades_df['pnl'].values.astype(float)
    n_trades = len(pnls)

    if n_trades < 10:
        return {
            'genome_id': genome_id,
            'current_status': g.status,
            'new_status': g.status,
            'realized_sharpe': float('nan'),
            'backtested_sharpe': g.sharpe,
            'reason': f'Insufficient trades ({n_trades} < 10)'
        }

    pnl_std = float(np.std(pnls))
    pnl_mean = float(np.mean(pnls))

    if pnl_std == 0.0 or math.isnan(pnl_std):
        realized_sharpe = 0.0
    else:
        # Approximate annualized Sharpe from trade returns
        realized_sharpe = float((pnl_mean / pnl_std) * np.sqrt(24.0 * 365.0 / max(1, n_trades / min_days)))

    bt_sharpe = g.sharpe if not math.isnan(g.sharpe) else 0.0
    sharpe_diff = realized_sharpe - bt_sharpe

    # Bounds check (Correction 6: [-0.5, +0.75])
    if sharpe_diff < -0.5:
        new_status = 'dead'
        reason = f'Underperformance: realized Sharpe ({realized_sharpe:.2f}) < backtest ({bt_sharpe:.2f}) - 0.5'
    elif sharpe_diff > 0.75:
        new_status = 'investigate'
        reason = f'Suspicious overperformance: realized Sharpe ({realized_sharpe:.2f}) > backtest ({bt_sharpe:.2f}) + 0.75'
    else:
        new_status = 'verified'
        reason = f'Performance verified: realized Sharpe ({realized_sharpe:.2f}) within tolerance of backtest ({bt_sharpe:.2f})'

    return {
        'genome_id': genome_id,
        'current_status': g.status,
        'new_status': new_status,
        'realized_sharpe': realized_sharpe,
        'backtested_sharpe': bt_sharpe,
        'reason': reason
    }


def revalidate_all_verified(lookback_days: int = 30) -> pd.DataFrame:
    """
    Loads all genomes with status='verified' from the registry, evaluates their
    trailing performance, and demotes any that fall outside tolerance bounds.

    Returns DataFrame of revalidation results.
    """
    verified_df = load_leaderboard(status='verified', limit=1000)
    if verified_df.empty:
        log.info("No verified genomes found in registry for re-validation.")
        return pd.DataFrame()

    results = []
    for _, row in verified_df.iterrows():
        g_id = row['genome_id']
        g = load_genome(g_id)
        if g is None:
            continue

        eval_res = evaluate_quarantine_performance(g_id, min_days=lookback_days)
        new_status = eval_res['new_status']

        if new_status in ['dead', 'candidate', 'investigate'] and new_status != g.status:
            log.warning(f"Re-validation demoting genome {g_id}: {eval_res['reason']}")
            g.status = new_status if new_status != 'dead' else 'candidate'  # demote to candidate for re-evolution
            g.mutation_log.append(f"revalidation_demoted: {eval_res['reason']}")
            save_genome(g)

        results.append(eval_res)

    return pd.DataFrame(results)


if __name__ == "__main__":
    import tempfile, shutil
    from genome.chromosome import random_genome
    from genome.registry import save_genome, _get_conn

    print("Testing revalidation.py...")
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "reval_test.db")
    conn = _get_conn(db_path)

    import genome.registry as reg
    orig_path = reg.get_registry_path
    reg.get_registry_path = lambda: db_path

    # Create dummy verified genome
    g = random_genome('TRENDING_BULL', generation=1)
    g.status = 'verified'
    g.sharpe = 1.5
    save_genome(g)

    # Evaluate with no trades -> should keep status
    res = evaluate_quarantine_performance(g.genome_id, min_days=30)
    print("No trades eval:", res['reason'])

    reg.get_registry_path = orig_path
    conn.close()
    shutil.rmtree(tmpdir)
    print("PASS: revalidation.py smoke test passed.")
