"""
models/symbol_contract.py — Canonical Symbol Vocabulary
=========================================================
Single source of truth for BTC symbol representations across all contexts.

The system uses THREE different symbol formats depending on context:
  - Internal / API / UI:  BTCUSD       (canonical)
  - CCXT (data ingest):   BTC/USD
  - Binance REST/WS:      BTCUSDT

All API responses must use CANONICAL_SYMBOL unless the field is explicitly
named `exchange_symbol` or `binance_symbol`.

DO NOT compare raw exchange symbols directly anywhere in runtime code.
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Canonical Values
# ---------------------------------------------------------------------------

CANONICAL_SYMBOL: str = "BTCUSD"    # API, UI, internal, database records
CCXT_SYMBOL:      str = "BTC/USD"   # ccxt library, data/ingest.py
BINANCE_SYMBOL:   str = "BTCUSDT"   # Binance REST API, WebSocket, http_client.py


# ---------------------------------------------------------------------------
# Symbol Contract Error
# ---------------------------------------------------------------------------

class SymbolContractError(ValueError):
    """Raised when an unrecognized symbol is encountered."""
    pass


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

def to_canonical(exchange_symbol: str) -> str:
    """
    Converts any known exchange symbol to the canonical internal symbol.

    Args:
        exchange_symbol: Raw symbol from exchange (e.g., "BTC/USD", "BTCUSDT").

    Returns:
        Canonical symbol string "BTCUSD".

    Raises:
        SymbolContractError: If the symbol is not recognized.
    """
    normalized = exchange_symbol.strip().upper().replace("-", "").replace("/", "")
    # Accept: BTCUSD, BTCUSDT, BTC/USD, BTC-USD, BTCUSD, etc.
    if normalized in {"BTCUSD", "BTCUSDT"}:
        return CANONICAL_SYMBOL
    raise SymbolContractError(
        f"SYMBOL_CONTRACT_ERROR: Unknown symbol '{exchange_symbol}'. "
        f"Expected one of: BTC/USD, BTCUSDT, BTCUSD."
    )


def to_ccxt(canonical: str = CANONICAL_SYMBOL) -> str:
    """Returns the CCXT-format symbol for use with data/ingest.py."""
    if canonical == CANONICAL_SYMBOL:
        return CCXT_SYMBOL
    raise SymbolContractError(f"No CCXT mapping for symbol '{canonical}'")


def to_binance(canonical: str = CANONICAL_SYMBOL) -> str:
    """Returns the Binance REST/WS format symbol for use with api/http_client.py."""
    if canonical == CANONICAL_SYMBOL:
        return BINANCE_SYMBOL
    raise SymbolContractError(f"No Binance mapping for symbol '{canonical}'")


def is_canonical(symbol: str) -> bool:
    """Returns True if the symbol is already in canonical form."""
    return symbol == CANONICAL_SYMBOL


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Symbol Contract Self-Test")
    errors = []

    tests = [
        ("BTC/USD",  CANONICAL_SYMBOL),
        ("BTCUSDT",  CANONICAL_SYMBOL),
        ("BTCUSD",   CANONICAL_SYMBOL),
        ("btcusdt",  CANONICAL_SYMBOL),
        ("BTC-USD",  CANONICAL_SYMBOL),
    ]
    for inp, exp in tests:
        result = to_canonical(inp)
        status = "PASS" if result == exp else "FAIL"
        if status == "FAIL":
            errors.append(f"to_canonical('{inp}') = '{result}', expected '{exp}'")
        print(f"  {status}: to_canonical('{inp}') -> '{result}'")

    # Adapter tests
    assert to_ccxt() == "BTC/USD",   f"FAIL: to_ccxt() = {to_ccxt()}"
    assert to_binance() == "BTCUSDT", f"FAIL: to_binance() = {to_binance()}"
    print("  PASS: to_ccxt() -> 'BTC/USD'")
    print("  PASS: to_binance() -> 'BTCUSDT'")

    # Unknown raises
    try:
        to_canonical("ETHUSDT")
        errors.append("FAIL: 'ETHUSDT' should raise SymbolContractError")
    except SymbolContractError:
        print("  PASS: 'ETHUSDT' raises SymbolContractError")

    print()
    if errors:
        print(f"FAIL: {len(errors)} errors"); [print(f"  {e}") for e in errors]
    else:
        print("PASS: All symbol contract checks passed.")
