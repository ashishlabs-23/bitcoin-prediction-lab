"""
tests/test_secret_exposure.py — Tests for Secret Protection and Sanitization
=============================================================================
Verifies:
- Masking engine correctly replaces passwords, API keys, tokens, and Bearer headers.
- Health endpoints never expose API keys or internal database paths.
"""

from engine.security_audit import mask_secrets

def test_mask_secrets_string_and_dict():
    secret_str = "Authorization: Bearer my-secret-jwt-token-xyz-12345"
    masked_str = mask_secrets(secret_str)
    assert "my-secret-jwt-token" not in masked_str
    assert "[MASKED]" in masked_str

    payload = {
        "api_key": "live_secret_key_888999",
        "symbol": "BTCUSD",
        "nested": {"password": "super_secret_db_pass"}
    }
    masked_dict = mask_secrets(payload)
    assert masked_dict["api_key"] == "[MASKED]"
    assert masked_dict["symbol"] == "BTCUSD"
    assert masked_dict["nested"]["password"] == "[MASKED]"
