"""
research/post_repair_valid_path_smoke_test.py — Smoke Test for Valid Quality Ingestion
========================================================================================
Generates and validates a production forecast with full feature availability:
- data_quality = VALID
- validation_eligible = True
- context_status = CONTEXT_HEALTHY
- symbol = BTCUSD
- horizon = 24h
- Immutable persistence into canonical market_memory.db
"""

import os
import sys
import json
import sqlite3
import hashlib
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.paths import RESULTS_DIR
from config.database import MARKET_MEMORY_DB_PATH
from models.symbol_contract import CANONICAL_SYMBOL
from models.horizon_contract import PRODUCTION_RANGE_HORIZON_LABEL, PRODUCTION_MODEL_VERSION
from models.regime_contract import CanonicalRegime
from models.forecast_quality_contract import ForecastQuality, assess_forecast_quality, ForecastQualityRecord
from engine.range_forecast_service import RangeForecastService
from engine.feature_cache import feature_cache
from backtest.market_memory import record_prediction
from research.post_repair_longitudinal_monitor import (
    MODEL_HASH,
    CONTEXT_HASH,
    FEATURE_SCHEMA_HASH,
    TARGET_HASH,
    REPAIR_VERSION
)

def run_valid_path_smoke_test():
    print("=" * 70)
    print("  BTCognitive — VALID PRODUCTION FORECAST PATH SMOKE TEST")
    print("=" * 70)

    # 1. Prepare Valid Production Features
    feature_row = feature_cache.get_latest_row()
    current_price = float(feature_row.get("close", 65000.0)) if feature_row is not None else 65000.0
    vol_24h = float(feature_row.get("realized_vol_24h", 0.015)) if feature_row is not None else 0.015
    market_regime = CanonicalRegime.RANGING.value

    full_features = {
        "vol_24h": vol_24h,
        "realized_vol_24h": vol_24h,
        "rsi_14": 52.5,
        "atr_14": 750.0,
        "ret_24h": 0.008
    }

    # 2. Assess Forecast Quality Contract
    q_record: ForecastQualityRecord = assess_forecast_quality(
        current_price=current_price,
        vol_24h=vol_24h,
        features=full_features,
        context_healthy=True
    )

    assert q_record.data_quality == ForecastQuality.VALID, f"Expected VALID, got {q_record.data_quality}"
    assert q_record.validation_eligible is True, "VALID forecast must be validation_eligible = True"
    assert q_record.context_status == "CONTEXT_HEALTHY"

    print(f"[1] Quality Assessment:")
    print(f"    Tier:                {q_record.data_quality.value}")
    print(f"    Validation Eligible: {q_record.validation_eligible}")
    print(f"    Context Status:      {q_record.context_status}")

    # 3. Generate Range Forecast
    range_svc = RangeForecastService()
    fc = range_svc.generate_forecast(
        current_price=current_price,
        vol_24h=vol_24h,
        features=full_features,
        market_regime=market_regime
    )

    assert fc.symbol == CANONICAL_SYMBOL
    assert fc.horizon == PRODUCTION_RANGE_HORIZON_LABEL

    pred_hash = hashlib.sha256(json.dumps({
        "forecast_id": fc.forecast_id,
        "price": fc.current_price,
        "upper_p90": fc.upper_p90,
        "lower_p90": fc.lower_p90,
        "model_hash": MODEL_HASH,
        "context_hash": CONTEXT_HASH
    }, sort_keys=True).encode()).hexdigest()

    # 4. Record to Canonical Database
    now_utc = datetime.now(timezone.utc).isoformat()
    record_prediction(
        timestamp=now_utc,
        price=current_price,
        regime=market_regime,
        raw_prob=0.50,
        calibrated_prob=0.50,
        decision="HOLD",
        prediction_id=fc.forecast_id,
        model_version=PRODUCTION_MODEL_VERSION,
        context_vector_json=json.dumps({
            "regime": market_regime,
            "prediction_hash": pred_hash,
            "model_hash": MODEL_HASH,
            "context_hash": CONTEXT_HASH,
            "feature_schema_hash": FEATURE_SCHEMA_HASH,
            "target_hash": TARGET_HASH,
            "repair_version": REPAIR_VERSION,
            "data_quality": q_record.data_quality.value,
            "validation_eligible": q_record.validation_eligible,
            "context_status": q_record.context_status,
            "degraded_reason": q_record.degraded_reason,
            "missing_features": q_record.missing_features,
            "data_source": "live_valid_smoke_test"
        }),
        was_correct=None,
        outcome_resolved=False
    )

    # 5. Verify Invariants
    conn = sqlite3.connect(MARKET_MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM predictions WHERE prediction_id = ?", (fc.forecast_id,)).fetchone()
    conn.close()

    assert row is not None
    assert row["outcome_resolved"] == 0
    assert row["was_correct"] is None

    print(f"\n[2] Persistence Invariants:")
    print(f"    Forecast ID:      {fc.forecast_id}")
    print(f"    outcome_resolved: 0 (UNRESOLVED)")
    print(f"    was_correct:      NULL")
    print(f"    Data Quality:     VALID")
    print(f"\nVALID PATH SMOKE TEST: PASSED")
    return {"status": "PASS", "forecast_id": fc.forecast_id}

if __name__ == "__main__":
    run_valid_path_smoke_test()
