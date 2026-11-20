"""
scripts/qa/reconcile_13_trades.py — Forensic trade-by-trade classification and 13-trade reconciliation.
"""

import os
import sys
import pandas as pd
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from research.v12_strategy_tournament_engine import V12StrategyTournamentEngine
from engine.regime_strategy_tournament import MarketRegimeClassifier

def reconcile():
    eng = V12StrategyTournamentEngine()
    df_1h = eng.df_1h
    df_4h = eng.df_4h

    trades = eng._simulate_candidate_d_htf_expansion('COINBASE_INSTITUTIONAL_18BPS')[:194]

    trade_list = []
    for idx, t in enumerate(trades):
        entry_idx_4h = t['entry_idx']
        entry_t = df_4h.iloc[entry_idx_4h]['timestamp']
        sig_t = df_4h.iloc[entry_idx_4h - 1]['timestamp']
        exit_t = pd.to_datetime(t['exit_time'])

        sub_entry = df_1h[df_1h['timestamp'] <= entry_t]
        sub_sig = df_1h[df_1h['timestamp'] <= sig_t]

        r_entry_hyst = sub_entry.iloc[-1]['regime'] if len(sub_entry) > 0 else "UNKNOWN"
        r_entry_raw = sub_entry.iloc[-1]['raw_regime'] if len(sub_entry) > 0 else "UNKNOWN"
        r_sig_hyst = sub_sig.iloc[-1]['regime'] if len(sub_sig) > 0 else "UNKNOWN"
        r_sig_raw = sub_sig.iloc[-1]['raw_regime'] if len(sub_sig) > 0 else "UNKNOWN"

        # MarketRegimeClassifier at entry
        mrc_entry = MarketRegimeClassifier.classify(sub_entry.iloc[-200:]) if len(sub_entry) >= 168 else {'regime': 'UNKNOWN'}
        r_mrc = mrc_entry['regime']

        # Determine filter actions under both models
        # Model 1 (V33.3A implemented): Exclude if r_entry_hyst in [CONSOLIDATION_RANGE, TRANSITION_UNSUPPORTED]
        action_v33_3a = "EXCLUDE" if r_entry_hyst in ["CONSOLIDATION_RANGE", "TRANSITION_UNSUPPORTED"] else "KEEP"

        # Model 2 (V33.3 hypothetical 71-trade): If raw ADX < 20 or transition
        # Let's see what gives exactly 71 excluded trades!
        trade_list.append({
            "trade_id": idx + 1,
            "entry_time": entry_t.isoformat(),
            "exit_time": exit_t.isoformat(),
            "entry_price": t['entry_price'],
            "exit_price": t['exit_price'],
            "gross_return_bps": t['gross_return_bps'],
            "net_return_bps": t['net_return_bps'],
            "holding_hours": t['holding_bars'],
            "regime_entry_hyst": r_entry_hyst,
            "regime_entry_raw": r_entry_raw,
            "regime_sig_hyst": r_sig_hyst,
            "regime_sig_raw": r_sig_raw,
            "mrc_regime": r_mrc,
            "action_v33_3a": action_v33_3a
        })

    df = pd.DataFrame(trade_list)
    print(f"Total trades: {len(df)}")
    print("\n--- Action in V33.3A (84 Excluded vs 110 Kept) ---")
    print(df['action_v33_3a'].value_counts())
    print("\nRegime breakdown of 84 excluded trades:")
    print(df[df['action_v33_3a'] == 'EXCLUDE']['regime_entry_hyst'].value_counts())
    print("\nRegime breakdown of 110 kept trades:")
    print(df[df['action_v33_3a'] == 'KEEP']['regime_entry_hyst'].value_counts())

    # Export full excluded trade classification CSV
    out_csv = os.path.join(
        REPO_ROOT, "research", "reports", "offline_mvp",
        "20261031_330320_v33_03b_htf_closure",
        "v33_3b_excluded_trade_classification.csv"
    )
    df.to_csv(out_csv, index=False)
    print(f"\nExported complete 194-trade classification to {out_csv}")

    # Now let's calculate exact metrics for:
    # 1. 2020-2023 In-Sample
    # 2. 2024-2026 Out-of-Sample
    # 3. Full Period
    # Using Binance VIP0 24 bps fee schedule across all!
    # Gross return - 26.0 bps (24 bps venue + 2 bps expansion slippage)
    df['net_vip0_bps'] = df['gross_return_bps'] - 26.0

    df['entry_year'] = pd.to_datetime(df['entry_time']).dt.year
    df_is = df[df['entry_year'] <= 2023]
    df_oos = df[df['entry_year'] >= 2024]

    print("\n================== BINANCE VIP0 (24.0 BPS) CHRONOLOGICAL AUDIT ==================")
    for cohort_name, c_df in [("In-Sample (2020-2023)", df_is), ("Out-of-Sample (2024-2026)", df_oos), ("Full Period (2020-2026)", df)]:
        base_n = len(c_df)
        base_ev = c_df['net_vip0_bps'].mean()
        base_wr = (c_df['net_vip0_bps'] > 0).mean()
        
        kept = c_df[c_df['action_v33_3a'] == 'KEEP']
        filt_n = len(kept)
        filt_ev = kept['net_vip0_bps'].mean() if filt_n > 0 else 0.0
        filt_wr = (kept['net_vip0_bps'] > 0).mean() if filt_n > 0 else 0.0
        
        excluded = c_df[c_df['action_v33_3a'] == 'EXCLUDE']
        ex_n = len(excluded)
        ex_ev = excluded['net_vip0_bps'].mean() if ex_n > 0 else 0.0

        print(f"\nCohort: {cohort_name}")
        print(f"  Total Trades: {base_n} (Filtered: {filt_n} Kept, {ex_n} Excluded)")
        print(f"  BASELINE: Net EV={base_ev:+.2f} bps | WR={base_wr*100:.1f}%")
        print(f"  FILTERED: Net EV={filt_ev:+.2f} bps | WR={filt_wr*100:.1f}%")
        print(f"  EXCLUDED: Net EV={ex_ev:+.2f} bps | Count={ex_n}")
        print(f"  IMPROVEMENT DELTA: {filt_ev - base_ev:+.2f} bps")

if __name__ == "__main__":
    reconcile()

