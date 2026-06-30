"""Tests for portfolio snapshot and risk metrics."""

from __future__ import annotations

from kobefinance.models import Instrument
from kobefinance.services.market_data import SimulatedProvider
from kobefinance.services.portfolio import build_snapshot
from kobefinance.services.trading.broker import OrderRequest, Side
from kobefinance.services.trading.paper_broker import PaperBroker


def _provider() -> SimulatedProvider:
    return SimulatedProvider(
        [
            Instrument("AAPL", "Apple", "NASDAQ", "USD", 200.0),
            Instrument("MSFT", "Microsoft", "NASDAQ", "USD", 400.0),
        ],
        seed=5,
    )


def test_empty_portfolio_snapshot():
    snap = build_snapshot(PaperBroker(_provider()), _provider())
    assert snap.holdings == []
    assert snap.total_value == 0.0
    assert snap.risk == {}


def test_snapshot_holdings_and_weights():
    provider = _provider()
    broker = PaperBroker(provider, starting_cash=1_000_000)
    broker.place_order(OrderRequest("AAPL", Side.BUY, 100))
    broker.place_order(OrderRequest("MSFT", Side.BUY, 50))
    snap = build_snapshot(broker, provider)

    assert {h.symbol for h in snap.holdings} == {"AAPL", "MSFT"}
    assert snap.total_value > 0
    assert abs(sum(h.weight_pct for h in snap.holdings) - 100.0) < 0.5
    # Sorted by market value descending.
    assert snap.holdings[0].market_value >= snap.holdings[1].market_value


def test_snapshot_risk_metrics_present():
    provider = _provider()
    broker = PaperBroker(provider, starting_cash=1_000_000)
    broker.place_order(OrderRequest("AAPL", Side.BUY, 100))
    snap = build_snapshot(broker, provider, range_key="6M")
    for key in ("annual_vol_pct", "sharpe", "max_drawdown_pct", "var95_pct", "var95_cash"):
        assert key in snap.risk
