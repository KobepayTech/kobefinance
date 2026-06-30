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


def test_buying_power_rejects_oversized_order():
    broker = PaperBroker(_provider(), starting_cash=10_000, max_leverage=1.0)
    # 100k units at ~1.10 = ~110k notional >> 10k buying power.
    res = broker.place_order(OrderRequest("EURUSD", Side.BUY, 100_000))
    assert not res.ok
    assert "buying power" in res.message.lower()


def test_marketable_limit_order_rests_then_fills_on_poll():
    broker = PaperBroker(_provider(), starting_cash=10_000)
    price = broker._price_for("EURUSD")
    # Limit buy above market is immediately marketable -> fills on poll.
    res = broker.place_order(
        OrderRequest("EURUSD", Side.BUY, 100, order_type=OrderType.LIMIT, limit_price=price * 2)
    )
    assert res.ok and res.working
    assert len(broker.working_orders()) == 1
    filled = broker.poll()
    assert filled and broker.positions()
    assert broker.working_orders() == []


def test_resting_limit_order_stays_until_triggered():
    broker = PaperBroker(_provider(), starting_cash=10_000)
    price = broker._price_for("EURUSD")
    # Limit buy far below market never triggers under a tiny price move.
    broker.place_order(
        OrderRequest("EURUSD", Side.BUY, 100, order_type=OrderType.LIMIT, limit_price=price * 0.01)
    )
    assert broker.poll() == []
    assert len(broker.working_orders()) == 1


def test_cancel_working_order():
    broker = PaperBroker(_provider())
    price = broker._price_for("EURUSD")
    res = broker.place_order(
        OrderRequest("EURUSD", Side.SELL, 1, order_type=OrderType.STOP, limit_price=price * 0.01)
    )
    assert broker.cancel_order(res.order_id).ok
    assert broker.working_orders() == []


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


def test_paper_broker_limit_without_price_is_rejected():
    broker = PaperBroker(_provider())
    res = broker.place_order(
        OrderRequest("EURUSD", Side.BUY, 1, order_type=OrderType.LIMIT, limit_price=None)
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
