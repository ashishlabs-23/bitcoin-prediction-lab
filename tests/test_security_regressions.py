import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from api import security_auth
from api.notifications import notification_manager
from api.server import app
from config import security as security_config
from config.security import UserRole


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setitem(security_config.API_KEYS_ENV, "pytest-explicit-admin", UserRole.ADMIN)
    monkeypatch.setitem(security_auth.API_KEYS_ENV, "pytest-explicit-admin", UserRole.ADMIN)
    monkeypatch.setattr(
        app.state,
        "research_gate",
        {"authorized": True},
        raising=False,
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


@pytest.fixture
def user_key(monkeypatch):
    key = "pytest-explicit-user"
    monkeypatch.setitem(security_config.API_KEYS_ENV, key, UserRole.USER)
    monkeypatch.setitem(security_auth.API_KEYS_ENV, key, UserRole.USER)
    return key


def test_unset_environment_has_no_api_keys_and_accepts_only_explicit_keys():
    env = os.environ.copy()
    for name in (
        "BTCOGNITIVE_USER_KEY",
        "BTCOGNITIVE_RESEARCH_KEY",
        "BTCOGNITIVE_ADMIN_KEY",
        "BTCOGNITIVE_ALLOWED_ORIGINS",
        "BTCOGNITIVE_ALLOWED_HOSTS",
    ):
        env.pop(name, None)

    script = """
import importlib
import os
from types import SimpleNamespace
from fastapi import HTTPException
import config.security as config
import api.security_auth as auth

assert config.API_KEYS_ENV == {}
assert set(config.ALLOWED_ORIGINS) == {
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}
assert set(config.ALLOWED_HOSTS) == {"localhost", "127.0.0.1", "testserver"}
assert "*" not in config.ALLOWED_ORIGINS
assert "*" not in config.ALLOWED_HOSTS

request = SimpleNamespace(
    url=SimpleNamespace(path="/test"),
    headers={},
    client=SimpleNamespace(host="127.0.0.1"),
)
try:
    auth.get_current_user_role(request, api_key="unconfigured-test-key", bearer=None)
except HTTPException as error:
    assert error.status_code == 401
else:
    raise AssertionError("an unconfigured API key authenticated")

os.environ["BTCOGNITIVE_USER_KEY"] = "explicit-user-test-key"
os.environ["BTCOGNITIVE_ADMIN_KEY"] = "explicit-admin-test-key"
config = importlib.reload(config)
auth = importlib.reload(auth)
assert config.API_KEYS_ENV == {
    "explicit-user-test-key": config.UserRole.USER,
    "explicit-admin-test-key": config.UserRole.ADMIN,
}
assert auth.get_current_user_role(
    request, api_key="explicit-user-test-key", bearer=None
) == config.UserRole.USER
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/notifications/settings", {"email_enabled": False}),
        ("/api/notifications/test", {}),
    ],
)
@pytest.mark.parametrize("credential", ["anonymous", "user"])
def test_notification_mutations_require_admin(
    admin_client,
    user_key,
    monkeypatch,
    path,
    payload,
    credential,
):
    called = []

    def update_settings(settings):
        called.append(("settings", settings))
        return notification_manager.get_settings()

    async def dispatch_alert(alert):
        called.append(("test", alert))
        return {"channels": {}}

    monkeypatch.setattr(notification_manager, "update_settings", update_settings)
    monkeypatch.setattr(notification_manager, "dispatch_alert", dispatch_alert)
    headers = {"X-API-Key": user_key} if credential == "user" else {}

    response = admin_client.post(path, json=payload, headers=headers)

    assert response.status_code == 403
    assert called == []


def test_admin_can_update_notification_settings(admin_client, monkeypatch):
    updated = []

    def update_settings(settings):
        updated.append(settings)
        return {"email_enabled": False}

    monkeypatch.setattr(notification_manager, "update_settings", update_settings)

    response = admin_client.post(
        "/api/notifications/settings",
        json={"email_enabled": False},
        headers={"X-API-Key": "pytest-explicit-admin"},
    )

    assert response.status_code == 200
    assert updated == [{"email_enabled": False}]


def test_admin_can_request_neutral_notification_test(admin_client, monkeypatch):
    dispatched = []

    async def dispatch_alert(alert):
        dispatched.append(alert)
        return {"channels": {"email": {"status": "disabled"}}}

    monkeypatch.setattr(notification_manager, "dispatch_alert", dispatch_alert)

    response = admin_client.post(
        "/api/notifications/test",
        headers={"X-API-Key": "pytest-explicit-admin"},
    )

    assert response.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0]["is_test"] is True


def test_public_notification_settings_remain_redacted(admin_client, monkeypatch):
    secrets = {
        "smtp_password": "smtp-test-secret",
        "telegram_bot_token": "telegram-test-secret",
        "webhook_url": "https://hooks.example.test/path?token=test-secret",
    }
    for name, value in secrets.items():
        monkeypatch.setitem(notification_manager.settings, name, value)

    response = admin_client.get("/api/notifications/settings")

    assert response.status_code == 200
    settings = response.json()
    for name, secret in secrets.items():
        assert name not in settings
        assert secret not in response.text
        assert settings[f"{name}_configured"] is True


@pytest.mark.parametrize(
    "webhook_url",
    [
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.8/hook",
        "https://192.168.1.8/hook",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::1]/hook",
        "http://hooks.example.test/hook",
        "ftp://hooks.example.test/hook",
    ],
)
def test_admin_webhook_settings_reject_local_private_or_non_https_urls(
    admin_client,
    monkeypatch,
    webhook_url,
):
    previous_url = notification_manager.settings.get("webhook_url")
    response = admin_client.post(
        "/api/notifications/settings",
        json={"webhook_url": webhook_url},
        headers={"X-API-Key": "pytest-explicit-admin"},
    )

    assert response.status_code == 422
    assert notification_manager.settings.get("webhook_url") == previous_url
