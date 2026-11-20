"""
engine/smart_entry_pipeline.py — End-to-End Strategy-to-Alert Pipeline
=====================================================================
Implements the 6-stage fail-closed quantitative pipeline:
Verified data → Strategy signal → Horizon-matched AI forecast → 
Cost and uncertainty evaluation → Smart Entry risk gate → Positive-edge research alert.

Key Invariants:
1. Strict Fail-Closed Governance:
   - Any missing data, stale candles, horizon mismatch, or unavailable meta-model
     forces an unconditional ABSTAIN.
2. Directional vs Meta Probability Separation:
   - The directional LightGBM return sign classifiers (1h, 4h, 24h) contribute market context.
   - Their raw P(UP) / P(DOWN) values MUST NEVER be substituted for p_TP.
3. Critical Blocker Enforced:
   - Because no validated triple-barrier meta-model currently exists in the repository,
     the pipeline fails closed at Stage 4/5 with META_MODEL_UNAVAILABLE.
   - Zero positive-edge alerts are emitted.
   - Rejected candidates and their exact machine-readable reasons are preserved for audit.
4. Non-Execution Boundary:
   - Live trading is permanently DISABLED.
   - ELIGIBLE_FOR_SHADOW_EVALUATION grants research-only shadow tracking, NOT order execution.
"""

from __future__ import annotations

import os
import math
import hashlib
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd

from engine.data_verification import DataContractValidator, DataValidationReport
from engine.strategy_signal_engine import StrategySignalEngine, StrategyCandidate
from engine.directional_forecast_service import compute_directional_gbdt_forecast
from engine.trade_outcome_evaluator import TradeOutcomeEvaluator, OutcomeEvaluationResult


@dataclass(frozen=True)
class PipelineExecutionReport:
    """Immutable audit record of full pipeline execution."""
    pipeline_id: str
    executed_at_utc: str
    instrument: str
    strategy_id: str
    stage1_data_validation: Dict[str, Any]
    stage2_strategy_signal: Optional[Dict[str, Any]]
    stage3_forecast_matching: Optional[Dict[str, Any]]
    stage4_outcome_evaluation: Optional[Dict[str, Any]]
    stage5_smart_entry_gate: Dict[str, Any]
    stage6_research_alert: Dict[str, Any]
    final_action: str  # "ABSTAIN" or "ELIGIBLE_FOR_SHADOW_EVALUATION"
    primary_reason: str
    governance_status: str = "OFFLINE_RESEARCH_ONLY"
    live_trading: str = "DISABLED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartEntryPipeline:
    """
    End-to-End Orchestrator executing the verified strategy-to-alert pipeline.
    """

    SUPPORTED_STRATEGIES = {
        "TSMOM_DONCHIAN_24H_168H",
        "RANGE_BOLLINGER_REVERSION_20H",
        "HTF_RANGE_EXPANSION_BREAKOUT"
    }

    # In-memory deduplication set for research alerts
    _SEEN_ALERT_HASHES: set[str] = set()

    @classmethod
    def execute_pipeline(
        cls,
        candles: Union[pd.DataFrame, List[Dict[str, Any]]],
        strategy_id: str = "TSMOM_DONCHIAN_24H_168H",
        instrument: str = "BTC-USD",
        venue: str = "COINBASE",
        timeframe: str = "1h",
        assumed_cost_scenario: str = "COINBASE_RETAIL_87BPS",
        custom_friction_bps: Optional[float] = None,
        current_epoch_sec: Optional[float] = None,
        notification_manager: Optional[Any] = None
    ) -> PipelineExecutionReport:
        """
        Executes all 6 stages of the strategy-to-alert pipeline.
        """
        now_epoch = current_epoch_sec if current_epoch_sec is not None else time.time()
        now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        pipe_id = f"pipe_{hashlib.sha256(f'{strategy_id}:{instrument}:{now_utc}'.encode()).hexdigest()[:16]}"

        strat_clean = str(strategy_id).upper().strip()

        # =========================================================================
        # STAGE 1: VERIFIED DATA CONTRACT
        # =========================================================================
        data_report = DataContractValidator.validate_market_data(
            candles=candles,
            instrument=instrument,
            venue=venue,
            timeframe=timeframe,
            current_epoch_sec=now_epoch
        )

        if not data_report.is_valid:
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_1_DATA_VERIFICATION",
                "reason_code": data_report.reason_code,
                "detail": data_report.details.get("error", "Data contract validation failed.")
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=None,
                stage3_forecast_matching=None,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": "PIPELINE_ABSTAINED_AT_DATA_GATE"},
                final_action="ABSTAIN",
                primary_reason=data_report.reason_code or "DATA_CONTRACT_BREACH"
            )

        df_candles = pd.DataFrame(candles) if not isinstance(candles, pd.DataFrame) else candles

        # =========================================================================
        # STAGE 2: STRATEGY SIGNAL GENERATION
        # =========================================================================
        if strat_clean not in cls.SUPPORTED_STRATEGIES:
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_2_STRATEGY_SELECTION",
                "reason_code": "STRATEGY_UNSUPPORTED",
                "detail": f"Strategy '{strategy_id}' not implemented. Supported: {sorted(cls.SUPPORTED_STRATEGIES)}"
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=None,
                stage3_forecast_matching=None,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": "PIPELINE_ABSTAINED_AT_STRATEGY_GATE"},
                final_action="ABSTAIN",
                primary_reason="STRATEGY_UNSUPPORTED"
            )

        candidate: Optional[StrategyCandidate] = None
        if strat_clean == "TSMOM_DONCHIAN_24H_168H":
            candidate = StrategySignalEngine.evaluate_tsmom_donchian(
                df_1h=df_candles, assumed_cost_scenario=assumed_cost_scenario
            )
        elif strat_clean == "RANGE_BOLLINGER_REVERSION_20H":
            candidate = StrategySignalEngine.evaluate_range_bollinger_reversion(
                df_1h=df_candles, assumed_cost_scenario=assumed_cost_scenario
            )
        elif strat_clean == "HTF_RANGE_EXPANSION_BREAKOUT":
            candidate = StrategySignalEngine.evaluate_htf_range_expansion(
                df_1h=df_candles, assumed_cost_scenario=assumed_cost_scenario
            )

        if candidate is None:
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_2_STRATEGY_SIGNAL",
                "reason_code": "NO_SETUP_TRIGGERED",
                "detail": "Market conditions do not satisfy strategy entry criteria on completed bar."
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal={"status": "NO_SETUP_TRIGGERED"},
                stage3_forecast_matching=None,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": "NO_SETUP_TRIGGERED"},
                final_action="ABSTAIN",
                primary_reason="NO_SETUP_TRIGGERED"
            )

        # Check spot short rejection
        if candidate.action == "ABSTAIN":
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_2_STRATEGY_SIGNAL",
                "reason_code": candidate.abstention_reason or "SPOT_SHORT_INELIGIBLE",
                "detail": "Coinbase Spot BTC-USD cannot short; borrow/margin not modeled."
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=candidate.to_dict(),
                stage3_forecast_matching=None,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": candidate.abstention_reason},
                final_action="ABSTAIN",
                primary_reason=candidate.abstention_reason or "SPOT_SHORT_INELIGIBLE"
            )

        # =========================================================================
        # STAGE 3: HORIZON-MATCHED AI FORECAST ATTACHMENT
        # =========================================================================
        strat_horizon_h = f"{int(candidate.holding_horizon_hours)}h"
        closes_arr = df_candles["close"].astype(float).values

        # Supported directional models exist for 1h, 4h, 24h
        if strat_horizon_h not in {"1h", "4h", "24h"}:
            forecast_info = {
                "status": "HORIZON_MISMATCH",
                "strategy_horizon": strat_horizon_h,
                "available_model_horizons": ["1h", "4h", "24h"],
                "error": f"Strategy holding horizon '{strat_horizon_h}' has no compatible directional model."
            }
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_3_FORECAST_MATCHING",
                "reason_code": "HORIZON_MISMATCH",
                "detail": f"Strategy holding horizon ({strat_horizon_h}) has no compatible GBDT model."
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=candidate.to_dict(),
                stage3_forecast_matching=forecast_info,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": "HORIZON_MISMATCH"},
                final_action="ABSTAIN",
                primary_reason="HORIZON_MISMATCH"
            )

        forecast_res = compute_directional_gbdt_forecast(
            closes=closes_arr, timeframe=timeframe, horizon=strat_horizon_h
        )

        if forecast_res.get("status") != "RESEARCH_INFERENCE_AVAILABLE":
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_3_FORECAST_MATCHING",
                "reason_code": "FORECAST_UNAVAILABLE",
                "detail": forecast_res.get("primary_reason", "Directional forecast unavailable.")
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=candidate.to_dict(),
                stage3_forecast_matching=forecast_res,
                stage4_outcome_evaluation=None,
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={"alert_emitted": False, "reason": "FORECAST_UNAVAILABLE"},
                final_action="ABSTAIN",
                primary_reason="FORECAST_UNAVAILABLE"
            )

        forecast_info = {
            "status": "FORECAST_ATTACHED_AS_CONTEXT",
            "model_id": forecast_res.get("model_id"),
            "horizon": strat_horizon_h,
            "probability_up": forecast_res.get("probability_up"),
            "probability_down": forecast_res.get("probability_down"),
            "directional_prediction": forecast_res.get("predicted_direction"),
            "epistemic_warning": "Directional sign probability MUST NOT be substituted for p_TP."
        }

        # =========================================================================
        # STAGE 4: COST AND UNCERTAINTY EVALUATION (CRITICAL BLOCKER)
        # =========================================================================
        # Because no trained, calibrated triple-barrier meta-model exists in the repository,
        # p_tp, p_sl, p_to are passed as None. The evaluator strictly fails closed.
        target_p = candidate.target_price if candidate.target_price is not None else candidate.proposed_entry_price * 1.03
        outcome_eval = TradeOutcomeEvaluator.calculate_net_expectancy(
            entry_price=candidate.proposed_entry_price,
            stop_price=candidate.stop_price,
            target_price=target_p,
            p_tp=None,  # CRITICAL CURRENT BLOCKER
            p_sl=None,
            p_to=None,
            assumed_cost_scenario=assumed_cost_scenario,
            custom_friction_bps=custom_friction_bps
        )

        # =========================================================================
        # STAGE 5: SMART ENTRY RISK GATE
        # =========================================================================
        if not outcome_eval.is_eligible:
            gate_verdict = {
                "gate_status": "ABSTAIN",
                "gate_passed": False,
                "rejection_stage": "STAGE_4_OUTCOME_EVALUATION",
                "reason_code": outcome_eval.status_code,
                "detail": outcome_eval.rejection_reason
            }
            return PipelineExecutionReport(
                pipeline_id=pipe_id,
                executed_at_utc=now_utc,
                instrument=instrument,
                strategy_id=strat_clean,
                stage1_data_validation=data_report.to_dict(),
                stage2_strategy_signal=candidate.to_dict(),
                stage3_forecast_matching=forecast_info,
                stage4_outcome_evaluation=outcome_eval.to_dict(),
                stage5_smart_entry_gate=gate_verdict,
                stage6_research_alert={
                    "alert_emitted": False,
                    "reason": outcome_eval.status_code,
                    "candidate_rejected_summary": {
                        "strategy": candidate.strategy_id,
                        "side": candidate.side,
                        "entry": candidate.proposed_entry_price,
                        "stop": candidate.stop_price,
                        "target": candidate.target_price,
                        "rejection_reason": outcome_eval.rejection_reason
                    }
                },
                final_action="ABSTAIN",
                primary_reason=outcome_eval.status_code
            )

        # =========================================================================
        # STAGE 6: POSITIVE-EDGE RESEARCH ALERT DISPATCH
        # =========================================================================
        # Only reached if all gates pass (which requires a valid meta-model)
        alert_payload = {
            "title": "Potential positive-edge research signal",
            "type": "RESEARCH_POSITIVE_EDGE_SIGNAL",
            "timestamp_utc": now_utc,
            "strategy_id": candidate.strategy_id,
            "instrument": candidate.instrument,
            "side": candidate.side,
            "holding_horizon": f"{candidate.holding_horizon_bars} bars ({candidate.holding_horizon_hours}h)",
            "proposed_entry_price": candidate.proposed_entry_price,
            "stop_loss_price": candidate.stop_price,
            "take_profit_price": candidate.target_price,
            "risk_unit_usd": candidate.risk_unit_usd,
            "assumed_cost_scenario": outcome_eval.assumed_cost_scenario,
            "expected_net_r": outcome_eval.expected_net_r,
            "ci_95_lower_r": outcome_eval.ci_95_lower_r,
            "ci_95_upper_r": outcome_eval.ci_95_upper_r,
            "forecast_model": forecast_info.get("model_id"),
            "disclaimer": "Research only — no order placed; not a guarantee of profit."
        }

        # Deduplication Hash: strategy + instrument + side + decision_timestamp + model
        dedup_key = f"{candidate.strategy_id}:{candidate.instrument}:{candidate.side}:{candidate.decision_timestamp_utc}:{forecast_info.get('model_id')}"
        dedup_hash = hashlib.sha256(dedup_key.encode()).hexdigest()[:16]

        if dedup_hash in cls._SEEN_ALERT_HASHES:
            alert_result = {"alert_emitted": False, "reason": "DEDUPLICATED_IDENTICAL_ALERT", "dedup_hash": dedup_hash}
        else:
            cls._SEEN_ALERT_HASHES.add(dedup_hash)
            alert_payload["alert_id"] = f"alert_{dedup_hash}"
            alert_result = {"alert_emitted": True, "alert_payload": alert_payload, "dedup_hash": dedup_hash}

            # If notification manager is passed, record in recent_alerts
            if notification_manager is not None and hasattr(notification_manager, "recent_alerts"):
                notification_manager.recent_alerts.insert(0, alert_payload)
                if len(notification_manager.recent_alerts) > 100:
                    notification_manager.recent_alerts.pop()

        gate_verdict = {
            "gate_status": "ELIGIBLE_FOR_SHADOW_EVALUATION",
            "gate_passed": True,
            "rejection_stage": None,
            "reason_code": "ALL_GATES_PASSED",
            "detail": "Candidate qualified for research-only shadow evaluation."
        }

        return PipelineExecutionReport(
            pipeline_id=pipe_id,
            executed_at_utc=now_utc,
            instrument=instrument,
            strategy_id=strat_clean,
            stage1_data_validation=data_report.to_dict(),
            stage2_strategy_signal=candidate.to_dict(),
            stage3_forecast_matching=forecast_info,
            stage4_outcome_evaluation=outcome_eval.to_dict(),
            stage5_smart_entry_gate=gate_verdict,
            stage6_research_alert=alert_result,
            final_action="ELIGIBLE_FOR_SHADOW_EVALUATION",
            primary_reason="ALL_GATES_PASSED"
        )
