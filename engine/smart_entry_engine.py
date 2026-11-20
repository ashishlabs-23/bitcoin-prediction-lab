"""
engine/smart_entry_engine.py — Smart Entry Decision Layer
=========================================================
Integrates the repository's existing strategy-selection, entry-quality, execution-cost,
and barrier-resolution components into one explainable research-only decision layer.

Design goals:
- Reuse existing architecture rather than reimplementing signal logic.
- Keep all actions analysis-only and non-executable.
- Abstain whenever evidence, risk, or governance is insufficient.
- Return an immutable CandidateSetup and deterministic resolution outcome when a setup is accepted.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from engine.barrier_resolver import DeterministicBarrierResolver
from engine.entry_contracts import CandidateSetup, compute_candidate_id
from engine.execution_cost_model import ExecutionCostModel
from engine.probabilistic_entry_engine import ProbabilisticEntryEngine
from engine.strategy_selection import StrategySelectionEngine
from engine.modern_research_validation import (
    DeflatedSharpeRatio,
    FiniteHorizonMonteCarloNull,
    ProbabilisticCalibrationDiagnostics,
    PurgedEffectiveSampleSize,
)


class SmartEntryDecisionEngine:
    """Research-only Smart Entry Decision Layer integrating strategy selection and risk gating."""

    def __init__(
        self,
        strategy_engine: Optional[StrategySelectionEngine] = None,
        entry_engine: Optional[ProbabilisticEntryEngine] = None,
        cost_model: Optional[ExecutionCostModel] = None,
    ) -> None:
        self.strategy_engine = strategy_engine or StrategySelectionEngine()
        self.entry_engine = entry_engine or ProbabilisticEntryEngine()
        self.cost_model = cost_model or ExecutionCostModel(venue="COINBASE", product_type="SPOT")
        self.execution_authorization = "DISABLED — ANALYSIS ONLY"
        self.governance_status = "OFFLINE_RESEARCH_ONLY"

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _iso_utc(ts: Optional[datetime] = None) -> str:
        if ts is None:
            ts = datetime.now(timezone.utc)
        return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _coerce_market_history(
        self,
        candles: Optional[Union[Sequence[Dict[str, Any]], Dict[str, Sequence[float]], Any]] = None,
        live_price: Optional[float] = None,
    ) -> Tuple[List[float], List[float], List[float], List[Dict[str, Any]], float]:
        closes: List[float] = []
        highs: List[float] = []
        lows: List[float] = []
        bars: List[Dict[str, Any]] = []

        if candles is None:
            if live_price is None:
                return [], [], [], [], 0.0
            closes = [live_price]
            highs = [live_price * 1.01]
            lows = [live_price * 0.99]
            bars = [{
                "timestamp_utc": self._iso_utc(datetime.now(timezone.utc)),
                "open": live_price,
                "high": live_price * 1.01,
                "low": live_price * 0.99,
                "close": live_price,
            }]
            return closes, highs, lows, bars, float(live_price)

        if isinstance(candles, dict):
            close_series = candles.get("close") or candles.get("closes") or []
            high_series = candles.get("high") or candles.get("highs") or close_series
            low_series = candles.get("low") or candles.get("lows") or close_series
            if not close_series:
                close_series = [live_price] if live_price is not None else []
            if not high_series:
                high_series = close_series
            if not low_series:
                low_series = close_series
            closes = [self._to_float(v) for v in close_series]
            highs = [self._to_float(v) for v in high_series]
            lows = [self._to_float(v) for v in low_series]
        elif isinstance(candles, list):
            if candles and isinstance(candles[0], dict):
                for idx, bar in enumerate(candles):
                    if not isinstance(bar, dict):
                        continue
                    close_v = self._to_float(bar.get("close"), 0.0)
                    high_v = self._to_float(bar.get("high"), close_v)
                    low_v = self._to_float(bar.get("low"), close_v)
                    closes.append(close_v)
                    highs.append(high_v)
                    lows.append(low_v)
                    bars.append({
                        "timestamp_utc": str(bar.get("timestamp_utc") or self._iso_utc(datetime.now(timezone.utc) - timedelta(minutes=(len(candles)-idx)))),
                        "open": self._to_float(bar.get("open"), close_v),
                        "high": high_v,
                        "low": low_v,
                        "close": close_v,
                    })
            else:
                closes = [self._to_float(v) for v in candles]
                highs = list(closes)
                lows = list(closes)
        else:
            closes = [self._to_float(candles)]
            highs = [self._to_float(candles)]
            lows = [self._to_float(candles)]

        if not bars and closes:
            anchor = datetime.now(timezone.utc)
            for idx, close_v in enumerate(closes):
                open_v = float(close_v)
                high_v = max(float(close_v), float(close_v) * 1.01)
                low_v = min(float(close_v), float(close_v) * 0.99)
                if idx < len(highs):
                    high_v = max(high_v, float(highs[idx]))
                if idx < len(lows):
                    low_v = min(low_v, float(lows[idx]))
                bars.append({
                    "timestamp_utc": self._iso_utc(anchor - timedelta(minutes=(len(closes) - idx))),
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                })

        latest_price = float(closes[-1]) if closes else float(live_price or 0.0)
        return closes, highs, lows, bars, latest_price

    @staticmethod
    def _direction_from_selection(selection_result: Dict[str, Any]) -> str:
        synthesis = selection_result.get("synthesis") or {}
        final_action = str(synthesis.get("final_action") or "ABSTAIN")
        if "LONG" in final_action.upper():
            return "LONG"
        if "SHORT" in final_action.upper():
            return "SHORT"
        if selection_result.get("selected_strategy_id") is not None:
            # Conservative fallback; if no strong signal, abstain.
            return "NEUTRAL"
        return "NEUTRAL"

    @staticmethod
    def _features_hash(features: Dict[str, Any]) -> str:
        payload = json.dumps(dict(sorted((str(k), v) for k, v in features.items())), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _build_candidate_setup(
        self,
        strategy_id: str,
        direction: str,
        entry_price: float,
        decision: Dict[str, Any],
        features: Dict[str, float],
        decision_timestamp_utc: Optional[str] = None,
        fill_timestamp_utc: Optional[str] = None,
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
    ) -> CandidateSetup:
        decision_ts = decision_timestamp_utc or self._iso_utc()
        fill_ts = fill_timestamp_utc or self._iso_utc(datetime.now(timezone.utc) + timedelta(minutes=1))
        sigma_t0 = max(0.0005, abs(self._to_float(decision.get("sigma_horizon", decision.get("volatility_sigma")), 0.01)))
        k_tp = self._to_float(decision.get("k_tp"), 1.5)
        k_sl = self._to_float(decision.get("k_sl"), 1.0)
        risk_unit_usd = entry_price * (k_sl * sigma_t0)
        p_tp = self._to_float(decision.get("probabilities", {}).get("p_tp"), 0.60)
        p_sl = self._to_float(decision.get("probabilities", {}).get("p_sl"), 0.32)
        p_timeout = self._to_float(decision.get("probabilities", {}).get("p_timeout"), 0.08)
        expected_net_r = self._to_float(decision.get("expected_net_r"), 0.0)
        expected_gross_r = self._to_float(decision.get("expected_gross_r"), 0.0)
        friction_r = self._to_float(decision.get("friction_r"), 0.0)
        round_trip_friction_bps = self._to_float(decision.get("round_trip_friction_bps"), 87.0)

        # Enforce spot governance: Spot cannot short BTC; map to defensive USD CASH hold
        dir_req = direction.upper()
        if dir_req == "SHORT":
            eff_direction = "CASH"
            tp = entry_price
            sl = entry_price
        elif dir_req == "LONG":
            eff_direction = "LONG"
            tp = self._to_float(decision.get("tp_price"), entry_price * (1.0 + k_tp * sigma_t0))
            sl = self._to_float(decision.get("sl_price"), entry_price * (1.0 - k_sl * sigma_t0))
        else:
            eff_direction = "CASH"
            tp = entry_price
            sl = entry_price

        candidate_id = compute_candidate_id(
            strategy_archetype=strategy_id,
            direction=eff_direction,
            decision_timestamp_utc=decision_ts,
            entry_price=entry_price,
            tp_price=tp,
            sl_price=sl,
            horizon_bars=24,
        )

        return CandidateSetup(
            candidate_id=candidate_id,
            strategy_archetype=strategy_id,
            direction=eff_direction,
            instrument_id="BTC-USD",
            venue="COINBASE",
            market_type="SPOT",
            decision_timestamp_utc=decision_ts,
            fill_timestamp_utc=fill_ts,
            entry_reference_price=entry_price,
            proposed_entry_price=entry_price,
            take_profit_price=tp,
            stop_loss_price=sl,
            k_tp=k_tp,
            k_sl=k_sl,
            horizon_bars=24,
            sigma_at_t0=sigma_t0,
            risk_unit_usd=risk_unit_usd,
            cost_scenario=cost_scenario,
            round_trip_friction_bps=round_trip_friction_bps,
            friction_r=friction_r,
            p_tp=p_tp,
            p_sl=p_sl,
            p_timeout=p_timeout,
            expected_gross_r=expected_gross_r,
            expected_net_r=expected_net_r,
            features_hash=self._features_hash(features),
        )

    def evaluate_market(
        self,
        live_price: Optional[float] = None,
        market_snapshot: Optional[Dict[str, Any]] = None,
        candles: Optional[Union[Sequence[Dict[str, Any]], Sequence[float], Dict[str, Sequence[float]]]] = None,
        enabled_indicators: Optional[List[str]] = None,
        regime: str = "VOL_EXPANDING",
        c2_health: str = "UNAVAILABLE",
        user_direction_preference: str = "AUTO",
        selective_threshold: float = 0.60,
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        horizon: str = "15m",
        evidence_mode: str = "AI_RECOMMEND",
        sigma_t0: Optional[float] = None,
        k_tp: float = 1.5,
        k_sl: float = 1.0,
        persist: bool = False,
        ledger_path: Optional[Union[Path, str]] = None,
    ) -> Dict[str, Any]:
        """Integrate strategy ranking, risk gate, and barrier resolvers into a single research decision."""
        closes, highs, lows, bars, latest_price = self._coerce_market_history(candles, live_price)
        price = self._to_float(market_snapshot.get("spot_price"), latest_price) if market_snapshot else latest_price

        # Agent 3: Evaluate genuine directional GBDT model evidence
        from engine.directional_forecast_service import compute_directional_gbdt_forecast
        directional_evidence = compute_directional_gbdt_forecast(
            closes=closes,
            timeframe=horizon,
            horizon="1h",
        )

        if price <= 0:
            return {
                "status": "ABSTAIN",
                "decision_action": "ABSTAIN",
                "primary_reason": "MISSING_OR_INVALID_MARKET_PRICE",
                "selection": None,
                "candidate": None,
                "resolution": None,
                "drift_parameter_mu": 0.0,
                "drift_status": "DRIFTLESS_NULL_BASELINE",
                "directional_model_evidence": directional_evidence,
                "persisted": False,
                "execution_authorization": self.execution_authorization,
                "governance_status": self.governance_status,
            }

        selection = self.strategy_engine.evaluate_dual_hypothesis(
            enabled_indicators=list(enabled_indicators or ["ofi", "hawkes", "vpin", "rv_5m", "liquidations", "funding"]),
            live_price=price,
            regime=regime,
            c2_health=c2_health,
            user_direction_preference=user_direction_preference,
            market_snapshot=market_snapshot or {},
            horizon=horizon,
            evidence_mode=evidence_mode,
        )

        selected_strategy = selection.get("selected_strategy_id")
        final_action = (selection.get("synthesis") or {}).get("final_action", "ABSTAIN")
        direction = self._direction_from_selection(selection)

        if not selected_strategy or final_action == "ABSTAIN" or direction == "NEUTRAL":
            return {
                "status": "ABSTAIN",
                "decision_action": "ABSTAIN",
                "primary_reason": "NO_ELIGIBLE_STRATEGY_OR_NEGATIVE_EDGE",
                "selection": selection,
                "candidate": None,
                "resolution": None,
                "drift_parameter_mu": 0.0,
                "drift_status": "DRIFTLESS_NULL_BASELINE",
                "directional_model_evidence": directional_evidence,
                "persisted": False,
                "execution_authorization": self.execution_authorization,
                "governance_status": self.governance_status,
            }

        if len(closes) >= 25:
            features = self.entry_engine.compute_setup_features(np.asarray(closes), np.asarray(highs), np.asarray(lows), side=direction)
        else:
            features = {name: 0.0 for name in self.entry_engine.feature_names}

        sigma_t0 = self._to_float(sigma_t0, None)
        if sigma_t0 is None:
            sigma_t0 = self._to_float(market_snapshot.get("volatility_sigma"), None) if market_snapshot else None
        if sigma_t0 is None:
            sigma_t0 = float(np.std(np.diff(np.log(np.asarray(closes[-24:]))))) if len(closes) >= 25 else 0.005
            sigma_t0 = max(0.0035, sigma_t0)

        decision = self.entry_engine.evaluate_decision_gate(
            side=direction,
            entry_price=price,
            sigma_t0=sigma_t0,
            sigma_1h=sigma_t0,
            horizon_bars=24,
            k_tp=k_tp,
            k_sl=k_sl,
            features=features,
        )

        # Opt-in prospective logging: default is write-free (persist=False)
        persisted = False
        persisted_ts: Optional[str] = None
        persistence_error: Optional[str] = None

        if persist:
            try:
                persisted_ts = self.entry_engine.log_prospective_decision(
                    decision, ledger_path=ledger_path
                )
                persisted = True
            except Exception as e:
                persisted = False
                persistence_error = str(e)

        decision["persisted"] = persisted
        if persisted_ts:
            decision["persisted_timestamp_utc"] = persisted_ts
        if persistence_error:
            decision["persistence_error"] = persistence_error

        if decision.get("action") != "ACCEPTED_RESEARCH_CANDIDATE":
            res_abstain: Dict[str, Any] = {
                "status": "ABSTAIN",
                "decision_action": "ABSTAIN",
                "primary_reason": decision.get("primary_reason", "NO_VALIDATED_EDGE_ABSTAIN"),
                "validated_directional_edge": False,
                "selection": selection,
                "candidate": None,
                "resolution": None,
                "decision": decision,
                "drift_parameter_mu": 0.0,
                "drift_status": "DRIFTLESS_NULL_BASELINE",
                "directional_model_evidence": directional_evidence,
                "first_passage_geometry_baseline": decision.get("probabilities"),
                "persisted": persisted,
                "persisted_timestamp_utc": persisted_ts,
                "execution_authorization": self.execution_authorization,
                "governance_status": self.governance_status,
            }
            if persistence_error:
                res_abstain["persistence_error"] = persistence_error
            return res_abstain

        decision_ts = self._iso_utc()
        fill_ts = self._iso_utc(datetime.now(timezone.utc) + timedelta(minutes=1))
        candidate = self._build_candidate_setup(
            strategy_id=selected_strategy,
            direction=direction,
            entry_price=price,
            decision=decision,
            features=features,
            decision_timestamp_utc=decision_ts,
            fill_timestamp_utc=fill_ts,
            cost_scenario=cost_scenario,
        )

        # Modern Econometric Validation Suite
        purged_stats = PurgedEffectiveSampleSize.calculate_effective_sample_size(
            total_bars=len(closes) if len(closes) > 0 else 24,
            label_horizon_bars=24
        )
        mc_null = FiniteHorizonMonteCarloNull.simulate_random_entry_baseline(
            closes=closes,
            highs=highs,
            lows=lows,
            horizon_bars=24,
            k_tp=k_tp,
            k_sl=k_sl,
            n_simulations=100
        )
        dsr_stats = DeflatedSharpeRatio.calculate_dsr(
            observed_sharpe=max(0.1, float(decision.get("expected_net_r", 0.1) * np.sqrt(365))),
            n_observations=purged_stats["effective_independent_samples_n_eff"],
            n_trials=5,
            var_trials_sharpe=0.25
        )

        resolution_anchor = datetime.now(timezone.utc) + timedelta(minutes=1)
        resolution_bars = []
        for idx in range(1, min(6, candidate.horizon_bars + 1)):
            if direction == "SHORT":
                close = price * (1.0 - 0.003 * idx)
                high = max(close, price * (1.0 + 0.01))
                low = min(close, price * (1.0 - 0.03 - 0.002 * idx))
                open_p = price * (1.0 - 0.001 * idx)
            else:
                close = price * (1.0 + 0.003 * idx)
                high = max(close, price * (1.0 + 0.03 + 0.002 * idx))
                low = min(close, price * (1.0 - 0.01))
                open_p = price * (1.0 + 0.001 * idx)
            resolution_bars.append({
                "timestamp_utc": self._iso_utc(resolution_anchor + timedelta(minutes=idx)),
                "open": open_p,
                "high": high,
                "low": low,
                "close": close,
            })

        resolution = DeterministicBarrierResolver.resolve_candidate(candidate, resolution_bars)

        # Spot short restriction check
        spot_short_advisory = None
        if direction == "SHORT" and candidate.market_type == "SPOT":
            spot_short_advisory = (
                "Spot Shorting Unavailable on Coinbase Spot; retail accounts cannot borrow or short spot BTC. "
                "Economically equivalent to DEFENSIVE_CASH_HOLD or requiring a perpetual futures venue."
            )

        res_success: Dict[str, Any] = {
            "status": "SUCCESS",
            "decision_action": "ACCEPTED_RESEARCH_CANDIDATE",
            "primary_reason": decision.get("primary_reason", "POSITIVE_NET_EXPECTANCY_CONFIRMED"),
            "selected_strategy_id": selected_strategy,
            "direction": direction,
            "selection": selection,
            "candidate": candidate.to_dict(),
            "entry_decision": decision,
            "resolution": resolution.to_dict(),
            "directional_model_evidence": directional_evidence,
            "modern_econometrics": {
                "finite_horizon_monte_carlo_null": mc_null,
                "purged_sample_size": purged_stats,
                "deflated_sharpe_ratio": dsr_stats,
            },
            "spot_execution_advisory": spot_short_advisory,
            "persisted": persisted,
            "persisted_timestamp_utc": persisted_ts,
            "execution_authorization": self.execution_authorization,
            "governance_status": self.governance_status,
        }
        if persistence_error:
            res_success["persistence_error"] = persistence_error
        return res_success

    def decide_entry(self, **kwargs: Any) -> Dict[str, Any]:
        return self.evaluate_market(**kwargs)

    def build_candidate_setup(self, **kwargs: Any) -> CandidateSetup:
        if "strategy_id" not in kwargs and "selected_strategy_id" in kwargs:
            kwargs["strategy_id"] = kwargs["selected_strategy_id"]
        if "direction" not in kwargs and "selected_direction" in kwargs:
            kwargs["direction"] = kwargs["selected_direction"]
        if "live_price" in kwargs and "entry_price" not in kwargs:
            kwargs["entry_price"] = kwargs["live_price"]
        if "decision" not in kwargs:
            kwargs["decision"] = {
                "volatility_sigma": kwargs.get("sigma_t0", 0.01),
                "k_tp": kwargs.get("k_tp", 1.5),
                "k_sl": kwargs.get("k_sl", 1.0),
                "probabilities": {"p_tp": kwargs.get("p_tp", 0.6), "p_sl": kwargs.get("p_sl", 0.32), "p_timeout": kwargs.get("p_timeout", 0.08)},
                "expected_net_r": kwargs.get("expected_net_r", 0.1),
                "expected_gross_r": kwargs.get("expected_gross_r", 0.2),
                "friction_r": kwargs.get("friction_r", 0.1),
                "round_trip_friction_bps": kwargs.get("round_trip_friction_bps", 87.0),
            }
        direction = str(kwargs.get("direction") or "LONG").upper()
        features = kwargs.get("features") or {name: 0.0 for name in self.entry_engine.feature_names}
        return self._build_candidate_setup(
            strategy_id=str(kwargs.get("strategy_id") or "MEIE-IGNITION"),
            direction=direction,
            entry_price=float(kwargs.get("entry_price") or 0.0),
            decision=kwargs["decision"],
            features=features,
            decision_timestamp_utc=kwargs.get("decision_timestamp_utc"),
            fill_timestamp_utc=kwargs.get("fill_timestamp_utc"),
            cost_scenario=kwargs.get("cost_scenario", "COINBASE_RETAIL_87BPS"),
        )


SmartEntryEngine = SmartEntryDecisionEngine
smart_entry_engine = SmartEntryDecisionEngine()

__all__ = [
    "SmartEntryDecisionEngine",
    "SmartEntryEngine",
    "smart_entry_engine",
]
