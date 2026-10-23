"""
engine/cross_venue_divergence.py — Cross-Exchange Spot-Price Divergence & Dislocation Engine
=============================================================================================
Computes causal, quote-normalized pairwise price divergence across approved spot exchanges:
1. Coinbase Spot BTC-USD (USD Fiat, Primary Reference)
2. Kraken Spot BTC-USD (USD Fiat, Secondary Reference)
3. Binance Spot BTC-USDT (USDT Stablecoin, Cross-Currency Basis)

GOVERNANCE CONTRACT:
- Quote Normalization: Fiat USD pairs (Coinbase vs Kraken) are directly comparable.
  USDT pairs (Coinbase vs Binance) are tagged with quote_currency='USDT' and reflect
  Tether basis / stablecoin peg risk, not executable pure fiat arbitrage.
- Feature Status: CROSS_VENUE_PRICE_DIVERGENCE (Research Only)
- Non-Execution: Zero order placement, trade routing, or arbitrage execution.
"""

from typing import Dict, Any, List, Optional
import math
import datetime
import json
from pathlib import Path


class CrossVenueDivergenceEngine:
    """Manages cross-venue price tracking and dislocation metrics."""

    FEATURE_STATUS = "CROSS_VENUE_PRICE_DIVERGENCE_RESEARCH_ONLY"

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path(__file__).resolve().parent.parent / "data" / "research")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.storage_dir / "cross_venue_divergence_ledger.jsonl"

    def compute_pairwise_divergence(
        self,
        ref_price: float,
        cmp_price: float,
        ref_venue: str,
        cmp_venue: str,
        ref_currency: str = "USD",
        cmp_currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Compute divergence in log basis points: ln(P_ref / P_cmp) * 10000.
        """
        if ref_price <= 0 or cmp_price <= 0:
            return {
                "status": "INVALID_PRICE_NONPOSITIVE",
                "divergence_log_bps": 0.0,
                "is_quote_normalized": False
            }

        div_bps = math.log(ref_price / cmp_price) * 10000.0
        is_same_quote = (ref_currency.upper() == cmp_currency.upper())

        return {
            "pair": f"{ref_venue}_{ref_currency}_vs_{cmp_venue}_{cmp_currency}",
            "ref_venue": ref_venue,
            "ref_instrument": f"BTC-{ref_currency}",
            "ref_price": round(ref_price, 2),
            "ref_quote_currency": ref_currency,
            "cmp_venue": cmp_venue,
            "cmp_instrument": f"BTC-{cmp_currency}",
            "cmp_price": round(cmp_price, 2),
            "cmp_quote_currency": cmp_currency,
            "divergence_log_bps": round(div_bps, 2),
            "is_quote_normalized": is_same_quote,
            "currency_risk_flag": "NONE" if is_same_quote else "STABLECOIN_PEG_BASIS",
            "feature_status": self.FEATURE_STATUS,
            "execution_authorization": "DISABLED"
        }

    def record_snapshot(
        self,
        timestamp_utc: str,
        coinbase_usd: float,
        kraken_usd: float,
        binance_usdt: float,
        receipt_time_utc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute and persist snapshot of pairwise dislocations.
        """
        receipt_time = receipt_time_utc or datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Pure USD fiat divergence: Coinbase vs Kraken
        usd_fiat_div = self.compute_pairwise_divergence(
            coinbase_usd, kraken_usd,
            ref_venue="COINBASE", cmp_venue="KRAKEN",
            ref_currency="USD", cmp_currency="USD"
        )

        # 2. Cross-currency basis: Coinbase USD vs Binance USDT
        usdt_basis_div = self.compute_pairwise_divergence(
            coinbase_usd, binance_usdt,
            ref_venue="COINBASE", cmp_venue="BINANCE",
            ref_currency="USD", cmp_currency="USDT"
        )

        record = {
            "timestamp_utc": timestamp_utc,
            "receipt_time_utc": receipt_time,
            "coinbase_usd": coinbase_usd,
            "kraken_usd": kraken_usd,
            "binance_usdt": binance_usdt,
            "fiat_spread_cb_kr_bps": usd_fiat_div["divergence_log_bps"],
            "tether_basis_cb_bn_bps": usdt_basis_div["divergence_log_bps"],
            "usd_fiat_metrics": usd_fiat_div,
            "usdt_basis_metrics": usdt_basis_div,
            "feature_status": self.FEATURE_STATUS
        }

        # Append-only write to ledger
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return record


cross_venue_engine = CrossVenueDivergenceEngine()
