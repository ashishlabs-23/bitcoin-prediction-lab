"""
tests/test_symbol_contract.py — Tests for Symbol Contract and Adapters
======================================================================
Verifies that:
- CANONICAL_SYMBOL is 'BTCUSD'.
- to_canonical correctly converts exchange symbols (BTC/USD, BTCUSDT).
- Unknown symbols raise SymbolContractError.
"""

import pytest
from models.symbol_contract import (
    CANONICAL_SYMBOL,
    CCXT_SYMBOL,
    BINANCE_SYMBOL,
    SymbolContractError,
    to_canonical,
    to_ccxt,
    to_binance,
    is_canonical
)

def test_symbol_constants():
    assert CANONICAL_SYMBOL == "BTCUSD"
    assert CCXT_SYMBOL == "BTC/USD"
    assert BINANCE_SYMBOL == "BTCUSDT"

def test_to_canonical_conversion():
    assert to_canonical("BTC/USD") == "BTCUSD"
    assert to_canonical("BTCUSDT") == "BTCUSD"
    assert to_canonical("BTCUSD") == "BTCUSD"
    assert to_canonical("btcusdt") == "BTCUSD"
    assert to_canonical("BTC-USD") == "BTCUSD"

def test_adapter_functions():
    assert to_ccxt() == "BTC/USD"
    assert to_binance() == "BTCUSDT"
    assert is_canonical("BTCUSD") is True
    assert is_canonical("BTC/USD") is False

def test_invalid_symbol_raises_error():
    with pytest.raises(SymbolContractError):
        to_canonical("ETHUSDT")
    with pytest.raises(SymbolContractError):
        to_canonical("SOLUSD")
