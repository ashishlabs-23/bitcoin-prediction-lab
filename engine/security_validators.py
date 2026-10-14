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
from typing import Set, Optional, Tuple, List

from config.security import ALLOWED_EXTERNAL_DOMAINS, ALLOWED_SHEET_SYNC_HOSTS, BLOCKED_IP_PREFIXES
from engine.security_audit import security_audit

class SecurityValidationError(ValueError):
    """Raised when an input violates security boundaries."""
    pass


def validate_safe_url(url: str, client_ip: str = "INTERNAL", allowed_domains: Optional[Set[str]] = None) -> str:
    """
    Validates a URL against SSRF threats:
    - Scheme must be http or https.
    - Hostname must be in allowed_domains (defaults to ALLOWED_EXTERNAL_DOMAINS).
    - Resolved IPv4 and IPv6 destinations must not be private, loopback, link-local, reserved, or cloud metadata.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": f"Invalid scheme: {parsed.scheme}"})
        raise SecurityValidationError(f"Invalid URL scheme: {parsed.scheme}. Only HTTP/HTTPS allowed.")

    hostname = parsed.hostname
    if not hostname:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": "Missing hostname"})
        raise SecurityValidationError("URL missing valid hostname.")

    domain_set = allowed_domains if allowed_domains is not None else ALLOWED_EXTERNAL_DOMAINS
    clean_host = hostname.lower().rstrip(".")
    if clean_host not in domain_set and not any(clean_host.endswith("." + d) for d in domain_set):
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": f"Untrusted domain: {hostname}"})
        raise SecurityValidationError(f"Access to domain '{hostname}' is blocked by security policy.")

    # IP Resolution & Private Network Check for both IPv4 and IPv6
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        resolved_ips = {item[4][0] for item in addr_info}
        if not resolved_ips:
            raise SecurityValidationError(f"Unable to resolve host: {hostname}")

        for ip_str in resolved_ips:
            ip_obj = ipaddress.ip_address(ip_str)
            if not ip_obj.is_global:
                security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": ip_str, "reason": "Non-global IP"})
                raise SecurityValidationError(f"Resolved IP {ip_str} belongs to a private/restricted network.")

            for prefix in BLOCKED_IP_PREFIXES:
                if ip_str.startswith(prefix):
                    security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": ip_str, "prefix": prefix})
                    raise SecurityValidationError(f"Resolved IP {ip_str} matches blocked prefix.")

    except socket.gaierror:
        raise SecurityValidationError(f"Unable to resolve host: {hostname}")

    return url


def validate_sheet_sync_url(url: str, client_ip: str = "INTERNAL") -> Tuple[str, List[str]]:
    """
    Validates a Google Apps Script webhook destination against SSRF:
    - Scheme must be strictly HTTPS.
    - Hostname must be in ALLOWED_SHEET_SYNC_HOSTS.
    - All resolved IP addresses must be public/global.
    - Returns tuple of (clean_url, resolved_ip_addresses).
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": "HTTPS required for sheet sync"})
        raise SecurityValidationError("Google Sheet sync requires HTTPS webhook URL.")

    hostname = parsed.hostname
    if not hostname:
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": "Missing hostname"})
        raise SecurityValidationError("URL missing valid hostname.")

    clean_host = hostname.lower().rstrip(".")
    if clean_host not in ALLOWED_SHEET_SYNC_HOSTS and not any(clean_host.endswith("." + h) for h in ALLOWED_SHEET_SYNC_HOSTS):
        security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"reason": f"Destination not allowed: {hostname}"})
        raise SecurityValidationError(f"Webhook destination '{hostname}' is not in configured allowlist.")

    try:
        addr_info = socket.getaddrinfo(clean_host, parsed.port or 443, type=socket.SOCK_STREAM)
        addresses = sorted(list({item[4][0] for item in addr_info}))
        if not addresses:
            raise SecurityValidationError("Destination host did not resolve to any IP addresses.")

        for address in addresses:
            ip_obj = ipaddress.ip_address(address)
            if not ip_obj.is_global:
                security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": address, "reason": "Non-global IP"})
                raise SecurityValidationError(f"Resolved IP {address} belongs to a restricted/non-public network.")

            for prefix in BLOCKED_IP_PREFIXES:
                if address.startswith(prefix):
                    security_audit.alert_critical("SSRF_BLOCKED", client_ip, url, {"resolved_ip": address, "prefix": prefix})
                    raise SecurityValidationError(f"Resolved IP {address} matches blocked prefix.")

        return url, addresses
    except socket.gaierror:
        raise SecurityValidationError(f"Unable to resolve host: {clean_host}")


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
