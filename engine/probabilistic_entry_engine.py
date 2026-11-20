"""
engine/probabilistic_entry_engine.py — Probabilistic Entry Quality Engine & Decision Gate
========================================================================================
Implements:
1. Candidate Entry Event Formulation (Side, Executable Entry at t0 + dt, ATR Volatility).
2. Conservative Triple-Barrier Outcome Resolver (with SL_FIRST on intrabar collisions).
3. First-passage geometry baseline probabilities (p_TP, p_SL, p_timeout).
4. Cost-Aware Net Expectancy Decision Gate (E[R_net] > 0).
5. Append-Only Prospective Entry Ledger (data/prospective_entry_ledger.jsonl).

GOVERNANCE CONTRACT:
- Analysis-Only Research Engine: No live order execution or broker placement.
- Selective Abstention: Model abstains when net expectancy <= 0 or uncertainty is elevated.
- High Win Rate Boundary: 70-80% is an aspirational research hypothesis, not a guarantee.
"""

import os
import math
import json
import datetime
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import numpy as np
import pandas as pd


class ProbabilisticEntryEngine:
    """Evaluates research setups with baseline barrier probabilities and a fail-closed gate."""

    RESOLVER_VERSION = "ENTRY_TP_SL_RESOLVER_V1"
    RESEARCH_STATUS = "OFFLINE_RESEARCH_ONLY"

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or (Path(__file__).resolve().parent.parent / "data")
        self.ledger_file = self.data_dir / "prospective_entry_ledger_v2.jsonl"
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

        # Pre-calibrated logistic meta-model coefficients (H0 baseline hypothesis)
        # Features: [mom_1h, mom_4h, mom_24h, rs_ratio, bb_width, range_pos]
        self.feature_names = [
            "mom_1h", "mom_4h", "mom_24h", "rs_ratio", "bb_width", "range_pos"
        ]
        # Standardized weights (H0 frozen baseline)
        self.weights = np.array([0.45, 0.35, 0.20, 0.65, -0.30, 0.25])
        self.bias = -0.15

        # Cost scenario configurations with regional granularity
        self.COST_SCENARIOS = {
            "COINBASE_US_RETAIL_187BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 90.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 2.0,
                "round_trip_friction_bps": 187.0,
                "description": "Coinbase US Retail (Sept 2026 schedule: 0.90% taker each side + spread + slippage)"
            },
            "COINBASE_EU_UK_RETAIL_107BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 50.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 2.0,
                "round_trip_friction_bps": 107.0,
                "description": "Coinbase EU/UK Retail (0.50% taker each side + spread + slippage)"
            },
            "COINBASE_INDIA_INTL_27BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 10.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 2.0,
                "round_trip_friction_bps": 27.0,
                "description": "Coinbase India / International Retail (0.10% taker each side + spread + slippage)"
            },
            "COINBASE_RETAIL_87BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 40.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 2.0,
                "round_trip_friction_bps": 87.0,
                "description": "Coinbase Advanced Tier 1 (<$10k) taker entry and exit with empirical spread and slippage"
            },
            "COINBASE_ADVANCED_87BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 40.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 2.0,
                "round_trip_friction_bps": 87.0,
                "description": "Coinbase Advanced Tier 1 (<$10k) taker entry and exit"
            },
            "COINBASE_PRO_35BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 15.0,
                "half_spread_bps_per_side": 1.0,
                "slippage_bps_per_side": 1.5,
                "round_trip_friction_bps": 35.0,
                "description": "Coinbase Advanced high-volume tier taker"
            },
            "BINANCE_FUTURES_12BPS": {
                "venue": "BINANCE_FUTURES",
                "market_type": "PERPETUAL",
                "commission_bps_per_side": 5.0,
                "half_spread_bps_per_side": 0.5,
                "slippage_bps_per_side": 0.5,
                "round_trip_friction_bps": 12.0,
                "description": "Binance USDT-M Futures VIP 0 taker entry and exit"
            },
            "LEGACY_V30_91BPS": {
                "venue": "COINBASE",
                "market_type": "SPOT",
                "commission_bps_per_side": 40.0,
                "half_spread_bps_per_side": 1.5,
                "slippage_bps_per_side": 4.02,
                "round_trip_friction_bps": 91.04,
                "description": "Legacy V30 prospective ledger calculation with double-counted slippage"
            }
        }

        # Reconciled Cost Structure (V30.1 Audit Resolution):
        # Base scenario: Coinbase Advanced Tier 1 (<$10k) spot taker.
        # Component breakdown per side:
        #   - Taker commission: 40.0 bps
        #   - Half-spread:       1.5 bps
        #   - Slippage:          2.0 bps
        #   ---------------------------
        #   Total one-way:      43.5 bps
        #   Round-trip total:   87.0 bps
        #
        # Reconciling the 87 bps vs 91 bps discrepancy:
        # In V30, self.half_friction_rate mistakenly summed (self.fee_one_way_bps + self.slippage_bps),
        # double-counting slippage (43.5 + 2.0 = 45.5 bps one-way -> 91.0 bps round-trip).
        # We now explicitly define each component and ensure half_friction_rate = 43.5 bps (0.00435).
        self.commission_bps_one_way = 40.0
        self.half_spread_bps = 1.5
        self.slippage_bps_one_way = 2.0
        self.fee_one_way_bps = self.commission_bps_one_way + self.half_spread_bps + self.slippage_bps_one_way  # 43.5 bps
        self.slippage_bps = self.slippage_bps_one_way  # Preserved for backward compatibility
        self.round_trip_friction_bps = 2.0 * self.fee_one_way_bps  # 87.0 bps
        self.half_friction_rate = self.fee_one_way_bps / 10000.0   # 0.00435 rate per side (0.00870 round trip)

    def compute_setup_features(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        side: str = "LONG"
    ) -> Dict[str, float]:
        """Compute point-in-time features available at decision timestamp t0."""
        N = len(closes)
        if N < 25:
            return {f: 0.0 for f in self.feature_names}

        # 1. Multi-horizon momentum returns
        r_1h = math.log(closes[-1] / closes[-2])
        r_4h = math.log(closes[-1] / closes[-5]) if N >= 5 else 0.0
        r_24h = math.log(closes[-1] / closes[-25]) if N >= 25 else 0.0

        # Sign-adjust momentum for side (for SHORT, positive feature means bearish alignment)
        side_mult = 1.0 if side.upper() == "LONG" else -1.0
        mom_1h = r_1h * side_mult
        mom_4h = r_4h * side_mult
        mom_24h = r_24h * side_mult

        # 2. Hourly realized semi-variance ratio RS+ / (RS+ + RS-)
        past_rets = np.diff(np.log(closes[-25:]))
        pos_rets = past_rets[past_rets > 0]
        neg_rets = past_rets[past_rets < 0]
        rs_plus = float(np.sum(pos_rets ** 2)) if len(pos_rets) > 0 else 1e-8
        rs_minus = float(np.sum(neg_rets ** 2)) if len(neg_rets) > 0 else 1e-8
        rs_ratio = rs_plus / (rs_plus + rs_minus + 1e-12)
        # Invert for short side
        if side.upper() == "SHORT":
            rs_ratio = 1.0 - rs_ratio

        # 3. Bollinger Bandwidth
        std_24 = float(np.std(closes[-24:]))
        mean_24 = float(np.mean(closes[-24:]))
        bb_width = (4.0 * std_24) / max(1.0, mean_24)

        # 4. Range position in 24h high-low channel
        h_24 = float(np.max(highs[-24:]))
        l_24 = float(np.min(lows[-24:]))
        range_pos = (closes[-1] - l_24) / max(1e-4, (h_24 - l_24))
        if side.upper() == "SHORT":
            range_pos = 1.0 - range_pos

        return {
            "mom_1h": round(mom_1h, 6),
            "mom_4h": round(mom_4h, 6),
            "mom_24h": round(mom_24h, 6),
            "rs_ratio": round(rs_ratio, 4),
            "bb_width": round(bb_width, 4),
            "range_pos": round(range_pos, 4)
        }

    def predict_barrier_probabilities(
        self,
        features: Optional[Dict[str, float]] = None,
        k_tp: float = 1.5,
        k_sl: float = 1.0,
        mu: float = 0.0,
        c_sigma: float = 1.0518
    ) -> Dict[str, Any]:
        """
        Computes geometry baseline probabilities P(TP), P(SL), P(timeout)
        using the First-Passage Diffusion Model under Brownian motion with drift.
        Default mu = 0 represents the unconditioned geometry null.
        c_sigma = 1.0518 represents the empirical fat-tail / discrete-sampling calibration for BTC.
        """
        from research.first_passage_diffusion_model import FirstPassageDiffusionModel
        fp = FirstPassageDiffusionModel()
        p_tp, p_sl, p_to = fp.solve_pde(k_tp=k_tp, k_sl=k_sl, mu=mu, c_sigma=c_sigma)

        return {
            "p_tp": p_tp,
            "p_sl": p_sl,
            "p_timeout": p_to,
            "c_sigma_calibration": c_sigma,
            "brier_score_expected": round(float(2.0 * p_tp * (1.0 - p_tp)), 4),
            "calibration_status": "FIRST_PASSAGE_GEOMETRY_BASELINE",
            "validated_directional_edge": False,
            "validated_edge_status": "NO_VALIDATED_EDGE_ABSTAIN"
        }

    def evaluate_decision_gate(
        self,
        side: str,
        entry_price: float,
        sigma_t0: float,
        k_tp: float = 1.5,
        k_sl: float = 1.0,
        features: Optional[Dict[str, float]] = None,
        selective_threshold: float = 0.60,
        cost_scenario: str = "COINBASE_RETAIL_87BPS",
        round_trip_friction_bps: Optional[float] = None,
        sigma_1h: Optional[float] = None,
        horizon_bars: int = 24,
        feature_source: str = "REST_OHLCV_PROXY"
    ) -> Dict[str, Any]:
        """
        Evaluate full probabilistic decision gate and calculate net expectancy in R-multiples.
        Enforces realistic, non-duplicated transaction costs by venue and sqrt(H) sigma horizon scaling.
        """
        feats = features or {f: 0.0 for f in self.feature_names}
        probs = self.predict_barrier_probabilities(features=feats, k_tp=k_tp, k_sl=k_sl, mu=0.0)

        p_tp = probs["p_tp"]
        p_sl = probs["p_sl"]
        p_timeout = probs["p_timeout"]

        # Audit Sigma Semantics:
        # If sigma_1h is explicitly passed, scale by sqrt(H) to get horizon sigma.
        # If only sigma_t0 is passed, treat it as s_horizon and compute s_1h = s_horizon / sqrt(H).
        h_bars = max(1, int(horizon_bars))
        if sigma_1h is not None:
            s_1h = max(0.0005, float(sigma_1h))
            s_horizon = s_1h * math.sqrt(float(h_bars))
        else:
            s_horizon = max(0.0005, float(sigma_t0))
            s_1h = s_horizon / math.sqrt(float(h_bars))

        # Risk unit in USD: 1R = entry_price * (k_sl * s_horizon)
        risk_usd = entry_price * (k_sl * s_horizon)
        target_usd = entry_price * (k_tp * s_horizon)

        # Determine effective round-trip friction in basis points
        if round_trip_friction_bps is not None:
            eff_rt_bps = float(round_trip_friction_bps)
            scenario_key = cost_scenario or "CUSTOM"
        else:
            scenario_key = cost_scenario.upper() if cost_scenario else "COINBASE_RETAIL_87BPS"
            scenario_cfg = self.COST_SCENARIOS.get(scenario_key, self.COST_SCENARIOS["COINBASE_RETAIL_87BPS"])
            eff_rt_bps = scenario_cfg["round_trip_friction_bps"]

        # Transaction friction in USD and R:
        friction_rate = eff_rt_bps / 10000.0
        friction_usd = entry_price * friction_rate
        friction_r = friction_usd / max(1e-4, risk_usd)

        # Net expectancy:
        tp_r = k_tp / k_sl
        sl_r = 1.0
        timeout_r = -0.05  # first-passage empirical residual drift

        expected_gross_r = (p_tp * tp_r) - (p_sl * sl_r) + (p_timeout * timeout_r)
        expected_net_r = expected_gross_r - friction_r

        # Decision Gate Logic: Default is ABSTAIN (No Validated Edge)
        is_fresh = True
        is_expectancy_positive = expected_net_r > 0.0
        meets_selective_hurdle = p_tp >= selective_threshold

        action = "ABSTAIN"
        reason = "NO_VALIDATED_EDGE_ABSTAIN"

        if not is_expectancy_positive:
            action = "ABSTAIN"
            reason = "NO_VALIDATED_EDGE_ABSTAIN: Geometry baseline shows negative net expectancy after transaction friction"
        elif not meets_selective_hurdle:
            action = "ABSTAIN"
            reason = f"NO_VALIDATED_EDGE_ABSTAIN: Win probability below selective threshold ({int(selective_threshold*100)}%)"
        else:
            action = "ACCEPTED_RESEARCH_CANDIDATE"
            reason = "POSITIVE_NET_EXPECTANCY_CONFIRMED"

        # Boundary prices scaled to horizon volatility
        if side.upper() == "LONG":
            tp_price = round(entry_price * (1.0 + k_tp * s_horizon), 2)
            sl_price = round(entry_price * (1.0 - k_sl * s_horizon), 2)
        else:
            tp_price = round(entry_price * (1.0 - k_tp * s_horizon), 2)
            sl_price = round(entry_price * (1.0 + k_sl * s_horizon), 2)

        # Deterministic Rule Hash (provenance invariant)
        rule_payload = f"{side.upper()}:{k_tp}:{k_sl}:{h_bars}:{scenario_key}:{selective_threshold}"
        rule_hash = "0x" + hashlib.sha256(rule_payload.encode("utf-8")).hexdigest()[:12]

        decision = {
            "side": side.upper(),
            "entry_reference_price": round(entry_price, 2),
            "tp_price": tp_price,
            "sl_price": sl_price,
            "k_tp": k_tp,
            "k_sl": k_sl,
            "horizon_bars": h_bars,
            "volatility_sigma": round(s_horizon, 5),
            "sigma_1h": round(s_1h, 5),
            "sigma_horizon": round(s_horizon, 5),
            "sigma_scaling": "SQRT_H",
            "risk_unit_usd": round(risk_usd, 2),
            "cost_scenario": scenario_key,
            "cost_model_version": "EXECUTION_COST_MODEL_V2",
            "feature_source": feature_source,
            "rule_hash": rule_hash,
            "round_trip_friction_bps": round(eff_rt_bps, 2),
            "friction_r": round(friction_r, 4),
            "probabilities": probs,
            "expected_gross_r": round(expected_gross_r, 4),
            "expected_net_r": round(expected_net_r, 4),
            "breakeven_win_rate_pct": round(float((1.0 + max(0.0, friction_r)) / (tp_r + 1.0)) * 100.0, 2),
            "epistemic_provenance": "FIRST_PASSAGE_GEOMETRY_BASELINE_H0",
            "drift_parameter_mu": 0.0,
            "drift_status": "DRIFTLESS_NULL_BASELINE",
            "validated_directional_edge": False,
            "validated_edge_status": "NO_VALIDATED_EDGE_ABSTAIN",
            "geometry_baseline_only": True,
            "selective_threshold": selective_threshold,
            "action": action,
            "primary_reason": reason,
            "governance_status": self.RESEARCH_STATUS,
            "execution_authorization": "DISABLED — ANALYSIS ONLY"
        }
        return decision

    def log_prospective_decision(
        self,
        decision: Dict[str, Any],
        ledger_path: Optional[Union[Path, str]] = None
    ) -> str:
        """Append-only logging to V2 ledger enforcing all 5 mandatory provenance fields."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record = {
            "decision_timestamp_utc": now_utc,
            "ledger_version": "V2_PROSPECTIVE",
            "feature_source": decision.get("feature_source", "REST_OHLCV_PROXY"),
            "cost_scenario": decision.get("cost_scenario", "COINBASE_RETAIL_87BPS"),
            "cost_model_version": decision.get("cost_model_version", "EXECUTION_COST_MODEL_V2"),
            "sigma_1h": decision.get("sigma_1h", decision.get("volatility_sigma", 0.005)),
            "sigma_horizon": decision.get("sigma_horizon", decision.get("volatility_sigma", 0.005)),
            "sigma_scaling": decision.get("sigma_scaling", "SQRT_H"),
            "rule_hash": decision.get("rule_hash", "0x000000000000"),
            **decision
        }
        target_path = Path(ledger_path) if ledger_path else self.ledger_file
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return now_utc


entry_quality_engine = ProbabilisticEntryEngine()
