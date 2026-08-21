"""
api/security_middleware.py — Security Middleware & Request Hardening
====================================================================
Implements OWASP ASVS 5.0 Security Headers, Rate Limiting, Request Body
Size Caps, and Error Sanitization (Zero Stack-Trace Leakage).
"""

import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.security import (
    SECURITY_HEADERS,
    RATE_LIMITS,
    MAX_REQUEST_BODY_BYTES,
    UserRole,
    API_KEYS_ENV
)
from engine.security_audit import security_audit

logger = logging.getLogger("BTCognitiveMiddleware")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects OWASP ASVS compliant security headers into all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        return response


class RateLimiter:
    """Sliding-window in-memory rate limiter per client IP / key."""

    def __init__(self):
        # ip -> list of timestamps
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str, limit_per_minute: int) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0

        # Prune old timestamps
        self.requests[client_id] = [t for t in self.requests[client_id] if t > window_start]

        if len(self.requests[client_id]) >= limit_per_minute:
            return False, 0

        self.requests[client_id].append(now)
        remaining = max(0, limit_per_minute - len(self.requests[client_id]))
        return True, remaining


rate_limiter = RateLimiter()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Enforces tier-based request rate limits and request payload size caps."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "UNKNOWN"
        path = request.url.path

        # 1. Enforce payload size limit
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
            security_audit.alert_critical(
                "PAYLOAD_TOO_LARGE",
                client_ip,
                path,
                {"content_length": content_length, "max_allowed": MAX_REQUEST_BODY_BYTES}
            )
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "PAYLOAD_TOO_LARGE", "message": f"Request body exceeds {MAX_REQUEST_BODY_BYTES} bytes."}
            )

        # 2. Determine rate limit tier
        token = request.headers.get("X-API-Key")
        role = UserRole.PUBLIC
        if token and token in API_KEYS_ENV:
            role = API_KEYS_ENV[token]

        limit = RATE_LIMITS.get(role, 60)
        client_key = f"{client_ip}:{role.value}"

        # Exclude local health checks from aggressive throttling
        if path not in ["/health", "/api/health"]:
            allowed, remaining = rate_limiter.is_allowed(client_key, limit)
            if not allowed:
                security_audit.log_event(
                    event_type="RATE_LIMIT_EXCEEDED",
                    severity="WARNING",
                    client_ip=client_ip,
                    role=role.value,
                    path=path,
                    details={"limit_per_minute": limit}
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "RATE_LIMIT_EXCEEDED", "message": f"Rate limit of {limit} req/min exceeded."},
                    headers={"Retry-After": "60"}
                )

        response: Response = await call_next(request)
        return response


async def sanitized_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler preventing stack traces, internal paths,
    or database connection details from leaking to clients.
    """
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "UNKNOWN"

    # Log full exception details safely in internal audit logger
    security_audit.log_event(
        event_type="UNHANDLED_EXCEPTION",
        severity="ERROR",
        client_ip=client_ip,
        path=request.url.path,
        details={"request_id": request_id, "error_type": type(exc).__name__, "error_msg": str(exc)}
    )

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTP_EXCEPTION", "detail": exc.detail, "request_id": request_id},
            headers=exc.headers
        )

    # Generic sanitized 500 response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal error occurred. Detailed diagnostic reference logged.",
            "request_id": request_id
        }
    )
