import importlib.util, io, zipfile
from pathlib import Path
import pandas as pd
import pytest

PATH=Path(__file__).parents[1]/"research/data_acquisition/collect_binance_vision_segments.py"
SPEC=importlib.util.spec_from_file_location("vision_collector",PATH); module=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(module)

def archive(rows):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as z: z.writestr("BTCUSDT-1h.csv","\n".join(",".join(map(str,row)) for row in rows))
    return out.getvalue()

def row(ts,low=99,high=102,op=100,close=101,volume=2): return [ts,op,high,low,close,volume,ts+3599999,3,volume,1,volume,0]

def test_valid_archive_and_gap_report():
    frame=module.parse_archive(archive([row(0),row(7200000)])); report=module.validate(frame); assert report["rows"]==2 and report["gaps"][0]["missing_intervals"]==1

@pytest.mark.parametrize("raw",[b"<html>error</html>",b"not-a-zip"])
def test_malformed_archives_fail_closed(raw):
    with pytest.raises(ValueError): module.parse_archive(raw)

def test_duplicate_and_ohlc_violation_fail_closed():
    with pytest.raises(ValueError): module.validate(module.parse_archive(archive([row(0),row(0)])))
    with pytest.raises(ValueError): module.validate(module.parse_archive(archive([row(0,low=99,high=100,op=101,close=101)])))

def test_no_download_creates_only_manifest(tmp_path):
    manifest=module.collect("2022-01-01","2022-01-31",tmp_path,False); assert manifest["segments"][0]["status"]=="NOT_DOWNLOADED"; assert not list(tmp_path.rglob("*.zip"))

def test_download_hash_and_production_path_boundary(tmp_path,monkeypatch):
    calls=[]
    def fail_then_zip(url,retries=3): calls.append(url); return archive([row(0)])
    monkeypatch.setattr(module,"download",fail_then_zip)
    manifest=module.collect("2022-01-01","2022-01-31",tmp_path,True); assert manifest["segments"][0]["zip_sha256"]
    with pytest.raises(ValueError): module.collect("2022-01-01","2022-01-31",module.ROOT/"data/raw/research_forbidden",False)
    with pytest.raises(ValueError): module.collect("2022-01-01","2022-01-31",tmp_path,False,symbol="BTCUSD")

def test_overlap_and_hash_mismatch_fail_closed(tmp_path):
    first=module.parse_archive(archive([row(0)])); overlap=module.parse_archive(archive([row(0)]))
    with pytest.raises(ValueError): module.validate_join([first,overlap])
    target=tmp_path/"archive.zip"; target.write_bytes(archive([row(0)]))
    with pytest.raises(ValueError): module.verify_file_hash(target,"0"*64)

def test_download_retries_transient_error(monkeypatch):
    calls=[]
    class Response:
        status=200
        def read(self): return archive([row(0)])
        def __enter__(self): return self
        def __exit__(self,*_): return False
    def opener(*_args,**_kwargs):
        calls.append(1)
        if len(calls)==1: raise OSError("temporary")
        return Response()
    monkeypatch.setattr(module,"urlopen",opener); monkeypatch.setattr(module.time,"sleep",lambda *_:None)
    assert module.download("https://example.invalid/archive.zip")[:2]==b"PK" and len(calls)==2
