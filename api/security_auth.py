"""
api/security_auth.py — Authentication & Role-Based Authorization (RBAC)
========================================================================
Implements OWASP ASVS 5.0 Authentication & Authorization controls:
- Constant-time token verification (secrets.compare_digest).
- RBAC dependencies (PUBLIC, USER, RESEARCH, ADMIN).
- Structured audit logging on AUTH_SUCCESS, AUTH_FAILURE, and AUTHZ_DENIED.
"""

import os
import secrets
import hashlib
from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from config.security import UserRole, ROLE_HIERARCHY, API_KEYS_ENV
from engine.security_audit import security_audit

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def token_fingerprint(token: str) -> str:
    """
    Non-reversible short fingerprint of a presented credential.

    Logs must never contain a prefix (or any other reversible slice) of an API
    token: a 6-character prefix is a search-space reduction that turns the audit
    log into a token oracle. A truncated SHA-256 digest still lets operators
    correlate repeated failed attempts with the same presented token, but it
    cannot be inverted into the token itself.
    """
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:12]

def get_current_user_role(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> UserRole:
    """
    Extracts and authenticates user role via X-API-Key or Bearer token.
    Defaults to UserRole.PUBLIC if unauthenticated.
    """
    client_ip = request.client.host if request.client else "UNKNOWN"
    token = api_key or (bearer.credentials if bearer else None)

    if not token:
        return UserRole.PUBLIC

    # Constant-time comparison against configured keys
    for configured_key, role in API_KEYS_ENV.items():
        if secrets.compare_digest(token, configured_key):
            security_audit.log_event(
                event_type="AUTH_SUCCESS",
                severity="INFO",
                client_ip=client_ip,
                role=role.value,
                path=request.url.path
            )
            return role

    # Failed authentication attempt
    security_audit.log_event(
        event_type="AUTH_FAILURE",
        severity="WARNING",
        client_ip=client_ip,
        path=request.url.path,
        details={
            "provided_token_fingerprint": token_fingerprint(token),
            "provided_token_length": len(token),
        }
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API credentials.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"}
    )

def require_role(min_role: UserRole) -> Callable:
    """
    Dependency factory enforcing minimum required role hierarchy.
    """
    def role_verifier(request: Request, current_role: UserRole = Security(get_current_user_role)) -> UserRole:
        client_ip = request.client.host if request.client else "UNKNOWN"
        min_level = ROLE_HIERARCHY[min_role]
        current_level = ROLE_HIERARCHY[current_role]

        if current_level < min_level:
            security_audit.log_event(
                event_type="AUTHZ_DENIED",
                severity="WARNING",
                client_ip=client_ip,
                role=current_role.value,
                path=request.url.path,
                details={"required_role": min_role.value, "user_role": current_role.value}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {min_role.value}"
            )
        return current_role

    return role_verifier
