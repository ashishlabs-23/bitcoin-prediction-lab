"""
tests/test_integrity_batch_2026_11_28.py — Pins the data-truth fixes.

Every test here corresponds to a defect where the application reported a number
that no observation produced (AGENTS.md §2.5), or where a cache/ledger could
serve or destroy stale/partial state.
"""
import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# 1. Market state must never invent a tape
# ---------------------------------------------------------------------------
def test_market_state_uses_a_real_price_or_fails_closed():
    from engine.market_state import MarketStateEngine

    engine = MarketStateEngine()
    state = engine.evaluate_market_state()

    ohlcv_path = os.path.join(PROJECT_ROOT, "data", "raw", "ohlcv.parquet")
    if os.path.exists(ohlcv_path):
        last_close = float(pd.read_parquet(ohlcv_path, columns=["close"])["close"].iloc[-1])
        assert state.overall_data_quality in {"PARTIAL_REAL_INPUTS", "DATA_UNAVAILABLE"}
        if state.overall_data_quality == "PARTIAL_REAL_INPUTS":
            # The old code returned a hard-coded 65200.0 tape; it must now match
            # the observed close to the cent.
            assert state.current_price == pytest.approx(last_close, rel=1e-9)
            assert state.current_price != 65200.0 or last_close == 65200.0
            assert state.long_term_state["upper_p90"] > state.current_price
            assert state.long_term_state["lower_p90"] < state.current_price
    else:
        assert state.overall_data_quality == "DATA_UNAVAILABLE"
        assert state.current_price is None


def test_market_state_rejects_nonsense_inputs():
    from engine.market_state import MarketStateEngine

    engine = MarketStateEngine()
    for price, vol in [(0.0, 0.01), (-5.0, 0.01), (60000.0, -0.2), (float("nan"), 0.01)]:
        state = engine.evaluate_market_state(current_price=price, vol_24h=vol)
        assert state.overall_data_quality == "DATA_UNAVAILABLE", (price, vol)
        assert state.current_price is None


def test_market_state_never_stamps_unavailable_subsystems_as_production():
    from engine.market_state import MarketStateEngine

    state = MarketStateEngine().evaluate_market_state(current_price=60000.0, vol_24h=0.01)
    assert state.long_term_state["governance_status"] != "PRODUCTION"
    assert state.microstructure_state["governance_status"] == "UNAVAILABLE"
    assert state.microstructure_state["buy_sell_intensity_ratio"] is None


# ---------------------------------------------------------------------------
# 2. The foundation leaderboard must not be a hard-coded table
# ---------------------------------------------------------------------------
def test_foundation_leaderboard_is_not_fabricated():
    from research.foundation_leaderboard import get_foundation_model_leaderboard_payload

    payload = get_foundation_model_leaderboard_payload()
    assert payload["status"] == "UNAVAILABLE_NOT_EXECUTED"
    assert payload["leaderboard"] == []
    assert payload["count"] == 0
    assert "VALIDATED_PRODUCTION" not in json.dumps(payload)


# ---------------------------------------------------------------------------
# 3. Reverse ledger reader must equal a full scan
# ---------------------------------------------------------------------------
def test_tail_jsonl_matches_full_scan(tmp_path):
    from api.routes_research import _tail_jsonl

    path = tmp_path / "ledger.jsonl"
    rows = [{"i": i, "event_type": "A" if i % 2 else "B"} for i in range(500)]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    assert _tail_jsonl(str(path), limit=25) == rows[-25:]
    filtered = _tail_jsonl(str(path), limit=10, event_type="A")
    assert filtered == [r for r in rows if r["event_type"] == "A"][-10:]
    assert _tail_jsonl(str(path), limit=10_000) == rows


def test_tail_jsonl_survives_a_truncated_final_line(tmp_path):
    from api.routes_research import _tail_jsonl

    path = tmp_path / "ledger.jsonl"
    path.write_text('{"i": 1}\n{"i": 2}\n{"i": 3, "tru', encoding="utf-8")
    assert _tail_jsonl(str(path), limit=5) == [{"i": 1}, {"i": 2}]


# ---------------------------------------------------------------------------
# 4. Dashboard cache must not survive a research-gate flip
# ---------------------------------------------------------------------------
def test_dashboard_cache_key_tracks_the_research_gate():
    from types import SimpleNamespace

    from api.market_monitor_routes import _gate_fingerprint

    blocked = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(research_gate={"authorized": False})))
    authorized = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(research_gate={"authorized": True})))
    missing = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    assert _gate_fingerprint(blocked) == "B"
    assert _gate_fingerprint(authorized) == "A"
    assert _gate_fingerprint(missing) == "B"
    assert _gate_fingerprint(blocked) != _gate_fingerprint(authorized)


# ---------------------------------------------------------------------------
# 5. Feature cache must expose a real observation time
# ---------------------------------------------------------------------------
def test_feature_cache_is_timestamp_indexed_and_flagged():
    from engine.feature_cache import FeatureCache

    cache = FeatureCache()
    cache.initialize()
    df = cache.get_features_df()
    if df is None or not len(df):
        pytest.skip("no local dataset to initialise the cache")

    assert isinstance(df.index, pd.DatetimeIndex)
    assert cache.last_observation_time() is not None
    for column in ("rsi_14_imputed", "realized_vol_24h_imputed", "funding_rate_synthetic"):
        assert column in df.columns
    # refresh() is a no-op when no newer candle exists, never an exception
    assert cache.refresh() in (True, False)


# ---------------------------------------------------------------------------
# 6. Ledger writes must be atomic
# ---------------------------------------------------------------------------
def test_paper_trade_ledger_writes_atomically(tmp_path):
    from engine.paper_trade_ledger import _atomic_write_jsonl

    path = tmp_path / "trades.jsonl"
    _atomic_write_jsonl(str(path), [{"id": 1}, {"id": 2}])
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [{"id": 1}, {"id": 2}]

    _atomic_write_jsonl(str(path), [])
    assert path.read_text(encoding="utf-8") == ""
    # no temp files are left behind
    assert [p.name for p in tmp_path.iterdir() if ".tmp-" in p.name] == []


# ---------------------------------------------------------------------------
# 7. Entry quality must fail closed without the dataset
# ---------------------------------------------------------------------------
def test_entry_quality_fails_closed_without_dataset(monkeypatch):
    import api.routes_research as rr

    monkeypatch.setattr(rr, "REPO_ROOT", "/nonexistent-repo-root")
    response = rr.get_entry_quality()
    assert response["status"] == "DATA_UNAVAILABLE"
    assert response["decision"] is None
