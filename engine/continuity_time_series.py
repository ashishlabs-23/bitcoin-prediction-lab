"""
engine/continuity_time_series.py — Gap-Aware Time-Series & Continuous Segmentation Layer
========================================================================================
Authoritative pipeline for continuity-aware time-series data preparation, feature engineering,
and forward-looking triple-barrier outcome labeling on cryptocurrency OHLCV data.

Mathematical & Econometric Principles:
1. Irregular spacing must never be treated as continuous hourly steps.
   A 24-row shift across a 31-day data gap is NOT a 24-hour return; it is a 31-day return.
2. Contiguous Segmentation: History is partitioned into strictly continuous segments where
   delta_t == expected_interval (e.g. 1 hour) for every consecutive candle.
3. Feature Lookback Boundary: Lagged returns (1h, 4h, 24h) and rolling statistics (rv_24h,
   rolling 168h mean) are reset at segment boundaries. A feature requiring K lookback bars
   is INVALID (NaN) for the first K bars of any segment.
4. Target Horizon Contract: For an H-hour target (e.g. H=24h), the outcome must span exactly
   H elapsed hours. If the forward horizon crosses a gap or contains missing candles, the
   label is marked EXCLUDED (DISCONTINUOUS_OUTCOME_WINDOW).
5. Split Boundary & Purging Embargo: No training or validation label is permitted to mature
   inside a subsequent evaluation period. Embargo and purge rules are calculated using exact
   UTC timestamps and label maturity horizons, not raw row counts.
6. Zero Synthetic Fabrication: Missing candles are never manufactured or forward-filled.
   Discontinuities are explicitly identified, logged, and isolated.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd


@dataclass
class TimeSeriesSegment:
    segment_id: int
    start_index: int
    end_index: int
    start_timestamp: pd.Timestamp
    end_timestamp: pd.Timestamp
    total_bars: int
    duration_hours: float
    is_contiguous: bool


@dataclass
class GapAuditSummary:
    total_input_rows: int
    total_duplicates_removed: int
    gap_count: int
    gaps: List[Dict[str, Any]]
    segments: List[TimeSeriesSegment]
    valid_contiguous_bars: int
    excluded_lookback_bars: int
    excluded_horizon_bars: int


class ContinuityTimeSeriesEngine:
    """
    Validates candle timestamp continuity, partitions data into contiguous segments,
    computes causal features strictly within segment boundaries, and builds gap-safe
    forward triple-barrier labels.
    """

    def __init__(self, expected_cadence_hours: float = 1.0):
        self.expected_cadence_hours = expected_cadence_hours
        self.expected_delta = pd.Timedelta(hours=expected_cadence_hours)

    def audit_and_segment(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, GapAuditSummary]:
        """
        Validates timestamps, removes exact duplicates, sorts chronologically,
        and assigns contiguous segment IDs.
        """
        df_clean = df.copy()
        initial_len = len(df_clean)

        # 1. Normalize timestamps to UTC
        df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], utc=True)
        
        # 2. Check and remove duplicates
        dup_count = int(df_clean["timestamp"].duplicated().sum())
        if dup_count > 0:
            df_clean = df_clean.drop_duplicates(subset=["timestamp"], keep="last")

        df_clean = df_clean.sort_values("timestamp").reset_index(drop=True)
        n = len(df_clean)

        # 3. Detect discontinuities
        diffs = df_clean["timestamp"].diff()
        
        # Segment 0 starts at index 0
        segment_id = 0
        segment_ids = np.zeros(n, dtype=int)
        gaps_list = []

        segment_start_idx = 0

        for i in range(1, n):
            delta = diffs[i]
            if delta != self.expected_delta:
                # Gap detected between i-1 and i
                gap_start = df_clean.loc[i - 1, "timestamp"]
                gap_end = df_clean.loc[i, "timestamp"]
                elapsed_hours = delta.total_seconds() / 3600.0
                missing_hours = elapsed_hours - self.expected_cadence_hours
                
                gaps_list.append({
                    "gap_id": len(gaps_list) + 1,
                    "gap_start_index": i - 1,
                    "gap_end_index": i,
                    "gap_start_timestamp": gap_start.isoformat(),
                    "gap_end_timestamp": gap_end.isoformat(),
                    "elapsed_hours": round(elapsed_hours, 2),
                    "missing_hours": round(missing_hours, 2)
                })

                segment_id += 1
            
            segment_ids[i] = segment_id

        df_clean["segment_id"] = segment_ids

        # 4. Build segment metadata
        segments_meta = []
        for s_id in range(segment_id + 1):
            s_mask = df_clean["segment_id"] == s_id
            s_indices = df_clean[s_mask].index
            s_start = df_clean.loc[s_indices.min(), "timestamp"]
            s_end = df_clean.loc[s_indices.max(), "timestamp"]
            s_bars = len(s_indices)
            duration_h = (s_end - s_start).total_seconds() / 3600.0 + self.expected_cadence_hours
            
            segments_meta.append(TimeSeriesSegment(
                segment_id=s_id,
                start_index=int(s_indices.min()),
                end_index=int(s_indices.max()),
                start_timestamp=s_start,
                end_timestamp=s_end,
                total_bars=s_bars,
                duration_hours=round(duration_h, 2),
                is_contiguous=True
            ))

        summary = GapAuditSummary(
            total_input_rows=initial_len,
            total_duplicates_removed=dup_count,
            gap_count=len(gaps_list),
            gaps=gaps_list,
            segments=segments_meta,
            valid_contiguous_bars=n,
            excluded_lookback_bars=0,
            excluded_horizon_bars=0
        )

        return df_clean, summary

    def build_continuity_features(
        self,
        df: pd.DataFrame,
        lookbacks_return: List[int] = [1, 4, 24],
        volatility_window: int = 24,
        long_vol_window: int = 168
    ) -> pd.DataFrame:
        """
        Computes causal features strictly within each contiguous segment.
        Any feature requiring lookback K is set to NaN for the first K bars of each segment.
        """
        if "segment_id" not in df.columns:
            df, _ = self.audit_and_segment(df)

        df_feat = df.copy()

        # Initialize feature columns with NaN
        for lag in lookbacks_return:
            df_feat[f"ret_{lag}h"] = np.nan
        df_feat["rv_24h"] = np.nan
        df_feat["vol_spread"] = np.nan
        df_feat["hl_ratio_24h"] = np.nan

        # Process each segment independently to guarantee zero gap contamination
        for seg_id, seg_data in df_feat.groupby("segment_id"):
            seg_indices = seg_data.index
            n_seg = len(seg_data)

            # Log returns within segment
            log_close = np.log(seg_data["close"].values)

            for lag in lookbacks_return:
                if n_seg > lag:
                    ret_lag = np.full(n_seg, np.nan)
                    ret_lag[lag:] = log_close[lag:] - log_close[:-lag]
                    df_feat.loc[seg_indices, f"ret_{lag}h"] = ret_lag

            # Realized volatility within segment (rolling 24 bars of 1h returns)
            if n_seg >= volatility_window:
                ret_1h_seg = np.full(n_seg, np.nan)
                ret_1h_seg[1:] = log_close[1:] - log_close[:-1]
                s_ret = pd.Series(ret_1h_seg, index=seg_indices)
                rv_seg = s_ret.rolling(volatility_window).std() * np.sqrt(volatility_window)
                df_feat.loc[seg_indices, "rv_24h"] = rv_seg

                # Rolling high-low ratio within segment
                high_s = seg_data["high"]
                low_s = seg_data["low"]
                hl_range = high_s.rolling(volatility_window).max() - low_s.rolling(volatility_window).min()
                df_feat.loc[seg_indices, "hl_ratio_24h"] = (hl_range / seg_data["close"]).values

                # Rolling long-term volatility mean within segment
                if n_seg >= long_vol_window:
                    rv_long = rv_seg.rolling(long_vol_window).mean()
                    df_feat.loc[seg_indices, "vol_spread"] = (rv_seg - rv_long).values
                else:
                    # Segment shorter than 168h cannot compute 168h rolling mean causally
                    df_feat.loc[seg_indices, "vol_spread"] = np.nan

        return df_feat

    def build_gap_safe_triple_barrier_labels(
        self,
        df: pd.DataFrame,
        horizon_hours: int = 24,
        k_tp: float = 1.5,
        k_sl: float = 1.0,
        collision_policy: str = "SL_FIRST_CONSERVATIVE"
    ) -> pd.DataFrame:
        """
        Builds triple-barrier labels strictly within continuous segments.
        If a candle's forward horizon [t+1, t+H] crosses a segment boundary,
        the label is marked EXCLUDED (DISCONTINUOUS_FORWARD_HORIZON).
        """
        if "segment_id" not in df.columns:
            df = self.build_continuity_features(df)

        df_out = df.copy()
        n = len(df_out)

        outcomes = [None] * n
        labels = [np.nan] * n
        raw_returns = [np.nan] * n
        exit_indices = [np.nan] * n
        exit_timestamps = [None] * n
        holding_hours = [np.nan] * n
        exclusion_reasons = [None] * n

        opens = df_out["open"].values
        highs = df_out["high"].values
        lows = df_out["low"].values
        closes = df_out["close"].values
        timestamps = df_out["timestamp"].values
        segment_ids = df_out["segment_id"].values
        rv_vals = df_out["rv_24h"].values if "rv_24h" in df_out.columns else np.full(n, np.nan)

        H = horizon_hours

        for i in range(n):
            curr_seg = segment_ids[i]
            
            # Check 1: Feature availability (rv_24h must be valid)
            vol = rv_vals[i]
            if np.isnan(vol) or vol <= 1e-5:
                exclusion_reasons[i] = "INSUFFICIENT_LOOKBACK_OR_VOL_NAN"
                continue

            # Check 2: Forward horizon boundary
            # Must have at least H bars remaining in the SAME continuous segment
            if i + H >= n or segment_ids[i + H] != curr_seg:
                exclusion_reasons[i] = "DISCONTINUOUS_FORWARD_HORIZON_GAP"
                continue

            # Check 3: Elapsed UTC time contract
            # The candle at i+H must be exactly H hours after candle i
            ts_issue = pd.Timestamp(timestamps[i])
            ts_horizon_end = pd.Timestamp(timestamps[i + H])
            elapsed_h = (ts_horizon_end - ts_issue).total_seconds() / 3600.0
            if not np.isclose(elapsed_h, H, atol=0.01):
                exclusion_reasons[i] = "ELAPSED_DURATION_MISMATCH"
                continue

            # Causal entry at open of bar i+1
            entry_p = opens[i + 1]
            b_tp = entry_p * (1.0 + k_tp * vol)
            b_sl = entry_p * (1.0 - k_sl * vol)

            outcome = "TIMEOUT"
            exit_p = closes[i + H]
            exit_idx = i + H
            exit_ts = timestamps[i + H]

            for j in range(i + 1, i + H + 1):
                h_j = highs[j]
                l_j = lows[j]

                # Collision check
                if h_j >= b_tp and l_j <= b_sl:
                    outcome = "SL_FIRST_CONSERVATIVE" if collision_policy == "SL_FIRST_CONSERVATIVE" else "AMBIGUOUS"
                    exit_p = b_sl
                    exit_idx = j
                    exit_ts = timestamps[j]
                    break
                elif l_j <= b_sl:
                    outcome = "SL_FIRST"
                    exit_p = b_sl
                    exit_idx = j
                    exit_ts = timestamps[j]
                    break
                elif h_j >= b_tp:
                    outcome = "TP_FIRST"
                    exit_p = b_tp
                    exit_idx = j
                    exit_ts = timestamps[j]
                    break

            hold_h = (pd.Timestamp(exit_ts) - pd.Timestamp(timestamps[i + 1])).total_seconds() / 3600.0 + self.expected_cadence_hours
            ret = (exit_p - entry_p) / entry_p

            outcomes[i] = outcome
            raw_returns[i] = ret
            exit_indices[i] = exit_idx
            exit_timestamps[i] = pd.Timestamp(exit_ts).isoformat()
            holding_hours[i] = hold_h
            labels[i] = 1 if outcome == "TP_FIRST" else 0

        df_out["tb_outcome"] = outcomes
        df_out["tb_label"] = labels
        df_out["tb_return"] = raw_returns
        df_out["tb_exit_index"] = exit_indices
        df_out["tb_exit_timestamp"] = exit_timestamps
        df_out["tb_holding_hours"] = holding_hours
        df_out["tb_exclusion_reason"] = exclusion_reasons

        return df_out

    def generate_eligibility_audit(self, df_raw: pd.DataFrame) -> Dict[str, Any]:
        """
        Produces a comprehensive machine-readable eligibility audit:
        - Segment metadata & boundaries
        - Lookback warm-up requirements and NaN counts per feature
        - Forward horizon gap exclusions
        - Sample split eligibility (train, val, test) with 24h embargo purges
        """
        df_clean, summary = self.audit_and_segment(df_raw)
        df_feat = self.build_continuity_features(df_clean)
        df_labeled = self.build_gap_safe_triple_barrier_labels(df_feat, horizon_hours=24)

        df_labeled["year"] = pd.to_datetime(df_labeled["timestamp"]).dt.year
        feature_cols = ["ret_1h", "ret_4h", "ret_24h", "rv_24h", "vol_spread", "hl_ratio_24h"]

        # Lookback audit per segment
        segment_lookbacks = {}
        for seg_id, group in df_feat.groupby("segment_id"):
            col_nans = {c: int(group[c].isna().sum()) for c in feature_cols}
            all_feat_nans = int(group[feature_cols].isna().any(axis=1).sum())
            segment_lookbacks[f"segment_{seg_id}"] = {
                "segment_id": int(seg_id),
                "total_bars": len(group),
                "feature_nan_counts": col_nans,
                "any_feature_nan_count": all_feat_nans,
                "max_lookback_required_bars": int(max(col_nans.values()))
            }

        # Label exclusions
        reason_counts = df_labeled["tb_exclusion_reason"].value_counts(dropna=False).to_dict()
        formatted_reasons = {str(k): int(v) for k, v in reason_counts.items()}

        # Splits
        train_mask = (df_labeled["year"] <= 2024) & df_labeled["tb_label"].notna() & (df_labeled["timestamp"] <= "2024-12-30 23:00:00+00:00")
        val_mask = (df_labeled["year"] == 2025) & df_labeled["tb_label"].notna() & (df_labeled["timestamp"] <= "2025-12-30 23:00:00+00:00")
        test_mask = (df_labeled["year"] == 2026) & df_labeled["tb_label"].notna()

        train_valid_features = int(df_labeled[train_mask].dropna(subset=feature_cols).shape[0])
        val_valid_features = int(df_labeled[val_mask].dropna(subset=feature_cols).shape[0])
        test_valid_features = int(df_labeled[test_mask].dropna(subset=feature_cols).shape[0])

        return {
            "audit_version": "V5-CONTINUITY-ELIGIBILITY-AUDIT",
            "total_input_bars": len(df_raw),
            "clean_bars": len(df_clean),
            "discontinuities_count": summary.gap_count,
            "discontinuities": summary.gaps,
            "segments_count": len(summary.segments),
            "feature_lookback_requirements": {
                "ret_1h": {"lookback_bars": 1, "total_dataset_nans": int(df_feat["ret_1h"].isna().sum())},
                "ret_4h": {"lookback_bars": 4, "total_dataset_nans": int(df_feat["ret_4h"].isna().sum())},
                "ret_24h": {"lookback_bars": 24, "total_dataset_nans": int(df_feat["ret_24h"].isna().sum())},
                "rv_24h": {"lookback_bars": 24, "total_dataset_nans": int(df_feat["rv_24h"].isna().sum())},
                "hl_ratio_24h": {"lookback_bars": 23, "total_dataset_nans": int(df_feat["hl_ratio_24h"].isna().sum())},
                "vol_spread": {"lookback_bars": 191, "total_dataset_nans": int(df_feat["vol_spread"].isna().sum()), "note": "24h rolling volatility + 168h rolling mean = 191 bars required"}
            },
            "segment_lookback_audit": segment_lookbacks,
            "label_exclusion_reasons": formatted_reasons,
            "sample_split_accounting": {
                "train_bars_total_with_valid_label": int(train_mask.sum()),
                "train_bars_with_all_features_ready": train_valid_features,
                "val_bars_total_with_valid_label": int(val_mask.sum()),
                "val_bars_with_all_features_ready": val_valid_features,
                "test_bars_total_with_valid_label": int(test_mask.sum()),
                "test_bars_with_all_features_ready": test_valid_features,
                "purging_embargo_hours": 24
            }
        }


# Global Singleton Instance
continuity_engine = ContinuityTimeSeriesEngine()

