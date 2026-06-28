"""Tests for the data models and the simulated provider."""

from __future__ import annotations

from kobefinance.models import Quote
from kobefinance.services.market_data import DEFAULT_UNIVERSE, SimulatedProvider


def test_quote_change_math():
    q = Quote(symbol="X", name="X Co", price=110.0, prev_close=100.0)
    assert q.change == 10.0
    assert q.change_pct == 10.0


def test_quote_zero_prev_close_is_safe():
    q = Quote(symbol="X", name="X Co", price=5.0, prev_close=0.0)
    assert q.change_pct == 0.0


def test_provider_knows_universe():
    p = SimulatedProvider()
    assert set(p.symbols()) == set(DEFAULT_UNIVERSE)


def test_provider_quote_roundtrip():
    p = SimulatedProvider(seed=42)
    q = p.quote("aapl")  # case-insensitive
    assert q is not None
    assert q.symbol == "AAPL"
    assert q.price > 0


def test_unknown_symbol_returns_none():
    p = SimulatedProvider()
    assert p.quote("NOPE") is None


def test_quotes_skips_unknown():
    p = SimulatedProvider()
    result = p.quotes(["AAPL", "NOPE", "MSFT"])
    assert [q.symbol for q in result] == ["AAPL", "MSFT"]


def test_tick_moves_prices_but_stays_near_seed():
    p = SimulatedProvider(seed=7)
    seed_price = p.quote("AAPL").price
    for _ in range(200):
        p.tick()
    later = p.quote("AAPL").price
    # Mean-reversion keeps it within a sane band of the seed.
    assert 0.5 * seed_price < later < 1.5 * seed_price


def test_tick_is_deterministic_for_seed():
    a = SimulatedProvider(seed=123)
    b = SimulatedProvider(seed=123)
    for _ in range(50):
        a.tick()
        b.tick()
    assert a.quote("MSFT").price == b.quote("MSFT").price
