# BTCognitive V33.1A — API & Frontend Decoupled Response Contract Verification

**Document ID:** `BTC-V33-1A-RPT-005`  
**Milestone:** V33.1A (Entry Decision Semantics & Analysis Runtime Acceptance)  
**Author:** Lead Quantitative Architect & Orchestrator  
**Governing Issue:** Manager Issue 5 (Positive-Path Analysis Verification) & Issue 6 (Test Results)  
**Operating Posture:** `OFFLINE_RESEARCH_ONLY` | Live Trading `DISABLED`  

---

## 1. Executive Summary & Verification Scope

In accordance with Section 5 of the Manager's V33.1A directive:
> *"Test the complete read-only Market Intelligence flow using approved historical fixtures: Frontend → API → data validation → regime features → volatility forecast → risk envelope → response schema → frontend rendering. Verify correct calculations, timestamps, missing-data handling, stale-data behaviour, API errors, historical report availability, forecast provenance, and consistent frontend/backend states. Do not simulate an authorized real trade."*

This document audits the API endpoints `/api/tournament/analyse` and `/api/terminal/analyse`, records the schema payloads, verifies all error boundary handlers, and proves compliance with non-execution governance.

---

## 2. API Contract Architecture & Response Schemas

### 2.1 Route Definition & Access Methods
- **Primary Analysis Ingress:** `POST /api/tournament/analyse`
- **Alternative Terminal Ingress:** `POST /api/terminal/analyse`
- **Underlying Controller:** `api/routes_tournament.py::_post_analyse_market()`
- **Authentication / Role:** Internal Read-Only Research Terminal (`ANONYMOUS / LOCALHOST`)

### 2.2 Complete JSON Response Schema (Contract Verified)

```json
{
  "analysis_id": "ana_f842a9b3e10c",
  "timestamp_utc": "2026-10-31T18:00:00.000000+00:00",
  "is_read_only": true,
  "attempts_created": 0,
  "status": "ABSTAIN",
  "regime": "TRENDING_BULLISH",
  "candle_watermark": {
    "last_closed_timestamp": "2026-10-31T17:00:00+00:00",
    "last_closed_close": 86429.99,
    "candle_watermark_hash": "cwm_9b83a210f4d8",
    "candle_window_sha256": "4b92c81a...",
    "total_closed_candles": 300
  },
  "data_provenance": {
    "instrument": "BTC-USD",
    "timeframe": "1h",
    "source": "coinbase_spot_closed_archive",
    "submitted_candle_count": 300,
    "analyzed_closed_candle_count": 300,
    "request_payload_sha256": "81f9a20...",
    "analyzed_window_sha256": "4b92c81a...",
    "latest_closed_timestamp": "2026-10-31T17:00:00+00:00",
    "authorization": "OFFLINE_RESEARCH_ONLY"
  },
  "market_intelligence": {
    "status": "SUCCESS",
    "timestamp_utc": "2026-10-31T18:00:00.000000+00:00",
    "current_market_assessment": "AVAILABLE",
    "current_price": 86429.99,
    "last_observed_candle_price": 86429.99,
    "last_observed_candle_time": "2026-10-31T17:00:00+00:00",
    "historical_volatility_analysis": "AVAILABLE",
    "historical_risk_envelope": "AVAILABLE",
    "data_freshness": {
      "is_fresh": true,
      "is_stale": false,
      "observed_age_hours": 1.0,
      "max_allowable_age_hours": 3.0,
      "has_gaps": false,
      "gap_count": 0,
      "total_closed_candles": 300,
      "freshness_warning": null
    },
    "volatility_term_structure": {
      "rv_1h_pct": 28.5,
      "rv_4h_pct": 32.1,
      "rv_24h_pct": 38.4,
      "rv_7d_pct": 45.2,
      "rv_30d_pct": 52.1,
      "vol_ratio_1h_24h": 0.742,
      "curve_shape": "CONTANGO_COMPRESSION",
      "measurement_horizon_hours": 720,
      "annualization_convention": "Hourly log-returns scaled by sqrt(8760)"
    },
    "volatility_regime": {
      "regime": "TRENDING_BULLISH",
      "is_expansion": true,
      "bollinger_band_width_pct": 2.86,
      "wilder_adx_14": 22.01,
      "trend_strength": "WEAK_TREND",
      "atr_14_usd": 715.1,
      "trend_direction": "BULLISH",
      "bb_mid": 85114.62,
      "bb_upper": 86331.54,
      "bb_lower": 83897.7,
      "evaluation_note": "Regime indicates volatility dynamics; does NOT imply directional trade probability."
    },
    "conformal_risk_envelope_7d": {
      "point_forecast_variance": 0.2043,
      "point_forecast_volatility_pct": 45.2,
      "conformal_lower_variance": 0.1185,
      "conformal_upper_variance": 0.2901,
      "conformal_lower_volatility_pct": 34.42,
      "conformal_upper_volatility_pct": 53.86,
      "nominal_target_coverage_pct": 90.0,
      "nominal_coverage_pct": 90.0,
      "measured_historical_coverage_pct": 90.43,
      "coverage_confidence_interval_95pct": [88.92, 91.94],
      "extreme_volatility_coverage_pct": 82.14,
      "calibration_status": "PROVISIONALLY_VALIDATED_FOR_RISK_CONTAINMENT",
      "forecast_timestamp_utc": "2026-10-31T17:00:00+00:00",
      "forecast_horizon": "7d (168h)",
      "uncertainty_engine": "C2 Dependence-Aware Conformal Prediction",
      "anti_conflation_notice": "Risk containment and directional prediction are different statistical problems. 90% nominal coverage quantifies volatility dispersion containment only; zero directional trade success probability is implied."
    },
    "excursion_estimates_24h": {
      "horizon": "24h",
      "favourable_excursion_upper": {
        "p10_price": 86900.0,
        "p50_price": 88150.0,
        "p90_price": 89800.0,
        "p50_pct": 1.99,
        "p90_pct": 3.90
      },
      "adverse_excursion_lower": {
        "p10_price": 85900.0,
        "p50_price": 84700.0,
        "p90_price": 83100.0,
        "p50_pct": 2.00,
        "p90_pct": 3.85
      },
      "expected_favourable_excursion_upper_p50": 88150.0,
      "expected_adverse_excursion_lower_p50": 84700.0,
      "mondrian_scaling_factor": 0.91,
      "anti_conflation_notice": "Excursion bounds quantify empirical dispersion quantiles, not a forecast of future trade profit."
    },
    "calibration_health_state": "CALIBRATED",
    "data_quality_warnings": []
  },
  "trade_authorization": {
    "decision_timestamp_utc": "2026-10-31T18:00:00.000000+00:00",
    "final_decision": "ABSTAIN",
    "actionable_recommendation": "NO_TRADE",
    "live_trading": "DISABLED — ANALYSIS ONLY",
    "decision_summary": "Trade authorization is ABSTAIN. Q2 Directional Evidence is INSUFFICIENT_EVIDENCE (currently unauthorized pending new validated evidence under a separately approved validation protocol). Individual checks Q1, Q3, Q4, Q5 cannot override directional evidence sufficiency.",
    "user_bias_rejected": false,
    "execution_friction_assumed_bps": 87.0,
    "cost_venue": "COINBASE_ADVANCED_87BPS",
    "research_authorization_status": "OFFLINE_RESEARCH_ONLY",
    "directional_eligibility_lock": "CURRENTLY_UNAUTHORIZED_PENDING_NEW_VALIDATED_EVIDENCE",
    "five_question_evaluation": {
      "question_1_market_regime": {
        "question": "Is BTC trending, ranging, compressing, or expanding?",
        "state": "PASS",
        "status": "PASS",
        "passed": true,
        "explanation": "Market is in TRENDING_BULLISH (ADX 22.0, trend: BULLISH). Regime compatibility check passed."
      },
      "question_2_directional_evidence": {
        "question": "Is there reliable evidence favouring LONG or SHORT?",
        "state": "INSUFFICIENT_EVIDENCE",
        "status": "INSUFFICIENT_EVIDENCE",
        "passed": false,
        "explanation": "Directional return classifiers achieve ~53.28% out-of-sample accuracy on hourly BTCUSD. Without external positioning shocks, empirical return edge is statistically indistinguishable from random drift (p >= 0.20). Directional prediction is currently unauthorized pending new validated evidence under a separately approved validation protocol. State is INSUFFICIENT_EVIDENCE (distinguished from technical failure).",
        "research_authorization_state": "CURRENTLY_UNAUTHORIZED_PENDING_NEW_VALIDATED_EVIDENCE"
      },
      "question_3_entry_location": {
        "question": "Is the proposed entry price favourable relative to current market structure?",
        "state": "PASS",
        "status": "ACCEPTABLE",
        "passed": true,
        "structural_location_quality": "STRUCTURALLY_BALANCED",
        "structural_location_score": 66.1,
        "support_price": 83897.7,
        "resistance_price": 86331.54,
        "atr_14_distance_usd": 715.1,
        "anti_conflation_notice": "Never equate location quality with probability of profit. A trade near support is not automatically a good LONG.",
        "explanation": "Price ($86,429.99) is within normal structural bands (1.54% from 20h mean $85,114.62). ATR distance: 1.0x ATR to nearest structural boundary. Structural location passes technical checks; does NOT guarantee trade profitability."
      },
      "question_4_execution_economics": {
        "question": "Is the potential return sufficient relative to adverse excursion and total costs?",
        "state": "FAIL",
        "status": "FAILS_FEE_DRAG",
        "passed": false,
        "gross_expected_return_bps": -22.3,
        "net_expected_value_bps": -109.3,
        "friction_breakdown": {
          "venue": "COINBASE_ADVANCED_87BPS",
          "commission_round_trip_bps": 83.0,
          "spread_bps": 4.0,
          "spread_status": "ESTIMATED_4BPS_UNAVAILABLE_WITHOUT_L2_DEPTH",
          "slippage_bps": 0.0,
          "total_round_trip_friction_bps": 87.0
        },
        "explanation": "At COINBASE_ADVANCED_87BPS (87.0 bps round-trip friction), required breakeven win rate is 47.8%. Gross expected return is -22.3 bps. Total friction of 87.0 bps yields Net EV of -109.3 bps/trade. Negative economics; fee drag consumes edge."
      },
      "question_5_confidence_calibration": {
        "question": "How reliable is the underlying evidence in this particular market condition?",
        "state": "PASS",
        "status": "CALIBRATION_OK_NO_ALPHA",
        "passed": true,
        "diagnostic_sample_floor_n": 30,
        "sample_size_classification": "DIAGNOSTIC_MINIMUM_ONLY — NOT_A_VALIDATION_THRESHOLD",
        "sample_size_governance_notice": "N >= 30 is a descriptive engineering diagnostic floor, not proof of statistical evidence. Research claims require effective sample size N_eff and dependence-aware validation under approved validation protocols.",
        "calibration_status": "PROVISIONALLY_VALIDATED_FOR_RISK_CONTAINMENT",
        "explanation": "Sample size N=300 (estimated N_eff=126.0) satisfies diagnostic engineering minimum (N >= 30). Note: N >= 30 is a diagnostic floor, NOT proof of adequate statistical evidence for directional alpha. C2 Conformal Risk Envelope is calibrated for provisional risk containment (nominal coverage 90%). Prospective forward block accumulation is FROZEN at 7/100 blocks (collector inactive)."
      }
    }
  }
}
```

---

## 3. Negative and Boundary Path Verification

| Test Scenario | Input Condition | Expected System Behavior | Verified in Test Suite |
| :--- | :--- | :--- | :--- |
| **Candles < 24 bars** | Short fixture (10 bars) | Returns `status: UNAVAILABLE`, reason: `"Insufficient closed candle history"`, `trade_authorization.final_decision = ABSTAIN`. | `tests/test_v32_47_analyse_selection_and_anomaly_monitor.py` |
| **Stale Candles (>3.0h)** | 12.0h old closed bars | Serves complete historical volatility and risk envelope with timestamp; `current_market_assessment = UNAVAILABLE`; `current_price = null`; trade locked to `ABSTAIN`. | `tests/test_v33_1_entry_and_analysis_decoupling.py` |
| **Missing OHLCV fields** | Missing `'high'` or `'low'` | Clean HTTP 422 or fail-closed validation error (`MALFORMED_CANDLES`). Zero unhandled 500 exceptions. | `tests/test_v32_48_integrated_analyse_and_tournament.py` |
| **Candle Gap Detection** | Missing 2-hour candle block | Returns `freshness_res.has_candle_gaps = True`, surfaces `CANDLE_GAP_WARNING` in `data_quality_warnings`. | `tests/test_stage8_data_experiments.py` |
| **User Bias Override** | Request payload `{ user_intent: "LONG" }` | Evaluated against Q1..Q5; rejected with `user_bias_rejected = True`; decision remains `ABSTAIN`. | `tests/test_v33_1_entry_and_analysis_decoupling.py` |

---

## 4. Strict Non-Execution Invariants

Across all API calls and test fixtures:
- `is_read_only` is strictly hardcoded to `True`.
- `attempts_created` is strictly hardcoded to `0`.
- `live_trading` is strictly hardcoded to `"DISABLED — ANALYSIS ONLY"`.
- Zero database writes occur in `manual_trades` or live order books during analysis.

