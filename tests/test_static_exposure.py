"""
tests/test_static_exposure.py — Tests for Static File Directory Isolation
==========================================================================
Verifies:
- Sensitive files (.env, .git, market_memory.db) are not inside web static directory.
"""

import os
from config.paths import PROJECT_ROOT

def test_web_static_directory_isolation():
    web_dir = os.path.join(PROJECT_ROOT, "web")
    forbidden_in_web = [".env", ".git", "market_memory.db", "security_audit.log"]

    for fname in forbidden_in_web:
        assert not os.path.exists(os.path.join(web_dir, fname)), f"Sensitive file {fname} found in web static directory!"
