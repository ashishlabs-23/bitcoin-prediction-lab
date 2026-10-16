"""
research/freeze_directional_models.py — Train and Freeze Benchmark Directional Models
=====================================================================================
Trains the canonical GBDT models for 1h, 4h, and 24h directional prediction strictly
on the pre-2026 training window (2022-01-08 00:00:00 to 2025-12-31 23:00:00 UTC).
Guarantees ZERO lookahead into the 2026 prospective holdout period.
Saves frozen model artifacts to models/registry/research/ and outputs SHA256 checksums.
"""

import os
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_PATH = os.path.join(REPO_ROOT, "data", "raw", "ohlcv.parquet")
OUT_DIR = os.path.join(REPO_ROOT, "models", "registry", "research")
os.makedirs(OUT_DIR, exist_ok=True)

HOLDOUT_CUTOFF = pd.to_datetime("2026-01-01 00:00:00+00:00")
FEATURES_4LAGS = ["ret_1h", "ret_4h", "ret_24h", "ret_168h"]


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def train_and_freeze():
    print(f"Loading raw OHLCV from: {RAW_DATA_PATH}")
    df = pd.read_parquet(RAW_DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    close = df["close"]
    df["ret_1h"] = np.log(close / close.shift(1))
    df["ret_4h"] = np.log(close / close.shift(4))
    df["ret_24h"] = np.log(close / close.shift(24))
    df["ret_168h"] = np.log(close / close.shift(168))

    df["fwd_ret_1h"] = np.log(close.shift(-1) / close)
    df["fwd_ret_4h"] = np.log(close.shift(-4) / close)
    df["fwd_ret_24h"] = np.log(close.shift(-24) / close)

    df["target_1h"] = (df["fwd_ret_1h"] > 0).astype(int)
    df["target_4h"] = (df["fwd_ret_4h"] > 0).astype(int)
    df["target_24h"] = (df["fwd_ret_24h"] > 0).astype(int)

    # Filter strictly to pre-2026 training window
    df_train = df[(df["timestamp"] < HOLDOUT_CUTOFF)].copy()
    print(f"Total rows in raw data: {len(df):,}")
    print(f"Rows before 2026-01-01 cutoff: {len(df_train):,}")

    horizons = [
        ("1h", "target_1h", "fwd_ret_1h", "directional_gbm_1h_v1.joblib"),
        ("4h", "target_4h", "fwd_ret_4h", "directional_gbm_4h_v1.joblib"),
        ("24h", "target_24h", "fwd_ret_24h", "directional_gbm_24h_v1.joblib"),
    ]

    manifest_artifacts = {}

    for h_name, target_col, fwd_ret_col, artifact_name in horizons:
        # Require valid features and target
        clean_tr = df_train.dropna(subset=FEATURES_4LAGS + [target_col]).reset_index(drop=True)
        # Avoid label leakage at the 2026 boundary: last observation must mature on or before 2025-12-31 23:00:00
        if h_name == "1h":
            clean_tr = clean_tr[clean_tr["timestamp"] <= pd.to_datetime("2025-12-31 22:00:00+00:00")]
        elif h_name == "4h":
            clean_tr = clean_tr[clean_tr["timestamp"] <= pd.to_datetime("2025-12-31 19:00:00+00:00")]
        elif h_name == "24h":
            clean_tr = clean_tr[clean_tr["timestamp"] <= pd.to_datetime("2025-12-30 23:00:00+00:00")]

        X_tr = clean_tr[FEATURES_4LAGS]
        y_tr = clean_tr[target_col]

        print(f"\nTraining frozen {h_name} model on {len(clean_tr):,} bars ({clean_tr['timestamp'].min()} to {clean_tr['timestamp'].max()})...")
        clf = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            random_state=42
        )
        clf.fit(X_tr, y_tr)

        artifact_path = os.path.join(OUT_DIR, artifact_name)
        joblib.dump(clf, artifact_path)
        sha = sha256_file(artifact_path)

        manifest_artifacts[h_name] = {
            "model_id": f"directional-gbm-{h_name}-v1",
            "artifact_file": artifact_name,
            "artifact_path": os.path.relpath(artifact_path, REPO_ROOT).replace("\\", "/"),
            "artifact_sha256": sha,
            "training_samples": len(clean_tr),
            "training_start": clean_tr["timestamp"].min().isoformat(),
            "training_end": clean_tr["timestamp"].max().isoformat(),
            "feature_schema": FEATURES_4LAGS,
            "target": f"Sign of forward {h_name} return (ln(Close_{{t+{h_name}}}/Close_t) > 0)",
            "hyperparameters": {
                "algorithm": "GradientBoostingClassifier",
                "n_estimators": 100,
                "max_depth": 3,
                "learning_rate": 0.05,
                "random_state": 42
            }
        }
        print(f"  Saved: {artifact_path}")
        print(f"  SHA256: {sha}")

    meta_path = os.path.join(OUT_DIR, "directional_models_freeze_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(manifest_artifacts, f, indent=2)
    print(f"\nMetadata written to: {meta_path}")
    return manifest_artifacts


if __name__ == "__main__":
    train_and_freeze()
