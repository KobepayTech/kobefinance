"""Tests for the AI Chat analyst helpers."""

from __future__ import annotations

from kobefinance.models import Instrument
from kobefinance.services.analyst import basic_answer, build_context, find_mentions
from kobefinance.services.market_data import SimulatedProvider


def _provider() -> SimulatedProvider:
    return SimulatedProvider(
        [
            Instrument("AAPL", "Apple", "NASDAQ", "USD", 200.0),
            Instrument("EURUSD", "Euro/USD", "FOREX", "USD", 1.10, kind="fx"),
        ],
        seed=1,
    )


def test_find_mentions_detects_symbols():
    p = _provider()
    assert "AAPL.NASDAQ" in find_mentions(p, "How is AAPL doing today?")
    assert "EURUSD.FOREX" in find_mentions(p, "what's eurusd at")


def test_find_mentions_ignores_unknown_words():
    assert find_mentions(_provider(), "tell me about the weather") == []


def test_build_context_includes_mentioned_quote():
    ctx = build_context(_provider(), "price of AAPL")
    assert "LIVE MARKET DATA" in ctx
    assert "AAPL" in ctx


def test_build_context_falls_back_to_snapshot():
    ctx = build_context(_provider(), "how are markets")
    assert "LIVE MARKET DATA" in ctx  # default movers snapshot


def test_basic_answer_quotes_mentioned_symbol():
    ans = basic_answer(_provider(), "what is AAPL")
    assert "AAPL" in ans
    assert "advice" in ans.lower()  # includes the not-advice caveat
