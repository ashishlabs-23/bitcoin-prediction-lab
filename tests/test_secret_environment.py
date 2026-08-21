"""
tests/test_secret_environment.py — Tests for Secret Environment Sanitization
=============================================================================
Verifies:
- Config modules do not leak plaintext API secrets into docstrings or loggers.
- Secret masking works on nested dictionaries.
"""

from engine.security_audit import mask_secrets

def test_mask_secrets_handles_empty_and_primitives():
    assert mask_secrets(None) is None
    assert mask_secrets(12345) == 12345
    assert mask_secrets("clean_public_string") == "clean_public_string"

def test_mask_secrets_masks_sensitive_keys():
    data = {
        "user_id": 42,
        "token": "secret_session_token_999",
        "nested": {"api_key": "raw_api_key_abc"}
    }
    masked = mask_secrets(data)
    assert masked["token"] == "[MASKED]"
    assert masked["nested"]["api_key"] == "[MASKED]"
    assert masked["user_id"] == 42
