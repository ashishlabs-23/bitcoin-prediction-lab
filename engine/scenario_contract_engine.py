"""
engine/scenario_contract_engine.py — Research-Only Scenario & Level Engine
==========================================================================
Computes mathematically consistent, side-specific entry, take-profit,
and stop-loss levels strictly compliant with the SignalContract specification.

Mathematical Invariants:
- For LONG:  SL < Entry < TP. Reward = TP - Entry > 0. Risk = Entry - SL > 0.
             Gross R:R = Reward / Risk.
- For SHORT: TP < Entry < SL. Reward = Entry - TP > 0. Risk = SL - Entry > 0.
             Gross R:R = Reward / Risk.
- If model is Gated, Direction is NOT_ESTIMATED/NEUTRAL/ABSTAIN, or EV <= Costs:
  The engine must ABSTAIN and return None for actionable levels.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from models.signal_contract import (
    SignalContract,
    SignalDirection,
    SignalStatus,
    CalibrationStatus,
    EntryType,
    ExecutionAuthorization,
    create_abstain_signal
)
from engine.execution_cost_model import ExecutionCostModel


@dataclass
class ScenarioCandidate:
    signal_id: str
    instrument: str
    direction: str
    reference_price: float
    entry_price: float
    take_profit: float
    stop_loss: float
    signal_status: str
    model_tier: str


@dataclass
class ScenarioValidationResult:
    is_actionable: bool
    analytical_status: str
    rejection_reason: str


class ScenarioLevelEngine:
    def __init__(self, max_entry_slippage_bps: float = 50.0):
        self.max_entry_slippage_bps = max_entry_slippage_bps

    def validate_candidate(self, candidate: ScenarioCandidate) -> ScenarioValidationResult:
        if "GATED" in candidate.model_tier or candidate.model_tier == "TIER_2_GATED":
            return ScenarioValidationResult(
                is_actionable=False,
                analytical_status="ABSTAIN_GATED",
                rejection_reason="GATED: Model status is TIER_2_GATED"
            )

        if candidate.reference_price > 0 and candidate.entry_price > 0:
            diff_bps = abs(candidate.entry_price - candidate.reference_price) / candidate.reference_price * 10000.0
            if diff_bps > self.max_entry_slippage_bps:
                return ScenarioValidationResult(
                    is_actionable=False,
                    analytical_status="STALE_ENTRY_MISMATCH",
                    rejection_reason=f"STALE_ENTRY_PRICE_MISMATCH: entry ${candidate.entry_price:,.2f} deviates {diff_bps:.1f} bps from live ${candidate.reference_price:,.2f}"
                )

        return ScenarioValidationResult(
            is_actionable=True,
            analytical_status="VALID_SCENARIO",
            rejection_reason=""
        )


def compute_bracket_geometry(
    direction: str,
    entry: float,
    tp: float,
    sl: float,
    cost_bps: float = 9.3
) -> Dict[str, Any]:
    """Validates side-specific invariants and calculates gross reward-to-risk ratio."""
    for val in [entry, tp, sl]:
        if val is None or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            return {"is_valid": False, "error_code": "NON_FINITE_VALUES"}

    dir_u = str(direction).upper()
    if dir_u == "LONG":
        if math.isclose(entry, sl, abs_tol=1e-5):
            return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_RISK"}
        if math.isclose(entry, tp, abs_tol=1e-5):
            return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_REWARD"}
        if sl > entry or entry > tp:
            return {"is_valid": False, "error_code": "INVERTED_LEVELS"}
        risk_dist = round(entry - sl, 4)
        reward_dist = round(tp - entry, 4)
    elif dir_u == "SHORT":
        if math.isclose(entry, sl, abs_tol=1e-5):
            return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_RISK"}
        if math.isclose(entry, tp, abs_tol=1e-5):
            return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_REWARD"}
        if tp > entry or entry > sl:
            return {"is_valid": False, "error_code": "INVERTED_LEVELS"}
        risk_dist = round(sl - entry, 4)
        reward_dist = round(entry - tp, 4)
    else:
        return {"is_valid": False, "error_code": "INVALID_DIRECTION"}

    if risk_dist <= 0:
        return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_RISK"}
    if reward_dist <= 0:
        return {"is_valid": False, "error_code": "ZERO_OR_NEGATIVE_REWARD"}

    gross_rr = round(reward_dist / risk_dist, 5)
    return {
        "is_valid": True,
        "reward_distance": reward_dist,
        "risk_distance": risk_dist,
        "gross_rr": gross_rr,
        "error_code": None
    }


class ScenarioContractEngine:
    """
    Authoritative calculation engine for research-only scenario levels.
    """

    def __init__(self, exchange: str = "Coinbase", instrument: str = "BTC-USD"):
        self.exchange = exchange
        self.instrument = instrument

    def compute_scenario_geometry(
        self,
        entry_price: float,
        direction: str,
        tp_price: float,
        sl_price: float,
        cost_bps: float = 9.3
    ) -> Dict[str, Any]:
        """
        Validates side-specific invariants and calculates gross and net R:R ratios.
        """
        dir_upper = direction.upper()
        if dir_upper not in ["LONG", "SHORT"]:
            raise ValueError(f"Direction must be LONG or SHORT for scenario geometry; got {direction}")

        entry_price = float(entry_price)
        tp_price = float(tp_price)
        sl_price = float(sl_price)

        if entry_price <= 0 or tp_price <= 0 or sl_price <= 0:
            raise ValueError("All prices must be strictly positive.")

        if dir_upper == "LONG":
            if not (sl_price < entry_price < tp_price):
                raise ValueError(
                    f"Long bracket invariant violated: SL ({sl_price:.2f}) < Entry ({entry_price:.2f}) < TP ({tp_price:.2f})"
                )
            risk_dist = round(entry_price - sl_price, 4)
            reward_dist = round(tp_price - entry_price, 4)
        else:  # SHORT
            if not (tp_price < entry_price < sl_price):
                raise ValueError(
                    f"Short bracket invariant violated: TP ({tp_price:.2f}) < Entry ({entry_price:.2f}) < SL ({sl_price:.2f})"
                )
            risk_dist = round(sl_price - entry_price, 4)
            reward_dist = round(entry_price - tp_price, 4)

        if risk_dist <= 0:
            raise ValueError(f"Non-positive risk distance: {risk_dist}")
        if reward_dist <= 0:
            raise ValueError(f"Non-positive reward distance: {reward_dist}")

        gross_rr = round(reward_dist / risk_dist, 2)

        # Net R:R accounting for round-trip execution costs
        cost_dist = round(entry_price * (cost_bps / 10000.0), 4)
        net_reward = max(0.0, reward_dist - cost_dist)
        net_risk = risk_dist + cost_dist
        net_rr = round(net_reward / net_risk, 2) if net_risk > 0 else 0.0

        return {
            "entry_price": round(entry_price, 2),
            "take_profit": round(tp_price, 2),
            "stop_loss": round(sl_price, 2),
            "risk_distance": risk_dist,
            "reward_distance": reward_dist,
            "gross_reward_to_risk": gross_rr,
            "net_reward_to_risk": net_rr,
            "cost_distance": cost_dist,
            "cost_bps": cost_bps,
            "is_valid": True
        }

    def evaluate_scenario_candidate(
        self,
        reference_price: float,
        direction: str,
        horizon: str = "1h",
        market_regime: str = "VOL_EXPANDING",
        c2_health: str = "CALIBRATED",
        is_model_gated: bool = True,
        raw_probability: Optional[float] = None,
        cost_bps: Optional[float] = None,
        price_timestamp: Optional[str] = None,
        p_tp: Optional[float] = None,
        p_sl: Optional[float] = None,
        p_timeout: Optional[float] = None,
        timeout_drift_bps: float = 0.0
    ) -> SignalContract:
        """
        Evaluates whether an active paper research scenario can be published.
        Enforces:
        1. Data frequency check: Only verified hourly intervals (1h, 4h, 24h, 168h) are supported.
           Sub-hourly requests (5m, 15m) fail closed with DATA_FREQUENCY_UNSUPPORTED.
        2. Governance gating: Gated or offline models fail closed with TIER_2_DIRECTIONAL_GATED.
        3. Directional validity: NOT_ESTIMATED / ABSTAIN fail closed with NO_DIRECTIONAL_EDGE.
        4. Economic expectancy gate: Net EV after venue transaction costs must be strictly positive.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        ts_price = price_timestamp or now_iso
        h_clean = str(horizon).lower()

        # Gate 1: Data frequency check
        verified_horizons = ["1h", "4h", "24h", "168h", "1d", "7d"]
        if h_clean in ["5m", "15m"] or h_clean not in verified_horizons:
            return create_abstain_signal(
                model_id="AEER_v3.3_CANONICAL",
                reference_price=reference_price,
                reason_code="DATA_FREQUENCY_UNSUPPORTED",
                instrument=self.instrument,
                horizon=horizon,
                price_timestamp=ts_price
            )

        # Gate 2: Governance / Gating check
        dir_clean = direction.upper() if isinstance(direction, str) else "ABSTAIN"
        if is_model_gated:
            return create_abstain_signal(
                model_id="AEER_v3.3_CANONICAL",
                reference_price=reference_price,
                reason_code="TIER_2_DIRECTIONAL_GATED",
                instrument=self.instrument,
                horizon=horizon,
                price_timestamp=ts_price
            )

        # Gate 3: Directional edge check
        if dir_clean in ["NONE", "NEUTRAL", "NOT_ESTIMATED", "ABSTAIN", "SKIP"]:
            return create_abstain_signal(
                model_id="AEER_v3.3_CANONICAL",
                reference_price=reference_price,
                reason_code="NO_DIRECTIONAL_EDGE",
                instrument=self.instrument,
                horizon=horizon,
                price_timestamp=ts_price
            )

        # Compute level geometry based on horizon and volatility bounds
        vol_scale = 1.0
        if h_clean in ["1h"]:
            vol_scale = 0.005  # 0.5%
        elif h_clean in ["4h"]:
            vol_scale = 0.010  # 1.0%
        elif h_clean in ["24h", "1d"]:
            vol_scale = 0.025  # 2.5%
        else:
            vol_scale = 0.050

        if dir_clean == "LONG":
            tp = round(reference_price * (1.0 + 1.5 * vol_scale), 2)
            sl = round(reference_price * (1.0 - 1.0 * vol_scale), 2)
        else:
            tp = round(reference_price * (1.0 - 1.5 * vol_scale), 2)
            sl = round(reference_price * (1.0 + 1.0 * vol_scale), 2)

        if cost_bps is None:
            effective_cost_bps = float(ExecutionCostModel.calculate_round_trip_cost(self.exchange)["total_round_trip_bps"])
        else:
            effective_cost_bps = float(cost_bps)

        geom = self.compute_scenario_geometry(
            entry_price=reference_price,
            direction=dir_clean,
            tp_price=tp,
            sl_price=sl,
            cost_bps=effective_cost_bps
        )

        # Gate 4: Economic Expectancy Gate
        # If probabilities are provided, compute net expected value rigorously
        reward_bps = (geom["reward_distance"] / reference_price) * 10000.0
        risk_bps = (geom["risk_distance"] / reference_price) * 10000.0

        if p_tp is not None and p_sl is not None:
            p_to = p_timeout if p_timeout is not None else max(0.0, 1.0 - p_tp - p_sl)
            ev_net = (
                p_tp * (reward_bps - effective_cost_bps)
                - p_sl * (risk_bps + effective_cost_bps)
                + p_to * (timeout_drift_bps - effective_cost_bps)
            )
        else:
            # Under uncalibrated empirical priors (from 2026 holdout: TP 17.8%, SL 36.1%, TO 46.1%)
            # Net expectancy is negative (-22.4 bps on Binance, -94.15 bps on Coinbase)
            ev_net = -22.4

        if ev_net <= 0.0:
            return create_abstain_signal(
                model_id="AEER_v3.3_CANONICAL",
                reference_price=reference_price,
                reason_code="ECONOMIC_EXPECTANCY_NEGATIVE",
                instrument=self.instrument,
                horizon=horizon,
                price_timestamp=ts_price
            )

        valid_until_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        return SignalContract(
            signal_id=f"sig_{dir_clean.lower()}_{int(datetime.now(timezone.utc).timestamp())}",
            generated_at=now_iso,
            valid_until=valid_until_iso,
            instrument=self.instrument,
            exchange=self.exchange,
            market_type="SPOT",
            reference_price=round(reference_price, 2),
            price_timestamp=ts_price,
            signal_horizon=horizon,
            maximum_holding_period=horizon,
            direction=SignalDirection(dir_clean),
            signal_status=SignalStatus.ACTIVE_CANDIDATE,
            model_id="AEER_v3.3_CANONICAL",
            model_version="v3.3",
            model_authorization="OFFLINE_RESEARCH_ONLY",
            execution_authorization=ExecutionAuthorization.DISABLED,
            event_probability=raw_probability,
            probability_target="TRIPLE_BARRIER_TP_FIRST",
            probability_horizon=horizon,
            calibration_status=CalibrationStatus.UNAVAILABLE if raw_probability is None else CalibrationStatus.CALIBRATED_CONFORMAL,
            entry_type=EntryType.CURRENT_MARKET_REFERENCE,
            entry_price=geom["entry_price"],
            take_profit=geom["take_profit"],
            stop_loss=geom["stop_loss"],
            risk_distance=geom["risk_distance"],
            reward_distance=geom["reward_distance"],
            gross_reward_to_risk=geom["gross_reward_to_risk"],
            net_reward_to_risk=geom["net_reward_to_risk"],
            estimated_costs={"cost_bps": effective_cost_bps, "total_cost_distance": geom["cost_distance"]},
            net_expected_value=round(ev_net, 1)
        )


# Global Singleton Engine
scenario_engine = ScenarioContractEngine()


SCENARIO_PLANNER_VERSION = "SCENARIO_PLANNER_v1.0"
SUPPORTED_HOURLY_HORIZONS = ["1h", "4h", "24h"]
DEFAULT_MAX_STALENESS_SECONDS = 10800.0  # 3.0 hours conservative threshold for closed hourly candles


class HypotheticalScenarioPlanner:
    """
    Independent calculation service for computing mathematically consistent
    hypothetical LONG and SHORT bracket levels (Entry reference, TP, SL, and Gross R:R)
    around a verified market reference and documented rolling volatility estimator.

    Strict Architectural Separation:
    - This service does NOT forecast price direction.
    - It does NOT require or inherit directional model authorization.
    - It is NOT an approved or actionable trading recommendation (is_actionable = False).
    - It NEVER updates the active signal store, paper position ledger, or chart markers.
    """

    SUPPORTED_HORIZONS = {
        "1h": 1.0,
        "4h": 4.0,
        "24h": 24.0,
        "1d": 24.0
    }
    UNSUPPORTED_SUB_HOURLY = ["5m", "15m", "30m"]

    def __init__(
        self,
        ohlcv_path: Optional[str] = None,
        default_k_tp: float = 1.5,
        default_k_sl: float = 1.0,
        lookback_bars: int = 24,
        max_staleness_seconds: float = DEFAULT_MAX_STALENESS_SECONDS
    ):
        self.ohlcv_path = ohlcv_path or "data/raw/ohlcv.parquet"
        self.default_k_tp = default_k_tp
        self.default_k_sl = default_k_sl
        self.lookback_bars = lookback_bars
        self.max_staleness_seconds = max_staleness_seconds

    def get_latest_verified_market_state(
        self,
        as_of_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extracts the latest closed candle and rolling log-return volatility
        strictly within the most recent continuous data segment.
        Enforces a conservative maximum staleness policy (3.0 hours max age).
        """
        import os
        import pandas as pd

        if not os.path.exists(self.ohlcv_path):
            return {
                "is_valid": False,
                "error_code": "MARKET_DATA_UNAVAILABLE",
                "narrative": f"Parquet dataset not found at {self.ohlcv_path}",
                "source": "Coinbase Spot",
                "instrument": "BTC/USD",
                "source_timeframe": "1h",
                "market_source": "Coinbase Spot (Closed Hourly Candle)"
            }

        try:
            df = pd.read_parquet(self.ohlcv_path)
            if df.empty:
                return {
                    "is_valid": False,
                    "error_code": "MARKET_DATA_EMPTY",
                    "narrative": "Parquet dataset contains 0 records.",
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "market_source": "Coinbase Spot (Closed Hourly Candle)"
                }

            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Detect contiguous segments
            diffs = df["timestamp"].diff()
            expected_delta = pd.Timedelta(hours=1)
            is_gap = diffs != expected_delta
            # First row diff is NaT
            is_gap.iloc[0] = False
            gap_indices = df.index[is_gap].tolist()

            last_seg_start = gap_indices[-1] if gap_indices else 0
            seg_df = df.iloc[last_seg_start:].copy().reset_index(drop=True)

            n_seg = len(seg_df)
            segment_id = len(gap_indices) + 1
            if n_seg < (self.lookback_bars + 1):
                return {
                    "is_valid": False,
                    "error_code": "INSUFFICIENT_CONTINUOUS_HISTORY",
                    "narrative": f"Continuous segment has {n_seg} bars; minimum {self.lookback_bars + 1} required for {self.lookback_bars}-bar lookback.",
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "continuity_segment_id": segment_id,
                    "segment_bars_available": n_seg,
                    "market_source": "Coinbase Spot (Closed Hourly Candle)"
                }

            # Preceding valid closed hourly bars within segment
            bars = seg_df.tail(self.lookback_bars + 1).copy().reset_index(drop=True)
            lookback_start_ts = bars.iloc[0]["timestamp"].isoformat()
            lookback_end_ts = bars.iloc[-1]["timestamp"].isoformat()

            log_returns = np.log(bars["close"] / bars["close"].shift(1)).dropna().values

            if len(log_returns) < self.lookback_bars:
                return {
                    "is_valid": False,
                    "error_code": "INSUFFICIENT_LOG_RETURNS",
                    "narrative": f"Calculated {len(log_returns)} log returns; expected {self.lookback_bars}.",
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "continuity_segment_id": segment_id,
                    "segment_bars_available": n_seg,
                    "market_source": "Coinbase Spot (Closed Hourly Candle)"
                }

            sigma_1h = float(np.std(log_returns, ddof=1))
            if math.isnan(sigma_1h) or math.isinf(sigma_1h) or sigma_1h <= 0.0:
                return {
                    "is_valid": False,
                    "error_code": "INVALID_VOLATILITY_ESTIMATE",
                    "narrative": f"Calculated non-finite or non-positive sigma_1h: {sigma_1h}",
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "continuity_segment_id": segment_id,
                    "segment_bars_available": n_seg,
                    "market_source": "Coinbase Spot (Closed Hourly Candle)"
                }

            latest_row = seg_df.iloc[-1]
            ref_price = float(latest_row["close"])
            ref_ts = latest_row["timestamp"].isoformat()

            # Measure age from latest timestamp relative to evaluation time
            ref_now = as_of_time if as_of_time is not None else datetime.now(timezone.utc)
            ts_dt = latest_row["timestamp"].to_pydatetime()
            age_sec = max(0.0, (ref_now - ts_dt).total_seconds())

            # Freshness Policy: reject data older than max_staleness_seconds
            if age_sec > self.max_staleness_seconds:
                return {
                    "is_valid": False,
                    "error_code": "MARKET_DATA_STALE",
                    "narrative": (
                        f"Market data timestamp ({ref_ts}) is {age_sec:.1f}s old, "
                        f"exceeding conservative maximum allowable staleness threshold "
                        f"of {self.max_staleness_seconds:.1f}s (3.0 hours)."
                    ),
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "reference_price": ref_price,
                    "price_timestamp": ref_ts,
                    "reference_price_timestamp_utc": ref_ts,
                    "price_freshness_seconds": round(age_sec, 1),
                    "reference_price_age_seconds": round(age_sec, 1),
                    "volatility_data_age_seconds": round(age_sec, 1),
                    "latest_volatility_candle_timestamp_utc": lookback_end_ts,
                    "volatility_lookback_start_utc": lookback_start_ts,
                    "volatility_lookback_end_utc": lookback_end_ts,
                    "volatility_observation_count": len(log_returns),
                    "continuity_segment_id": segment_id,
                    "segment_bars_available": n_seg,
                    "sigma_1h": sigma_1h,
                    "lookback_bars": self.lookback_bars,
                    "staleness_threshold_seconds": self.max_staleness_seconds,
                    "market_source": "Coinbase Spot (Closed Hourly Candle)"
                }

            return {
                "is_valid": True,
                "source": "Coinbase Spot",
                "instrument": "BTC/USD",
                "source_timeframe": "1h",
                "reference_price": ref_price,
                "price_timestamp": ref_ts,
                "reference_price_timestamp_utc": ref_ts,
                "price_freshness_seconds": round(age_sec, 1),
                "reference_price_age_seconds": round(age_sec, 1),
                "volatility_data_age_seconds": round(age_sec, 1),
                "latest_volatility_candle_timestamp_utc": lookback_end_ts,
                "volatility_lookback_start_utc": lookback_start_ts,
                "volatility_lookback_end_utc": lookback_end_ts,
                "volatility_observation_count": len(log_returns),
                "continuity_segment_id": segment_id,
                "segment_bars_available": n_seg,
                "sigma_1h": sigma_1h,
                "lookback_bars": self.lookback_bars,
                "staleness_threshold_seconds": self.max_staleness_seconds,
                "market_source": "Coinbase Spot (Closed Hourly Candle)"
            }
        except Exception as e:
            return {
                "is_valid": False,
                "error_code": "MARKET_DATA_EXCEPTION",
                "narrative": f"Failed reading market dataset: {str(e)}",
                "source": "Coinbase Spot",
                "instrument": "BTC/USD",
                "source_timeframe": "1h",
                "market_source": "Coinbase Spot (Closed Hourly Candle)"
            }

    def compute_scenario_preview(
        self,
        horizon: str = "24h",
        entry_price: Optional[float] = None,
        k_tp: Optional[float] = None,
        k_sl: Optional[float] = None,
        custom_entry_price: Optional[float] = None,
        as_of_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Computes side-by-side hypothetical LONG and SHORT bracket scenarios.
        Enforces strict geometric invariants, input freshness, and error handling.
        
        Parameters
        ----------
        custom_entry_price : float, optional
            User-supplied hypothetical anchor price. When provided the response
            ``anchor_source`` is set to ``"USER_CUSTOM"`` rather than
            ``"VERIFIED_MARKET_REFERENCE"``. Takes precedence over ``entry_price``.
        as_of_time : datetime, optional
            Evaluation timestamp for reproducible freshness and staleness audits.
            Defaults to current UTC time.
        """
        # Accept `custom_entry_price` as an explicit alias so callers can distinguish
        # a user-hypothetical anchor from the live reference. If both are provided,
        # custom_entry_price takes precedence.
        if custom_entry_price is not None:
            entry_price = custom_entry_price
        h_norm = str(horizon).lower().strip()
        ktp = float(k_tp if k_tp is not None and k_tp > 0 else self.default_k_tp)
        ksl = float(k_sl if k_sl is not None and k_sl > 0 else self.default_k_sl)

        # 1. Frequency gate: reject sub-hourly requests
        if h_norm in self.UNSUPPORTED_SUB_HOURLY:
            mkt_state = self.get_latest_verified_market_state(as_of_time=as_of_time)
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "DATA_FREQUENCY_UNSUPPORTED",
                "rejection_narrative": f"Hourly data only: Horizon '{horizon}' is unsupported; only Hourly data (1h, 4h, 24h) is verified.",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "source": mkt_state.get("source", "Coinbase Spot"),
                "instrument": mkt_state.get("instrument", "BTC/USD"),
                "source_timeframe": "1h",
                "market_source": mkt_state.get("market_source", "Coinbase Spot (Closed Hourly Candle)"),
                "reference_price": mkt_state.get("reference_price"),
                "price_timestamp": mkt_state.get("price_timestamp"),
                "reference_price_timestamp_utc": mkt_state.get("reference_price_timestamp_utc"),
                "price_freshness_seconds": mkt_state.get("price_freshness_seconds"),
                "reference_price_age_seconds": mkt_state.get("reference_price_age_seconds"),
                "latest_volatility_candle_timestamp_utc": mkt_state.get("latest_volatility_candle_timestamp_utc"),
                "volatility_data_age_seconds": mkt_state.get("volatility_data_age_seconds"),
                "volatility_lookback_start_utc": mkt_state.get("volatility_lookback_start_utc"),
                "volatility_lookback_end_utc": mkt_state.get("volatility_lookback_end_utc"),
                "volatility_observation_count": mkt_state.get("volatility_observation_count"),
                "volatility_input_1h": mkt_state.get("sigma_1h"),
                "volatility_1h": mkt_state.get("sigma_1h"),
                "continuity_segment_id": mkt_state.get("continuity_segment_id"),
                "segment_bars_available": mkt_state.get("segment_bars_available"),
                "staleness_threshold_seconds": mkt_state.get("staleness_threshold_seconds", self.max_staleness_seconds),
                "selected_horizon": horizon,
                "contract_version": SCENARIO_PLANNER_VERSION,
                "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED.",
                "scenarios": None
            }

        if h_norm not in self.SUPPORTED_HORIZONS:
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "HORIZON_NOT_SUPPORTED",
                "rejection_narrative": f"Horizon '{horizon}' is not in supported list: {list(self.SUPPORTED_HORIZONS.keys())}.",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "source": "Coinbase Spot",
                "instrument": "BTC/USD",
                "source_timeframe": "1h",
                "market_source": "Coinbase Spot (Closed Hourly Candle)",
                "selected_horizon": horizon,
                "contract_version": SCENARIO_PLANNER_VERSION,
                "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED.",
                "scenarios": None
            }

        horizon_hours = self.SUPPORTED_HORIZONS[h_norm]

        # 2. Get verified market state and volatility
        mkt_state = self.get_latest_verified_market_state(as_of_time=as_of_time)
        if not mkt_state["is_valid"]:
            return {
                "status": "UNAVAILABLE",
                "rejection_code": mkt_state["error_code"],
                "rejection_narrative": mkt_state["narrative"],
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "source": mkt_state.get("source", "Coinbase Spot"),
                "instrument": mkt_state.get("instrument", "BTC/USD"),
                "source_timeframe": mkt_state.get("source_timeframe", "1h"),
                "market_source": mkt_state.get("market_source", "Coinbase Spot (Closed Hourly Candle)"),
                "reference_price": mkt_state.get("reference_price"),
                "price_timestamp": mkt_state.get("price_timestamp"),
                "reference_price_timestamp_utc": mkt_state.get("reference_price_timestamp_utc"),
                "reference_price_age_seconds": mkt_state.get("reference_price_age_seconds"),
                "latest_volatility_candle_timestamp_utc": mkt_state.get("latest_volatility_candle_timestamp_utc"),
                "volatility_data_age_seconds": mkt_state.get("volatility_data_age_seconds"),
                "volatility_lookback_start_utc": mkt_state.get("volatility_lookback_start_utc"),
                "volatility_lookback_end_utc": mkt_state.get("volatility_lookback_end_utc"),
                "volatility_observation_count": mkt_state.get("volatility_observation_count"),
                "continuity_segment_id": mkt_state.get("continuity_segment_id"),
                "segment_bars_available": mkt_state.get("segment_bars_available"),
                "staleness_threshold_seconds": mkt_state.get("staleness_threshold_seconds", self.max_staleness_seconds),
                "selected_horizon": horizon,
                "contract_version": SCENARIO_PLANNER_VERSION,
                "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED.",
                "scenarios": None
            }

        # 3. Determine Entry Reference Price P
        if entry_price is not None:
            try:
                p_user = float(entry_price)
                if math.isnan(p_user) or math.isinf(p_user) or p_user <= 0.0:
                    return {
                        "status": "UNAVAILABLE",
                        "rejection_code": "INVALID_CUSTOM_ENTRY_PRICE",
                        "rejection_narrative": f"User-entered entry price must be positive and finite; got {entry_price}",
                        "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                        "is_actionable": False,
                        "execution_authorization": "DISABLED",
                        "source": "Coinbase Spot",
                        "instrument": "BTC/USD",
                        "source_timeframe": "1h",
                        "market_source": "Coinbase Spot (Closed Hourly Candle)",
                        "selected_horizon": horizon,
                        "contract_version": SCENARIO_PLANNER_VERSION,
                        "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED.",
                        "scenarios": None
                    }
                ref_price = p_user
                anchor_source = "USER_CUSTOM"
            except (ValueError, TypeError):
                return {
                    "status": "UNAVAILABLE",
                    "rejection_code": "INVALID_CUSTOM_ENTRY_PRICE",
                    "rejection_narrative": f"User-entered entry price could not be parsed as float: {entry_price}",
                    "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                    "is_actionable": False,
                    "execution_authorization": "DISABLED",
                    "source": "Coinbase Spot",
                    "instrument": "BTC/USD",
                    "source_timeframe": "1h",
                    "market_source": "Coinbase Spot (Closed Hourly Candle)",
                    "selected_horizon": horizon,
                    "contract_version": SCENARIO_PLANNER_VERSION,
                    "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED.",
                    "scenarios": None
                }
        else:
            ref_price = mkt_state["reference_price"]
            anchor_source = "VERIFIED_MARKET_REFERENCE"

        # 4. Volatility Scaling across horizon (Square-Root-of-Time approximation)
        sigma_1h = mkt_state["sigma_1h"]
        sigma_h = sigma_1h * math.sqrt(horizon_hours)

        # 5. Price Level Computations
        # LONG: TP = P * exp(k_tp * sigma_H), SL = P * exp(-k_sl * sigma_H)
        long_tp = round(ref_price * math.exp(ktp * sigma_h), 2)
        long_sl = round(ref_price * math.exp(-ksl * sigma_h), 2)

        # Enforce strict invariant: SL < Entry < TP
        if not (long_sl < ref_price < long_tp):
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "LONG_INVARIANT_VIOLATION",
                "rejection_narrative": f"Computed LONG levels violated SL < P < TP: SL={long_sl}, P={ref_price}, TP={long_tp}",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "scenarios": None
            }

        long_reward_usd = round(long_tp - ref_price, 2)
        long_risk_usd = round(ref_price - long_sl, 2)
        if long_risk_usd <= 0 or long_reward_usd <= 0:
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "NON_POSITIVE_DISTANCE",
                "rejection_narrative": "Computed zero or negative distance for LONG scenario.",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "scenarios": None
            }

        long_rr = round(long_reward_usd / long_risk_usd, 2)
        long_tp_pct = round((long_reward_usd / ref_price) * 100.0, 3)
        long_sl_pct = round((long_risk_usd / ref_price) * 100.0, 3)

        # SHORT: TP = P * exp(-k_tp * sigma_H), SL = P * exp(k_sl * sigma_H)
        short_tp = round(ref_price * math.exp(-ktp * sigma_h), 2)
        short_sl = round(ref_price * math.exp(ksl * sigma_h), 2)

        # Enforce strict invariant: TP < Entry < SL
        if not (short_tp < ref_price < short_sl):
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "SHORT_INVARIANT_VIOLATION",
                "rejection_narrative": f"Computed SHORT levels violated TP < P < SL: TP={short_tp}, P={ref_price}, SL={short_sl}",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "scenarios": None
            }

        short_reward_usd = round(ref_price - short_tp, 2)
        short_risk_usd = round(short_sl - ref_price, 2)
        if short_risk_usd <= 0 or short_reward_usd <= 0:
            return {
                "status": "UNAVAILABLE",
                "rejection_code": "NON_POSITIVE_DISTANCE",
                "rejection_narrative": "Computed zero or negative distance for SHORT scenario.",
                "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
                "is_actionable": False,
                "execution_authorization": "DISABLED",
                "scenarios": None
            }

        short_rr = round(short_reward_usd / short_risk_usd, 2)
        short_tp_pct = round((short_reward_usd / ref_price) * 100.0, 3)
        short_sl_pct = round((short_risk_usd / ref_price) * 100.0, 3)

        return {
            "status": "SUCCESS",
            "scenario_type": "HYPOTHETICAL_VOLATILITY_BARRIER",
            "is_actionable": False,
            "execution_authorization": "DISABLED",
            "source": mkt_state["source"],
            "instrument": mkt_state["instrument"],
            "source_timeframe": mkt_state["source_timeframe"],
            "market_type": "SPOT",
            "market_source": mkt_state["market_source"],
            "reference_price": round(ref_price, 2),
            "reference_price_timestamp_utc": mkt_state["reference_price_timestamp_utc"],
            "reference_price_age_seconds": mkt_state["reference_price_age_seconds"],
            "latest_volatility_candle_timestamp_utc": mkt_state["latest_volatility_candle_timestamp_utc"],
            "volatility_data_age_seconds": mkt_state["volatility_data_age_seconds"],
            "volatility_lookback_start_utc": mkt_state["volatility_lookback_start_utc"],
            "volatility_lookback_end_utc": mkt_state["volatility_lookback_end_utc"],
            "volatility_observation_count": mkt_state["volatility_observation_count"],
            "continuity_segment_id": mkt_state["continuity_segment_id"],
            "segment_bars_available": mkt_state["segment_bars_available"],
            "anchor_source": anchor_source,
            "price_timestamp": mkt_state["price_timestamp"],
            "price_freshness_seconds": mkt_state["price_freshness_seconds"],
            "selected_horizon": horizon,
            "horizon_hours": horizon_hours,
            "volatility_estimate": round(sigma_h, 6),
            "volatility_input_1h": round(sigma_1h, 6),
            "volatility_1h": round(sigma_1h, 6),
            "volatility_lookback_bars": mkt_state["lookback_bars"],
            "volatility_estimator": "ROLLING_LOG_RETURN_STD_SQRT_H",
            "volatility_units": "LOG_RETURN_STANDARD_DEVIATION",
            "horizon_scaling_method": "SQUARE_ROOT_OF_TIME_APPROXIMATION",
            "horizon_scaling_notice": (
                "Square-root-of-time scaling (sigma_H = sigma_1h * sqrt(H)) is a theoretical "
                "Brownian motion approximation under i.i.d. increments, NOT a validated forecast "
                "of future realized path volatility."
            ),
            "staleness_threshold_seconds": mkt_state["staleness_threshold_seconds"],
            "k_tp_multiplier": ktp,
            "k_sl_multiplier": ksl,
            "scenarios": {
                "LONG": {
                    "scenario": "LONG",
                    "entry_reference": round(ref_price, 2),
                    "take_profit": long_tp,
                    "stop_loss": long_sl,
                    "reward_distance_usd": long_reward_usd,
                    "risk_distance_usd": long_risk_usd,
                    "reward_distance_pct": long_tp_pct,
                    "risk_distance_pct": long_sl_pct,
                    "gross_reward_to_risk": long_rr,
                    "geometry_valid": True
                },
                "SHORT": {
                    "scenario": "SHORT",
                    "entry_reference": round(ref_price, 2),
                    "take_profit": short_tp,
                    "stop_loss": short_sl,
                    "reward_distance_usd": short_reward_usd,
                    "risk_distance_usd": short_risk_usd,
                    "reward_distance_pct": short_tp_pct,
                    "risk_distance_pct": short_sl_pct,
                    "gross_reward_to_risk": short_rr,
                    "geometry_valid": True
                }
            },
            "contract_version": SCENARIO_PLANNER_VERSION,
            "disclaimer": "Hypothetical volatility barrier calculation only. Does NOT constitute a directional prediction, trade signal, or investment advice. Execution authorization is DISABLED."
        }


# Global Singleton Planner Instance
scenario_planner = HypotheticalScenarioPlanner()

