"""
research/evaluate_v5_directional_and_drift.py — Directional Re-Test, Break-Even PDE Drift, and Fat-Tailed Calibration
======================================================================================================================
Implements User Directives:
1. Re-test Variant V5 (and V1-V4) strictly on direction among resolved trades only (y in {0, 1} where 1=TP, 0=SL,
   dropping timeouts) to isolate directional skill from volatility timing.
2. Calculate realized Net R across regional friction tiers (India 27 bps, EU/UK 13 bps, US 9.3 bps).
3. Solve exact Kolmogorov PDE break-even drift mu^* for each geometry and friction tier using scipy.optimize.brentq.
4. Calibrate effective sigma scale factor c_sigma so theoretical diffusion null matches empirical BTC hitting rates.
"""

import json
import math
import os
import sys
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats, optimize
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from research.first_passage_diffusion_model import FirstPassageDiffusionModel

DATA_PATH = "data/raw/ohlcv.parquet"


def compute_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    ranks = stats.rankdata(np.concatenate([pos, neg]))
    rank_sum_pos = np.sum(ranks[:n_pos])
    u_stat = rank_sum_pos - (n_pos * (n_pos + 1)) / 2.0
    return float(u_stat / (n_pos * n_neg))


def solve_break_even_drift(fp_model: FirstPassageDiffusionModel, k_tp: float, k_sl: float, friction_r: float) -> float:
    """
    Finds mu^* such that E[R_net](mu^*) = 0.
    E[R_net] = P(TP) * (k_tp / k_sl) - P(SL) * 1.0 - friction_r = 0.
    """
    def obj(mu: float) -> float:
        p_tp, p_sl, _ = fp_model.solve_pde(k_tp, k_sl, mu)
        r_mult = k_tp / k_sl
        ev_net = p_tp * r_mult - p_sl * 1.0 - friction_r
        return ev_net

    # Find root between -1.0 and 2.5
    try:
        sol = optimize.brentq(obj, -0.5, 2.5, xtol=1e-4)
        return float(sol)
    except Exception as e:
        # Fallback grid search
        grid = np.linspace(-0.5, 2.5, 301)
        vals = [obj(m) for m in grid]
        idx = np.argmin(np.abs(vals))
        return float(grid[idx])


def run_evaluation() -> Dict[str, Any]:
    print("Loading OHLCV dataset from:", DATA_PATH)
    df = pd.read_parquet(DATA_PATH)
    df["dt"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("dt").reset_index(drop=True)

    diffs = df["dt"].diff()
    df["seg_id"] = (diffs != pd.Timedelta(hours=1)).cumsum()

    df["r_1h"] = np.log(df["close"] / df["close"].shift(1))
    df["r_4h"] = np.log(df["close"] / df["close"].shift(4))
    df["r_24h"] = np.log(df["close"] / df["close"].shift(24))

    df["sigma_1h"] = df.groupby("seg_id")["r_1h"].transform(
        lambda s: s.rolling(24, min_periods=24).std()
    )
    df["sigma_168h"] = df.groupby("seg_id")["r_1h"].transform(
        lambda s: s.rolling(168, min_periods=168).std()
    )
    df["vol_ratio"] = df["sigma_1h"] / np.maximum(1e-5, df["sigma_168h"])

    H = 24
    k_tp = 1.5
    k_sl = 1.0

    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values
    sigmas = df["sigma_1h"].values
    segs = df["seg_id"].values
    n = len(df)

    outcomes = [None] * n
    for i in range(168, n - H):
        if segs[i] != segs[i + H]:
            continue
        vol = sigmas[i]
        if np.isnan(vol) or vol <= 1e-5:
            continue

        entry_p = opens[i + 1]
        sigma_H = vol * math.sqrt(H)
        b_tp = entry_p * (1.0 + k_tp * sigma_H)
        b_sl = entry_p * (1.0 - k_sl * sigma_H)

        outcome = "TIMEOUT"
        for j in range(i + 1, i + H + 1):
            if highs[j] >= b_tp and lows[j] <= b_sl:
                outcome = "SL"
                break
            elif lows[j] <= b_sl:
                outcome = "SL"
                break
            elif highs[j] >= b_tp:
                outcome = "TP"
                break
        outcomes[i] = outcome

    df["outcome"] = outcomes
    df["year"] = df["dt"].dt.year

    df["f_r1"] = df["r_1h"] / np.maximum(1e-4, df["sigma_1h"])
    df["f_r4"] = df["r_4h"] / np.maximum(1e-4, df["sigma_1h"] * 2.0)
    df["f_r24"] = df["r_24h"] / np.maximum(1e-4, df["sigma_1h"] * math.sqrt(24))
    df["f_vol_ratio"] = np.log(np.maximum(0.1, df["vol_ratio"]))

    # Regional fee scenarios in R terms (k_sl = 1.0, typical sigma_H = 1.7%)
    # For k_sl * sigma_H ~ 0.017 (170 bps):
    # India (27 bps round-trip): friction_r = 0.0027 / 0.017 = 0.1588 R
    # EU/UK (13 bps round-trip): friction_r = 0.0013 / 0.017 = 0.0765 R
    # US (9.3 bps round-trip): friction_r = 0.00093 / 0.017 = 0.0547 R
    friction_dict = {
        "India (27 bps)": 0.1588,
        "EU/UK (13 bps)": 0.0765,
        "US (9.3 bps)": 0.0547,
    }

    # -------------------------------------------------------------
    # 1. Break-Even Drift mu^* Analysis via Kolmogorov PDE
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    print("1. KOLMOGOROV PDE BREAK-EVEN DRIFT ANALYSIS (mu^*)")
    print("=" * 75)
    fp_model = FirstPassageDiffusionModel()

    geometries = [
        {"name": "Legacy 24h (1.5 : 1.0)", "H": 24, "k_tp": 1.5, "k_sl": 1.0},
        {"name": "Balanced 48h (0.9 : 0.6)", "H": 48, "k_tp": 0.9, "k_sl": 0.6},
        {"name": "Symmetric 48h (0.7 : 0.7)", "H": 48, "k_tp": 0.7, "k_sl": 0.7},
        {"name": "Symmetric 72h (0.7 : 0.7)", "H": 72, "k_tp": 0.7, "k_sl": 0.7},
    ]

    pde_break_even_results = []
    for g in geometries:
        k_tp_g = g["k_tp"]
        k_sl_g = g["k_sl"]
        H_g = g["H"]
        # Approximate average sigma_H for horizon H
        # sigma_1h ~ 0.0035 (35 bps) -> sigma_24h ~ 1.7%, sigma_48h ~ 2.4%, sigma_72h ~ 3.0%
        sigma_H_est = 0.0035 * math.sqrt(H_g)
        sl_dist = k_sl_g * sigma_H_est

        g_row = {"geometry": g["name"], "k_tp": k_tp_g, "k_sl": k_sl_g, "H": H_g}
        for region, fee_bps in [("India (27 bps)", 0.0027), ("EU/UK (13 bps)", 0.0013), ("US (9.3 bps)", 0.00093)]:
            friction_r = fee_bps / sl_dist
            mu_star = solve_break_even_drift(fp_model, k_tp_g, k_sl_g, friction_r)
            # Evaluate hit rates at mu_star
            p_tp_star, p_sl_star, p_to_star = fp_model.solve_pde(k_tp_g, k_sl_g, mu_star)
            # Null hit rates (mu = 0)
            p_tp_null, p_sl_null, _ = fp_model.solve_pde(k_tp_g, k_sl_g, 0.0)

            # Share of resolved outcomes: P(TP) / (P(TP) + P(SL))
            resolved_share_null = p_tp_null / (p_tp_null + p_sl_null)
            resolved_share_star = p_tp_star / (p_tp_star + p_sl_star)
            edge_needed_pts = (resolved_share_star - resolved_share_null) * 100.0

            g_row[f"{region}_mu_star"] = round(mu_star, 4)
            g_row[f"{region}_friction_r"] = round(friction_r, 4)
            g_row[f"{region}_null_share"] = round(resolved_share_null * 100, 1)
            g_row[f"{region}_req_share"] = round(resolved_share_star * 100, 1)
            g_row[f"{region}_edge_pts"] = round(edge_needed_pts, 1)

        pde_break_even_results.append(g_row)

    for row in pde_break_even_results:
        print(f"Geometry: {row['geometry']}")
        for reg in ["India (27 bps)", "EU/UK (13 bps)", "US (9.3 bps)"]:
            print(f"  [{reg}]: Break-Even Drift mu^* = {row[f'{reg}_mu_star']:+.4f} | Req TP Share = {row[f'{reg}_req_share']}% (Null: {row[f'{reg}_null_share']}%, Edge: +{row[f'{reg}_edge_pts']:.1f} pts)")

    # -------------------------------------------------------------
    # 2. Re-test Variant V5 & Baselines on Direction Among Resolved Trades
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    print("2. DIRECTIONAL RE-TEST AMONG RESOLVED TRADES (DROPPING TIMEOUTS)")
    print("=" * 75)

    valid_mask = df["outcome"].isin(["TP", "SL"]) & df["f_r1"].notna() & df["f_r4"].notna() & df["f_r24"].notna() & df["f_vol_ratio"].notna()
    df_resolved = df[valid_mask].copy().reset_index(drop=True)
    df_resolved["y_dir"] = (df_resolved["outcome"] == "TP").astype(int)

    print(f"Total resolved trades: {len(df_resolved)} (TP: {sum(df_resolved['y_dir']==1)}, SL: {sum(df_resolved['y_dir']==0)})")
    print(f"Unconditional TP share among resolved: {np.mean(df_resolved['y_dir'])*100:.2f}%")

    variants = {
        "V1_1h_momentum": ["f_r1"],
        "V2_4h_momentum": ["f_r4"],
        "V3_24h_momentum": ["f_r24"],
        "V4_multi_horizon": ["f_r1", "f_r4", "f_r24"],
        "V5_momentum_vol_interaction": ["f_r1", "f_r4", "f_r24", "f_vol_ratio"],
        "V5_vol_ratio_ONLY": ["f_vol_ratio"],
    }

    train_mask = (df_resolved["year"] <= 2024) & (df_resolved["dt"] <= "2024-12-30 23:00:00+00:00")
    test_mask = (df_resolved["year"] >= 2025)

    dir_results = {}
    r_tp = 1.5
    r_sl = 1.0

    for v_name, feat_cols in variants.items():
        X_tr = df_resolved.loc[train_mask, feat_cols].values
        y_tr = df_resolved.loc[train_mask, "y_dir"].values

        X_te = df_resolved.loc[test_mask, feat_cols].values
        y_te = df_resolved.loc[test_mask, "y_dir"].values

        clf = LogisticRegression(penalty="l2", C=0.1, solver="lbfgs")
        clf.fit(X_tr, y_tr)

        probs_te = clf.predict_proba(X_te)[:, 1]
        auc_te = compute_auc(y_te, probs_te)

        # Net R if trading top quintile (q5) vs all
        # Gross R per trade: TP gives +1.5R, SL gives -1.0R
        trade_r_gross = np.where(y_te == 1, r_tp, -r_sl)
        
        # Top 20% highest predicted TP probability
        threshold_q80 = np.percentile(probs_te, 80)
        selected_mask = probs_te >= threshold_q80
        
        n_sel = int(np.sum(selected_mask))
        tp_rate_sel = float(np.mean(y_te[selected_mask])) if n_sel > 0 else 0.0
        gross_r_sel = float(np.mean(trade_r_gross[selected_mask])) if n_sel > 0 else 0.0

        net_r_sel = {}
        for region, f_r in friction_dict.items():
            net_r_sel[region] = round(gross_r_sel - f_r, 4)

        coefs = {f: round(float(c), 4) for f, c in zip(feat_cols, clf.coef_[0])}
        coefs["intercept"] = round(float(clf.intercept_[0]), 4)

        dir_results[v_name] = {
            "features": feat_cols,
            "coefficients": coefs,
            "test_sample_size": len(y_te),
            "directional_auc_resolved_only": round(auc_te, 4),
            "top_quintile_n": n_sel,
            "top_quintile_tp_rate": round(tp_rate_sel * 100, 2),
            "top_quintile_gross_r": round(gross_r_sel, 4),
            "top_quintile_net_r": net_r_sel,
        }

        print(f"Model: {v_name}")
        print(f"  Features: {feat_cols}")
        print(f"  Coefficients: {coefs}")
        print(f"  Directional AUC (Resolved Only): {auc_te:.4f}")
        print(f"  Top Quintile (N={n_sel}): TP Rate = {tp_rate_sel*100:.1f}%, Gross R = {gross_r_sel:+.4f}R")
        for reg, nr in net_r_sel.items():
            print(f"    Net R [{reg}]: {nr:+.4f}R per trade")

    # -------------------------------------------------------------
    # 3. Empirical vs Theoretical Null & Scale Factor c_sigma
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    print("3. EMPIRICAL VS THEORETICAL BROWNIAN NULL & SCALE FACTOR c_sigma")
    print("=" * 75)

    # Let's count all non-overlapping or contiguous trades across 2022-2026
    all_outcomes = df[df["outcome"].notna()]["outcome"].values
    n_all = len(all_outcomes)
    emp_tp_rate = float(np.mean(all_outcomes == "TP"))
    emp_sl_rate = float(np.mean(all_outcomes == "SL"))
    emp_to_rate = float(np.mean(all_outcomes == "TIMEOUT"))

    # Theoretical Brownian at mu=0 with scale factor c_sigma
    # If barriers are scaled by 1/c_sigma, i.e. effective barrier k' = k / c_sigma
    def hitting_error(c: float) -> float:
        p_tp, p_sl, _ = fp_model.solve_pde(k_tp / c, k_sl / c, 0.0)
        # Minimize squared error between theoretical hitting rates and empirical
        return (p_tp - emp_tp_rate)**2 + (p_sl - emp_sl_rate)**2

    c_opt = optimize.minimize_scalar(hitting_error, bounds=(0.8, 2.0), method="bounded").x
    c_opt = float(c_opt)

    p_tp_null_std, p_sl_null_std, p_to_null_std = fp_model.solve_pde(k_tp, k_sl, 0.0)
    p_tp_null_cal, p_sl_null_cal, p_to_null_cal = fp_model.solve_pde(k_tp / c_opt, k_sl / c_opt, 0.0)

    calibration_summary = {
        "empirical_all_trades_n": n_all,
        "empirical_tp_rate": round(emp_tp_rate * 100, 2),
        "empirical_sl_rate": round(emp_sl_rate * 100, 2),
        "empirical_timeout_rate": round(emp_to_rate * 100, 2),
        "uncalibrated_brownian_null": {
            "scale_factor": 1.0,
            "p_tp": round(p_tp_null_std * 100, 2),
            "p_sl": round(p_sl_null_std * 100, 2),
            "p_timeout": round(p_to_null_std * 100, 2),
        },
        "recalibrated_fat_tailed_null": {
            "optimal_scale_factor_c_sigma": round(c_opt, 4),
            "p_tp": round(p_tp_null_cal * 100, 2),
            "p_sl": round(p_sl_null_cal * 100, 2),
            "p_timeout": round(p_to_null_cal * 100, 2),
        }
    }

    print(f"Empirical Rates (N={n_all}): TP={emp_tp_rate*100:.2f}%, SL={emp_sl_rate*100:.2f}%, TO={emp_to_rate*100:.2f}%")
    print(f"Standard Brownian (c=1.0): TP={p_tp_null_std*100:.2f}%, SL={p_sl_null_std*100:.2f}%, TO={p_to_null_std*100:.2f}%")
    print(f"Recalibrated (c_sigma={c_opt:.4f}): TP={p_tp_null_cal*100:.2f}%, SL={p_sl_null_cal*100:.2f}%, TO={p_to_null_cal*100:.2f}%")

    output_data = {
        "pde_break_even_drift": pde_break_even_results,
        "directional_retest_resolved_trades": dir_results,
        "fat_tailed_null_calibration": calibration_summary,
    }

    with open("research/v5_directional_and_drift_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    return output_data


if __name__ == "__main__":
    run_evaluation()
