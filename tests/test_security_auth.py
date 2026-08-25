"""
tests/test_security_auth.py — Unit Tests for Authentication & RBAC
==================================================================
Verifies:
- Public requests resolve to UserRole.PUBLIC.
- Valid API keys resolve to respective UserRole (USER, RESEARCH, ADMIN).
- Invalid keys raise HTTP 401 Unauthorized.
- Insufficient roles raise HTTP 403 Forbidden.
"""

import pytest
from fastapi import HTTPException
from config.security import UserRole, API_KEYS_ENV
from api.security_auth import require_role, get_current_user_role

class MockRequest:
    def __init__(self, path="/test", headers=None, host="127.0.0.1"):
        self.url = type("URL", (), {"path": path})()
        self.headers = headers or {}
        self.client = type("Client", (), {"host": host})()

def test_unauthenticated_role_is_public():
    req = MockRequest()
    role = get_current_user_role(req, api_key=None, bearer=None)
    assert role == UserRole.PUBLIC

def test_valid_user_key_authentication():
    user_key = list(API_KEYS_ENV.keys())[0]
    req = MockRequest()
    role = get_current_user_role(req, api_key=user_key, bearer=None)
    assert role in [UserRole.USER, UserRole.RESEARCH, UserRole.ADMIN]

def test_invalid_key_raises_401():
    req = MockRequest()
    with pytest.raises(HTTPException) as exc:
        get_current_user_role(req, api_key="malicious-invalid-key-999", bearer=None)
    assert exc.value.status_code == 401

def test_role_hierarchy_authorization():
    user_verifier = require_role(UserRole.USER)
    admin_verifier = require_role(UserRole.ADMIN)

    req = MockRequest()
    # USER role accessing USER endpoint -> PASS
    assert user_verifier(req, current_role=UserRole.USER) == UserRole.USER
    # ADMIN role accessing USER endpoint -> PASS (inherited)
    assert user_verifier(req, current_role=UserRole.ADMIN) == UserRole.ADMIN

    # USER role accessing ADMIN endpoint -> FAIL (403)
    with pytest.raises(HTTPException) as exc:
        admin_verifier(req, current_role=UserRole.USER)
    assert exc.value.status_code == 403
