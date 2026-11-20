"""Opt-in Binance Vision BTCUSDT archives for isolated non-commercial research only.

This module never reads from or writes to production routes or protected datasets.
Network access occurs only when the CLI caller passes --download.
"""
from __future__ import annotations

import argparse, csv, hashlib, io, json, math, os, time, zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "research" / "research_only_data" / "binance_vision_btcusdt_1h"
TERMS_URL = "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md"
TERMS_VERSION = "2026-08-26 / CC-BY-NC-SA-4.0 / research-only screening"
REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def months(start: str, end: str) -> list[str]:
    def utc_month(value: str):
        timestamp=pd.Timestamp(value)
        timestamp=timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        return pd.Period(year=timestamp.year, month=timestamp.month, freq="M")
    first, last = utc_month(start), utc_month(end)
    if first > last: raise ValueError("--start must not follow --end")
    result=[]
    while first <= last:
        result.append(str(first)); first += 1
    return result

def archive_url(symbol: str, interval: str, month: str) -> str:
    return f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"

def canonical_range() -> tuple[str, str]:
    manifest = ROOT / "data/research/coinbase_btc_usd_hourly_verified_v3/acquisition_manifest.json"
    if not manifest.is_file(): raise FileNotFoundError("Canonical metadata unavailable; provide --start and --end explicitly")
    data=json.loads(manifest.read_text(encoding="utf-8"))
    return data["requested_start_utc"], data["requested_last_candle_utc"]

def parse_archive(raw: bytes, interval_seconds: int = 3600) -> pd.DataFrame:
    if raw.lstrip().lower().startswith((b"<!doctype", b"<html")): raise ValueError("Unexpected HTML response")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names=[name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(names)!=1: raise ValueError("Archive must contain exactly one CSV")
            text=archive.read(names[0]).decode("utf-8-sig")
    except zipfile.BadZipFile as exc: raise ValueError("Invalid ZIP archive") from exc
    rows=list(csv.reader(io.StringIO(text)))
    if not rows: raise ValueError("Archive CSV is empty")
    if rows[0] and not rows[0][0].strip().isdigit(): rows=rows[1:]
    parsed=[]
    for index,row in enumerate(rows):
        if len(row)<6: raise ValueError(f"Malformed archive row {index}")
        try:
            timestamp_ms=int(row[0]); low=float(row[3]); high=float(row[2]); opening=float(row[1]); close=float(row[4]); volume=float(row[5])
        except (ValueError, TypeError) as exc: raise ValueError(f"Invalid archive row {index}") from exc
        parsed.append({"timestamp":pd.Timestamp(timestamp_ms, unit="ms", tz="UTC"), "open":opening, "high":high, "low":low, "close":close, "volume":volume, "available_time":pd.Timestamp(timestamp_ms//1000+interval_seconds,unit="s",tz="UTC")})
    frame=pd.DataFrame(parsed)
    return frame.sort_values("timestamp", kind="stable").reset_index(drop=True)

def validate(frame: pd.DataFrame, interval_seconds: int = 3600) -> dict:
    if frame.empty: raise ValueError("Segment is empty")
    timestamps=pd.to_datetime(frame["timestamp"], utc=True)
    numeric=frame[["open","high","low","close","volume"]].to_numpy(float)
    duplicates=int(timestamps.duplicated().sum())
    gaps=[]
    for before,after in zip(timestamps.iloc[:-1], timestamps.iloc[1:]):
        delta=int((after-before).total_seconds())
        if delta != interval_seconds: gaps.append({"after_utc":before.isoformat(),"resumes_utc":after.isoformat(),"missing_intervals":max(0,delta//interval_seconds-1)})
    report={"rows":len(frame),"first_timestamp_utc":timestamps.iloc[0].isoformat(),"last_timestamp_utc":timestamps.iloc[-1].isoformat(),"strictly_increasing":bool(timestamps.is_monotonic_increasing and duplicates==0),"duplicate_timestamps":duplicates,"utc_hour_boundaries":bool((timestamps.astype("int64")//10**9 % interval_seconds == 0).all()),"finite_ohlcv":bool(all(math.isfinite(x) for x in numeric.flat)),"nonnegative_volume":bool((frame["volume"]>=0).all()),"valid_ohlc":bool(((frame["low"]<=frame[["open","close"]].min(axis=1)) & (frame["high"]>=frame[["open","close"]].max(axis=1))).all()),"gaps":gaps}
    if not all([report["strictly_increasing"],report["utc_hour_boundaries"],report["finite_ohlcv"],report["nonnegative_volume"],report["valid_ohlc"]]): raise ValueError("Segment failed integrity validation")
    return report

def download(url: str, retries: int = 3) -> bytes:
    for attempt in range(retries):
        try:
            request=Request(url,headers={"User-Agent":"BTCognitive-Research-Only-Segments/1.0","Accept":"application/zip"})
            with urlopen(request,timeout=30) as response:
                if response.status != 200: raise ValueError(f"HTTP {response.status}")
                raw=response.read()
                if not raw.startswith(b"PK"): raise ValueError("Response is not a ZIP archive")
                return raw
        except (HTTPError,URLError,TimeoutError,OSError,ValueError):
            if attempt == retries-1: raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+".tmp"); temp.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8"); os.replace(temp,path)

def validate_join(frames: list[pd.DataFrame], interval_seconds: int = 3600) -> list[dict]:
    """Reject overlap conflicts/duplicates; return visible gaps without bridging them."""
    if not frames: return []
    joined=pd.concat(frames).sort_values("timestamp",kind="stable")
    if joined["timestamp"].duplicated().any():
        raise ValueError("Cross-segment overlap/duplicate conflict; build stopped")
    return validate(joined,interval_seconds)["gaps"]

def verify_file_hash(path: Path, expected: str) -> None:
    if sha256_bytes(path.read_bytes()) != expected: raise ValueError("Archive hash mismatch")

def collect(start: str, end: str, output: Path, download_enabled: bool, symbol: str="BTCUSDT", interval: str="1h") -> dict:
    if symbol != "BTCUSDT" or interval != "1h": raise ValueError("This research collector currently accepts only BTCUSDT 1h")
    output=output.resolve(); output.mkdir(parents=True,exist_ok=True)
    protected_raw=(ROOT/"data/raw").resolve()
    if output == protected_raw or protected_raw in output.parents:
        raise ValueError("Research-only output must not be inside data/raw")
    records=[]; all_frames=[]
    for month in months(start,end):
        destination=output/month; destination.mkdir(exist_ok=True)
        url=archive_url(symbol,interval,month); item={"month":month,"source_url":url,"source_symbol":"BTCUSDT","quote_currency":"USDT","venue":"BINANCE_SPOT","interval":"1h","terms_url":TERMS_URL,"terms_version":TERMS_VERSION,"retrieved_at_utc":None,"status":"NOT_DOWNLOADED"}
        raw_path=destination/f"BTCUSDT-1h-{month}.zip"
        if download_enabled:
            try:
                raw=download(url); raw_path.write_bytes(raw); item.update({"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"zip_file":str(raw_path.relative_to(output)),"zip_sha256":sha256_bytes(raw),"zip_bytes":len(raw)})
                frame=parse_archive(raw); item["validation"]=validate(frame); item["status"]="ACQUIRED_VALIDATED_RESEARCH_ONLY"; frame.to_parquet(destination/"normalized_research_only.parquet",index=False); all_frames.append(frame)
            except Exception as exc: item.update({"status":"FAILED","error_type":type(exc).__name__})
        records.append(item)
        if download_enabled: time.sleep(.25)
    joins=[]
    if all_frames:
        joined=pd.concat(all_frames).sort_values("timestamp",kind="stable")
        joins=validate_join(all_frames)
        joined.to_parquet(output/"normalized_research_only_all_segments.parquet",index=False)
    manifest={"dataset_status":"RESEARCH_ONLY_NOT_FOR_PUBLIC_DISPLAY","provider":"BINANCE_VISION","venue":"BINANCE_SPOT","symbol":"BTCUSDT","base_currency":"BTC","quote_currency":"USDT","market_type":"SPOT","interval":"1h","start":start,"end":end,"download_enabled":download_enabled,"terms_url":TERMS_URL,"terms_version":TERMS_VERSION,"segments":records,"join_gaps":joins,"no_gap_filling_or_synthetic_candles":True,"production_use_prohibited":True,"model_pipeline_use_prohibited":True}
    write_json(output/"manifest.json",manifest)
    (output/"REPORT.md").write_text("# Binance Vision segmented BTCUSDT 1h\n\n**RESEARCH_ONLY_NOT_FOR_PUBLIC_DISPLAY.** Binance Vision BTCUSDT spot data is not BTCUSD, is not a production feed, and is not licensed here for public display, export, or commercial model pipelines. Raw ZIPs are preserved when --download is explicitly used; missing/failed months remain missing.\n",encoding="utf-8")
    return manifest

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--start"); parser.add_argument("--end"); parser.add_argument("--symbol",default="BTCUSDT"); parser.add_argument("--interval",default="1h"); parser.add_argument("--output-dir",type=Path,default=DEFAULT_OUT); parser.add_argument("--download",action="store_true",help="explicitly enable Binance Vision archive download")
    args=parser.parse_args(); default_start,default_end=canonical_range(); manifest=collect(args.start or default_start,args.end or default_end,args.output_dir,args.download,args.symbol,args.interval); print(json.dumps({"output":str(args.output_dir),"months":len(manifest["segments"]),"download_enabled":args.download,"status":manifest["dataset_status"]},indent=2))
if __name__ == "__main__": main()
