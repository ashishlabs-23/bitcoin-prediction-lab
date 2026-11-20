"""
scripts/qa/reproduce_htf_trades.py — Forensic trade reproduction and reconciliation for V33.3A.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine
from engine.regime_strategy_tournament import MarketRegimeClassifier

def run_forensic_reproduction():
    engine = V12StrategyTournamentEngine()
    df_1h = engine.df_1h
    df_4h = engine.df_4h

    # 1. Run simulation for Institutional 18.6 bps
    trades_inst = engine._simulate_candidate_d_htf_expansion(cost_scenario="COINBASE_INSTITUTIONAL_18BPS")
    print(f"Total trades reproduced: {len(trades_inst)}")

    # 2. Extract detailed trade records
    trade_records = []
    regime_counts = {}
    regime_returns = {}

    for idx, t in enumerate(trades_inst):
        entry_ts = pd.to_datetime(t["entry_time"])
        exit_ts = pd.to_datetime(t["exit_time"])
        
        # Find 1h bar corresponding to entry
        sub_1h = df_1h[df_1h["timestamp"] <= entry_ts]
        regime_1h = sub_1h.iloc[-1]["regime"] if len(sub_1h) > 0 else "UNKNOWN"
        raw_regime_1h = sub_1h.iloc[-1]["raw_regime"] if len(sub_1h) > 0 else "UNKNOWN"

        # Also run MarketRegimeClassifier on preceding 168 1h bars
        if len(sub_1h) >= 168:
            cls_res = MarketRegimeClassifier.classify(sub_1h.iloc[-200:])
            clf_regime = cls_res["regime"]
        else:
            clf_regime = "INSUFFICIENT_HISTORY"

        t_copy = dict(t)
        t_copy["trade_id"] = idx + 1
        t_copy["regime_at_entry"] = regime_1h
        t_copy["raw_regime_at_entry"] = raw_regime_1h
        t_copy["classifier_regime"] = clf_regime
        t_copy["filter_action"] = "EXCLUDE" if regime_1h in ["CONSOLIDATION_RANGE", "TRANSITION_UNSUPPORTED"] else "KEEP"

        trade_records.append(t_copy)

        regime_counts[regime_1h] = regime_counts.get(regime_1h, 0) + 1
        regime_returns.setdefault(regime_1h, []).append(t["net_return_bps"])

    df_trades = pd.DataFrame(trade_records)

    print("\n--- REGIME BREAKDOWN (Institutional 18.6 bps) ---")
    weighted_sum = 0.0
    for r, counts in regime_counts.items():
        rets = regime_returns[r]
        mean_ret = float(np.mean(rets))
        win_rate = float(np.mean([1 if x > 0 else 0 for x in rets]))
        weighted_sum += counts * mean_ret
        print(f"Regime: {r:<25} Count: {counts:<4} Mean Net EV: {mean_ret:+6.2f} bps | Win Rate: {win_rate*100:5.1f}%")

    weighted_mean = weighted_sum / len(df_trades)
    arithmetic_mean = float(df_trades["net_return_bps"].mean())
    print(f"\nWeighted mean across regimes: {weighted_mean:+.2f} bps")
    print(f"Direct arithmetic mean net EV: {arithmetic_mean:+.2f} bps")

    # Save complete 194-trade ledger to CSV
    out_csv = os.path.join(
        "research", "reports", "offline_mvp",
        "20261031_330310_v33_03a_htf_validation",
        "v33_3a_194_trade_event_ledger.csv"
    )
    df_trades.to_csv(out_csv, index=False)
    print(f"\nSaved trade ledger to {out_csv}")

    # Compute Drawdown comparison
    # Compounded equity curve calculation
    def compute_equity_and_mdd(returns_bps):
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns_bps:
            equity *= (1.0 + (r / 10000.0))
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        return equity, max_dd

    eq_all, mdd_all = compute_equity_and_mdd(df_trades["net_return_bps"])
    kept_trades = df_trades[df_trades["filter_action"] == "KEEP"]
    eq_kept, mdd_kept = compute_equity_and_mdd(kept_trades["net_return_bps"])

    print(f"\nSequential Compounded Portfolio MDD:")
    print(f"All 194 trades: Final Equity = {eq_all:.4f}, Max Drawdown = {mdd_all*100:.2f}%")
    print(f"Filtered (KEEP) trades ({len(kept_trades)} trades): Final Equity = {eq_kept:.4f}, Max Drawdown = {mdd_kept*100:.2f}%")
    print(f"Filtered Mean Net EV = {kept_trades['net_return_bps'].mean():+.2f} bps, Win Rate = {(kept_trades['net_return_bps'] > 0).mean()*100:.1f}%")

if __name__ == "__main__":
    run_forensic_reproduction()
