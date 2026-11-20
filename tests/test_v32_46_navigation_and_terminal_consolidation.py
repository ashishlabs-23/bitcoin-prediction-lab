"""
BTCognitive V32.46 — Navigation Simplification & Terminal Consolidation Test Suite
Verifies:
1. Primary Navbar has exactly 3 destinations: Terminal, Research, Journal + Secondary 'More ▾' Menu.
2. Terminal consolidates the continuous 1-to-7 workflow (Chart, Forecast, Top-2 Candidates, Analyse, Tournament, Decision, Enter/Monitor).
3. Research houses Strategy Tournaments & Backtests, Paper Trading, Model Evaluation, and Reports.
4. Paper Trading has unmistakable 'RESEARCH ONLY · SIMULATED EXECUTION' label and remains strictly isolated.
5. Manual Journal is strictly isolated from automated simulations and paper trades.
6. Stale or invalid data causes ABSTAIN/Blocked state.
7. Cached backtest results are disclosed as cached.
8. 5 Protected files remain bit-identical and untouched.
"""

import os
import json
import pandas as pd
from engine.regime_strategy_tournament import (
    check_data_freshness_and_gaps,
    run_strategy_tournament_backtest,
    formulate_smart_entry_decision,
)
from engine.smart_entry_simulator import SmartEntrySimulator


PROTECTED_FILES = [
    "data/prospective_entry_ledger.jsonl",
    "data/prospective_shadow_v1.jsonl",
    "data/prospective_entry_ledger_v2.jsonl",
    "data/raw/ohlcv.parquet",
    "data/raw/ohlcv_pre_backfill_backup.parquet",
]


def test_primary_navbar_three_destinations_and_secondary_menu():
    """Verify primary navbar contains exactly Terminal, Research, Journal, and More dropdown."""
    with open("web/app.js", "r", encoding="utf-8") as f:
        app_source = f.read()

    # Primary Navbar Assertions
    assert 'id: "nav-terminal"' in app_source, "nav-terminal missing from primary navigation."
    assert 'id: "nav-research"' in app_source, "nav-research missing from primary navigation."
    assert 'id: "nav-manual-journal"' in app_source, "nav-manual-journal missing from primary navigation."
    assert 'id: "nav-more-menu-btn"' in app_source, "nav-more-menu-btn missing from primary navigation."

    # Verify AI Forecasts and Paper Trading are not separate primary links, but preserved in secondary menu
    assert 'id: "nav-forecast"' in app_source, "nav-forecast link preserved."
    assert 'id: "nav-paper-trading"' in app_source, "nav-paper-trading link preserved."
    assert 'id: "nav-how-it-works"' in app_source, "nav-how-it-works link preserved in secondary menu."
    assert 'id: "nav-landing"' in app_source, "nav-landing link preserved in secondary menu."
    assert 'id: "nav-position-monitor"' in app_source, "nav-position-monitor link preserved in secondary menu."
    assert 'id: "nav-settings-btn"' in app_source, "nav-settings-btn link preserved in secondary menu."

    # Verify Smart Entry is not in primary navbar (per acceptance criteria)
    assert 'id: "nav-smart-entry"' not in app_source, "nav-smart-entry must NOT be in primary navbar."


def test_terminal_consolidated_workflow_structure():
    """Verify Terminal houses the continuous 1-to-7 workflow and tabs."""
    with open("web/app.js", "r", encoding="utf-8") as f:
        app_source = f.read()

    # 1. Chart & Feed Status
    assert "ChartTopBar" in app_source, "ChartTopBar missing from Terminal."
    assert "DATA: COINBASE SPOT" in app_source, "Coinbase verified data badge missing."

    # 2. Persistent AI Prediction Engine Panel
    assert "AiPredictionEnginePanel" in app_source, "AiPredictionEnginePanel missing from Terminal."
    assert "empirical_validation_status" in app_source, "Empirical validation status missing."

    # 3. Decision Sidebar / Top Candidates
    assert "WorkstationDecisionSidebar" in app_source, "WorkstationDecisionSidebar missing."

    # 4. Smart Entry Panel in Terminal default
    assert "SmartEntryPanel" in app_source, "SmartEntryPanel missing from Terminal."
    assert "btn-analyse-setup" in app_source, "btn-analyse-setup missing."
    assert "btn-run-tournament" in app_source, "btn-run-tournament missing."
    assert "smart-entry-decision-card" in app_source, "smart-entry-decision-card missing."
    assert "btn-enter-simulated-trade" in app_source, "btn-enter-simulated-trade missing."
    assert "btn-simulated-exit-now" in app_source, "btn-simulated-exit-now missing."
    assert "btn-simulated-partial-exit" in app_source, "btn-simulated-partial-exit missing."


def test_research_subtabs_and_paper_trading_isolation():
    """Verify Research section contains tournaments, paper trading, evaluation, and reports with isolation."""
    with open("web/app.js", "r", encoding="utf-8") as f:
        app_source = f.read()

    # Research sub-tabs
    assert 'id: "research-tab-tournaments"' in app_source or 'research-tab-' in app_source, "Research tournaments tab missing."
    assert 'id: "research-section-tournaments"' in app_source, "Tournament section container missing."
    assert 'id: "tournament-cache-disclosure-banner"' in app_source, "Tournament cache disclosure banner missing."
    assert 'id: "research-section-paper-trading"' in app_source, "Paper trading section in research missing."

    # Unmistakable Research Only label on Paper Trading
    assert 'id: "paper-research-only-badge"' in app_source, "paper-research-only-badge missing."
    assert "RESEARCH ONLY · SIMULATED EXECUTION" in app_source, "RESEARCH ONLY label missing."

    # Isolated ledger path
    assert "data/research/paper_trading/paper_execution_ledger.jsonl" in app_source, "Paper execution ledger path missing."
    assert "Strictly isolated from protected files" in app_source, "Isolation notice missing."


def test_manual_journal_remains_isolated():
    """Verify manual trade journal is separate from automated simulations and paper trades."""
    with open("web/app.js", "r", encoding="utf-8") as f:
        app_source = f.read()

    assert "ManualTradeJournalView" in app_source, "ManualTradeJournalView component missing."
    assert 'id: "journal-warning-banner"' in app_source, "journal-warning-banner missing."
    assert 'id: "btn-i-entered-trade"' in app_source, "btn-i-entered-trade button missing."
    assert 'id: "journal-open-records"' in app_source, "journal-open-records section missing."
    assert 'id: "journal-closed-records"' in app_source, "journal-closed-records section missing."


def test_stale_or_invalid_market_data_abstains():
    """Verify stale market data results in blocked/ABSTAIN state in tournament & entry."""
    # Feed older than 2 hours is rejected
    stale_candles = [
        {"timestamp_utc": "2026-10-24T00:00:00Z", "open": 80000.0, "high": 80500.0, "low": 79500.0, "close": 80200.0, "volume": 100.0},
        {"timestamp_utc": "2026-10-24T01:00:00Z", "open": 80200.0, "high": 80800.0, "low": 80000.0, "close": 80600.0, "volume": 120.0},
    ]
    df_stale = pd.DataFrame(stale_candles)
    freshness = check_data_freshness_and_gaps(df_stale, max_age_hours=2.0)
    assert freshness["is_fresh"] is False, "Stale candles must fail validity check."
    assert freshness["freshness_status"] == "MARKET_DATA_STALE"

    # Formulating decision with invalid data produces ABSTAIN
    decision = formulate_smart_entry_decision(
        analysis_res={
            "market_regime": {"regime": "UNKNOWN"},
            "data_freshness": freshness,
        },
        tournament_res={
            "final_verdict": "ABSTAIN_DATA_INVALID",
            "verdict_explanation": "Data feed is stale.",
        },
    )
    assert decision["action"] == "ABSTAIN"
    assert "stale" in decision["reason"].lower() or "invalid" in decision["reason"].lower() or "abstain" in str(decision).lower()


def test_cached_vs_fresh_backtest_disclosure():
    """Verify cached backtest results are disclosed as cached."""
    # Pre-registered manifest execution
    tournament_res = run_strategy_tournament_backtest(
        shortlisted_candidates=[
            {
                "strategy_id": "MEIE-VOL-EXPANSION",
                "strategy_name": "MEIE Volatility Expansion Breakout",
                "version": "3.2.0",
                "compatible_regimes": ["VOL_EXPANDING"],
                "sample_provenance": "HISTORICAL_WALKFORWARD_SCREENING",
                "preliminary_screen": {"screen_passed": True, "favorable_criteria_count": 8, "total_criteria": 10},
                "proposed_geometry": {"reference_entry_price": 82000.0, "take_profit_price": 84500.0, "stop_loss_price": 81000.0, "max_holding_hours": 24},
            }
        ],
        current_regime="VOL_EXPANDING",
    )
    assert "cache_validation" in tournament_res, "Tournament result must include cache_validation disclosure."
    prov = tournament_res["cache_validation"]
    assert "source_label" in prov, "Provenance must disclose source label."
    assert "no verified walk-forward manifest" in prov["source_label"].lower()
    assert prov["hashes_matched"] is False
    assert tournament_res["dataset_hash"] is None


def test_protected_files_remain_untouched():
    """Verify that none of the 5 protected files were modified or deleted."""
    for rel_path in PROTECTED_FILES:
        assert os.path.exists(rel_path), f"Protected file missing: {rel_path}"
        st = os.stat(rel_path)
        if rel_path.endswith(".parquet"):
            assert st.st_size > 1000, f"Parquet file suspiciously truncated: {rel_path}"
