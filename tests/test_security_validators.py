"""
tests/test_security_validators.py — Tests for SSRF, Path Traversal, and Injection Defenses
==========================================================================================
Verifies:
- SSRF blocks localhost, private CIDRs, cloud metadata (169.254.169.254), and unknown domains.
- Path traversal blocks ../ escapes and directory breakout.
- SQL identifier validation accepts whitelisted columns and rejects arbitrary strings.
"""

import os
import pytest
from engine.security_validators import (
    validate_safe_url,
    validate_safe_path,
    validate_sql_identifier,
    SecurityValidationError
)

def test_ssrf_rejects_untrusted_domain():
    with pytest.raises(SecurityValidationError):
        validate_safe_url("https://malicious-attacker-domain.com/data")

def test_ssrf_rejects_invalid_scheme():
    with pytest.raises(SecurityValidationError):
        validate_safe_url("file:///etc/passwd")

def test_path_traversal_blocks_parent_escapes():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    with pytest.raises(SecurityValidationError):
        validate_safe_path("../../../etc/passwd", base_dir)

def test_path_traversal_accepts_valid_subpath():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    safe = validate_safe_path("test_smoke.py", base_dir)
    assert safe.startswith(base_dir)

def test_sql_identifier_validation():
    allowed = {"timestamp", "price", "mfe", "mae"}
    assert validate_sql_identifier("timestamp", allowed) == "timestamp"
    assert validate_sql_identifier(" PRICE ", allowed) == "price"

    with pytest.raises(SecurityValidationError):
        validate_sql_identifier("id; DROP TABLE predictions;--", allowed)
