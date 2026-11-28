"""
engine/market_state.py — Unified Multiscale Market-State Orchestrator
====================================================================
Synthesizes decoupled, multi-layer contextual market intelligence:
1. Microstructure State: 5m Hawkes event pressure, buy/sell intensity ratio, health
2. Short-Term State: 5m/15m momentum, OFI, liquidity
3. Intermediate State: 1h/4h technical trend, derivatives asymmetry, funding state
4. Volatility State: Multi-horizon volatility term structure and regime transitions
5. Derivatives State: Perpetual funding rate, open interest acceleration
6. Long-Term State: 24h Production Ridge excursion envelope and risk asymmetry
7. Deterministic Narrative: Rule-based explanation without probability blending
"""

import os
import sys
import time
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from engine.volatility_bridge import volatility_bridge_service, VolatilityTermStructure

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def classify_utc_session(dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Classifies the current UTC time into empirical trading session regimes using
    explicit, disjoint half-open minute intervals:
      - 00:00 <= t < 07:00 (0 <= m < 420):   ASIA_RANGE
      - 07:00 <= t < 13:30 (420 <= m < 810):  LONDON_EXPANSION
      - 13:30 <= t < 16:30 (810 <= m < 990):  NY_LONDON_OVERLAP
      - 16:30 <= t < 21:00 (990 <= m < 1260): US_AFTERNOON
      - 21:00 <= t < 24:00 (1260 <= m < 1440): POST_CLOSE_CHOP
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    hour = dt.hour
    minute = dt.minute
    m = hour * 60 + minute

    if 0 <= m < 420:
        state = "ASIA_RANGE"
    elif 420 <= m < 810:
        state = "LONDON_EXPANSION"
    elif 810 <= m < 990:
        state = "NY_LONDON_OVERLAP"
    elif 990 <= m < 1260:
        state = "US_AFTERNOON"
    else:
        state = "POST_CLOSE_CHOP"

    return {
        "session_state": state,
        "utc_hour": hour,
        "utc_minute": minute,
        "session_version": "1.0.0"
    }


def classify_derivatives_quadrant(price_change_pct: float, oi_change_pct: float, threshold: float = 0.05) -> str:
    """
    Neutral 4-quadrant state classification of price change vs open interest change:
      - PRICE_UP_OI_UP
      - PRICE_DOWN_OI_UP
      - PRICE_DOWN_OI_DOWN
      - PRICE_UP_OI_DOWN
      - STABLE
    Avoids prescriptive directional interpretations; provides empirical conditioning state.
    """
    if abs(price_change_pct) < threshold and abs(oi_change_pct) < threshold:
        return "STABLE"
    if price_change_pct >= threshold and oi_change_pct >= threshold:
        return "PRICE_UP_OI_UP"
    elif price_change_pct < -threshold and oi_change_pct >= threshold:
        return "PRICE_DOWN_OI_UP"
    elif price_change_pct < -threshold and oi_change_pct < -threshold:
        return "PRICE_DOWN_OI_DOWN"
    elif price_change_pct >= threshold and oi_change_pct < -threshold:
        return "PRICE_UP_OI_DOWN"
    return "STABLE"



# ---------------------------------------------------------------------------
# Real point-in-time inputs (added 2026-11-28)
# ---------------------------------------------------------------------------
# The market-state endpoint previously reported a hard-coded $65,200 tape while
# the live quote was $59,450. These helpers read the last closed hourly candle
# from the local dataset and refuse to answer when the observation is stale.
_LIVE_INPUT_CACHE: Dict[str, Any] = {"ts": 0.0, "value": None}
LIVE_INPUT_TTL_SECONDS = 60.0
# Shared with the status contract: age is measured from the newest CLOSED
# hourly bar, which is already 1h..2h old on a perfectly healthy feed. A bare
# 7200 s cut-off made the market state go DATA_UNAVAILABLE for part of every
# hour even though the feed was current.
from engine.status_contract import LIVE_MAX_CANDLE_AGE_SECONDS as _LIVE_MAX_AGE
MARKET_STATE_MAX_AGE_SECONDS = float(_LIVE_MAX_AGE)


def _load_live_inputs(ttl: float = LIVE_INPUT_TTL_SECONDS) -> Optional[Dict[str, Any]]:
    """Return {current_price, vol_24h, source} from the last closed candle, or None."""
    now = time.time()
    cached = _LIVE_INPUT_CACHE.get("value")
    if cached is not None and (now - float(_LIVE_INPUT_CACHE.get("ts", 0.0))) < ttl:
        return cached

    path = os.path.join(ROOT_DIR, "data", "raw", "ohlcv.parquet")
    if not os.path.exists(path):
        _LIVE_INPUT_CACHE.update({"ts": now, "value": None})
        return None
    try:
        df = pd.read_parquet(path, columns=["timestamp", "close"])
    except Exception:
        _LIVE_INPUT_CACHE.update({"ts": now, "value": None})
        return None
    if df.empty or len(df) < 25:
        _LIVE_INPUT_CACHE.update({"ts": now, "value": None})
        return None

    df = df.sort_values("timestamp")
    last_ts = pd.Timestamp(df["timestamp"].iloc[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    age = (datetime.now(timezone.utc) - last_ts.to_pydatetime()).total_seconds()
    if age > MARKET_STATE_MAX_AGE_SECONDS:
        _LIVE_INPUT_CACHE.update({"ts": now, "value": None})
        return None

    closes = df["close"].astype(float).to_numpy()[-25:]
    if not np.all(np.isfinite(closes)) or closes[-1] <= 0:
        _LIVE_INPUT_CACHE.update({"ts": now, "value": None})
        return None
    log_ret = np.diff(np.log(closes))
    vol_24h = float(np.std(log_ret, ddof=1) * np.sqrt(24.0)) if log_ret.size >= 2 else 0.0

    value = {
        "current_price": float(closes[-1]),
        "vol_24h": vol_24h,
        "source": f"ohlcv.parquet last closed candle {last_ts.isoformat()} (age {age:.0f}s)",
    }
    _LIVE_INPUT_CACHE.update({"ts": now, "value": value})
    return value


@dataclass
class MarketState:
    timestamp: str
    symbol: str
    current_price: float
    microstructure_state: Dict[str, Any]
    short_term_state: Dict[str, Any]
    intermediate_state: Dict[str, Any]
    volatility_state: Dict[str, Any]
    derivatives_state: Dict[str, Any]
    long_term_state: Dict[str, Any]
    uncertainty_state: Dict[str, Any]
    explanation: Dict[str, str]
    overall_data_quality: str
    model_versions: Dict[str, str]
    session_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketStateEngine:
    """
    Assembles real-time unified multiscale market state across decoupled subsystems.
    """

    def evaluate_market_state(
        self,
        current_price: Optional[float] = None,
        vol_24h: Optional[float] = None,
        hawkes_direction: Optional[str] = None,
        uncertainty: Optional[float] = None,
        persist: bool = False,
    ) -> MarketState:
        """
        Build the market state from REAL inputs only.

        Governance (AGENTS.md §2.5): this method used to return hard-coded
        defaults (price 65200.0, vol 0.015, "BEARISH", a $65,200 tape that was
        9.7% away from the live quote) stamped overall_data_quality="VALID" and
        governance_status="PRODUCTION". Anything that cannot be derived from a
        real observation is now reported as UNAVAILABLE with a null value, and a
        missing/stale price source returns a DATA_UNAVAILABLE state instead of
        invented numbers.
        """
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        session_ctx = classify_utc_session(now_dt)

        source_note = "supplied"
        if current_price is None or vol_24h is None:
            derived = _load_live_inputs()
            if derived is None:
                return self._unavailable_state(
                    now_iso, session_ctx,
                    reason="No fresh closed-candle observation available for the market state.",
                )
            if current_price is None:
                current_price = derived["current_price"]
            if vol_24h is None:
                vol_24h = derived["vol_24h"]
            source_note = derived["source"]

        try:
            current_price = float(current_price)
            vol_24h = float(vol_24h)
        except (TypeError, ValueError):
            return self._unavailable_state(
                now_iso, session_ctx, reason="Non-numeric price or volatility input.",
            )
        if not np.isfinite(current_price) or current_price <= 0 or not np.isfinite(vol_24h) or vol_24h < 0:
            return self._unavailable_state(
                now_iso, session_ctx, reason="Non-positive price or negative volatility input.",
            )

        # Volatility term structure
        vol_ts = volatility_bridge_service.analyze_term_structure(vol_24h=vol_24h)

        # Microstructure / order-flow subsystems have no wired point-in-time
        # source on this path, so they are reported as unavailable rather than
        # filled with invented intensities.
        micro_state = {
            "hawkes_event_pressure": None,
            "buy_sell_intensity_ratio": None,
            "liquidity_intensity": None,
            "volatility_intensity": None,
            "short_term_direction": hawkes_direction,
            "short_term_uncertainty": None,
            "governance_status": "UNAVAILABLE",
        }

        short_state = {
            "short_term_momentum": None,
            "short_term_range": f"${round(current_price * 0.998, 2)} - ${round(current_price * 1.002, 2)}",
            "short_term_range_basis": "nominal +/-0.2% band around the reference price, not a model forecast",
            "order_flow_state": None,
            "governance_status": "UNAVAILABLE",
        }

        inter_state = {
            "1h_volatility_bps": round(vol_24h * 10000.0 / np.sqrt(24.0), 1),
            "1h_technical_trend": None,
            "1h_ofi_state": None,
            "4h_volatility_bps": round(vol_24h * 10000.0 / np.sqrt(6.0), 1),
            "4h_derivatives_asymmetry": None,
            "4h_funding_state": None,
            "governance_status": "RESEARCH_ONLY",
        }

        deriv_state = {
            "perp_funding_rate_8h": None,
            "open_interest_24h_change_pct": None,
            "funding_regime": None,
            "derivatives_quadrant": None,
            "governance_status": "UNAVAILABLE",
        }

        # P90 excursion band derived from the supplied 24h volatility, not from
        # hard-coded percentages.
        z90 = 1.6449
        upper = current_price * float(np.exp(z90 * vol_24h))
        lower = current_price * float(np.exp(-z90 * vol_24h))
        long_state = {
            "24h_mfe_p50_pct": None,
            "24h_mae_p50_pct": None,
            "upper_p90": round(upper, 2),
            "lower_p90": round(lower, 2),
            "band_basis": "lognormal 90% band from the supplied 24h realized volatility (nominal, uncalibrated)",
            "long_term_risk_state": None,
            "governance_status": "RESEARCH_ONLY",
        }

        uncert_state = {
            "composite_uncertainty": uncertainty,
            "confidence_band": None,
            "conformal_coverage_p90": None,
        }

        explanation = {
            "summary": (
                f"Reference price {current_price:,.2f} with a 24h realized volatility of "
                f"{vol_24h * 100:.2f}% ({vol_ts.regime}). Microstructure, order-flow and "
                "derivatives states are reported as unavailable because no point-in-time "
                "source is wired into this path."
            ),
            "input_source": source_note,
            "governance": "OFFLINE_RESEARCH_ONLY — descriptive only, no directional recommendation.",
        }

        ms = MarketState(
            timestamp=now_iso,
            symbol="BTCUSD",
            current_price=current_price,
            microstructure_state=micro_state,
            short_term_state=short_state,
            intermediate_state=inter_state,
            volatility_state=vol_ts.to_dict(),
            derivatives_state=deriv_state,
            long_term_state=long_state,
            uncertainty_state=uncert_state,
            explanation=explanation,
            overall_data_quality="PARTIAL_REAL_INPUTS",
            model_versions={
                "production_ridge": "NOT_LOADED",
                "shadow_hawkes": "NOT_LOADED",
                "volatility_bridge": "v1.0.0-deterministic-term-structure"
            },
            session_context=session_ctx
        )

        if persist:
            # Persistence is opt-in: a GET must never truncate the history file.
            self._append_snapshot(ms, vol_ts.regime)

        return ms

    # One canonical column order for every snapshot row. Rows written before
    # 2026-11-28 used a different layout (and contained fabricated defaults such
    # as price 65200.0), so a mismatched header is quarantined rather than
    # appended to, which would interleave two schemas in one file.
    SNAPSHOT_COLUMNS = (
        "timestamp", "current_price", "volatility_regime",
        "short_direction", "long_risk_state", "uncertainty", "data_quality",
    )

    @classmethod
    def _append_snapshot(cls, ms: "MarketState", regime: str) -> None:
        csv_path = os.path.join(RESULTS_DIR, "market_state.csv")
        if os.path.exists(csv_path):
            try:
                existing_header = tuple(pd.read_csv(csv_path, nrows=0).columns)
            except Exception:
                existing_header = ()
            if existing_header != cls.SNAPSHOT_COLUMNS:
                legacy_path = os.path.join(
                    RESULTS_DIR, f"market_state.legacy-{int(time.time())}.csv"
                )
                os.replace(csv_path, legacy_path)
                print(f"Market-state store had a legacy schema; archived to {legacy_path}")
        row = pd.DataFrame([{
            "timestamp": ms.timestamp,
            "current_price": ms.current_price,
            "volatility_regime": regime,
            "short_direction": ms.short_term_state.get("short_term_direction"),
            "long_risk_state": ms.long_term_state.get("long_term_risk_state"),
            "uncertainty": ms.uncertainty_state.get("composite_uncertainty"),
            "data_quality": ms.overall_data_quality,
        }], columns=list(cls.SNAPSHOT_COLUMNS))
        row.to_csv(csv_path, index=False, mode="a", header=not os.path.exists(csv_path))

    def _unavailable_state(self, now_iso: str, session_ctx: Optional[Dict[str, Any]], reason: str) -> MarketState:
        """Explicit typed unavailable state (never invented values)."""
        return MarketState(
            timestamp=now_iso,
            symbol="BTCUSD",
            current_price=None,
            microstructure_state={"governance_status": "UNAVAILABLE"},
            short_term_state={"governance_status": "UNAVAILABLE"},
            intermediate_state={"governance_status": "UNAVAILABLE"},
            volatility_state={"governance_status": "UNAVAILABLE"},
            derivatives_state={"governance_status": "UNAVAILABLE"},
            long_term_state={"governance_status": "UNAVAILABLE"},
            uncertainty_state={"governance_status": "UNAVAILABLE"},
            explanation={"summary": reason, "governance": "DATA_UNAVAILABLE"},
            overall_data_quality="DATA_UNAVAILABLE",
            model_versions={"production_ridge": "NOT_LOADED", "shadow_hawkes": "NOT_LOADED"},
            session_context=session_ctx,
        )


market_state_engine = MarketStateEngine()
