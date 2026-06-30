"""Tests for the live-data helpers and the hybrid provider (no network)."""

from __future__ import annotations

from kobefinance.models import Candle, Instrument
from kobefinance.services.live_data import (
    HybridProvider,
    YahooLiveProvider,
    normalize_minor,
    yahoo_symbol,
)
from kobefinance.services.market_data import SimulatedProvider


def test_yahoo_symbol_us_is_bare():
    assert yahoo_symbol(Instrument("AAPL", "Apple", "NASDAQ", "USD", 1.0)) == "AAPL"


def test_yahoo_symbol_jse_suffix():
    assert yahoo_symbol(Instrument("NPN", "Naspers", "JSE", "ZAR", 1.0)) == "NPN.JO"


def test_yahoo_symbol_lse_suffix():
    assert yahoo_symbol(Instrument("SHEL", "Shell", "LSE", "GBP", 1.0)) == "SHEL.L"


def test_yahoo_symbol_crypto_is_bare():
    assert yahoo_symbol(Instrument("BTC-USD", "Bitcoin", "CRYPTO", "USD", 1.0)) == "BTC-USD"


def test_yahoo_symbol_unsupported_returns_none():
    # NGX has no Yahoo suffix -> not supported.
    assert yahoo_symbol(Instrument("MTNN", "MTN Nigeria", "NGX", "NGN", 1.0)) is None


def test_normalize_minor_cents_and_pence():
    assert normalize_minor(79953.0, 80000.0, "ZAc") == (799.53, 800.0, "ZAR")
    assert normalize_minor(2898.0, 2900.0, "GBp") == (28.98, 29.0, "GBP")


def test_normalize_minor_passthrough():
    assert normalize_minor(100.0, 99.0, "USD") == (100.0, 99.0, "USD")


def _fake_meta(sym: str) -> dict:
    return {"regularMarketPrice": 200.0, "chartPreviousClose": 190.0, "currency": "USD"}


def test_live_provider_refresh_with_injected_fetcher():
    universe = [
        Instrument("AAPL", "Apple", "NASDAQ", "USD", 100.0),
        Instrument("MTNN", "MTN Nigeria", "NGX", "NGN", 50.0),  # unsupported
    ]
    live = YahooLiveProvider(universe, fetcher=_fake_meta, request_gap=0)
    assert live.live_uids() == ["AAPL.NASDAQ"]  # only supported one
    n = live.refresh_once()
    assert n == 1
    q = live.quote("AAPL.NASDAQ")
    assert q is not None and q.price == 200.0 and q.change == 10.0
    assert live.quote("MTNN.NGX") is None


def test_hybrid_prefers_live_then_falls_back():
    sim = SimulatedProvider(
        [
            Instrument("AAPL", "Apple", "NASDAQ", "USD", 100.0),
            Instrument("MTNN", "MTN Nigeria", "NGX", "NGN", 50.0),
        ],
        seed=1,
    )
    live = YahooLiveProvider(sim.instruments(), fetcher=_fake_meta, request_gap=0)
    hybrid = HybridProvider(simulated=sim, live=live)

    # Before any live refresh, both come from the simulator.
    assert not hybrid.is_live("AAPL.NASDAQ")
    assert hybrid.quote("MTNN.NGX") is not None  # simulated

    live.refresh_once()
    assert hybrid.is_live("AAPL.NASDAQ")
    assert hybrid.quote("AAPL.NASDAQ").price == 200.0  # live overrides sim
    # NGX never live -> still simulated.
    assert not hybrid.is_live("MTNN.NGX")


def test_hybrid_delegates_universe():
    hybrid = HybridProvider()
    assert len(hybrid.symbols()) > 50
    assert hybrid.instruments_for("JSE")


def test_yahoo_symbol_fx_and_crypto():
    fx = Instrument("EURUSD", "Euro / USD", "FOREX", "USD", 1.085, kind="fx")
    crypto = Instrument("BTC-USD", "Bitcoin", "CRYPTO", "USD", 96000.0, kind="crypto")
    assert yahoo_symbol(fx) == "EURUSD=X"
    assert yahoo_symbol(crypto) == "BTC-USD"


def _fake_history(yahoo_sym: str, yahoo_range: str) -> list[Candle]:
    return [Candle(1000 + i, 10, 11, 9, 10 + i, 100) for i in range(5)]


def test_live_history_supported_vs_unsupported():
    universe = [
        Instrument("AAPL", "Apple", "NASDAQ", "USD", 100.0),
        Instrument("MTNN", "MTN Nigeria", "NGX", "NGN", 50.0),
    ]
    live = YahooLiveProvider(universe, history_fetcher=_fake_history, request_gap=0)
    assert len(live.history("AAPL.NASDAQ", "6M")) == 5
    assert live.history("MTNN.NGX", "6M") == []  # unsupported -> empty


def test_hybrid_history_prefers_live_then_synth():
    sim = SimulatedProvider(
        [
            Instrument("AAPL", "Apple", "NASDAQ", "USD", 100.0),
            Instrument("MTNN", "MTN Nigeria", "NGX", "NGN", 50.0),
        ],
        seed=1,
    )
    live = YahooLiveProvider(sim.instruments(), history_fetcher=_fake_history, request_gap=0)
    hybrid = HybridProvider(simulated=sim, live=live)

    # Live-capable -> uses the (injected) live history.
    assert len(hybrid.history("AAPL.NASDAQ", "6M")) == 5
    # Not live-capable -> synthesised series with the requested length.
    synth = hybrid.history("MTNN.NGX", "1M")
    assert len(synth) == 30
