"""Tests for the data models and the simulated provider."""

from __future__ import annotations

from kobefinance.models import Instrument, Quote
from kobefinance.services.market_data import SimulatedProvider


def _toy_universe() -> list[Instrument]:
    return [
        Instrument("AAA", "Alpha Co", "JSE", "ZAR", 100.0),
        Instrument("BBB", "Beta Co", "NGX", "NGN", 50.0),
        Instrument("AAA", "Alpha Mirror", "NSE", "KES", 10.0),  # same symbol, diff exchange
    ]


def test_quote_change_math():
    q = Quote("X", "X Co", price=110.0, prev_close=100.0)
    assert q.change == 10.0
    assert q.change_pct == 10.0


def test_quote_zero_prev_close_is_safe():
    q = Quote("X", "X Co", price=5.0, prev_close=0.0)
    assert q.change_pct == 0.0


def test_instrument_uid():
    assert Instrument("NPN", "Naspers", "JSE", "ZAR", 1.0).uid == "NPN.JSE"


def test_same_symbol_different_exchange_does_not_collide():
    p = SimulatedProvider(_toy_universe(), seed=1)
    assert set(p.symbols()) == {"AAA.JSE", "BBB.NGX", "AAA.NSE"}
    assert p.quote("AAA.JSE").currency == "ZAR"
    assert p.quote("AAA.NSE").currency == "KES"


def test_instruments_for_exchange():
    p = SimulatedProvider(_toy_universe())
    jse = p.instruments_for("JSE")
    assert [i.symbol for i in jse] == ["AAA"]


def test_unknown_uid_returns_none():
    p = SimulatedProvider(_toy_universe())
    assert p.quote("NOPE.JSE") is None


def test_quotes_skips_unknown():
    p = SimulatedProvider(_toy_universe())
    result = p.quotes(["AAA.JSE", "NOPE.X", "BBB.NGX"])
    assert [q.uid for q in result] == ["AAA.JSE", "BBB.NGX"]


def test_tick_stays_near_seed():
    p = SimulatedProvider(_toy_universe(), seed=7)
    for _ in range(200):
        p.tick()
    later = p.quote("AAA.JSE").price
    assert 50.0 < later < 150.0


def test_tick_is_deterministic_for_seed():
    a = SimulatedProvider(_toy_universe(), seed=123)
    b = SimulatedProvider(_toy_universe(), seed=123)
    for _ in range(50):
        a.tick()
        b.tick()
    assert a.quote("BBB.NGX").price == b.quote("BBB.NGX").price


def test_default_universe_loads():
    p = SimulatedProvider()
    assert len(p.symbols()) > 50  # comprehensive African + global coverage
