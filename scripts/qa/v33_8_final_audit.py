import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pandas as pd
import json
import hashlib
from engine.htf_setup_detector import HTFSetupDetector
from engine.bitstamp_market_data_service import BitstampMarketDataService

svc = BitstampMarketDataService.get_instance()
ok, df, prov = svc.get_or_refresh_bitstamp_data(force_refresh=False)

# Load existing persisted Bitstamp dataset from parquet if df is None
if df is None:
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "providers", "bitstamp", "BTCUSD_1h.parquet")
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        print("Loaded persisted Bitstamp dataset from parquet:", len(df), "candles")

detector = HTFSetupDetector()
res = detector.detect_setup(df, observed_regime="VOLATILITY_EXPANSION")
print("Detector result status:", res.get("setup_status"))
print("Detector breakout reference:", res.get("breakout_reference"))
print("Detector regime:", res.get("regime"))
print("Detector trigger status:", res.get("trigger_status"))
print("Detector distance bps:", res.get("distance_to_trigger_bps"))
print("Detector distance atr:", res.get("distance_to_trigger_atr"))
print("Detector next condition:", res.get("next_required_condition"))
print("Detector data age seconds:", res.get("data_age_seconds"))
print("Detector data age hours:", res.get("data_age_hours"))
print("Detector candle watermark:", res.get("candle_watermark_hash"))

# 4h aggregation inside detector
df_4h, agg_meta = detector.aggregate_completed_4h_candles(df)
print("Total 4h candles:", len(df_4h))
print("Latest completed 4h candle:", df_4h.iloc[-1].to_dict())

latest_4h_ts = df_4h.iloc[-1]["timestamp"]
latest_4h_close_ts = latest_4h_ts + pd.Timedelta(hours=4)
print("Latest 4h bucket:", latest_4h_ts, "to", latest_4h_close_ts)

constituent_1h = df[(df["timestamp"] >= latest_4h_ts) & (df["timestamp"] < latest_4h_close_ts)]
print("Constituent 1h count:", len(constituent_1h))
for idx, r in constituent_1h.iterrows():
    ts_str = str(r["timestamp"])
    o, h, l, c, v = r["open"], r["high"], r["low"], r["close"], r["volume"]
    print(f"  1h: {ts_str} O={o} H={h} L={l} C={c} V={v}")

calc_open = constituent_1h.iloc[0]["open"]
calc_high = constituent_1h["high"].max()
calc_low = constituent_1h["low"].min()
calc_close = constituent_1h.iloc[-1]["close"]
calc_vol = constituent_1h["volume"].sum()

print("Calculated 4h:", f"O={calc_open} H={calc_high} L={calc_low} C={calc_close} V={calc_vol}")
match_o = calc_open == df_4h.iloc[-1]["open"]
match_h = calc_high == df_4h.iloc[-1]["high"]
match_l = calc_low == df_4h.iloc[-1]["low"]
match_c = calc_close == df_4h.iloc[-1]["close"]
match_v = abs(calc_vol - df_4h.iloc[-1]["volume"]) < 1e-6
print(f"Matches: Open={match_o}, High={match_h}, Low={match_l}, Close={match_c}, Vol={match_v}")

# Check Donchian 20-bar causal shift
rolling_20_high = df_4h["high"].rolling(20).max().shift(1)
rolling_20_low = df_4h["low"].rolling(20).min().shift(1)
expected_breakout_ref = rolling_20_high.iloc[-1]
expected_channel_low = rolling_20_low.iloc[-1]
print("Expected Breakout Ref (shifted 1):", expected_breakout_ref)
print("Expected Channel Low (shifted 1):", expected_channel_low)
print("Detector Breakout Ref:", res.get("breakout_reference"))
print("Breakout Ref match:", abs(expected_breakout_ref - res.get("breakout_reference")) < 0.01)

# Check incomplete bucket exclusion
# The latest 1h candle in df is 17:00 UTC. The 16:00-20:00 4h candle is incomplete (only has 16:00 and 17:00)!
# Has it been properly excluded?
print("Latest 1h candle in df:", df.iloc[-1]["timestamp"])
print("Latest 4h candle timestamp:", df_4h.iloc[-1]["timestamp"])
is_incomplete_excluded = df_4h.iloc[-1]["timestamp"] == pd.Timestamp("2026-11-02 12:00:00+0000", tz="UTC")
print("Incomplete 16:00 bucket excluded:", is_incomplete_excluded)
