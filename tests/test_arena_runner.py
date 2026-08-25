"""
Unit tests for BTCognitive 24/7 AI Experiment Arena Runner (engine/arena_runner.py).
"""

import os
import tempfile
import pytest
from engine.arena_runner import ArenaRunner


@pytest.fixture
def temp_arena():
    """Creates an isolated ArenaRunner with a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "test_arena_memory.db")
        runner = ArenaRunner(db_path=test_db)
        yield runner


def test_arena_initial_state(temp_arena):
    """Verifies that the arena initializes with $10.00 virtual bankroll."""
    status = temp_arena.get_status()
    assert status["status"] == "ACTIVE"
    assert status["initial_balance"] == 10.00
    assert status["virtual_balance"] >= 10.00
    assert status["risk_per_trade_pct"] == 2.0
    assert status["active_model"] == "Genome v4.1"


def test_arena_paper_trade_execution(temp_arena):
    """Verifies paper trade execution with $10 bankroll formula."""
    init_status = temp_arena.get_status()
    init_bal = init_status["virtual_balance"]

    trade = temp_arena.execute_paper_trade(
        action="BUY",
        price=64200.0,
        confidence=0.85,
        reasoning="Test RSI Oversold Entry"
    )

    assert "trade_id" in trade
    assert trade["action"] == "BUY"
    assert trade["entry_price"] == 64200.0
    assert "new_balance" in trade

    # Verify updated status
    new_status = temp_arena.get_status()
    assert new_status["total_trades"] > 0
    recent = new_status["recent_trades"]
    assert len(recent) > 0
    assert recent[0]["action"] == "BUY"


def test_arena_drawdown_and_equity_curve(temp_arena):
    """Verifies that equity history and drawdowns are tracked accurately."""
    equity = temp_arena.get_equity_curve()
    assert len(equity) > 0
    for pt in equity:
        assert "balance" in pt
        assert "timestamp" in pt
        assert "drawdown" in pt


def test_arena_reset_experiment(temp_arena):
    """Verifies that experiment resets back to $10.00 initial state."""
    # Execute a trade
    temp_arena.execute_paper_trade(action="BUY", price=65000.0, confidence=0.90)
    
    # Reset
    res = temp_arena.reset_experiment()
    assert res["initial_balance"] == 10.00
    assert res["status"] == "ACTIVE"


def test_arena_retrain_and_dsr_gate(temp_arena):
    """Verifies offline retraining and Deflated Sharpe Ratio gate check."""
    result = temp_arena.trigger_retrain()
    assert "candidate_version" in result
    assert "dsr_score" in result
    assert "dsr_threshold" in result
    assert result["dsr_threshold"] == 0.95
    assert "promoted" in result
    assert "status" in result


def test_arena_export_csv(temp_arena):
    """Verifies CSV export for Excel & Google Sheets compatibility."""
    temp_arena.execute_paper_trade(action="BUY", price=64000.0, confidence=0.88)
    csv_file = temp_arena.export_csv()
    assert os.path.exists(csv_file)
    assert os.path.getsize(csv_file) > 0

