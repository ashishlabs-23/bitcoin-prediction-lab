"""
engine/barrier_resolver.py — Deterministic Barrier Resolver
===========================================================
Implements deterministic, causal evaluation of triple-barrier candidate excursions.

Epistemic & Causality Invariants:
1. Conservative Intrabar Collision Rule: If both TP and SL are penetrated within
   the same candle (e.g. High >= TP and Low <= SL), the resolver MUST resolve to
   SL_FIRST and set is_ambiguous_touch=True. One-minute candles cannot establish
   sub-minute arrival order.
2. Gap Handling: If candle Open gaps beyond a barrier, exit price is filled at Open,
   capturing slippage on gap-openings.
3. Strict Causal Ordering: Bars preceding or equal to the decision timestamp are rejected.
   Evaluation begins strictly from fill_timestamp_utc onward.
4. MFE / MAE Tracking: Path-dependent Maximum Favorable Excursion and Maximum Adverse Excursion
   are computed in R-multiples across every traversed candle.
5. Horizon Timeout: If neither barrier is touched within horizon_bars, position exits at the
   closing price of the horizon candle with exit_reason="TIMEOUT".
"""

from typing import List, Dict, Any, Union
import math
from engine.entry_contracts import CandidateSetup, ResolutionOutcome


class DeterministicBarrierResolver:
    """
    Deterministic triple-barrier resolver adhering to conservative non-optimistic rules.
    """

    RESOLVER_VERSION = "DETERMINISTIC_BARRIER_RESOLVER_V1"

    @classmethod
    def resolve_candidate(
        cls,
        candidate: CandidateSetup,
        bars: List[Dict[str, Any]]
    ) -> ResolutionOutcome:
        """
        Deterministically resolves a CandidateSetup against an ordered sequence of OHLCV bars.

        Parameters:
            candidate: Immutable CandidateSetup contract.
            bars: List of dicts with keys: 'timestamp_utc', 'open', 'high', 'low', 'close'.

        Returns:
            ResolutionOutcome with exact fill, return in R, MFE/MAE, and ambiguity audit.
        """
        if not bars:
            raise ValueError(f"Cannot resolve candidate {candidate.candidate_id}: bars list is empty.")

        entry = candidate.proposed_entry_price
        tp = candidate.take_profit_price
        sl = candidate.stop_loss_price
        is_long = candidate.direction.upper() == "LONG"
        risk_per_coin = entry * (candidate.k_sl * max(0.002, candidate.sigma_at_t0))

        mfe_r = 0.0
        mae_r = 0.0
        bars_held = 0

        for idx, bar in enumerate(bars):
            # Causal verification: bar timestamp must not precede fill timestamp
            bar_ts = str(bar.get("timestamp_utc", ""))
            if bar_ts and bar_ts < candidate.fill_timestamp_utc:
                raise ValueError(
                    f"Causal violation in candidate {candidate.candidate_id}: "
                    f"bar timestamp {bar_ts} precedes fill timestamp {candidate.fill_timestamp_utc}."
                )

            bars_held += 1
            b_open = float(bar["open"])
            b_high = float(bar["high"])
            b_low = float(bar["low"])
            b_close = float(bar["close"])

            # 1. Update MFE & MAE in R-multiples
            if is_long:
                fav_excursion = (b_high - entry) / risk_per_coin
                adv_excursion = (b_low - entry) / risk_per_coin
            else:  # SHORT
                fav_excursion = (entry - b_low) / risk_per_coin
                adv_excursion = (entry - b_high) / risk_per_coin

            mfe_r = max(mfe_r, fav_excursion)
            mae_r = min(mae_r, adv_excursion)

            # 2. Check for Opening Gaps
            if is_long:
                if b_open >= tp:
                    return cls._create_outcome(
                        candidate=candidate,
                        exit_ts=bar_ts,
                        exit_price=b_open,
                        exit_reason="TP_FIRST",
                        bars_held=bars_held,
                        gross_r=(b_open - entry) / risk_per_coin,
                        mfe_r=max(mfe_r, (b_open - entry) / risk_per_coin),
                        mae_r=mae_r,
                        is_ambiguous=False,
                        ambiguity_reason=None
                    )
                if b_open <= sl:
                    return cls._create_outcome(
                        candidate=candidate,
                        exit_ts=bar_ts,
                        exit_price=b_open,
                        exit_reason="SL_FIRST",
                        bars_held=bars_held,
                        gross_r=(b_open - entry) / risk_per_coin,
                        mfe_r=mfe_r,
                        mae_r=min(mae_r, (b_open - entry) / risk_per_coin),
                        is_ambiguous=False,
                        ambiguity_reason=None
                    )
            else:  # SHORT
                if b_open <= tp:
                    return cls._create_outcome(
                        candidate=candidate,
                        exit_ts=bar_ts,
                        exit_price=b_open,
                        exit_reason="TP_FIRST",
                        bars_held=bars_held,
                        gross_r=(entry - b_open) / risk_per_coin,
                        mfe_r=max(mfe_r, (entry - b_open) / risk_per_coin),
                        mae_r=mae_r,
                        is_ambiguous=False,
                        ambiguity_reason=None
                    )
                if b_open >= sl:
                    return cls._create_outcome(
                        candidate=candidate,
                        exit_ts=bar_ts,
                        exit_price=b_open,
                        exit_reason="SL_FIRST",
                        bars_held=bars_held,
                        gross_r=(entry - b_open) / risk_per_coin,
                        mfe_r=mfe_r,
                        mae_r=min(mae_r, (entry - b_open) / risk_per_coin),
                        is_ambiguous=False,
                        ambiguity_reason=None
                    )

            # 3. Check for Intrabar Barrier Touches
            if is_long:
                tp_touched = b_high >= tp
                sl_touched = b_low <= sl
            else:  # SHORT
                tp_touched = b_low <= tp
                sl_touched = b_high >= sl

            # 4. Same-candle Collision Resolution
            if tp_touched and sl_touched:
                # Epistemic Rule: Conservative SL_FIRST resolution with explicit ambiguity flag
                gross_r = (sl - entry) / risk_per_coin if is_long else (entry - sl) / risk_per_coin
                return cls._create_outcome(
                    candidate=candidate,
                    exit_ts=bar_ts,
                    exit_price=sl,
                    exit_reason="INTRABAR_COLLISION_RESOLVED_SL",
                    bars_held=bars_held,
                    gross_r=gross_r,
                    mfe_r=mfe_r,
                    mae_r=mae_r,
                    is_ambiguous=True,
                    ambiguity_reason="INTRABAR_COLLISION_BOTH_BARRIERS_TOUCHED"
                )

            # 5. Single Barrier Touches
            if tp_touched:
                gross_r = (tp - entry) / risk_per_coin if is_long else (entry - tp) / risk_per_coin
                return cls._create_outcome(
                    candidate=candidate,
                    exit_ts=bar_ts,
                    exit_price=tp,
                    exit_reason="TP_FIRST",
                    bars_held=bars_held,
                    gross_r=gross_r,
                    mfe_r=mfe_r,
                    mae_r=mae_r,
                    is_ambiguous=False,
                    ambiguity_reason=None
                )

            if sl_touched:
                gross_r = (sl - entry) / risk_per_coin if is_long else (entry - sl) / risk_per_coin
                return cls._create_outcome(
                    candidate=candidate,
                    exit_ts=bar_ts,
                    exit_price=sl,
                    exit_reason="SL_FIRST",
                    bars_held=bars_held,
                    gross_r=gross_r,
                    mfe_r=mfe_r,
                    mae_r=mae_r,
                    is_ambiguous=False,
                    ambiguity_reason=None
                )

            # 6. Check Horizon Expiry
            if bars_held >= candidate.horizon_bars:
                gross_r = (b_close - entry) / risk_per_coin if is_long else (entry - b_close) / risk_per_coin
                return cls._create_outcome(
                    candidate=candidate,
                    exit_ts=bar_ts,
                    exit_price=b_close,
                    exit_reason="TIMEOUT",
                    bars_held=bars_held,
                    gross_r=gross_r,
                    mfe_r=mfe_r,
                    mae_r=mae_r,
                    is_ambiguous=False,
                    ambiguity_reason=None
                )

        # If bars exhausted before horizon reached, return timeout on last available candle
        last_bar = bars[-1]
        last_close = float(last_bar["close"])
        last_ts = str(last_bar.get("timestamp_utc", ""))
        gross_r = (last_close - entry) / risk_per_coin if is_long else (entry - last_close) / risk_per_coin

        return cls._create_outcome(
            candidate=candidate,
            exit_ts=last_ts,
            exit_price=last_close,
            exit_reason="TIMEOUT",
            bars_held=bars_held,
            gross_r=gross_r,
            mfe_r=mfe_r,
            mae_r=mae_r,
            is_ambiguous=False,
            ambiguity_reason=None
        )

    @classmethod
    def _create_outcome(
        cls,
        candidate: CandidateSetup,
        exit_ts: str,
        exit_price: float,
        exit_reason: str,
        bars_held: int,
        gross_r: float,
        mfe_r: float,
        mae_r: float,
        is_ambiguous: bool,
        ambiguity_reason: Union[str, None]
    ) -> ResolutionOutcome:
        net_r = gross_r - candidate.friction_r
        return ResolutionOutcome(
            candidate_id=candidate.candidate_id,
            exit_timestamp_utc=exit_ts,
            exit_price=round(exit_price, 2),
            exit_reason=exit_reason,
            bars_held=bars_held,
            gross_return_r=round(gross_r, 4),
            net_return_r=round(net_r, 4),
            mfe_r=round(mfe_r, 4),
            mae_r=round(mae_r, 4),
            is_ambiguous_touch=is_ambiguous,
            ambiguity_reason=ambiguity_reason,
            cost_scenario=candidate.cost_scenario,
            round_trip_friction_bps=candidate.round_trip_friction_bps,
            friction_r=candidate.friction_r,
            resolver_version=cls.RESOLVER_VERSION
        )
