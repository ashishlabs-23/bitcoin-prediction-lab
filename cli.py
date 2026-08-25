#!/usr/bin/env python3
"""
BTCognitive CLI Tool
====================
Interactive command-line interface for querying:
1. BTC Volatility Intelligence Terminal (4 Foundational Decision Questions)
2. Continuous Forecast Accuracy Observatory (5-State Calibration Health & Ledger)
3. Market Regimes and Engine Health
"""

import sys
import argparse
import urllib.request
import json


DEFAULT_API_URL = "http://localhost:8000"


def query_api(endpoint: str, base_url: str = DEFAULT_API_URL):
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "BTCognitive-CLI/3.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"\033[91m[Error]\033[0m Failed to query {url}: {e}")
        return None


def cmd_terminal(args):
    print("\n\033[96m======================= BTCOGNITIVE VOLATILITY INTELLIGENCE TERMINAL =======================\033[0m")
    data = query_api("/api/terminal/live", args.url)
    if not data:
        return
        
    q = data.get("four_questions", {})
    
    # Question 1: Expected Volatility
    q1 = q.get("1_expected_volatility", {})
    print("\n\033[93m1. WHAT DOES THE MODEL EXPECT?\033[0m")
    print(f"   • Forward 7D Realized Variance:   \033[97m{q1.get('point_forecast_har_rs_dow', 'N/A')}\033[0m (Annualized)")
    print(f"   • Equivalent Annualized Volatility: \033[92m{q1.get('equivalent_annualized_vol_pct', 'N/A')}\033[0m")
    print(f"   • Point Model:                    {q1.get('model_version', 'HAR-RS-DOW')}")

    # Question 2: Uncertainty Risk Envelope
    q2 = q.get("2_uncertainty_risk_envelope", {})
    print("\n\033[93m2. HOW UNCERTAIN IS THAT ESTIMATE? (90% TARGET RISK ENVELOPE)\033[0m")
    print(f"   • Variance Risk Envelope [L, U]:  \033[97m[{q2.get('lower_bound_variance', 'N/A')}, {q2.get('upper_bound_variance', 'N/A')}]\033[0m (Width: {q2.get('envelope_width', 'N/A')})")
    print(f"   • Calibrated Engine:              {q2.get('calibrated_engine', 'C2 Dependence-Aware Conformal')}")
    print(f"   • 2026 Holdout Empirical Coverage:{q2.get('empirical_holdout_coverage', 'N/A')}")
    print(f"   • Extreme Volatility (Q5) Spikes: {q2.get('extreme_vol_q5_containment', 'N/A')}")
    print(f"   • Tail Breach Balance:            {q2.get('tail_breach_balance', 'N/A')}")

    # Question 3: Current Regime
    q3 = q.get("3_current_regime", {})
    print("\n\033[93m3. WHAT REGIME ARE WE CURRENTLY IN?\033[0m")
    print(f"   • Macro Epoch:                    \033[97m{q3.get('macro_epoch', 'N/A')}\033[0m")
    print(f"   • Volatility State:               \033[96m{q3.get('volatility_state', 'NORMAL')}\033[0m")
    print(f"   • Structural Dynamics:            {q3.get('structural_descriptor', 'N/A')}")
    print(f"   • Structural Warning:             \033[90m{q3.get('structural_warning', 'N/A')}\033[0m")

    # Question 4: Operational Calibration Trust
    q4 = q.get("4_operational_calibration_trust", {})
    status = q4.get("calibration_health_status", "UNKNOWN")
    color = "\033[92m" if status == "STABLE" else ("\033[93m" if status == "WATCH" else "\033[91m")
    print("\n\033[93m4. SHOULD I TRUST THE CURRENT RISK ENVELOPE OPERATIONALLY?\033[0m")
    print(f"   • Calibration Health Status:      {color}{status}\033[0m")
    print(f"   • System Rationale:               {q4.get('status_rationale', 'N/A')}")
    print(f"   • Sample Counts:                  \033[97m{q4.get('resolved_forecasts_count', 0):,} Resolved\033[0m | \033[90m{q4.get('pending_forecasts_count', 0):,} Pending (168h horizon)\033[0m")
    print(f"   • 30D Responsive Coverage:        {q4.get('30d_responsive_coverage_pct', 'N/A')}% (Drift: {q4.get('30d_coverage_drift_pct', 0):+.2f}%)")
    print(f"   • 90D Persistent Governance:      {q4.get('90d_persistent_coverage_pct', 'N/A')}%")
    print(f"   • 30D Tail Asymmetry (Delta):     {q4.get('tail_asymmetry_delta_pct', 'N/A')}%")
    print(f"   • Automated ABSTAIN Active:       {'YES (RISK-DEFENSE TRIGGERED)' if q4.get('risk_defense_abstain_active') else 'NO (NORMAL OPERATION)'}")

    print("\n\033[90m--------------------------------------------------------------------------------------------\033[0m")
    print(f"\033[90mContract: {data.get('epistemic_contract', '')}\033[0m")
    print("\033[96m============================================================================================\033[0m\n")


def cmd_observatory(args):
    print("\n\033[96m======================= FORECAST ACCURACY OBSERVATORY AUDIT SUMMARY =======================\033[0m")
    summary = query_api("/api/observatory/summary", args.url)
    if summary:
        status = summary.get("status", "UNKNOWN")
        color = "\033[92m" if status == "STABLE" else ("\033[93m" if status == "WATCH" else "\033[91m")
        
        exp_id = summary.get("prospective_experiment_id", "N/A")
        epoch_id = summary.get("prospective_epoch_id", "N/A")
        audit_status = summary.get("prospective_audit_status", "ACCUMULATING")
        
        print(f"\n\033[93mPROSPECTIVE EXPERIMENT IDENTITY\033[0m")
        print(f"   • Experiment ID:          \033[97m{exp_id}\033[0m")
        print(f"   • Epoch ID:               {epoch_id}")
        print(f"   • Audit Status:           \033[96m{audit_status}\033[0m (Next Milestone: N_resolved = 720)")

        print(f"\n\033[93mOPERATIONAL CONTROL STATUS\033[0m")
        print(f"   • Health State:           {color}{status}\033[0m")
        print(f"   • System Rationale:       {summary.get('status_rationale')}")

        resolved_n = summary.get("valid_N", summary.get("total_resolved_forecasts", 0))
        pending_n = summary.get("pending_N", summary.get("pending_unresolved_forecasts", 0))
        invalid_n = summary.get("data_invalid_N", 0)
        corrupted_n = summary.get("hash_failures", 0)
        abstained_n = summary.get("abstained_N", 0)
        total_n = resolved_n + pending_n + invalid_n + corrupted_n + abstained_n
        census_ok = summary.get("census_verified", True)

        print(f"\n\033[93mPROSPECTIVE CENSUS ACCOUNTING\033[0m")
        print(f"   • Total Issued:           \033[97m{total_n:,}\033[0m")
        print(f"   • Resolved (168h):        \033[92m{resolved_n:,}\033[0m")
        print(f"   • Pending Maturing (168h):\033[90m{pending_n:,}\033[0m")
        print(f"   • DATA_INVALID:           {invalid_n}")
        print(f"   • AUDIT_CORRUPTED:        {corrupted_n}")
        print(f"   • Abstained:              {abstained_n}")
        print(f"   • Census Balance Check:   \033[92m{'BALANCED (ZERO SILENT LOSS)' if census_ok else 'FAILED'}\033[0m")

        print(f"\n\033[93mEMPIRICAL CALIBRATION PANELS\033[0m")
        print(f"   • 30D Rolling Coverage:   {summary.get('coverage_30d_pct', 0):.2f}% (Drift: {summary.get('coverage_drift_30d_pct', 0):+.2f}%)")
        print(f"   • 90D Persistent Coverage:{summary.get('coverage_90d_pct', 0):.2f}%")
        print(f"   • All-Time Holdout:       {summary.get('coverage_all_pct', 0):.2f}%")
        print(f"   • 30D Upper / Lower Breach:{summary.get('upper_breach_30d_pct', 0):.2f}% / {summary.get('lower_breach_30d_pct', 0):.2f}% (Delta: {summary.get('tail_asymmetry_30d_pct', 0):.2f}%)")
        print(f"   • 30D Mean Winkler Score: {summary.get('mean_winkler_30d', 0):.5f}")
        
        stress_n = summary.get("stress_N", 0)
        stress_cov = summary.get("stress_coverage_pct")
        stress_cov_str = f"{stress_cov:.2f}%" if stress_cov is not None else "N/A"
        print(f"   • Stress Panel (Ex-Ante): N = {stress_n} | Coverage: {stress_cov_str}")

    print("\n\033[90m--------------------------------------------------------------------------------------------\033[0m")
    print(f"\033[90mRule: Observe != Optimize | Operational health states are control limits, not statistical validation.\033[0m")
    print("\033[96m============================================================================================\033[0m\n")


def cmd_health(args):
    print("\n\033[96m=== BTCognitive Engine Health ===\033[0m")
    data = query_api("/health", args.url)
    if data:
        status_color = "\033[92m" if data.get("status") == "live" else "\033[93m"
        print(f"Status:        {status_color}{data.get('status', 'unknown').upper()}\033[0m")
        print(f"Models Loaded: {data.get('models_loaded')}")
        print(f"Uptime:        {data.get('uptime', 0)} seconds")
    print()


def main():
    parser = argparse.ArgumentParser(description="BTCognitive CLI — Volatility Intelligence & Uncertainty Terminal")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="Backend Engine URL (default: http://localhost:8000)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("terminal", help="Query real-time terminal answering the 4 foundational decision questions")
    subparsers.add_parser("observatory", help="Query continuous forecast accuracy observatory calibration health")
    subparsers.add_parser("health", help="Check engine health and uptime")

    args = parser.parse_args()

    if args.command == "terminal":
        cmd_terminal(args)
    elif args.command == "observatory":
        cmd_observatory(args)
    elif args.command == "health":
        cmd_health(args)
    else:
        # Default to terminal if no subcommand
        cmd_terminal(args)


if __name__ == "__main__":
    main()
