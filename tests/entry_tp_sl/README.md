# Entry/TP/SL G0 Tests

Create the isolated Windows/Python 3.13 research environment from the repository root, then run only the research-track tests:

```powershell
$venv = Join-Path $env:TEMP "btcognitive-entry-tp-sl-venv"
py -3.13 -m venv $venv
& (Join-Path $venv "Scripts\python.exe") -m pip install --require-hashes --only-binary=:all: -r research/entry_tp_sl/requirements.lock
```

The lock contains hashes for Windows CPython binary wheels. Do not use it on a different OS/architecture; resolve a separate lock there. Set the deterministic process variables before starting Python:

```powershell
$env:PYTHONHASHSEED = "0"
$env:TZ = "UTC"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:VECLIB_MAXIMUM_THREADS = "1"
& (Join-Path $venv "Scripts\python.exe") -m pytest -q --timeout=30 tests/entry_tp_sl
```

This directory intentionally does not import production models, HAR artifacts, market-memory databases, exchange clients, or IV data. It uses the repository's pytest configuration for collection, while keeping its test node IDs independently selectable. The timeout comes from the isolated research lock and is not added to global `pytest.ini`. Future LightGBM estimator calls must also pass `deterministic=True`, `force_row_wise=True`, a fixed seed, and a fixed thread count; setting process variables alone does not enable those LightGBM parameters.
