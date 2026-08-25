"""
tests/test_security_headers.py — Tests for Security Headers & Error Masking
===========================================================================
Verifies:
- SecurityHeadersMiddleware injects HSTS, CSP, X-Frame-Options, X-Content-Type-Options.
- Sanitized exception handler generates structured JSON with opaque request_id and no stack traces.
"""

import pytest
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from api.security_middleware import SecurityHeadersMiddleware, sanitized_exception_handler

app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)
app.add_exception_handler(Exception, sanitized_exception_handler)

@app.get("/test-endpoint")
def sample_endpoint():
    return {"status": "ok"}

@app.get("/error-endpoint")
def error_endpoint():
    raise RuntimeError("Sensitive internal database connection error: /var/db/internal.key")

client = TestClient(app, raise_server_exceptions=False)

def test_security_headers_present():
    resp = client.get("/test-endpoint")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in resp.headers
    assert "Content-Security-Policy" in resp.headers

def test_error_sanitization_no_leakage():
    resp = client.get("/error-endpoint")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"] == "INTERNAL_SERVER_ERROR"
    assert "request_id" in data
    # Sensitive internal path/error must NOT be in client response
    assert "/var/db/internal.key" not in resp.text
    assert "RuntimeError" not in resp.text
