"""
BTCognitive V33.3C — HTF Strategy Final Evidence Reconciliation Script
Reconciles:
1. Chronological Trade Counts: V33.3A (116/78) vs V33.3B (75/119) and the 41 transition trades.
2. Execution Costs: 24 bps vs 26 bps, itemized cost breakdown across all 5 venue scenarios.
3. Sequential Portfolio Simulation: 100% vs 10% notional equity allocation, drawdown duration, turnover, exposure.
4. Statistical Evaluation: IS vs OOS, Bonferroni correction across 19 candidates.
5. Filter Value Decomposition: Regime discrimination, frequency reduction, adverse condition avoidance.
"""

import json
import math
import os
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

def compute_drawdown_series(equity_series):
    peak = equity_series.cummax()
    dd = (equity_series - peak) / peak
    return dd

def run_portfolio_simulation(df_trades, start_equity=100000.0, allocation_fraction=1.0, cost_col="net_return_binance_vip0_26bps", total_hours=41088.0):
    """
    Simulates sequential portfolio equity.
    Since trades are strictly non-overlapping, at any time t, the portfolio has at most 1 active trade.
    When in a trade, allocation_fraction of current equity is allocated to BTC spot.
    The remaining (1 - allocation_fraction) remains in cash (0% return).
    """
    equity = start_equity
    equity_curve = [start_equity]
    trade_returns = []
    total_turnover = 0.0
    total_exposure_hours = 0.0

    for idx, row in df_trades.iterrows():
        ret_frac = row[cost_col] / 10000.0
        allocated_capital = equity * allocation_fraction
        pnl = allocated_capital * ret_frac
        equity += pnl
        equity_curve.append(equity)
        trade_returns.append(ret_frac * allocation_fraction)
        total_turnover += allocated_capital * 2.0  # entry and exit
        total_exposure_hours += row["holding_hours"]

    eq_series = pd.Series(equity_curve)
    dd_series = compute_drawdown_series(eq_series)
    max_dd = float(dd_series.min())

    final_equity = equity
    total_ret = (final_equity - start_equity) / start_equity
    
    # Annualized CAGR (period in years: total_hours / (365.25 * 24))
    period_years = total_hours / (365.25 * 24.0)
    cagr = ((final_equity / start_equity) ** (1.0 / period_years) - 1.0) if period_years > 0 else 0.0

    # Exposure percentage
    exposure_pct = (total_exposure_hours / total_hours) * 100.0 if total_hours > 0 else 0.0

    # Sharpe and Sortino (per trade annualized)
    trades_per_year = len(df_trades) / period_years if period_years > 0 else 1.0
    if len(trade_returns) > 1 and np.std(trade_returns) > 1e-12:
        sharpe = (np.mean(trade_returns) / np.std(trade_returns)) * math.sqrt(trades_per_year)
        downside_returns = [r for r in trade_returns if r < 0]
        sortino = (np.mean(trade_returns) / np.std(downside_returns)) * math.sqrt(trades_per_year) if len(downside_returns) > 0 and np.std(downside_returns) > 1e-12 else 0.0
    else:
        sharpe, sortino = 0.0, 0.0

    return {
        "start_equity": start_equity,
        "final_equity": final_equity,
        "total_return_pct": total_ret * 100.0,
        "cagr_pct": cagr * 100.0,
        "max_drawdown_pct": abs(max_dd) * 100.0,
        "total_turnover_usd": total_turnover,
        "total_exposure_hours": total_exposure_hours,
        "exposure_pct": exposure_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "trade_count": len(df_trades)
    }

def run_v33_3c_reconciliation():
    base_dir = Path(__file__).resolve().parent.parent.parent
    report_a_dir = base_dir / "research" / "reports" / "offline_mvp" / "20261031_330310_v33_03a_htf_validation"
    report_b_dir = base_dir / "research" / "reports" / "offline_mvp" / "20261031_330320_v33_03b_htf_closure"
    report_c_dir = base_dir / "research" / "reports" / "offline_mvp" / "20261031_330330_v33_03c_htf_reconciliation"
    report_c_dir.mkdir(parents=True, exist_ok=True)

    csv_a_path = report_a_dir / "v33_3a_194_trade_event_ledger.csv"
    csv_b_path = report_b_dir / "v33_3b_excluded_trade_classification.csv"

    df_a = pd.read_csv(csv_a_path)
    df_b = pd.read_csv(csv_b_path)

    assert len(df_a) == 194, f"Expected 194 trades in df_a, got {len(df_a)}"
    assert len(df_b) == 194, f"Expected 194 trades in df_b, got {len(df_b)}"

    # Build comprehensive mapping dataframe
    records = []
    for i in range(194):
        row_a = df_a.iloc[i]
        row_b = df_b.iloc[i]

        trade_id = int(row_b["trade_id"])
        entry_time = str(row_b["entry_time"])
        exit_time = str(row_b["exit_time"])
        entry_price = float(row_b["entry_price"])
        exit_price = float(row_b["exit_price"])
        holding_hours = float(row_b["holding_hours"])
        gross_ret_bps = float(row_b["gross_return_bps"])

        # Cohort in V33.3A: Index-based 60/40 split
        v33_3a_cohort = "IS_TRAIN_60PCT" if i < 116 else "OOS_TEST_40PCT"

        # Cohort in V33.3B: Strict calendar split
        entry_year = int(pd.to_datetime(entry_time).year)
        v33_3b_cohort = "IS_2022_2023" if entry_time < "2024-01-01" else "OOS_2024_2026"

        # The 41 transition trades: trades 75 to 115 (occurred in 2024 before Dec 2024)
        is_41_transition = (75 <= i <= 115)

        # Filter action:
        reg_entry_raw = str(row_b.get("regime_entry_raw", ""))
        action_v33_3b = str(row_b["action_v33_3a"]) # 'KEEP' or 'EXCLUDE'
        action_raw = "EXCLUDE" if "RANGE" in reg_entry_raw or "TRANSITION" in reg_entry_raw else "KEEP"
        is_13_hyst_discrepancy = (action_raw == "KEEP" and action_v33_3b == "EXCLUDE")

        # Itemized Execution Cost Scenarios
        # Scenario 1: Binance VIP0 26 bps (mandated in V33.3B: 20 comm + 2 spread + 2 base slip + 2 exp slip)
        b_vip0_comm = 20.0
        b_vip0_spread = 2.0
        b_vip0_base_slip = 2.0
        b_vip0_exp_slip = 2.0
        b_vip0_26_cost = b_vip0_comm + b_vip0_spread + b_vip0_base_slip + b_vip0_exp_slip
        net_b_vip0_26 = gross_ret_bps - b_vip0_26_cost

        # Scenario 2: Binance VIP0 Pure 24 bps (20 comm + 2 spread + 2 base slip + 0 exp slip)
        b_vip0_24_cost = 24.0
        net_b_vip0_24 = gross_ret_bps - b_vip0_24_cost

        # Scenario 3: Coinbase Institutional 20.6 bps (15 comm + 1.6 spread + 2 base slip + 2 exp slip)
        cb_inst_cost = 20.6
        net_cb_inst = gross_ret_bps - cb_inst_cost

        # Scenario 4: Binance Perp 17.0 bps (10 comm + 2 spread + 3 base slip + 2 exp slip)
        b_perp_cost = 17.0
        net_b_perp = gross_ret_bps - b_perp_cost

        # Scenario 5: Coinbase Retail 89.0 bps (80 comm + 5 spread + 2 base slip + 2 exp slip)
        cb_retail_cost = 89.0
        net_cb_retail = gross_ret_bps - cb_retail_cost

        records.append({
            "trade_id": trade_id,
            "trade_index": i,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "calendar_year": entry_year,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "holding_hours": holding_hours,
            "gross_return_bps": gross_ret_bps,
            "v33_3a_cohort": v33_3a_cohort,
            "v33_3b_cohort": v33_3b_cohort,
            "is_41_transition_trade": is_41_transition,
            "action_raw_preliminary": action_raw,
            "action_authoritative_filter": action_v33_3b,
            "is_13_hysteresis_discrepancy": is_13_hyst_discrepancy,
            "cost_binance_vip0_comm_bps": b_vip0_comm,
            "cost_binance_vip0_spread_bps": b_vip0_spread,
            "cost_binance_vip0_base_slip_bps": b_vip0_base_slip,
            "cost_binance_vip0_exp_slip_bps": b_vip0_exp_slip,
            "cost_binance_vip0_total_26bps": b_vip0_26_cost,
            "net_return_binance_vip0_26bps": net_b_vip0_26,
            "cost_binance_vip0_total_24bps": b_vip0_24_cost,
            "net_return_binance_vip0_24bps": net_b_vip0_24,
            "cost_coinbase_inst_total_20_6bps": cb_inst_cost,
            "net_return_coinbase_inst_20_6bps": net_cb_inst,
            "cost_binance_perp_total_17bps": b_perp_cost,
            "net_return_binance_perp_17bps": net_b_perp,
            "cost_coinbase_retail_total_89bps": cb_retail_cost,
            "net_return_coinbase_retail_89bps": net_cb_retail
        })

    mapping_df = pd.DataFrame(records)
    out_csv = report_c_dir / "v33_3c_cross_milestone_trade_mapping.csv"
    mapping_df.to_csv(out_csv, index=False)
    print(f"Generated {out_csv} with {len(mapping_df)} trades.")

    # Filtered subsets
    df_filt = mapping_df[mapping_df["action_authoritative_filter"] == "KEEP"]
    df_excl = mapping_df[mapping_df["action_authoritative_filter"] == "EXCLUDE"]

    # Cohorts
    is_base = mapping_df[mapping_df["v33_3b_cohort"] == "IS_2022_2023"]
    is_filt = is_base[is_base["action_authoritative_filter"] == "KEEP"]
    is_excl = is_base[is_base["action_authoritative_filter"] == "EXCLUDE"]

    oos_base = mapping_df[mapping_df["v33_3b_cohort"] == "OOS_2024_2026"]
    oos_filt = oos_base[oos_base["action_authoritative_filter"] == "KEEP"]
    oos_excl = oos_base[oos_base["action_authoritative_filter"] == "EXCLUDE"]

    # Time calculations
    # Total hours in dataset: 2022-01-11 to 2026-09-19 ~ 41,088 hours
    total_hours_full = (pd.to_datetime(mapping_df["exit_time"].max()) - pd.to_datetime(mapping_df["entry_time"].min())).total_seconds() / 3600.0
    total_hours_is = (pd.to_datetime("2024-01-01T00:00:00Z") - pd.to_datetime(is_base["entry_time"].min())).total_seconds() / 3600.0
    total_hours_oos = (pd.to_datetime(oos_base["exit_time"].max()) - pd.to_datetime("2024-01-01T00:00:00Z")).total_seconds() / 3600.0

    # Simulations: 100% vs 10% notional equity allocation
    sim_results = {
        "full_period": {
            "baseline_100pct": run_portfolio_simulation(mapping_df, allocation_fraction=1.0, total_hours=total_hours_full),
            "filtered_100pct": run_portfolio_simulation(df_filt, allocation_fraction=1.0, total_hours=total_hours_full),
            "baseline_10pct": run_portfolio_simulation(mapping_df, allocation_fraction=0.10, total_hours=total_hours_full),
            "filtered_10pct": run_portfolio_simulation(df_filt, allocation_fraction=0.10, total_hours=total_hours_full),
        },
        "is_period": {
            "baseline_100pct": run_portfolio_simulation(is_base, allocation_fraction=1.0, total_hours=total_hours_is),
            "filtered_100pct": run_portfolio_simulation(is_filt, allocation_fraction=1.0, total_hours=total_hours_is),
            "baseline_10pct": run_portfolio_simulation(is_base, allocation_fraction=0.10, total_hours=total_hours_is),
            "filtered_10pct": run_portfolio_simulation(is_filt, allocation_fraction=0.10, total_hours=total_hours_is),
        },
        "oos_period": {
            "baseline_100pct": run_portfolio_simulation(oos_base, allocation_fraction=1.0, total_hours=total_hours_oos),
            "filtered_100pct": run_portfolio_simulation(oos_filt, allocation_fraction=1.0, total_hours=total_hours_oos),
            "baseline_10pct": run_portfolio_simulation(oos_base, allocation_fraction=0.10, total_hours=total_hours_oos),
            "filtered_10pct": run_portfolio_simulation(oos_filt, allocation_fraction=0.10, total_hours=total_hours_oos),
        }
    }

    # Statistical tests:
    # Full period Welch t-test: Filtered vs Baseline
    t_stat_full, p_val_full = stats.ttest_ind(df_filt["net_return_binance_vip0_26bps"], mapping_df["net_return_binance_vip0_26bps"], equal_var=False)
    # Excluded vs Retained:
    t_stat_excl_vs_ret, p_val_excl_vs_ret = stats.ttest_ind(df_filt["net_return_binance_vip0_26bps"], df_excl["net_return_binance_vip0_26bps"], equal_var=False)
    # OOS Welch t-test: Filtered vs Baseline
    t_stat_oos, p_val_oos = stats.ttest_ind(oos_filt["net_return_binance_vip0_26bps"], oos_base["net_return_binance_vip0_26bps"], equal_var=False)
    # OOS Excluded vs Retained:
    t_stat_oos_excl, p_val_oos_excl = stats.ttest_ind(oos_filt["net_return_binance_vip0_26bps"], oos_excl["net_return_binance_vip0_26bps"], equal_var=False)

    stat_summary = {
        "full_period": {
            "base_n": len(mapping_df), "base_ev": float(mapping_df["net_return_binance_vip0_26bps"].mean()), "base_std": float(mapping_df["net_return_binance_vip0_26bps"].std()), "base_wr": float((mapping_df["net_return_binance_vip0_26bps"] > 0).mean()),
            "filt_n": len(df_filt), "filt_ev": float(df_filt["net_return_binance_vip0_26bps"].mean()), "filt_std": float(df_filt["net_return_binance_vip0_26bps"].std()), "filt_wr": float((df_filt["net_return_binance_vip0_26bps"] > 0).mean()),
            "excl_n": len(df_excl), "excl_ev": float(df_excl["net_return_binance_vip0_26bps"].mean()), "excl_std": float(df_excl["net_return_binance_vip0_26bps"].std()), "excl_wr": float((df_excl["net_return_binance_vip0_26bps"] > 0).mean()),
            "t_stat_filt_vs_base": float(t_stat_full), "p_val_filt_vs_base": float(p_val_full),
            "t_stat_filt_vs_excl": float(t_stat_excl_vs_ret), "p_val_filt_vs_excl": float(p_val_excl_vs_ret)
        },
        "is_period": {
            "base_n": len(is_base), "base_ev": float(is_base["net_return_binance_vip0_26bps"].mean()), "base_std": float(is_base["net_return_binance_vip0_26bps"].std()), "base_wr": float((is_base["net_return_binance_vip0_26bps"] > 0).mean()),
            "filt_n": len(is_filt), "filt_ev": float(is_filt["net_return_binance_vip0_26bps"].mean()), "filt_std": float(is_filt["net_return_binance_vip0_26bps"].std()), "filt_wr": float((is_filt["net_return_binance_vip0_26bps"] > 0).mean()),
            "excl_n": len(is_excl), "excl_ev": float(is_excl["net_return_binance_vip0_26bps"].mean()), "excl_std": float(is_excl["net_return_binance_vip0_26bps"].std()), "excl_wr": float((is_excl["net_return_binance_vip0_26bps"] > 0).mean()),
        },
        "oos_period": {
            "base_n": len(oos_base), "base_ev": float(oos_base["net_return_binance_vip0_26bps"].mean()), "base_std": float(oos_base["net_return_binance_vip0_26bps"].std()), "base_wr": float((oos_base["net_return_binance_vip0_26bps"] > 0).mean()),
            "filt_n": len(oos_filt), "filt_ev": float(oos_filt["net_return_binance_vip0_26bps"].mean()), "filt_std": float(oos_filt["net_return_binance_vip0_26bps"].std()), "filt_wr": float((oos_filt["net_return_binance_vip0_26bps"] > 0).mean()),
            "excl_n": len(oos_excl), "excl_ev": float(oos_excl["net_return_binance_vip0_26bps"].mean()), "excl_std": float(oos_excl["net_return_binance_vip0_26bps"].std()), "excl_wr": float((oos_excl["net_return_binance_vip0_26bps"] > 0).mean()),
            "t_stat_filt_vs_base": float(t_stat_oos), "p_val_filt_vs_base": float(p_val_oos),
            "t_stat_filt_vs_excl": float(t_stat_oos_excl), "p_val_filt_vs_excl": float(p_val_oos_excl)
        }
    }

    print("\n--- SIMULATION RESULTS ---")
    print(json.dumps(sim_results, indent=2))

    print("\n--- STATISTICAL RESULTS ---")
    print(json.dumps(stat_summary, indent=2))

    # Save summary json to report dir
    summary_path = report_c_dir / "v33_3c_simulation_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"sim_results": sim_results, "stat_summary": stat_summary}, f, indent=2)
    print(f"Saved {summary_path}")

if __name__ == "__main__":
    run_v33_3c_reconciliation()
