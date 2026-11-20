import os
import hashlib
import json
import pandas as pd

def inspect():
    path = "data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear.parquet"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    df = pd.read_parquet(path)
    with open(path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
        
    print(f"File: {path}")
    print(f"Row count: {len(df)}")
    print(f"First timestamp: {df['timestamp'].iloc[0]}")
    print(f"Last timestamp: {df['timestamp'].iloc[-1]}")
    print(f"SHA-256: {sha256}")
    print(f"Columns: {list(df.columns)}")
    
    diffs = df["timestamp"].diff().dropna().dt.total_seconds()
    gaps = int((diffs != 3600).sum())
    duplicates = int(df["timestamp"].duplicated().sum())
    print(f"Gaps: {gaps}")
    print(f"Duplicates: {duplicates}")
    
    # Check OHLC extrema
    high_valid = (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    low_valid = (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    print(f"OHLC High valid: {high_valid}")
    print(f"OHLC Low valid: {low_valid}")
    print(f"Volume non-negative: {(df['volume'] >= 0).all()}")

    # Check provenance file if present
    prov_path = "data/providers/bitstamp/BTCUSD_1h_v34_2_multiyear_provenance.json"
    if os.path.exists(prov_path):
        with open(prov_path, "r", encoding="utf-8") as f:
            prov = json.load(f)
        print("\nProvenance JSON:")
        print(json.dumps(prov, indent=2))

if __name__ == "__main__":
    inspect()

