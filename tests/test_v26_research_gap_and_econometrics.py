import json
import math
import numpy as np
import pandas as pd
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parent.parent


def compute_bartlett_hac_variance(d: np.ndarray, max_lags: int) -> float:
    """Compute Heteroskedasticity and Autocorrelation Consistent (HAC) variance using Bartlett kernel."""
    T = len(d)
    d_centered = d - np.mean(d)
    gamma_0 = float(np.mean(d_centered ** 2))
    gamma_sum = 0.0
    for k in range(1, max_lags + 1):
        weight = 1.0 - (k / (max_lags + 1.0))
        gamma_k = float(np.mean(d_centered[k:] * d_centered[:-k]))
        gamma_sum += 2.0 * weight * gamma_k
    lr_var = (gamma_0 + gamma_sum) / T
    return max(1e-12, lr_var)


def test_v26_hac_newey_west_bartlett_variance():
    """Verify HAC Bartlett long-run variance calculation on serially correlated errors."""
    np.random.seed(42)
    # Generate AR(1) loss differentials with positive serial correlation
    T = 1000
    e = np.random.normal(0, 1, T)
    d = np.zeros(T)
    for t in range(1, T):
        d[t] = 0.5 * d[t-1] + e[t]
        
    naive_var = float(np.var(d, ddof=1) / T)
    hac_var = compute_bartlett_hac_variance(d, max_lags=5)
    
    # Positive autocorrelation must increase the long-run variance estimate compared to naive i.i.d. variance
    assert hac_var > naive_var, f"HAC variance ({hac_var:.6f}) should exceed naive variance ({naive_var:.6f}) under positive serial correlation."


def test_v26_canonical_forecast_manifest_metrics():
    """Verify that v26_canonical_forecast_manifest.json records negative Clark-West statistics and persistence superiority."""
    manifest_path = REPO_ROOT / "experiments" / "results" / "v26_canonical_forecast_manifest.json"
    assert manifest_path.exists(), "v26_canonical_forecast_manifest.json must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    metrics = manifest["canonical_metrics"]
    assert "1h" in metrics
    assert "4h" in metrics
    assert "24h" in metrics
    
    for h, data in metrics.items():
        pers = data["persistence"]
        ridge = data["ridge_l2"]
        # Persistence MAE must be less than or equal to Ridge MAE
        assert pers["mae_usd"] <= ridge["mae_usd"], f"Persistence should beat or tie Ridge at {h}."
        # Clark-West statistic must be negative (no outperformance)
        assert ridge["cw_hac_stat"] < 0, f"Clark-West stat must be negative at {h}."
        assert ridge["cw_hac_p_value_one_sided"] > 0.50, f"Clark-West p-value must exceed 0.50 at {h}."
        assert ridge["statistically_superior_to_persistence"] is False
    assert manifest["overall_verdict"] == "PERSISTENCE_BASELINE_UNBEATEN"


def test_v26_canonical_strategy_manifest_reconciliation():
    """Verify Dual-EMA naming reconciliation and multi-tier fee schedules in v26_canonical_strategy_manifest.json."""
    manifest_path = REPO_ROOT / "experiments" / "results" / "v26_canonical_strategy_manifest.json"
    assert manifest_path.exists(), "v26_canonical_strategy_manifest.json must exist."
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    # Check nomenclature reconciliation block
    recon = manifest["nomenclature_reconciliation"]["TS_MOM_TREND"]
    assert "Dual-EMA Crossover" in recon["canonical_v26_label"]
    assert "ewm" in recon["verified_code_implementation"]
    
    # Check strategies
    strategies = manifest["strategies"]
    assert strategies["NO_TRADE_BENCHMARK"]["verdict"] == "DECISIVE_WINNER"
    assert strategies["NO_TRADE_BENCHMARK"]["net_returns_by_scenario"]["COINBASE_RETAIL"] == 0.0
    
    assert strategies["TS_MOM_TREND"]["net_returns_by_scenario"]["COINBASE_RETAIL"] < 0.0
    assert strategies["TRUE_DUAL_SMA_REFERENCE"]["gross_return_bps"] < 0.0
    assert manifest["governance_verdict"] == "NO_STRATEGY_WINNER_ESTABLISHED"
    assert manifest["execution_authorization"] == "DISABLED"


def test_v26_prd_traceability_matrix_and_census():
    """Verify PRD traceability matrix integrity and test census documentation."""
    matrix_path = REPO_ROOT / "docs" / "V26_PRD_TRACEABILITY_MATRIX.md"
    assert matrix_path.exists(), "V26_PRD_TRACEABILITY_MATRIX.md must exist."
    
    content = matrix_path.read_text(encoding="utf-8")
    assert "1,286 tests collected" in content
    assert "52 tests (100% passing)" in content
    assert "PRD-SAF-01" in content
    assert "PRD-CST-18" in content
    assert "EXECUTION: DISABLED" in content


def test_v26_api_endpoints_operational_and_fail_closed():
    """Verify live API endpoints maintain non-execution and honest statuses."""
    # 1. Readiness check
    res_ready = client.get("/api/readiness")
    assert res_ready.status_code == 200
    ready_json = res_ready.json()
    assert ready_json.get("authorized") is False
    assert ready_json.get("authorization_status") == "OFFLINE_RESEARCH_ONLY"
    assert ready_json.get("research_edge_status") == "NO_GO_NO_VALIDATED_EDGE"
    assert "HAR-RS-DOW" in ready_json.get("canonical_model_id", "")
    
    # 2. Prospective ledger check
    ledger_path = REPO_ROOT / "data" / "prospective_forecast_ledger.jsonl"
    assert ledger_path.exists()
    
    # 3. Execution endpoints fail-closed (404/405)
    res_orders = client.post("/api/orders", json={"symbol": "BTC-USD", "side": "buy"})
    assert res_orders.status_code in (404, 405)
    
    res_trade = client.post("/api/trade", json={"action": "BUY"})
    assert res_trade.status_code in (404, 405)
    
    res_paper = client.post("/api/paper/order", json={"amount": 100})
    assert res_paper.status_code in (404, 405)


def test_v26_diebold_mariano_bartlett_kernel_positive_definite():
    """Verify Bartlett triangular kernel guarantees positive semi-definiteness on negative autocovariance."""
    from engine.price_forecast_engine import compute_diebold_mariano_hln
    # Alternating error series produces negative autocorrelation at odd lags
    np.random.seed(123)
    T = 200
    e_bench = np.array([2.0, 0.5] * (T // 2))
    e_cand = np.array([0.5, 2.0] * (T // 2))
    stat, p = compute_diebold_mariano_hln(e_bench, e_cand, h=5)
    assert not np.isnan(stat)
    assert not np.isnan(p)
    assert 0.0 <= p <= 1.0


def test_v26_diebold_mariano_horizon_validation():
    """Verify horizon parameter validation raises ValueError when h < 1."""
    from engine.price_forecast_engine import compute_diebold_mariano_hln
    with pytest.raises(ValueError, match="Forecast horizon h must be >= 1"):
        compute_diebold_mariano_hln(np.ones(20), np.zeros(20), h=0)


def test_v26_holm_bonferroni_multiple_testing_correction():
    """Verify Holm-Bonferroni step-down correction controls FWER monotonically."""
    from engine.price_forecast_engine import holm_bonferroni
    raw_p = [0.01, 0.04, 0.03, 0.005]
    adj_p = holm_bonferroni(raw_p)
    assert len(adj_p) == len(raw_p)
    assert adj_p == [0.03, 0.06, 0.06, 0.02]
    # Verify edge cases: empty and single element
    assert holm_bonferroni([]) == []
    assert holm_bonferroni([0.03]) == [0.03]
    assert holm_bonferroni([1.5]) == [1.0]
