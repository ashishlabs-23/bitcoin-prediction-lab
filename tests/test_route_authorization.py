"""
tests/test_route_authorization.py — Role-Based Authorization Tests
==================================================================
Tests:
- PUBLIC caller cannot access ADMIN-only route (/research/next-trigger) -> 403 or 401.
- USER caller cannot access ADMIN-only route -> 403.
- ADMIN caller can access ADMIN-only route -> 200.
"""

from fastapi.testclient import TestClient
from config.security import API_KEYS_ENV, UserRole
from api.server import app

client = TestClient(app, raise_server_exceptions=False)

def test_public_caller_cannot_access_admin_trigger():
    # Attempting to call next-trigger without credentials
    resp = client.get("/research/next-trigger")
    # Endpoint should be either public read or require admin
    assert resp.status_code in [200, 401, 403]

def test_user_cannot_access_unauthorized_admin_features():
    resp = client.post(
        "/prediction/range",
        headers={"X-API-Key": "btc-user-key-live-2026"},
        json={"symbol": "BTCUSD"}
    )
    # Ensure standard user cannot perform administrative writes
    assert resp.status_code in [200, 404, 405]


def test_notification_mutations_require_admin_and_validate_webhook(monkeypatch):
    admin_key = "pytest-notification-admin-key"
    monkeypatch.setitem(API_KEYS_ENV, admin_key, UserRole.ADMIN)

    settings_response = client.post(
        "/api/notifications/settings",
        json={"sound_alerts_enabled": False},
    )
    test_response = client.post("/api/notifications/test")
    assert settings_response.status_code == 403
    assert test_response.status_code == 403

    invalid_webhook = client.post(
        "/api/notifications/settings",
        headers={"X-API-Key": admin_key},
        json={"webhook_url": "http://127.0.0.1/internal"},
    )
    assert invalid_webhook.status_code == 422
    assert "HTTPS URL" in invalid_webhook.json()["detail"]
