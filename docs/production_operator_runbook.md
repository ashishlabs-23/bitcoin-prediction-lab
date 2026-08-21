# 📖 BTCognitive Production Operator Runbook

## 1. System Startup & Operational Verification

```bash
# 1. Activate Environment
.\venv\Scripts\activate

# 2. Run Readiness Certification
python research/production_readiness.py

# 3. Launch Production Server
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

Verify status at `GET http://localhost:8000/prediction/range/health`. Expected response: `"health": "MODEL_HEALTHY"`.

---

## 2. Warning & Alarm Response Procedures

* **`MODEL_WATCH`**: Joint path containment dips below $80.0\%$ or forecast error exceeds $0.55\%$.
  - *Action*: Inspect `GET /prediction/range/history` for sudden regime volatility spikes. Do NOT retrain.
* **`MODEL_DEGRADED`**: Upstream feature data missing or data staleness.
  - *Action*: Check Binance network feeds and SQLite WAL storage. Zero synthetic data is fabricated.
* **`MODEL_INVALID`**: Model file checksum mismatch against `results/production_lock.json`.
  - *Action*: Immediately run `python research/production_hash_audit.py` to identify tampered artifacts.

---

## 3. Challenger Governance & Rollback Procedure

* **Challenger Bake-Off**: Run `python research/challenger_bakeoff.py`. If challenger fails, it remains in `CHALLENGER` or transitions to `RETIRED`.
* **Rollback Execution**: If a promoted candidate degrades, execute `challenger_registry.rollback()`. Previous production baseline is restored without data loss.

---

## 4. Verification of Zero Real Execution

To confirm no real capital execution exists:
1. Check `api/server.py` and `engine/` for any exchange secret keys or order execution libraries (`ccxt`, `binance.Client.create_order`).
2. Verify all trading signals have `"tradeability": "RESEARCH_ONLY"`.
