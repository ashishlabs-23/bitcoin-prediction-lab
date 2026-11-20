import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import json
import pandas as pd
from api.routes_tournament import _post_analyse_market, AnalyseRequestModel

t0 = time.perf_counter()
res = _post_analyse_market(AnalyseRequestModel(live_price=76985.40, auto_tournament=True))
t1 = time.perf_counter()

print(f"Full _post_analyse_market isolated wall time: {t1-t0:.4f}s")
print(f"Analysis ID: {res.get('analysis_id')}")
print(f"Candidate count: {len(res.get('candidate_set', []))}")
print(f"Recommendation: {res.get('recommendation')}")
print(f"Watermark SHA256: {res.get('candle_watermark', {}).get('candle_window_sha256')}")
