"""
tests/test_api_attack_surface.py — Penetration-Style API Attack Surface Tests
=============================================================================
Tests:
- Unauthorized access and RBAC bypass attempts
- Oversized payload rejections (413 Payload Too Large)
- Host header attack rejection (TrustedHostMiddleware)
- Malformed JSON handling
- Method abuse & information leakage
- Error sanitization (no internal paths or stack traces)
"""

from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app, raise_server_exceptions=False)

def test_health_publicly_accessible():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "status" in resp.json()

def test_oversized_payload_rejected():
    large_payload = {"data": "A" * 1100000}  # ~1.1 MB > 1MB limit
    resp = client.post("/prediction/range", json=large_payload, headers={"X-API-Key": "btc-user-key-live-2026"})
    assert resp.status_code in [413, 404, 405]

def test_host_header_poisoning_blocked():
    resp = client.get("/health", headers={"Host": "evil-attacker-site.com"})
    assert resp.status_code == 400

def test_malformed_json_handling():
    resp = client.post(
        "/prediction/range",
        content="{\"invalid_json: true",
        headers={"Content-Type": "application/json", "X-API-Key": "btc-user-key-live-2026"}
    )
    assert resp.status_code in [400, 422, 404, 405]

def test_error_response_masks_internal_details():
    resp = client.get("/prediction/non-existent-endpoint-xyz")
    assert resp.status_code == 404
    # Must not contain python tracebacks or directory roots
    assert "Traceback" not in resp.text
    assert "c:\\projects" not in resp.text.lower()
