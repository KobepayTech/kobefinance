"""Tests for the yfinance fundamentals wrapper (no network) and formatting."""

from __future__ import annotations

import kobefinance.services.fundamentals as fund
from kobefinance.services.fundamentals import (
    _num,
    fetch_capsule,
    fetch_fundamentals,
    fetch_history,
    fetch_market_cap,
)
from kobefinance.ui.formatting import fmt_compact


def test_num_drops_bad_values():
    assert _num(None) is None
    assert _num("x") is None
    assert _num(float("nan")) is None
    assert _num("12.5") == 12.5
    assert _num(3) == 3.0


def test_fmt_compact_scales():
    assert fmt_compact(4_167_000_000_000, "USD") == "$4.17T"
    assert fmt_compact(235_000_000_000, "USD") == "$235.00B"
    assert fmt_compact(5_000_000, "USD") == "$5.00M"
    assert fmt_compact(900, "USD") == "$900.00"


def test_fetch_fundamentals_returns_none_on_error(monkeypatch):
    def boom(_sym):
        raise RuntimeError("no network")

    monkeypatch.setattr(fund, "_ticker", boom)
    assert fetch_fundamentals("AAPL") is None


def test_fetch_history_returns_empty_on_error(monkeypatch):
    def boom(_sym):
        raise RuntimeError("no network")

    monkeypatch.setattr(fund, "_ticker", boom)
    assert fetch_history("AAPL") == []


def test_fetch_fundamentals_parses_a_fake_ticker(monkeypatch):
    class _FastInfo(dict):
        pass

    class _FakeTicker:
        fast_info = _FastInfo(market_cap=3.0e12, year_high=260.0, year_low=160.0, currency="USD")

        def get_info(self):
            return {
                "longName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "trailingPE": 34.4,
                "forwardPE": 30.1,
                "trailingEps": 6.5,
                "dividendYield": 0.005,
                "beta": 1.2,
                "longBusinessSummary": "Apple designs phones.",
            }

    monkeypatch.setattr(fund, "_ticker", lambda _sym: _FakeTicker())
    f = fetch_fundamentals("AAPL")
    assert f is not None
    assert f.name == "Apple Inc."
    assert f.market_cap == 3.0e12
    assert f.sector == "Technology"
    assert f.trailing_pe == 34.4
    assert f.year_high == 260.0


def _fake_ticker_with_analysts():
    class _FastInfo(dict):
        pass

    class _FakeTicker:
        fast_info = _FastInfo(market_cap=3.0e12, currency="USD")
        calendar = {"Earnings Date": ["2026-07-30"]}

        def get_info(self):
            return {
                "longName": "Apple Inc.",
                "trailingPE": 34.4,
                "targetMeanPrice": 320.0,
                "targetHighPrice": 400.0,
                "targetLowPrice": 250.0,
                "recommendationKey": "buy",
                "numberOfAnalystOpinions": 42,
            }

    return _FakeTicker()


def test_fetch_fundamentals_parses_analyst_fields(monkeypatch):
    monkeypatch.setattr(fund, "_ticker", lambda _sym: _fake_ticker_with_analysts())
    f = fetch_fundamentals("AAPL")
    assert f.target_mean == 320.0
    assert f.target_high == 400.0
    assert f.recommendation == "buy"
    assert f.num_analysts == 42
    assert f.earnings_date == "2026-07-30"


def test_fetch_market_cap_and_capsule(monkeypatch):
    monkeypatch.setattr(fund, "_ticker", lambda _sym: _fake_ticker_with_analysts())
    assert fetch_market_cap("AAPL") == 3.0e12
    cap, pe = fetch_capsule("AAPL")
    assert cap == 3.0e12 and pe == 34.4


def test_fetch_market_cap_none_on_error(monkeypatch):
    def boom(_sym):
        raise RuntimeError("no network")

    monkeypatch.setattr(fund, "_ticker", boom)
    assert fetch_market_cap("AAPL") is None
