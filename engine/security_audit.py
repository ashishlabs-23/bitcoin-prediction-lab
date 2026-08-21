"""
engine/security_audit.py — Security Event Audit Logger & Secret Masking
========================================================================
Implements OWASP ASVS 5.0 Section 16 compliant security logging:
- Logs security lifecycle events (AUTH_SUCCESS, AUTH_FAILURE, AUTHZ_DENIED,
  ADMIN_ACTION, SSRF_BLOCKED, PATH_TRAVERSAL_BLOCKED, PRODUCTION_MODEL_MUTATION_ATTEMPT).
- Masks API keys, JWT tokens, Bearer headers, and database credentials.
- Dispatches high-severity alerts for unauthorized production state changes.
"""

import os
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config.paths import LOGS_DIR

SECURITY_LOG_PATH = os.path.join(LOGS_DIR, "security_audit.log")
os.makedirs(LOGS_DIR, exist_ok=True)

# Regex patterns for masking sensitive data
SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
    re.compile(r"(api[_\-]?key[\"'\s:=]+)[A-Za-z0-9\-\._~\+\/]{6,}", re.IGNORECASE),
    re.compile(r"(secret[\"'\s:=]+)[A-Za-z0-9\-\._~\+\/]{6,}", re.IGNORECASE),
    re.compile(r"(password[\"'\s:=]+)[^\"'\s,]+", re.IGNORECASE),
    re.compile(r"(token[\"'\s:=]+)[A-Za-z0-9\-\._~\+\/]{6,}", re.IGNORECASE),
]

def mask_secrets(data: Any) -> Any:
    """Recursively traverses strings, dicts, or lists and masks sensitive secrets."""
    if isinstance(data, str):
        masked = data
        for pat in SECRET_PATTERNS:
            masked = pat.sub(r"\1[MASKED]", masked)
        return masked
    elif isinstance(data, dict):
        return {k: ("[MASKED]" if any(s in k.lower() for s in ["key", "secret", "password", "token", "auth"]) else mask_secrets(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_secrets(item) for item in data]
    return data

class SecurityAuditLogger:
    """High-integrity security event auditor with structured JSON emission."""

    def __init__(self):
        self.logger = logging.getLogger("BTCognitiveSecurityAudit")
        self.logger.setLevel(logging.INFO)
        
        # File handler for local immutable append-only security log
        handler = logging.FileHandler(SECURITY_LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def log_event(
        self,
        event_type: str,
        severity: str = "INFO",
        client_ip: Optional[str] = None,
        role: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Emits a structured, sanitized security event."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "client_ip": client_ip or "UNKNOWN",
            "role": role or "ANONYMOUS",
            "path": path or "/",
            "details": mask_secrets(details or {})
        }
        
        msg = json.dumps(payload)
        if severity in ["CRITICAL", "HIGH"]:
            self.logger.error(msg)
        elif severity == "WARNING":
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

        return payload

    def alert_critical(self, event_type: str, client_ip: str, path: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Immediate high-severity alert on potential intrusion or mutation attempt."""
        return self.log_event(
            event_type=event_type,
            severity="CRITICAL",
            client_ip=client_ip,
            path=path,
            details=details
        )

security_audit = SecurityAuditLogger()
