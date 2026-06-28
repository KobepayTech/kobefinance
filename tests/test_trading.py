"""Tests for the paper broker and the (gated) MetaTrader adapter."""

from __future__ import annotations

from kobefinance.models import Instrument
from kobefinance.services.market_data import SimulatedProvider
from kobefinance.services.trading.broker import OrderRequest, OrderType, Side
from kobefinance.services.trading.metatrader import MetaTraderBroker
from kobefinance.services.trading.paper_broker import PaperBroker


def _provider() -> SimulatedProvider:
    return SimulatedProvider(
        [Instrument("EURUSD", "Euro/USD", "FOREX", "USD", 1.10, kind="fx")], seed=1
    )


def test_paper_broker_fills_and_tracks_position():
    broker = PaperBroker(_provider(), starting_cash=10_000)
    res = broker.place_order(OrderRequest("EURUSD", Side.BUY, 1000))
    assert res.ok and res.filled_price > 0
    positions = broker.positions()
    assert len(positions) == 1 and positions[0].symbol == "EURUSD"
    assert positions[0].side is Side.BUY


def test_paper_broker_close_realizes_position():
    broker = PaperBroker(_provider(), starting_cash=10_000)
    broker.place_order(OrderRequest("EURUSD", Side.BUY, 1000))
    res = broker.close_position("EURUSD")
    assert res.ok
    assert broker.positions() == []


def test_paper_broker_rejects_unknown_symbol():
    broker = PaperBroker(_provider())
    res = broker.place_order(OrderRequest("NOPE", Side.BUY, 1))
    assert not res.ok


def test_paper_broker_rejects_limit_orders():
    broker = PaperBroker(_provider())
    res = broker.place_order(
        OrderRequest("EURUSD", Side.BUY, 1, order_type=OrderType.LIMIT, limit_price=1.0)
    )
    assert not res.ok


def test_paper_broker_account_reports_equity():
    broker = PaperBroker(_provider(), starting_cash=5_000)
    acct = broker.account()
    assert acct.balance == 5_000.0
    assert acct.currency == "USD"


def test_metatrader_is_unavailable_here_and_refuses_orders():
    # No MetaTrader5 package on Linux — adapter must report unavailable and not trade.
    mt = MetaTraderBroker()
    assert mt.is_live is True
    assert mt.available is False
    assert not mt.connect().ok
    assert not mt.place_order(OrderRequest("EURUSD", Side.BUY, 1)).ok
