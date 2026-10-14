"""
config/security.py — BTCognitive Production Security Configuration
===================================================================
Defines security roles, rate limits, CORS origins, security headers,
SSRF denial policies, and master security invariants aligned with
OWASP ASVS 5.0 and OWASP API Top 10.
"""

import os
from enum import Enum
from typing import List, Dict, Set


def _load_local_env_file() -> None:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.isfile(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_local_env_file()

# ==============================================================================
# 1. MASTER SECURITY INVARIANTS & KILL-SWITCHES (Application Layer)
# ==============================================================================
TRADING_ENABLED: bool = False
PRODUCTION_MODEL_FROZEN: bool = True
AUTO_RETRAINING_ENABLED: bool = False
AUTO_PROMOTION_ENABLED: bool = False
RESEARCH_CAN_WRITE_PRODUCTION: bool = False
PUBLIC_MODEL_WRITE_ACCESS: bool = False
PUBLIC_DATABASE_ACCESS: bool = False
PUBLIC_SHELL_ACCESS: bool = False

# ==============================================================================
# 2. ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================================
class UserRole(str, Enum):
    PUBLIC = "PUBLIC"
    USER = "USER"
    RESEARCH = "RESEARCH"
    ADMIN = "ADMIN"

# Role hierarchy: higher roles inherit permissions of lower roles
ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.PUBLIC: 0,
    UserRole.USER: 1,
    UserRole.RESEARCH: 2,
    UserRole.ADMIN: 3,
}

# API credentials are opt-in. Never ship reusable default keys.
def _build_api_key_roles(configured_keys):
    key_roles = {}
    for key, role in configured_keys:
        if not key:
            continue
        if key in key_roles:
            raise RuntimeError("API keys must be unique across configured roles.")
        key_roles[key] = role
    return key_roles


API_KEYS_ENV = _build_api_key_roles((
    (os.getenv("BTCOGNITIVE_USER_KEY", "").strip(), UserRole.USER),
    (os.getenv("BTCOGNITIVE_RESEARCH_KEY", "").strip(), UserRole.RESEARCH),
    (os.getenv("BTCOGNITIVE_ADMIN_KEY", "").strip(), UserRole.ADMIN),
))

# ==============================================================================
# 3. RATE LIMITS (Requests per minute per IP / Token)
# ==============================================================================
RATE_LIMITS: Dict[UserRole, int] = {
    UserRole.PUBLIC: int(os.getenv("RATE_LIMIT_PUBLIC", "60")),       # 60 req/min
    UserRole.USER: int(os.getenv("RATE_LIMIT_USER", "300")),         # 300 req/min
    UserRole.RESEARCH: int(os.getenv("RATE_LIMIT_RESEARCH", "120")), # 120 req/min
    UserRole.ADMIN: int(os.getenv("RATE_LIMIT_ADMIN", "60")),        # 60 req/min
}

MAX_REQUEST_BODY_BYTES: int = int(os.getenv("MAX_REQUEST_BODY_BYTES", "1048576"))  # 1 MB
MAX_WEBSOCKET_CONNECTIONS_PER_IP: int = int(os.getenv("MAX_WS_PER_IP", "5"))
MAX_WEBSOCKET_MESSAGE_BYTES: int = int(os.getenv("MAX_WS_MSG_BYTES", "65536"))     # 64 KB

# ==============================================================================
# 4. NETWORK & CORS CONFIGURATION
# ==============================================================================
ALLOWED_ORIGINS: List[str] = os.getenv(
    "BTCOGNITIVE_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000"
).split(",")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]

ALLOWED_HOSTS: List[str] = os.getenv(
    "BTCOGNITIVE_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver"
).split(",")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

ALLOWED_WEBHOOK_HOSTS: Set[str] = {
    host.strip().lower().rstrip(".")
    for host in os.getenv("BTCOGNITIVE_WEBHOOK_ALLOWED_HOSTS", "discord.com").split(",")
    if host.strip()
}

# ==============================================================================
# 5. SECURITY HEADERS (OWASP ASVS & API Security Compliant)
# ==============================================================================
SECURITY_HEADERS: Dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss: https:; "
        "img-src 'self' data: https:; "
        "frame-ancestors 'none';"
    )
}

# ==============================================================================
# 6. SSRF ALLOWLIST & DENIED NETWORKS
# ==============================================================================
ALLOWED_EXTERNAL_DOMAINS: Set[str] = {
    "api.binance.com",
    "fapi.binance.com",
    "dapi.binance.com",
    "api.coinbase.com",
    "api.exchange.coinbase.com",
    "api.kraken.com",
    "www.bitstamp.net",
    "api.bybit.com",
    "community-api.coinmetrics.io",
    "api.coinmetrics.io"
}

BLOCKED_IP_PREFIXES: List[str] = [
    "0.", "10.", "127.", "169.254.", "172.16.", "172.17.", "172.18.",
    "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.",
    "172.31.", "192.168.", "::1", "fc00:", "fe80:"
]
