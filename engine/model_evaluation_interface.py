"""
engine/model_evaluation_interface.py — Universal Model Evaluation & Extensibility Layer
========================================================================================
BTCognitive V32.38: Adaptive Market Intelligence & Universal Model Interface

Provides a versioned, extensible forecasting interface unifying:
1. Directional GBDTs (directional-gbm-1h-v1, 4h, 24h).
2. Random Walk Persistence baseline (E[r]=0).
3. Rolling Empirical Quantile baseline.
4. Future candidate models (without requiring frontend refactors or modifying protected datasets).

All model adapters enforce strict OFFLINE_RESEARCH_ONLY governance and point-in-time causality.
"""

from __future__ import annotations

import os
import sys
import abc
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Sequence, Tuple
import numpy as np
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from engine.directional_forecast_service import verify_and_load_directional_model
from engine.l2_microstructure_features import L2MicrostructureSnapshot


@dataclass(frozen=True)
class ModelInputContext:
    """Immutable causal market input context available at decision epoch t."""
    origin_epoch: float
    origin_timestamp_utc: str
    current_price: float
    ret_1h: float
    ret_4h: float
    ret_24h: float
    ret_168h: float
    historical_closes: Sequence[float]
    l2_snapshot: Optional[L2MicrostructureSnapshot] = None
    schema_version: str = "v32.38.input_context"

    @classmethod
    def from_closes(
        cls,
        closes: Sequence[float],
        epoch: float,
        l2_snapshot: Optional[L2MicrostructureSnapshot] = None
    ) -> ModelInputContext:
        if len(closes) < 169:
            raise ValueError(f"Need at least 169 closed bars for causal return lags; got {len(closes)}")
        c_t = float(closes[-1])
        ts_utc = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        return cls(
            origin_epoch=epoch,
            origin_timestamp_utc=ts_utc,
            current_price=c_t,
            ret_1h=float(math.log(c_t / closes[-2])),
            ret_4h=float(math.log(c_t / closes[-5])),
            ret_24h=float(math.log(c_t / closes[-25])),
            ret_168h=float(math.log(c_t / closes[-169])),
            historical_closes=closes,
            l2_snapshot=l2_snapshot
        )


@dataclass(frozen=True)
class ModelForecast:
    """Standardized versioned forecast emission across all models."""
    model_id: str
    model_version: str
    horizon_hours: int
    issue_epoch: float
    issue_timestamp_utc: str
    point_forecast_price: float
    point_forecast_return: float
    predicted_direction: int  # 1 for UP, 0 for DOWN
    prob_up: Optional[float]
    quantiles: Dict[str, float]  # {"p10": ..., "p50": ..., "p90": ...}
    governance_authorization: str = "OFFLINE_RESEARCH_ONLY"
    schema_version: str = "v32.38.model_forecast"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ForecastModelInterface(abc.ABC):
    """Abstract base class for all versioned forecasting models in BTCognitive."""

    @property
    @abc.abstractmethod
    def model_id(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def supported_horizons(self) -> List[int]:
        pass

    @abc.abstractmethod
    def predict(self, context: ModelInputContext, horizon_hours: int) -> ModelForecast:
        pass


class GBDTDirectionalModelAdapter(ForecastModelInterface):
    """
    Adapter wrapping verified frozen LightGBM directional classifiers
    for 1h, 4h, and 24h horizons.
    """

    def __init__(self):
        self._models: Dict[int, Any] = {}
        for h_str, h_int in [("1h", 1), ("4h", 4), ("24h", 24)]:
            m, info, err = verify_and_load_directional_model(h_str)
            if err or m is None:
                raise RuntimeError(f"Failed loading GBDT for {h_str}: {err}")
            self._models[h_int] = m

    @property
    def model_id(self) -> str:
        return "directional-gbm-suite-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_horizons(self) -> List[int]:
        return [1, 4, 24]

    def predict(self, context: ModelInputContext, horizon_hours: int) -> ModelForecast:
        if horizon_hours not in self._models:
            raise ValueError(f"Unsupported horizon {horizon_hours}h. Supported: {self.supported_horizons}")

        model = self._models[horizon_hours]
        feat_df = pd.DataFrame(
            [[context.ret_1h, context.ret_4h, context.ret_24h, context.ret_168h]],
            columns=["ret_1h", "ret_4h", "ret_24h", "ret_168h"]
        )
        prob_up = float(model.predict_proba(feat_df)[0][1])
        pred_dir = 1 if prob_up > 0.5 else 0

        # Implied point forecast return from probability deviation
        implied_ret = (prob_up - 0.5) * 0.02 * math.sqrt(horizon_hours)
        pred_price = context.current_price * math.exp(implied_ret)

        return ModelForecast(
            model_id=f"directional-gbm-{horizon_hours}h-v1",
            model_version=self.version,
            horizon_hours=horizon_hours,
            issue_epoch=context.origin_epoch,
            issue_timestamp_utc=context.origin_timestamp_utc,
            point_forecast_price=round(pred_price, 2),
            point_forecast_return=round(implied_ret, 6),
            predicted_direction=pred_dir,
            prob_up=round(prob_up, 4),
            quantiles={
                "p10": round(context.current_price * (1.0 - 0.01 * math.sqrt(horizon_hours)), 2),
                "p50": round(pred_price, 2),
                "p90": round(context.current_price * (1.0 + 0.01 * math.sqrt(horizon_hours)), 2)
            }
        )


class RandomWalkPersistenceAdapter(ForecastModelInterface):
    """
    Standard martingale baseline: predicts zero expected forward return E[r]=0
    and future price equal to current price.
    """

    @property
    def model_id(self) -> str:
        return "random-walk-persistence-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_horizons(self) -> List[int]:
        return [1, 4, 24, 72, 168]

    def predict(self, context: ModelInputContext, horizon_hours: int) -> ModelForecast:
        p_t = context.current_price
        return ModelForecast(
            model_id=self.model_id,
            model_version=self.version,
            horizon_hours=horizon_hours,
            issue_epoch=context.origin_epoch,
            issue_timestamp_utc=context.origin_timestamp_utc,
            point_forecast_price=round(p_t, 2),
            point_forecast_return=0.0,
            predicted_direction=0,  # Flat / default
            prob_up=0.50,
            quantiles={
                "p10": round(p_t * (1.0 - 0.015 * math.sqrt(horizon_hours)), 2),
                "p50": round(p_t, 2),
                "p90": round(p_t * (1.0 + 0.015 * math.sqrt(horizon_hours)), 2)
            }
        )


class RollingEmpiricalQuantileAdapter(ForecastModelInterface):
    """
    Computes empirical quantiles from rolling causal 168-hour return history.
    """

    def __init__(self, window_bars: int = 168):
        self.window_bars = window_bars

    @property
    def model_id(self) -> str:
        return f"empirical-quantile-{self.window_bars}h-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_horizons(self) -> List[int]:
        return [1, 4, 24]

    def predict(self, context: ModelInputContext, horizon_hours: int) -> ModelForecast:
        closes = context.historical_closes
        if len(closes) < self.window_bars + horizon_hours:
            raise ValueError(f"Need at least {self.window_bars + horizon_hours} bars for empirical quantiles")

        # Prior window_bars historical returns at horizon_hours stride
        rets = [
            math.log(closes[-(k + 1)] / closes[-(k + 1 + horizon_hours)])
            for k in range(self.window_bars)
        ]
        q10, q50, q90 = np.percentile(rets, [10, 50, 90])
        p_t = context.current_price

        pred_price = p_t * math.exp(q50)
        pred_dir = 1 if q50 > 0 else 0

        return ModelForecast(
            model_id=self.model_id,
            model_version=self.version,
            horizon_hours=horizon_hours,
            issue_epoch=context.origin_epoch,
            issue_timestamp_utc=context.origin_timestamp_utc,
            point_forecast_price=round(pred_price, 2),
            point_forecast_return=round(float(q50), 6),
            predicted_direction=pred_dir,
            prob_up=round(float(np.mean(np.array(rets) > 0)), 4),
            quantiles={
                "p10": round(p_t * math.exp(q10), 2),
                "p50": round(pred_price, 2),
                "p90": round(p_t * math.exp(q90), 2)
            }
        )
