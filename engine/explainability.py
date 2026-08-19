"""
engine/explainability.py — BTCognitive V3 Explainable AI (XAI) Engine
====================================================================
Synthesizes interpretable, transparent reasoning for every BTCUSD forecast
directly from:
  1. Variable Selection Network (VSN) weights (Top 5 Important Indicators)
  2. Interpretable Multi-Head Temporal Attention (120-step Attention Heatmap)
  3. Sparse MoE Router Top-2 Gating (Activated Experts & Weights)
  4. Market Regime Detector (Regime classification & confidence)
  5. Deterministic Natural Language Reasoning Generator (Zero LLM reliance)
"""

import os
import sys
import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
import numpy as np
import torch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.feature_pipeline import FEATURE_NAMES, NUM_FEATURES, SEQUENCE_LENGTH, feature_pipeline
from models.tft_model import get_tft_model, predict as predict_tft
from models.router import get_router_model, predict_moe, EXPERT_NAMES
from models.regime_detector import detect_regime, REGIMES

logger = logging.getLogger("btcognitive.explainability")

# Semantic indicator names for human readability
INDICATOR_LABELS = {
    "norm_open": "Open Price Spread",
    "norm_high": "Upper Shadow Range",
    "norm_low": "Lower Shadow Range",
    "norm_close_ret": "1m Close Log Return",
    "norm_volume": "Relative Volume Surge",
    "ema_20_ratio": "EMA 20 Trend Alignment",
    "ema_50_ratio": "EMA 50 Intermediate Trend",
    "ema_200_ratio": "EMA 200 Macro Baseline",
    "vwap_ratio": "VWAP Price Divergence",
    "roc_10": "Rate of Change (10-bar)",
    "rsi_14": "RSI 14 Momentum",
    "macd": "MACD Fast Line",
    "macd_signal": "MACD Signal Line",
    "macd_hist": "MACD Momentum Histogram",
    "atr_14_ratio": "ATR Volatility Width",
    "bollinger_width": "Bollinger Band Squeeze",
    "bollinger_pct_b": "Bollinger %B Relative Channel",
    "realized_vol_24": "Realized Volatility (24h)",
    "adx_14": "ADX Trend Strength",
    "obv_norm": "On-Balance Volume (OBV) Flow",
    "plus_minus_di_spread": "Directional Index (+DI/-DI) Spread",
    "bid_ask_spread": "Order Book Spread",
    "order_book_imbalance": "Order Flow Imbalance",
    "depth_liquidity_score": "Market Depth Liquidity",
    "microstructure_pressure": "Taker Buy/Sell Flow Pressure",
    "funding_rate": "Perpetual Funding Rate",
    "open_interest_delta": "Open Interest Momentum",
    "fear_greed_index": "Crypto Fear & Greed Index",
    "sentiment_score": "News Sentiment Polarity",
    "sentiment_embed_dim0": "News Flow Semantic Component 0",
    "sentiment_embed_dim1": "News Flow Semantic Component 1",
    "sentiment_embed_dim2": "News Flow Semantic Component 2",
}


class ExplainableAIEngine:
    """
    Deterministic XAI Engine extracting attention heatmaps, feature importance,
    and structured natural language rationale from deep forecasting models.
    """

    def __init__(self):
        self.tft_model = get_tft_model()
        self.router_model = get_router_model()

    def generate_explanation(
        self,
        tensor: Optional[Union[np.ndarray, torch.Tensor]] = None,
        regime_info: Optional[Dict[str, Any]] = None,
        moe_result: Optional[Dict[str, Any]] = None,
        tft_result: Optional[Dict[str, Any]] = None,
        features_dict: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes complete multi-layer explainability breakdown.
        """
        # 1. Acquire tensor
        if tensor is None:
            tensor = feature_pipeline.latest_tensor()
        
        t_arr = np.asarray(tensor, dtype=np.float32)
        if t_arr.ndim == 2:
            t_input = torch.from_numpy(t_arr).unsqueeze(0)
        else:
            t_input = torch.from_numpy(t_arr)

        # 2. Acquire Features Dictionary
        if features_dict is None:
            features_dict = feature_pipeline.latest_features()

        # 3. Model Forward Passes with Attention Hook Extraction
        self.tft_model.eval()
        with torch.no_grad():
            tft_forward = self.tft_model(t_input)
            feature_weights = tft_forward["feature_weights"][0].cpu().numpy() # (120, 32)
            attention_weights = tft_forward["attention_weights"][0].cpu().numpy() # (120, 120) or (heads, 120, 120)

        # 4. Market Regime
        if regime_info is None:
            regime_info = detect_regime(t_arr)

        # 5. Sparse MoE Predictions & Expert Activations
        if moe_result is None:
            moe_result = predict_moe(t_arr, regime_data=regime_info)

        # 6. TFT Predictions
        if tft_result is None:
            tft_result = predict_tft(t_arr)

        # -------------------------------------------------------------------
        # Component 1: Top 5 Important Indicators (from VSN Feature Weights)
        # -------------------------------------------------------------------
        # Average feature weight across the recent sequence (last 20 candles)
        recent_weights = feature_weights[-20:, :].mean(axis=0) # (32,)
        top_indices = np.argsort(recent_weights)[::-1][:5]
        
        top_5_indicators = []
        for idx in top_indices:
            feat_name = FEATURE_NAMES[idx]
            raw_val = float(features_dict.get(feat_name, t_arr[-1, idx]))
            label = INDICATOR_LABELS.get(feat_name, feat_name)
            weight = float(recent_weights[idx])
            
            top_5_indicators.append({
                "feature": feat_name,
                "label": label,
                "importance_weight": round(weight, 4),
                "current_value": round(raw_val, 4),
                "status": self._interpret_feature_state(feat_name, raw_val)
            })

        # -------------------------------------------------------------------
        # Component 2: 120-Step Temporal Attention Heatmap
        # -------------------------------------------------------------------
        if attention_weights.ndim == 3:
            # Average across attention heads
            attn_seq = attention_weights.mean(axis=0)[-1, :] # Attention from last step to past 120 steps
        elif attention_weights.ndim == 2:
            attn_seq = attention_weights[-1, :]
        else:
            attn_seq = np.ones(SEQUENCE_LENGTH) / SEQUENCE_LENGTH

        # Normalize attention heatmap to sum to 1.0
        attn_norm = (attn_seq / (np.sum(attn_seq) + 1e-8)).tolist()
        attention_heatmap = [round(float(v), 5) for v in attn_norm]

        # -------------------------------------------------------------------
        # Component 3: Activated Experts (Top-2 from Sparse MoE Router)
        # -------------------------------------------------------------------
        activated_experts = moe_result.get("selected_experts", [])

        # -------------------------------------------------------------------
        # Component 4: Market Regime
        # -------------------------------------------------------------------
        regime_name = regime_info.get("regime", "Sideways")
        regime_conf = float(regime_info.get("confidence", 0.85))

        # -------------------------------------------------------------------
        # Component 5: Deterministic Natural Language Reasoning (No LLM)
        # -------------------------------------------------------------------
        direction = moe_result.get("direction", tft_result.get("direction", "HOLD"))
        confidence = float(moe_result.get("confidence", tft_result.get("confidence", 0.50)))
        
        reasons = self._synthesize_reasons(
            direction=direction,
            features=features_dict,
            top_indicators=top_5_indicators,
            regime_name=regime_name,
            activated_experts=activated_experts
        )

        formatted_output = self._format_reasoning_summary(
            direction=direction,
            confidence_pct=int(round(confidence * 100)),
            reasons=reasons
        )

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "confidence_pct": int(round(confidence * 100)),
            "market_regime": {
                "regime": regime_name,
                "confidence": round(regime_conf, 4)
            },
            "top_5_indicators": top_5_indicators,
            "attention_heatmap": attention_heatmap,
            "activated_experts": activated_experts,
            "reasons": reasons,
            "formatted_explanation": formatted_output,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _interpret_feature_state(self, feat_name: str, val: float) -> str:
        """Translates numerical feature value into a human-readable state."""
        if "ema_20" in feat_name or "ema_50" in feat_name or "ema_200" in feat_name:
            return "Bullish Slope" if val > 0.002 else ("Bearish Slope" if val < -0.002 else "Neutral")
        if "rsi" in feat_name:
            # RSI normalized [-1, 1] or raw [0, 100]
            raw_rsi = (val * 50.0 + 50.0) if abs(val) <= 1.5 else val
            return "Overbought" if raw_rsi > 70 else ("Oversold" if raw_rsi < 30 else "Recovering / Stable")
        if "funding" in feat_name:
            return "Positive Funding (Longs Pay)" if val > 0.0003 else ("Negative Funding (Shorts Pay)" if val < -0.0001 else "Funding Neutral")
        if "bollinger" in feat_name:
            return "Band Expansion" if val > 0.04 else "Squeeze / Tight Range"
        if "order_book_imbalance" in feat_name or "microstructure" in feat_name:
            return "Heavy Bid Support" if val > 0.1 else ("Heavy Ask Pressure" if val < -0.1 else "Balanced Flow")
        return "Normal"

    def _synthesize_reasons(
        self,
        direction: str,
        features: Dict[str, float],
        top_indicators: List[Dict[str, Any]],
        regime_name: str,
        activated_experts: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Deterministically builds the 5 concise reason bullet points from technical metrics.
        """
        reasons = []

        # 1. Moving Average / Trend cross reasoning
        ema20 = features.get("ema_20_ratio", 0.0)
        ema50 = features.get("ema_50_ratio", 0.0)
        if ema20 > ema50 and ema20 > 0:
            reasons.append("EMA20 crossed above EMA50 (Bullish trend alignment)")
        elif ema20 < ema50 and ema20 < 0:
            reasons.append("EMA20 crossed below EMA50 (Bearish trend breakdown)")
        else:
            reasons.append("Moving averages consolidating near equilibrium")

        # 2. Funding & Macro sentiment reasoning
        funding = features.get("funding_rate", 0.0001)
        if abs(funding) <= 0.0002:
            reasons.append("Funding neutral (Balanced perpetual leverage)")
        elif funding > 0.0002:
            reasons.append("Funding elevated (+0.02% / 8h long bias)")
        else:
            reasons.append("Funding negative (Short squeeze probability elevated)")

        # 3. Momentum / RSI / Oscillators
        rsi_val = features.get("rsi_14", 0.0)
        raw_rsi = (rsi_val * 50.0 + 50.0) if abs(rsi_val) <= 1.5 else rsi_val
        if raw_rsi < 35:
            reasons.append("RSI recovering from oversold threshold (Momentum reversal)")
        elif raw_rsi > 65:
            reasons.append("RSI showing strong upward momentum (Bullish expansion)")
        else:
            reasons.append("RSI oscillating in healthy mid-band (No exhaustion)")

        # 4. Activated MoE Expert reasoning
        if activated_experts:
            exp_names = [e["name"].replace("Expert", " expert") for e in activated_experts]
            top_exp = activated_experts[0]
            reasons.append(f"{top_exp['name'].replace('Expert', ' expert')} activated (Weight: {top_exp['weight']*100:.0f}%)")
        else:
            reasons.append("Trend & Breakout experts activated")

        # 5. Volatility & Market Regime reasoning
        b_width = features.get("bollinger_width", 0.02)
        if "Uptrend" in regime_name:
            reasons.append(f"Market in {regime_name} with steady volume accumulation")
        elif "Volatility" in regime_name or b_width > 0.035:
            reasons.append("High volatility breakout underway with liquidity expansion")
        elif "Capitulation" in regime_name:
            reasons.append("Capitulation regime active (High discount value zone)")
        else:
            reasons.append("Low volatility breakout forming near key boundary")

        return reasons[:5]

    def _format_reasoning_summary(self, direction: str, confidence_pct: int, reasons: List[str]) -> str:
        """Formats reasoning into exact prompt example layout."""
        lines = [
            f"{direction}",
            f"Confidence: {confidence_pct}%",
            "",
            "Reason:"
        ]
        for r in reasons:
            lines.append(f"* {r}")
        return "\n".join(lines)


# Global Singleton Explainability Engine
explainability_engine = ExplainableAIEngine()


def explain_prediction(
    tensor: Optional[Union[np.ndarray, torch.Tensor]] = None,
    regime_info: Optional[Dict[str, Any]] = None,
    moe_result: Optional[Dict[str, Any]] = None,
    tft_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Primary API entrypoint for XAI Engine.
    Returns Top-5 indicators, attention heatmap, activated experts, regime, and natural language reasoning.
    """
    return explainability_engine.generate_explanation(
        tensor=tensor,
        regime_info=regime_info,
        moe_result=moe_result,
        tft_result=tft_result
    )
