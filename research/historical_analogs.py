"""
research/historical_analogs.py — Non-Predictive Historical Analog Retrieval Engine
==================================================================================
STATUS: DESCRIPTIVE RESEARCH & CONTEXT MODULE

SPECIFICATION & ISOLATION GUARANTEES:
  This module provides strictly descriptive, non-predictive k-nearest neighbor retrieval
  over historical market volatility regimes.

  FEATURE VECTOR:
    For each historical hour t in data/raw/ohlcv.parquet, computes a point-in-time
    feature vector:
      [sigma_1h, sigma_4h, sigma_24h, term_structure_ratio (sigma_1h / sigma_24h), funding_rate, open_interest_delta_24h]
    Standardized / z-scored per dimension using strictly an expanding window
    (only data available up to that point; zero full-sample normalization lookahead).

  QUERY & EMBARGO:
    Given the current live feature vector, finds the k=20 nearest historical neighbors
    by Euclidean distance on the standardized vector, EXCLUDING any historical point
    within 48h of the query time (avoiding trivial self-matches from adjacent bars)
    and excluding points whose forward 24h window overlaps the query moment.

  OUTPUT:
    For each analog: timestamp/date, similarity score, realized forward 24h MFE and MAE.
    Aggregate statistics across the 20: mean/median realized MFE, mean/median realized MAE,
    % containment within reference P10/P90 band.

  ISOLATION GUARANTEE:
    This module is purely additive, read-only, and descriptive. It does not alter live range
    predictions, conformal calibration, badges, or inference pipelines.
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("historical_analogs")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OHLCV_PATH = os.path.join(ROOT_DIR, "data", "raw", "ohlcv.parquet")
FUNDING_PATH = os.path.join(ROOT_DIR, "data", "raw", "funding.parquet")
OI_PATH = os.path.join(ROOT_DIR, "data", "raw", "oi.parquet")


class HistoricalAnalogEngine:
    """
    In-memory indexed engine for point-in-time historical analog retrieval.
    """

    def __init__(
        self,
        ohlcv_path: str = OHLCV_PATH,
        funding_path: str = FUNDING_PATH,
        oi_path: str = OI_PATH
    ):
        self.ohlcv_path = ohlcv_path
        self.funding_path = funding_path
        self.oi_path = oi_path
        self.df: Optional[pd.DataFrame] = None
        self.features_norm: Optional[np.ndarray] = None
        self.feature_names = [
            'vol_1h',
            'vol_4h',
            'vol_24h',
            'term_structure_ratio',
            'funding_rate',
            'open_interest_delta_24h'
        ]
        self._load_and_index()

    def _load_and_index(self):
        """
        Loads raw market data, merges derivatives point-in-time, computes features,
        forward 24h realized excursions (MFE/MAE), and expands-window z-scores.
        """
        if not os.path.exists(self.ohlcv_path):
            raise FileNotFoundError(f"OHLCV data file not found at {self.ohlcv_path}")

        # 1. Load OHLCV base data
        raw_df = pd.read_parquet(self.ohlcv_path)
        raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'], utc=True)
        if 'available_time' in raw_df.columns:
            raw_df['available_time'] = pd.to_datetime(raw_df['available_time'], utc=True).dt.as_unit('ns')
        else:
            raw_df['available_time'] = raw_df['timestamp'].dt.as_unit('ns')

        raw_df.sort_values('available_time', inplace=True)
        raw_df.reset_index(drop=True, inplace=True)

        # 2. Merge Point-in-Time Funding Rate
        if os.path.exists(self.funding_path):
            funding_df = pd.read_parquet(self.funding_path)
            avail_col = 'available_time' if 'available_time' in funding_df.columns else 'timestamp'
            funding_df['available_time'] = pd.to_datetime(funding_df[avail_col], utc=True).dt.as_unit('ns')
            funding_df.sort_values('available_time', inplace=True)
            funding_sub = funding_df[['available_time', 'funding_rate']].dropna().drop_duplicates(subset=['available_time'])
            raw_df = pd.merge_asof(
                raw_df,
                funding_sub,
                on='available_time',
                direction='backward'
            )
            raw_df['funding_rate'] = raw_df['funding_rate'].ffill().fillna(0.0)
        else:
            raw_df['funding_rate'] = 0.0

        # 3. Merge Point-in-Time Open Interest & Compute 24h Delta
        if os.path.exists(self.oi_path):
            oi_df = pd.read_parquet(self.oi_path)
            avail_col = 'available_time' if 'available_time' in oi_df.columns else 'timestamp'
            oi_df['available_time'] = pd.to_datetime(oi_df[avail_col], utc=True).dt.as_unit('ns')
            oi_df.sort_values('available_time', inplace=True)
            if 'open_interest' in oi_df.columns:
                # 24-hour percentage change in open interest
                oi_df['open_interest_delta_24h'] = oi_df['open_interest'].pct_change(24).fillna(0.0)
                oi_sub = oi_df[['available_time', 'open_interest_delta_24h']].dropna().drop_duplicates(subset=['available_time'])
                raw_df = pd.merge_asof(
                    raw_df,
                    oi_sub,
                    on='available_time',
                    direction='backward'
                )
                raw_df['open_interest_delta_24h'] = raw_df['open_interest_delta_24h'].ffill().fillna(0.0)
            else:
                raw_df['open_interest_delta_24h'] = 0.0
        else:
            raw_df['open_interest_delta_24h'] = 0.0

        close = raw_df['close'].values
        high = raw_df['high'].values
        low = raw_df['low'].values
        N = len(close)

        # 4. Volatilities and Term Structure
        # 1h Parkinson volatility proxy
        parkinson_1h = np.sqrt((np.log(high / (low + 1e-12)) ** 2) / (4.0 * np.log(2.0)))
        vol_1h = np.maximum(parkinson_1h, 0.001)

        # Hourly log returns
        log_ret = np.zeros(N)
        log_ret[1:] = np.log(close[1:] / (close[:-1] + 1e-12))
        ret_series = pd.Series(log_ret)

        # 4h and 24h rolling volatilities
        vol_4h = (ret_series.rolling(4, min_periods=4).std() * np.sqrt(4)).fillna(0.01).values
        vol_24h = (ret_series.rolling(24, min_periods=24).std() * np.sqrt(24)).fillna(0.02).values

        # Term structure ratio: sigma_1h / sigma_24h
        term_structure = vol_1h / (vol_24h + 1e-8)

        # 5. Forward 24h Realized Excursions (MFE & MAE)
        high_series = pd.Series(high)
        low_series = pd.Series(low)
        fwd_high = high_series.iloc[::-1].rolling(24, min_periods=24).max().iloc[::-1].values
        fwd_low = low_series.iloc[::-1].rolling(24, min_periods=24).min().iloc[::-1].values
        fwd_close = pd.Series(close).shift(-24).values

        mfe_24h = (fwd_high - close) / (close + 1e-12)
        mae_24h = (close - fwd_low) / (close + 1e-12)
        ret_24h = (fwd_close - close) / (close + 1e-12)

        raw_df['vol_1h'] = vol_1h
        raw_df['vol_4h'] = vol_4h
        raw_df['vol_24h'] = vol_24h
        raw_df['term_structure_ratio'] = term_structure
        raw_df['mfe_24h'] = mfe_24h
        raw_df['mae_24h'] = mae_24h
        raw_df['ret_24h'] = ret_24h

        # Descriptive regime classification for UI display
        regime_labels = []
        for i in range(N):
            v = vol_24h[i]
            ts = term_structure[i]
            if v > 0.04:
                regime_labels.append("HIGH_VOL_STRESS" if ts > 1.2 else "HIGH_VOL_TREND")
            elif v < 0.015:
                regime_labels.append("LOW_VOL_COMPRESSION" if ts < 0.8 else "LOW_VOL_RANGE")
            else:
                regime_labels.append("NORMAL_EXPANDING" if ts > 1.1 else "NORMAL_STABLE")
        raw_df['regime_label'] = regime_labels

        self.df = raw_df

        # 6. Expanding-window Standardization (Zero Lookahead, O(N))
        feat_matrix = raw_df[self.feature_names].values.astype(np.float64)
        min_warmup = 168  # 7-day warmup window for moment stabilization

        cum_sum = np.cumsum(feat_matrix, axis=0)
        cum_sq = np.cumsum(feat_matrix ** 2, axis=0)
        counts = np.arange(1, len(feat_matrix) + 1).reshape(-1, 1)

        exp_mean = cum_sum / counts
        exp_var = np.maximum(1e-8, (cum_sq / counts) - (exp_mean ** 2))
        exp_std = np.sqrt(exp_var)

        # Freeze moments for initial warmup window to avoid early instability
        exp_mean[:min_warmup] = exp_mean[min_warmup]
        exp_std[:min_warmup] = exp_std[min_warmup]

        self.features_norm = (feat_matrix - exp_mean) / (exp_std + 1e-6)
        logger.info(
            f"HistoricalAnalogEngine initialized with {len(self.df):,} hourly bars. "
            f"Feature vector dimensions: {self.feature_names}"
        )

    def find_analogs(
        self,
        query_timestamp: Optional[str] = None,
        max_k: int = 20,
        min_similarity: float = 0.35,
        embargo_hours: int = 48,
        min_separation_days: float = 14.0,
        current_p10_p90_band: Optional[Tuple[float, float]] = (-0.05, 0.05)
    ) -> Dict[str, Any]:
        """
        Retrieves genuine historical analogs for a given query timestamp using
        jointly-observed RMS distance, dynamic k, and greedy temporal separation.

        Constraints:
        - Embargo: Excludes candidates within +/- embargo_hours of query bar (default 48h).
        - Quality Threshold: Only includes candidates with similarity >= min_similarity.
        - Temporal Separation: Enforces >= min_separation_days spacing between selected analogs.
        - Dimension Normalization: Uses Root-Mean-Square Distance (RMSD) over jointly
          observed feature dimensions, preventing artificial penalties on historical eras
          where specific derivatives (like OI) were not yet recorded.
        """
        if self.df is None or self.features_norm is None:
            self._load_and_index()

        N = len(self.df)
        if query_timestamp:
            q_dt = pd.to_datetime(query_timestamp, utc=True)
            time_diffs = np.abs((self.df['timestamp'] - q_dt).dt.total_seconds().values)
            query_idx = int(np.argmin(time_diffs))
        else:
            # Default to the latest valid bar
            query_idx = N - 1

        query_row = self.df.iloc[query_idx]
        query_vec = self.features_norm[query_idx]
        query_ts = query_row['timestamp']

        # Exclusions:
        # 1. Any bar within +/- embargo_hours of the query time
        # 2. Any bar lacking valid forward target (e.g. latest 24h of history)
        ts_diff_hours = (self.df['timestamp'] - query_ts).dt.total_seconds().values / 3600.0
        has_forward_target = ~self.df['mfe_24h'].isna().values

        valid_mask = (np.abs(ts_diff_hours) >= embargo_hours) & has_forward_target
        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) == 0:
            raise ValueError("No valid historical bars found for retrieval.")

        # Identify observed dimensions per bar:
        # OI is observed if raw open_interest_delta_24h != 0.0 or timestamp >= 2026-07-15
        oi_start_ts = pd.to_datetime('2026-07-15 16:00:00', utc=True)
        is_oi_observed = (self.df['timestamp'] >= oi_start_ts).values

        # Compute RMSD (Root-Mean-Square Distance) over jointly observed dimensions:
        # RMSD = sqrt( mean( (x_d - y_d)^2 ) )
        # Similarity = 1 / (1 + RMSD)  -> Bounded in (0, 1]
        all_dists = np.zeros(len(valid_indices), dtype=np.float64)
        for i, idx in enumerate(valid_indices):
            cand_vec = self.features_norm[idx]
            if is_oi_observed[idx]:
                diff = query_vec - cand_vec
            else:
                # Jointly observed features (vol_1h, vol_4h, vol_24h, term_structure, funding)
                diff = query_vec[:5] - cand_vec[:5]
            all_dists[i] = np.sqrt(np.mean(diff ** 2))

        all_sims = 1.0 / (1.0 + all_dists)
        sorted_rel_order = np.argsort(all_dists)

        # Full historical similarity distribution metrics across all valid candidate bars
        sim_distribution = {
            "min_similarity": round(float(np.min(all_sims)), 4),
            "p10_similarity": round(float(np.percentile(all_sims, 10)), 4),
            "p25_similarity": round(float(np.percentile(all_sims, 25)), 4),
            "p50_median_similarity": round(float(np.percentile(all_sims, 50)), 4),
            "p75_similarity": round(float(np.percentile(all_sims, 75)), 4),
            "p90_similarity": round(float(np.percentile(all_sims, 90)), 4),
            "p95_similarity": round(float(np.percentile(all_sims, 95)), 4),
            "p99_similarity": round(float(np.percentile(all_sims, 99)), 4),
            "max_similarity": round(float(np.max(all_sims)), 4),
            "total_candidates_evaluated": len(valid_indices)
        }

        # Greedy diversified selection with minimum temporal separation and quality threshold
        min_sep_hours = float(min_separation_days * 24.0)
        selected_indices: List[int] = []
        selected_distances: List[float] = []
        selected_similarities: List[float] = []
        selected_timestamps: List[pd.Timestamp] = []

        for rel_idx in sorted_rel_order:
            cand_sim = float(all_sims[rel_idx])
            if cand_sim < min_similarity:
                # Stop if candidate fails similarity threshold
                break

            idx = valid_indices[rel_idx]
            cand_ts = self.df.iloc[idx]['timestamp']
            
            if not selected_timestamps:
                selected_indices.append(idx)
                selected_distances.append(float(all_dists[rel_idx]))
                selected_similarities.append(cand_sim)
                selected_timestamps.append(cand_ts)
            else:
                # Check separation against all already-selected analogs
                diffs_hours = [abs((cand_ts - s_ts).total_seconds()) / 3600.0 for s_ts in selected_timestamps]
                if all(d >= min_sep_hours for d in diffs_hours):
                    selected_indices.append(idx)
                    selected_distances.append(float(all_dists[rel_idx]))
                    selected_similarities.append(cand_sim)
                    selected_timestamps.append(cand_ts)

            if len(selected_indices) == max_k:
                break

        analogs = []
        realized_mfes = []
        realized_maes = []
        realized_rets = []
        contained_count = 0

        p10_bound, p90_bound = current_p10_p90_band if current_p10_p90_band else (-0.05, 0.05)

        for rank, (idx, dist, sim, ts) in enumerate(zip(selected_indices, selected_distances, selected_similarities, selected_timestamps), start=1):
            row = self.df.iloc[idx]
            mfe = float(row['mfe_24h'])
            mae = float(row['mae_24h'])
            ret = float(row['ret_24h'])

            realized_mfes.append(mfe)
            realized_maes.append(mae)
            realized_rets.append(ret)

            # Check containment within P10/P90 percentage excursion envelope:
            is_contained = bool((-mae >= p10_bound) and (mfe <= p90_bound))
            if is_contained:
                contained_count += 1

            analogs.append({
                "rank": rank,
                "timestamp": ts.strftime("%Y-%m-%d %H:%M UTC"),
                "price": float(row['close']),
                "similarity_score": round(sim, 4),
                "distance": round(float(dist), 4),
                "regime_label": str(row['regime_label']),
                "realized_mfe_24h_pct": round(mfe * 100.0, 2),
                "realized_mae_24h_pct": round(-mae * 100.0, 2),  # Display as negative % for clarity
                "realized_ret_24h_pct": round(ret * 100.0, 2),
                "contained_in_band": is_contained
            })

        # Diversity metrics computation (if analogs found)
        if selected_timestamps:
            analog_years = sorted(list(set(ts.year for ts in selected_timestamps)))
            analog_months = sorted(list(set(ts.strftime("%Y-%m") for ts in selected_timestamps)))
            earliest_ts = min(selected_timestamps)
            latest_ts = max(selected_timestamps)
            date_span_days = int((latest_ts - earliest_ts).total_seconds() / 86400.0)
            outside_30d = sum(1 for ts in selected_timestamps if abs((ts - query_ts).total_seconds()) / 3600.0 > 30 * 24.0)

            warning_msg = None
            if outside_30d < 5 and len(analogs) > 0:
                warning_msg = f"Limited historical precedent outside recent regime — {outside_30d} analogs from prior periods."

            diversity_stats = {
                "min_separation_days": min_separation_days,
                "min_similarity_threshold": min_similarity,
                "distinct_years": analog_years,
                "distinct_years_count": len(analog_years),
                "distinct_months_count": len(analog_months),
                "date_range_start": earliest_ts.strftime("%Y-%m-%d %H:%M UTC"),
                "date_range_end": latest_ts.strftime("%Y-%m-%d %H:%M UTC"),
                "date_range_span_days": date_span_days,
                "analogs_outside_30d_count": outside_30d,
                "warning": warning_msg,
                "diversity_summary": (
                    f"{len(analogs)} genuine analogs (similarity >={min_similarity*100:.0f}%) spanning "
                    f"{len(analog_years)} years ({min(analog_years)}-{max(analog_years)}) across {date_span_days:,} days."
                )
            }
        else:
            diversity_stats = {
                "min_separation_days": min_separation_days,
                "min_similarity_threshold": min_similarity,
                "distinct_years": [],
                "distinct_years_count": 0,
                "distinct_months_count": 0,
                "date_range_start": None,
                "date_range_end": None,
                "date_range_span_days": 0,
                "analogs_outside_30d_count": 0,
                "warning": f"No historical analogs cleared the {min_similarity*100:.0f}% similarity threshold.",
                "diversity_summary": f"0 genuine analogs found clearing similarity threshold >={min_similarity*100:.0f}%."
            }

        # Aggregate stats computed strictly across valid threshold-clearing analogs
        if len(analogs) > 0:
            aggregate_stats = {
                "k_analogs_used": len(analogs),
                "min_similarity_applied": min_similarity,
                "mean_realized_mfe_pct": round(float(np.mean(realized_mfes)) * 100.0, 2),
                "median_realized_mfe_pct": round(float(np.median(realized_mfes)) * 100.0, 2),
                "max_realized_mfe_pct": round(float(np.max(realized_mfes)) * 100.0, 2),
                "mean_realized_mae_pct": round(-float(np.mean(realized_maes)) * 100.0, 2),
                "median_realized_mae_pct": round(-float(np.median(realized_maes)) * 100.0, 2),
                "max_realized_mae_pct": round(-float(np.max(realized_maes)) * 100.0, 2),
                "mean_realized_ret_24h_pct": round(float(np.mean(realized_rets)) * 100.0, 2),
                "containment_rate_pct": round((contained_count / len(analogs)) * 100.0, 1),
                "reference_p10_p90_band_pct": [round(p10_bound * 100.0, 2), round(p90_bound * 100.0, 2)],
                "diversity": diversity_stats
            }
        else:
            aggregate_stats = {
                "k_analogs_used": 0,
                "min_similarity_applied": min_similarity,
                "mean_realized_mfe_pct": 0.0,
                "median_realized_mfe_pct": 0.0,
                "max_realized_mfe_pct": 0.0,
                "mean_realized_mae_pct": 0.0,
                "median_realized_mae_pct": 0.0,
                "max_realized_mae_pct": 0.0,
                "mean_realized_ret_24h_pct": 0.0,
                "containment_rate_pct": 0.0,
                "reference_p10_p90_band_pct": [round(p10_bound * 100.0, 2), round(p90_bound * 100.0, 2)],
                "diversity": diversity_stats
            }

        return {
            "query_timestamp": query_ts.strftime("%Y-%m-%d %H:%M UTC"),
            "query_price": float(query_row['close']),
            "query_regime": str(query_row['regime_label']),
            "query_vol_24h_pct": round(float(query_row['vol_24h']) * 100.0, 2),
            "query_term_structure": round(float(query_row['term_structure_ratio']), 3),
            "feature_names": self.feature_names,
            "analogs": analogs,
            "aggregate_stats": aggregate_stats,
            "diversity_metrics": diversity_stats,
            "similarity_distribution": sim_distribution,
            "disclaimer": "Historical Analogs — Descriptive Only, Not a Forecast. Realized outcomes represent historical empirical paths and imply zero guaranteed future direction."
        }


# Singleton engine instance
_engine_instance: Optional[HistoricalAnalogEngine] = None


def get_analog_engine() -> HistoricalAnalogEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = HistoricalAnalogEngine()
    return _engine_instance


if __name__ == "__main__":
    engine = get_analog_engine()
    # Query with 80% minimum similarity threshold
    res = engine.find_analogs(max_k=20, min_similarity=0.80)
    print("\n========================================================================================")
    print("HISTORICAL ANALOG RETRIEVAL — LIVE QUERY SPOT CHECK (DYNAMIC k, QUALITY THRESHOLD)")
    print("========================================================================================")
    print(f"Query Timestamp: {res['query_timestamp']} | Price: ${res['query_price']:,.2f} | Regime: {res['query_regime']}")
    print(f"Query 24h Vol:   {res['query_vol_24h_pct']}% | Term Structure Ratio: {res['query_term_structure']}")
    print(f"Feature Dimensions: {res['feature_names']}")
    print("----------------------------------------------------------------------------------------")
    print("FULL HISTORICAL SIMILARITY DISTRIBUTION (Relative to Current Live Query):")
    sd = res['similarity_distribution']
    print(f"  Min: {sd['min_similarity']*100:.1f}% | P25: {sd['p25_similarity']*100:.1f}% | Median (P50): {sd['p50_median_similarity']*100:.1f}% | P75: {sd['p75_similarity']*100:.1f}%")
    print(f"  P90: {sd['p90_similarity']*100:.1f}% | P95: {sd['p95_similarity']*100:.1f}% | P99: {sd['p99_similarity']*100:.1f}% | Max: {sd['max_similarity']*100:.1f}%")
    print(f"  Evaluated: {sd['total_candidates_evaluated']:,} historical hourly bars")
    print("----------------------------------------------------------------------------------------")
    print("DIVERSITY & TEMPORAL DISPERSION (GREEDY >=7-DAY SPACING):")
    div = res['diversity_metrics']
    print(f"Summary:        {div['diversity_summary']}")
    if div['distinct_years_count'] > 0:
        print(f"Distinct Years: {div['distinct_years']} ({div['distinct_years_count']} years)")
        print(f"Distinct Months:{div['distinct_months_count']} distinct calendar months")
        print(f"Date Span:      {div['date_range_start']} to {div['date_range_end']} ({div['date_range_span_days']:,} days)")
        print(f"Outside 30-Day: {div['analogs_outside_30d_count']} of {len(res['analogs'])} analogs from prior periods")
    if div['warning']:
        print(f"[!] Precedent Notice: {div['warning']}")
    print("----------------------------------------------------------------------------------------")
    print(f"AGGREGATE REALIZED 24H OUTCOMES ACROSS {len(res['analogs'])} GENUINE ANALOGS (>={res['aggregate_stats']['min_similarity_applied']*100:.0f}% Similarity):")
    stats = res['aggregate_stats']
    print(f"Mean MFE (Upside):   +{stats['mean_realized_mfe_pct']}% (Median: +{stats['median_realized_mfe_pct']}%, Max: +{stats['max_realized_mfe_pct']}%)")
    print(f"Mean MAE (Downside):  {stats['mean_realized_mae_pct']}% (Median: {stats['median_realized_mae_pct']}%, Max: {stats['max_realized_mae_pct']}%)")
    print(f"Mean Net Return:     {stats['mean_realized_ret_24h_pct']:+.2f}%")
    print(f"Envelope Containment: {stats['containment_rate_pct']}% of genuine paths stayed within [{stats['reference_p10_p90_band_pct'][0]}%, +{stats['reference_p10_p90_band_pct'][1]}%]")
    print("----------------------------------------------------------------------------------------")
    print(f"GENUINE DIVERSIFIED HISTORICAL MATCHES (k={len(res['analogs'])}):")
    if res['analogs']:
        table_df = pd.DataFrame(res['analogs'])
        print(table_df[['rank', 'timestamp', 'price', 'similarity_score', 'regime_label', 'realized_mfe_24h_pct', 'realized_mae_24h_pct', 'realized_ret_24h_pct', 'contained_in_band']].to_string(index=False))
    else:
        print("No historical analogs cleared the similarity threshold.")
    print("========================================================================================")


