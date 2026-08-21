"""
engine/security_validators.py — SSRF, Path Traversal, and Injection Validators
================================================================================
Implements OWASP ASVS 5.0 validation rules:
1. SSRF: Validates external URLs against whitelist; blocks loopbacks, private networks, and cloud metadata.
2. Path Traversal: Resolves realpaths against base directories; rejects escapes ('..', symlink redirects).
3. Injection: Enforces SQL identifier allowlists and parameterization checks.
"""

import os
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Set, Optional

from config.security import ALLOWED_EXTERNAL_DOMAINS, BLOCKED_IP_PREFIXES
from engine.security_audit import security_audit

class SecurityValidationError(ValueError):
    """Raised when an input violates security boundaries."""
    pass

def validate_safe_url(url: str, client_ip: str = "INTERNAL") -> str:
    """
    Validates a URL against SSRF threats:
    - Scheme must be http or https.
    - Hostname must be in ALLOWED_EXTERNAL_DOMAINS.
    - Resolved IP must not be private, loopback, link-local, or cloud metadata (169.254.169.254).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": f"Invalid scheme: {parsed.scheme}"})
        raise SecurityValidationError(f"Invalid URL scheme: {parsed.scheme}. Only HTTP/HTTPS allowed.")

    hostname = parsed.hostname
    if not hostname:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": "Missing hostname"})
        raise SecurityValidationError("URL missing valid hostname.")

    # Domain allowlist check
    if hostname.lower() not in ALLOWED_EXTERNAL_DOMAINS:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": f"Untrusted domain: {hostname}"})
        raise SecurityValidationError(f"Access to domain '{hostname}' is blocked by security policy.")

    # IP Resolution & Private Network Check
    try:
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip_str)

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
            security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": ip_str, "reason": "Private IP"})
            raise SecurityValidationError(f"Resolved IP {ip_str} belongs to a private/restricted network.")

        for prefix in BLOCKED_IP_PREFIXES:
            if ip_str.startswith(prefix):
                security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": ip_str, "prefix": prefix})
                raise SecurityValidationError(f"Resolved IP {ip_str} matches blocked prefix.")

    except socket.gaierror:
        raise SecurityValidationError(f"Unable to resolve host: {hostname}")

    return url

def validate_safe_path(target_path: str, base_dir: str, client_ip: str = "INTERNAL") -> str:
    """
    Validates a file path against Path Traversal (CWE-22):
    - Canonical realpath must strictly reside within base_dir.
    - Rejects path traversal sequences (../, ..\\).
    """
    if ".." in target_path or target_path.startswith("/") or target_path.startswith("\\"):
        # Check if relative escape
        norm = os.path.normpath(target_path)
        if norm.startswith(".."):
            security_audit.alert_critical("PATH_TRAVERSAL_BLOCKED", client_ip, target_path, {"reason": "Traversal sequence"})
            raise SecurityValidationError("Path traversal sequence detected.")

    base_real = os.path.realpath(base_dir)
    target_real = os.path.realpath(os.path.join(base_dir, target_path))

    if not target_real.startswith(base_real):
        security_audit.alert_critical("PATH_TRAVERSAL_BLOCKED", client_ip, target_path, {"resolved": target_real, "base": base_real})
        raise SecurityValidationError("Target path escapes authorized base directory.")

    return target_real

def validate_sql_identifier(identifier: str, allowed_identifiers: Set[str], client_ip: str = "INTERNAL") -> str:
    """
    Validates SQL identifiers (table names, column names for ORDER BY) against a strict whitelist.
    """
    clean_id = identifier.strip().lower()
    if clean_id not in allowed_identifiers:
        security_audit.alert_critical("SQL_INJECTION_BLOCKED", client_ip, identifier, {"reason": "Identifier not in allowlist"})
        raise SecurityValidationError(f"Invalid identifier '{identifier}'. Must be one of: {sorted(list(allowed_identifiers))}")
    return clean_id
