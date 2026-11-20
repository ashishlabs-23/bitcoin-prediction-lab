"""V32.56: position monitoring must not substitute an invented market quote."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from api import routes_user_positions


@pytest.mark.asyncio
async def test_position_quote_failure_is_explicitly_unavailable(monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr(routes_user_positions, "_fetch_quote", unavailable)
    result = await routes_user_positions._get_current_market_quote(
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(http=None)))
    )

    assert result["status"] == "UNAVAILABLE"
    assert result["price"] is None
    assert result["bid"] is None
    assert result["ask"] is None
    assert result["is_live"] is False
    assert "synthetic" in result["reason"].lower()
