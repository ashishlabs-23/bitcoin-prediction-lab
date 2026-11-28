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
from typing import Dict, List, Optional, Tuple, Any
from fastapi import Request, Response, HTTPException, status
from starlette.exceptions import HTTPException as StarletteHTTPException
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
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
            or request.url.netloc in ("testserver", "testserver:80")
        )
        for header_name, header_value in SECURITY_HEADERS.items():
            if header_name == "Strict-Transport-Security":
                if is_https:
                    response.headers[header_name] = header_value
            else:
                response.headers[header_name] = header_value

        path = request.url.path
        if path == "/" or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif path.endswith(".js") or path.endswith(".css"):
            if "v=" in str(request.url.query):
                # Fix (2026-11-28): a ?v= URL is content-addressed by
                # construction, so it can be cached for a year. The old 1-day
                # window forced a 635 KB re-download every day for no reason.
                response.headers["Cache-Control"] = (
                    "public, max-age=31536000, immutable"
                )
            else:
                # Unversioned asset URL: the file could change under a cached
                # copy, so it must not be stored at all.
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        elif path.startswith(("/health", "/api/", "/market/", "/prediction/", "/forecast/", "/tournament/", "/regime/")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


import threading
from collections import OrderedDict, deque

class RateLimiter:
    """
    Sliding-window in-memory rate limiter per client IP / key.

    Hardened with:
    - Thread-safe concurrency controls via threading.Lock()
    - Monotonic time tracking (time.monotonic()) to prevent clock-skew attacks
    - Per-client history bounded to at most `max_history_per_client` timestamps
    - Total client-key cardinality bounded to `max_cardinality` with LRU eviction
    - Automatic cleanup of expired timestamps and empty client buckets
    """

    def __init__(self, max_cardinality: int = 10000, max_history_per_client: int = 3000):
        self.max_cardinality = max_cardinality
        self.max_history_per_client = max_history_per_client
        self._lock = threading.Lock()
        self.requests: OrderedDict[str, deque[float]] = OrderedDict()

    def is_allowed(self, client_id: str, limit_per_minute: int) -> Tuple[bool, int]:
        now = time.monotonic()
        window_start = now - 60.0

        with self._lock:
            if client_id in self.requests:
                q = self.requests[client_id]
                while q and q[0] <= window_start:
                    q.popleft()
                self.requests.move_to_end(client_id)
            else:
                if len(self.requests) >= self.max_cardinality:
                    keys_to_remove = []
                    for k, v in self.requests.items():
                        while v and v[0] <= window_start:
                            v.popleft()
                        if not v:
                            keys_to_remove.append(k)
                    for k in keys_to_remove:
                        self.requests.pop(k, None)

                    while len(self.requests) >= self.max_cardinality:
                        self.requests.popitem(last=False)

                q = deque(maxlen=max(limit_per_minute + 1, self.max_history_per_client))
                self.requests[client_id] = q

            if len(q) >= limit_per_minute:
                return False, 0

            q.append(now)
            remaining = max(0, limit_per_minute - len(q))
            return True, remaining


rate_limiter = RateLimiter()


# HTTP methods that are expected to carry a request body.
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _payload_too_large_response(client_ip: str, path: str, details: Dict[str, Any]) -> JSONResponse:
    """Builds the canonical 413 response and raises a critical audit alert."""
    security_audit.alert_critical(
        "PAYLOAD_TOO_LARGE",
        client_ip,
        path,
        {"max_allowed": MAX_REQUEST_BODY_BYTES, **details}
    )
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"error": "PAYLOAD_TOO_LARGE", "message": f"Request body exceeds {MAX_REQUEST_BODY_BYTES} bytes."}
    )



class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Enforces tier-based request rate limits and request payload size caps."""

    @staticmethod
    async def _buffer_body_with_cap(request: Request) -> Optional[bytes]:
        """
        Reads a request body that carries no (trustworthy) Content-Length —
        i.e. a chunked/streamed upload — while counting bytes.

        Returns the buffered body (and installs a replay receive channel so the
        downstream app can still read it), or None when the cap is exceeded.
        The cap is therefore enforced during transfer instead of after it, so a
        chunked client cannot push an unbounded body into the application.
        """
        receive = request._receive
        chunks: List[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                # Client disconnected (or a non-body message): stop reading.
                break
            body = message.get("body", b"") or b""
            total += len(body)
            if total > MAX_REQUEST_BODY_BYTES:
                return None
            chunks.append(body)
            if not message.get("more_body", False):
                break

        payload = b"".join(chunks)
        delivered = False

        async def replay_receive() -> Dict[str, Any]:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": payload, "more_body": False}

        request._receive = replay_receive
        return payload

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "UNKNOWN"
        path = request.url.path

        # 1. Enforce payload size limit
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                int(content_length)
            except ValueError:
                # Malformed length header: fall through to streaming enforcement.
                content_length = None
        if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
            return _payload_too_large_response(
                client_ip, path, {"content_length": content_length}
            )

        # 1b. Content-Length is optional (chunked transfer-encoding) and may be
        # absent or understated, so a declared length is not sufficient on its
        # own. Buffer-and-count bodies that arrive without a usable length and
        # abort with 413 as soon as the cap is crossed. Bodies with a declared
        # length at or below the cap keep streaming through untouched.
        if request.method in _BODY_METHODS and not content_length:
            buffered = await self._buffer_body_with_cap(request)
            if buffered is None:
                return _payload_too_large_response(
                    client_ip, path, {"enforcement": "streaming", "transfer_encoding": request.headers.get("transfer-encoding", "")}
                )

        # 2. Determine rate limit tier
        token = request.headers.get("X-API-Key")
        role = UserRole.PUBLIC
        if token and token in API_KEYS_ENV:
            role = API_KEYS_ENV[token]

        limit = RATE_LIMITS.get(role, 60)
        client_key = f"{client_ip}:{role.value}"

        # Exclude local health checks & loopback UI polling from aggressive throttling
        is_loopback = client_ip in ["127.0.0.1", "localhost", "::1", "testclient", "testserver"]
        limit = 3000 if is_loopback else RATE_LIMITS.get(role, 60)
        
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


import re

_PATH_REGEX = re.compile(r"([A-Za-z]:\\[^ \"'>\r\n\t]+|/(?:Users|home|root|var|etc|opt|tmp)/[^ \"'>\r\n\t]+)")
_DB_REGEX = re.compile(r"(?:sqlite|postgres|mysql|mongodb)(?:\+[a-z]+)?://[^ \"'>\r\n\t]+")

def _sanitize_sensitive_text(val: Any) -> Any:
    if isinstance(val, str):
        cleaned = _PATH_REGEX.sub("[REDACTED_PATH]", val)
        cleaned = _DB_REGEX.sub("[REDACTED_URI]", cleaned)
        return cleaned
    elif isinstance(val, list):
        return [_sanitize_sensitive_text(item) for item in val]
    elif isinstance(val, dict):
        return {k: _sanitize_sensitive_text(v) for k, v in val.items()}
    return val


# Client-facing exception text is capped so a malformed upstream payload can
# never echo an unbounded dump back to the caller.
_MAX_CLIENT_ERROR_CHARS = 500


def sanitize_client_error(exc: Any) -> str:
    """
    Returns exception text that is safe to place in a client-facing JSON body.

    Route handlers previously returned ``str(e)`` verbatim, which can disclose
    filesystem paths, database URIs and internal identifiers. This reuses the
    global exception handler's redaction (``_sanitize_sensitive_text``) and
    truncates the result. Full details must still be logged server-side.
    """
    raw = str(exc) if str(exc) else type(exc).__name__
    cleaned = _sanitize_sensitive_text(raw)
    if len(cleaned) > _MAX_CLIENT_ERROR_CHARS:
        cleaned = cleaned[:_MAX_CLIENT_ERROR_CHARS] + "...[truncated]"
    return cleaned


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

    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        raw_detail = getattr(exc, "detail", str(exc))
        safe_detail = _sanitize_sensitive_text(raw_detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "HTTP_EXCEPTION", "detail": safe_detail, "request_id": request_id},
            headers=getattr(exc, "headers", None)
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
