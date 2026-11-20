"""
engine/historical_evidence_loader.py
====================================
BTCognitive V33.4L — Read-Only Historical HTF Evidence Loader & Validator.
Strictly loads and validates the 194-trade retrospective research artifact.

Epistemic & Governance Constraints:
1. Status is strictly RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY.
2. Never satisfies prospective authorization or live execution gates.
3. Completely isolates demo fixtures (N=4 mock attempts) from empirical metrics.
4. Validates artifact bitwise SHA-256, 110/84 partition, and 26.0 bps cost schedule.
5. Preserves separate dataset provenance fingerprints and PARTIALLY_RESOLVED qualification.
"""

import os
import hashlib
import logging
import threading
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger("btcognitive.historical_evidence_loader")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Canonical Relative Artifact Paths
DEFAULT_LEDGER_PATH = os.path.join(
    REPO_ROOT, "research", "reports", "offline_mvp",
    "20261031_330310_v33_03a_htf_validation",
    "v33_3a_194_trade_event_ledger.csv"
)
DEFAULT_EXCLUSION_PATH = os.path.join(
    REPO_ROOT, "research", "reports", "offline_mvp",
    "20261031_330320_v33_03b_htf_closure",
    "v33_3b_excluded_trade_classification.csv"
)

# Canonical Bitwise SHA-256 Hashes
EXPECTED_LEDGER_SHA256 = "0b1e1cd089f32798d6c011acf2900c42e1c94e0b97b3349b356c0b25189d8b00"
EXPECTED_EXCLUSION_SHA256 = "59f89b90706e0d60e9feecea1dc6c09e3aa31265b3de77b834b18d78890eda67"

# Canonical Candle-Window Fingerprints (Price Invariance Hashes)
ORIGINAL_DATASET_FINGERPRINT = "b1900a7f450543c5643e0b713f738931c4361a4fb62f1110f34edc004844be18"  # 41,273 bars
FULL_WINDOW_DATASET_FINGERPRINT = "855f157d1fa28477908759adeb50bb1e26d0bd36a98f898808f83100138909b4"  # 41,397 bars
REPRODUCTION_DATASET_FINGERPRINT = "8936ed31ac2ec339f5add90bed350a1d378df573d15e292ed9a6cea9dbe4e069"  # 42,177 bars
RUNTIME_DATASET_FINGERPRINT = "bbe0fc8c436526456899c4a8aa5abef929e85f3d1970551ec053051d5cf3f70c"  # 42,326 bars


def compute_file_sha256(filepath: str) -> str:
    """Computes bitwise SHA-256 hash of a file on disk."""
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class HistoricalEvidenceLoader:
    """
    Read-only loader and validator for the 194-trade historical research artifact.
    Thread-safe and cached in memory after first validation.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(
        self,
        ledger_path: Optional[str] = None,
        exclusion_path: Optional[str] = None,
        expected_ledger_sha256: Optional[str] = None,
        expected_exclusion_sha256: Optional[str] = None
    ):
        self.ledger_path = ledger_path or DEFAULT_LEDGER_PATH
        self.exclusion_path = exclusion_path or DEFAULT_EXCLUSION_PATH
        self.expected_ledger_sha256 = expected_ledger_sha256 or EXPECTED_LEDGER_SHA256
        self.expected_exclusion_sha256 = expected_exclusion_sha256 or EXPECTED_EXCLUSION_SHA256
        self._cached_evidence: Optional[Dict[str, Any]] = None
        self._cache_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "HistoricalEvidenceLoader":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def validate_and_load(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Validates artifact hashes, counts, partition invariants, cost schedule,
        and ledger arithmetic. Returns a structured historical evidence payload.
        """
        with self._cache_lock:
            if self._cached_evidence is not None and not force_reload:
                return self._cached_evidence

            # 1. Verify file existence
            if not os.path.exists(self.exclusion_path) or not os.path.exists(self.ledger_path):
                self._cached_evidence = {
                    "status": "EVIDENCE_UNAVAILABLE",
                    "error_code": "ARTIFACT_NOT_FOUND",
                    "detail": "Historical evidence CSV artifacts are missing on disk.",
                    "evidence_classification": "UNAVAILABLE",
                    "is_valid": False
                }
                return self._cached_evidence

            # 2. Verify bitwise SHA-256 hashes
            ledger_sha = compute_file_sha256(self.ledger_path)
            exclusion_sha = compute_file_sha256(self.exclusion_path)

            if ledger_sha != self.expected_ledger_sha256 or exclusion_sha != self.expected_exclusion_sha256:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "SHA256_MISMATCH",
                    "detail": f"Artifact hash mismatch. Ledger: {ledger_sha[:16]}... Excl: {exclusion_sha[:16]}...",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 3. Read exclusion dataset
            try:
                df = pd.read_csv(self.exclusion_path)
            except Exception as e:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "PARSE_ERROR",
                    "detail": f"Failed to parse exclusion CSV: {str(e)}",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 4. Verify row count and trade IDs
            if len(df) != 194:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "ROW_COUNT_MISMATCH",
                    "detail": f"Expected exactly 194 trade rows, found {len(df)}.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            trade_ids = set(df["trade_id"])
            if trade_ids != set(range(1, 195)):
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "TRADE_ID_SEQUENCE_ERROR",
                    "detail": "Trade IDs must be strictly unique and contiguous from 1 to 194.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 5. Verify 110/84 partition invariants
            kept_sub = df[df["action_v33_3a"] == "KEEP"]
            excl_sub = df[df["action_v33_3a"] == "EXCLUDE"]
            kept_ids = set(kept_sub["trade_id"])
            excl_ids = set(excl_sub["trade_id"])

            if len(kept_ids) != 110 or len(excl_ids) != 84:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "PARTITION_COUNT_ERROR",
                    "detail": f"Partition mismatch: expected 110 kept / 84 excluded, got {len(kept_ids)} / {len(excl_ids)}.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            if len(kept_ids.intersection(excl_ids)) != 0:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "NON_DISJOINT_PARTITION",
                    "detail": "Retained and excluded subsets overlap.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            if kept_ids.union(excl_ids) != trade_ids:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "NON_EXHAUSTIVE_PARTITION",
                    "detail": "Union of retained and excluded subsets does not cover all 194 trades.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 6. Verify 26.0 bps cost model
            cost_diffs = (df["gross_return_bps"] - 26.0) - df["net_vip0_bps"]
            if (cost_diffs.abs() > 1e-4).any():
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "COST_SCHEDULE_MISMATCH",
                    "detail": "Column net_vip0_bps does not match gross_return_bps - 26.0 bps.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 7. Verify arithmetic expectations
            mean_all = float(df["net_vip0_bps"].mean())
            mean_kept = float(kept_sub["net_vip0_bps"].mean())
            mean_excl = float(excl_sub["net_vip0_bps"].mean())

            if abs(mean_all - 9.5712) > 0.005 or abs(mean_kept - 59.2546) > 0.005 or abs(mean_excl - (-55.4902)) > 0.005:
                self._cached_evidence = {
                    "status": "INTEGRITY_FAILURE",
                    "error_code": "EXPECTANCY_ARITHMETIC_MISMATCH",
                    "detail": f"Ledger expectancy mismatch: all={mean_all:.4f}, kept={mean_kept:.4f}, excl={mean_excl:.4f}.",
                    "evidence_classification": "CORRUPTED_OR_TAMPERED",
                    "is_valid": False
                }
                return self._cached_evidence

            # 8. Calculate regime breakdowns
            regime_breakdowns = []
            for r_name, r_action in [
                ("TRENDING_BULL", "KEEP"),
                ("VOL_COMPRESSION_RANGE", "KEEP"),
                ("TRENDING_BEAR", "KEEP"),
                ("CONSOLIDATION_RANGE", "EXCLUDE"),
                ("TRANSITION_UNSUPPORTED", "EXCLUDE")
            ]:
                r_df = df[df["regime_entry_hyst"] == r_name]
                r_n = len(r_df)
                r_wins = int((r_df["net_vip0_bps"] > 0).sum())
                r_wr = float(r_wins / r_n * 100.0) if r_n > 0 else 0.0
                regime_breakdowns.append({
                    "regime": r_name,
                    "action": r_action,
                    "sample_count": r_n,
                    "winning_trades": r_wins,
                    "win_rate_pct": round(r_wr, 2),
                    "mean_gross_return_bps": round(float(r_df["gross_return_bps"].mean()), 2),
                    "mean_net_vip0_bps": round(float(r_df["net_vip0_bps"].mean()), 2),
                    "total_net_vip0_bps": round(float(r_df["net_vip0_bps"].sum()), 2)
                })

            # 9. Build authoritative evidence payload
            self._cached_evidence = {
                "status": "SUCCESS",
                "is_valid": True,
                "strategy_id": "HTF_RANGE_EXPANSION_BREAKOUT",
                "strategy_name": "High-Timeframe Range Expansion Breakout (4h / 20-bar)",
                "historical_contract_description": (
                    "4-Hour 20-bar Donchian channel breakout on closed candles, entry at next bar open, "
                    "structural stop at opposite 20-bar channel low, 18-bar (72h) maximum holding time exit, "
                    "filtered by 3-bar confirmation hysteresis MarketRegimeClassifier."
                ),
                "evidence_classification": "RETROSPECTIVE_REPRODUCIBLE_NON_CONFIRMATORY",
                "governance_locks": {
                    "is_confirmatory": False,
                    "is_prospective": False,
                    "is_live_authorized": False,
                    "satisfies_prospective_gate": False,
                    "demo_fixtures_excluded": True,
                    "live_trading": "DISABLED"
                },
                "provenance": {
                    "original_dataset_fingerprint": ORIGINAL_DATASET_FINGERPRINT,
                    "full_window_dataset_fingerprint": FULL_WINDOW_DATASET_FINGERPRINT,
                    "reproduction_dataset_fingerprint": REPRODUCTION_DATASET_FINGERPRINT,
                    "runtime_dataset_fingerprint": RUNTIME_DATASET_FINGERPRINT,
                    "original_source_provenance_status": "PARTIALLY_RESOLVED",
                    "qualification_note": (
                        "Original V13 manifest recorded 41,273 bars ending 2026-09-16 UTC, while the full "
                        "194-trade event window requires 41,397 bars ending 2026-09-21 20:00 UTC to include "
                        "the completed exit of Trade 194. Trade 194 was the final trade prior to the late-2026 freeze."
                    ),
                    "ledger_file_sha256": ledger_sha,
                    "exclusion_file_sha256": exclusion_sha
                },
                "cost_schedule": {
                    "venue": "BINANCE_VIP0",
                    "taker_fee_bps": 20.0,
                    "spread_bps": 2.0,
                    "base_slippage_bps": 2.0,
                    "expansion_slippage_penalty_bps": 2.0,
                    "total_modeled_drag_bps": 26.0
                },
                "population_statistics": {
                    "total_trades": 194,
                    "winning_trades": int((df["net_vip0_bps"] > 0).sum()),
                    "overall_win_rate_pct": round(float((df["net_vip0_bps"] > 0).mean() * 100.0), 2),
                    "mean_gross_return_bps": round(float(df["gross_return_bps"].mean()), 2),
                    "mean_net_expectancy_bps": round(mean_all, 4),
                    "cumulative_net_drag_bps": round(float(df["net_vip0_bps"].sum()), 2)
                },
                "retained_subgroup": {
                    "trade_count": 110,
                    "winning_trades": int((kept_sub["net_vip0_bps"] > 0).sum()),
                    "win_rate_pct": round(float((kept_sub["net_vip0_bps"] > 0).mean() * 100.0), 2),
                    "mean_gross_return_bps": round(float(kept_sub["gross_return_bps"].mean()), 2),
                    "mean_net_expectancy_bps": round(mean_kept, 4),
                    "total_net_contribution_bps": round(float(kept_sub["net_vip0_bps"].sum()), 2)
                },
                "excluded_subgroup": {
                    "trade_count": 84,
                    "winning_trades": int((excl_sub["net_vip0_bps"] > 0).sum()),
                    "win_rate_pct": round(float((excl_sub["net_vip0_bps"] > 0).mean() * 100.0), 2),
                    "mean_gross_return_bps": round(float(excl_sub["gross_return_bps"].mean()), 2),
                    "mean_net_expectancy_bps": round(mean_excl, 4),
                    "cumulative_drag_eliminated_bps": round(float(excl_sub["net_vip0_bps"].sum()), 2)
                },
                "regime_breakdowns": regime_breakdowns,
                "disclaimer": (
                    "The figures above are retrospective research statistics from offline backtest replay. "
                    "They do not represent prospective validation, live execution clearance, or a guarantee "
                    "of future profitability. Real trading remains strictly DISABLED."
                ),
                "prospective_validation": {
                    "status": "NOT_VALIDATED",
                    "ledger_path": "data/htf_prospective_shadow_ledger.jsonl",
                    "events_accumulated": 0,
                    "min_required_blocks": 100,
                    "collector_status": "INACTIVE_AWAITING_MANAGEMENT_AUTHORIZATION"
                }
            }

            return self._cached_evidence

    def get_historical_evidence(self) -> Dict[str, Any]:
        """Public getter for cached historical evidence."""
        return self.validate_and_load(force_reload=False)

