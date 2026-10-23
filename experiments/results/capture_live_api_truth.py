import urllib.request
import json
import os

endpoints = [
    '/',
    '/health',
    '/api/health',
    '/api/readiness',
    '/api/dashboard?horizon=1h',
    '/api/dashboard?horizon=4h',
    '/api/dashboard?horizon=24h',
    '/prediction/latest?horizon=24h',
    '/api/prediction/latest?horizon=24h',
    '/prediction/range?horizon=24h',
    '/prediction/range/health',
    '/api/terminal/model-identity',
    '/api/terminal/live',
    '/api/research/entry-tp-sl',
    '/api/research/prospective-ledger'
]

results = {}
base_url = 'http://127.0.0.1:8000'

for ep in endpoints:
    url = base_url + ep
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Phase1-Diagnostics'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body_bytes = resp.read()
            try:
                data = json.loads(body_bytes.decode('utf-8'))
            except Exception:
                data = body_bytes.decode('utf-8', errors='replace')[:500]
            results[ep] = {'status': status, 'body': data}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            body = json.loads(body)
        except Exception:
            pass
        results[ep] = {'status': e.code, 'error': str(e), 'body': body}
    except Exception as e:
        results[ep] = {'status': 'ERROR', 'error': str(e)}

os.makedirs('experiments/results', exist_ok=True)
output_path = 'experiments/results/live_api_truth_phase1.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f'Captured {len(results)} endpoints to {output_path}')
for ep in ['/api/readiness', '/api/dashboard?horizon=24h', '/prediction/range?horizon=24h', '/api/terminal/live']:
    res = results.get(ep, {})
    print(f"=== {ep} === (Status: {res.get('status')})")
    b = res.get('body')
    if isinstance(b, dict):
        summary = {k: (b[k] if k not in ['checks', 'series', 'recent_events', 'observations'] else f'<{type(b[k]).__name__}>') for k in b}
        print(json.dumps(summary, indent=2))
    else:
        print(str(b)[:200])
