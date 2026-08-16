"""
High-Profit Opportunity Detection Engine for BTCognitive.

Evaluates real-time predictions, market microstructure, trend momentum confluence,
and calibrated probabilities to detect high-profit / high-conviction trading opportunities.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class OpportunityDetector:
    """
    Analyzes live market predictions and indicators to identify high-profit setups.
    """

    def __init__(
        self,
        min_probability_long: float = 0.54,
        max_probability_short: float = 0.46,
        min_expected_profit_pct: float = 1.5,
        min_quality_score: int = 70,
        cooldown_seconds: int = 900  # 15 minutes minimum between same-direction alerts
    ):
        self.min_prob_long = min_probability_long
        self.max_prob_short = max_probability_short
        self.min_expected_profit_pct = min_expected_profit_pct
        self.min_quality_score = min_quality_score
        self.cooldown_seconds = cooldown_seconds
        
        self.last_alert_time: Dict[str, float] = {"LONG": 0.0, "SHORT": 0.0}
        self.alert_history: list = []

    def evaluate_opportunity(
        self,
        prediction: Dict[str, Any],
        regime_data: Optional[Dict[str, Any]] = None,
        quality_data: Optional[Dict[str, Any]] = None,
        candle_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates whether current market state constitutes a high-profit opportunity.
        Returns alert payload dict if threshold is cleared, None otherwise.
        """
        if not prediction:
            return None

        direction = prediction.get("direction", "SKIP")
        if direction not in ["LONG", "SHORT"]:
            return None

        prob = float(prediction.get("probability", 0.50))
        entry_price = float(prediction.get("entry_price") or prediction.get("btc_price") or 0.0)
        tp = float(prediction.get("tp", 0.0))
        sl = float(prediction.get("sl", 0.0))
        expected_ret = float(prediction.get("expected_return", 0.0))
        expected_profit_pct = abs(expected_ret) * 100.0

        if entry_price <= 0 or tp <= 0 or sl <= 0:
            return None

        # 1. Profit Target Percentage & Risk-Reward calculation
        if direction == "LONG":
            profit_pct = ((tp - entry_price) / entry_price) * 100.0
            risk_pct = ((entry_price - sl) / entry_price) * 100.0
        else:
            profit_pct = ((entry_price - tp) / entry_price) * 100.0
            risk_pct = ((sl - entry_price) / entry_price) * 100.0

        risk_reward_ratio = round(profit_pct / max(0.01, risk_pct), 2)
        effective_profit_pct = max(profit_pct, expected_profit_pct)

        # 2. Quality & Regime Checks
        quality_score = 75
        if quality_data:
            quality_score = int(quality_data.get("score", 75))

        current_regime = "NORMAL"
        event_flags = []
        if regime_data:
            current_regime = regime_data.get("current_regime", "NORMAL")
            event_flags = regime_data.get("event_flags", [])

        # Avoid counter-trend traps during liquidation cascades
        has_cascade = "LIQUIDATION_CASCADE" in event_flags

        # 3. Opportunity Scoring Algorithm (0 to 100)
        # Factor A: Probability Conviction (0-35 pts)
        prob_edge = abs(prob - 0.50) * 2.0  # 0.0 to 1.0
        prob_score = min(35, int(prob_edge * 70))

        # Factor B: Profit Potential (0-35 pts)
        profit_score = min(35, int(effective_profit_pct * 12))

        # Factor C: Risk-to-Reward Ratio (0-15 pts)
        rr_score = min(15, int(risk_reward_ratio * 5))

        # Factor D: Market Quality & Regime (0-15 pts)
        q_score = min(15, int((quality_score / 100.0) * 15))

        total_opportunity_score = prob_score + profit_score + rr_score + q_score

        # 4. Qualification Criteria for High Profit Alert
        is_conviction_prob = (direction == "LONG" and prob >= self.min_prob_long) or \
                             (direction == "SHORT" and prob <= self.max_prob_short)
        is_high_profit = effective_profit_pct >= self.min_expected_profit_pct
        is_favorable_rr = risk_reward_ratio >= 1.5
        is_good_quality = quality_score >= self.min_quality_score

        # Must clear core thresholds or achieve exceptional composite score (>= 75)
        if not (is_conviction_prob and is_high_profit and is_favorable_rr and is_good_quality):
            if total_opportunity_score < 75:
                return None

        # 5. Cooldown Throttle
        now = time.time()
        if now - self.last_alert_time.get(direction, 0.0) < self.cooldown_seconds:
            return None

        # Tier Categorization
        if total_opportunity_score >= 85 and effective_profit_pct >= 2.5:
            tier = "ULTRA_HIGH_PROFIT"
            tier_title = "💎 ULTRA HIGH PROFIT OPPORTUNITY"
            badge = "ULTRA SETUP"
        elif total_opportunity_score >= 75:
            tier = "HIGH_CONVICTION"
            tier_title = "🔥 HIGH CONVICTION SETUP"
            badge = "HIGH EDGE"
        else:
            tier = "PRIME_SETUP"
            tier_title = "⚡ PRIME TRADING OPPORTUNITY"
            badge = "OPPORTUNITY"

        alert_payload = {
            "id": f"alert_{int(now)}_{direction.lower()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tier": tier,
            "tier_title": tier_title,
            "badge": badge,
            "opportunity_score": total_opportunity_score,
            "direction": direction,
            "probability": round(prob, 4),
            "probability_pct": round(prob * 100, 1),
            "entry_price": round(entry_price, 2),
            "target_profit_price": round(tp, 2),
            "stop_loss_price": round(sl, 2),
            "target_profit_pct": round(profit_pct, 2),
            "risk_pct": round(risk_pct, 2),
            "risk_reward_ratio": f"{risk_reward_ratio}:1",
            "expected_gain_usd_per_btc": round(abs(tp - entry_price), 2),
            "regime": current_regime,
            "quality_score": quality_score,
            "rationale": f"Strong {direction} edge detected with {effective_profit_pct:.1f}% profit target and {risk_reward_ratio}:1 Risk/Reward ratio in {current_regime} market.",
            "sound_alert": True
        }

        self.last_alert_time[direction] = now
        self.alert_history.append(alert_payload)
        if len(self.alert_history) > 50:
            self.alert_history.pop(0)

        return alert_payload


opportunity_detector = OpportunityDetector()
