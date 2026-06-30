"""Tests for the live bot runner and manager."""

from __future__ import annotations

from kobefinance.models import Candle, Instrument
from kobefinance.services.backtest.library import SmaCrossStrategy
from kobefinance.services.market_data import SimulatedProvider
from kobefinance.services.trading.bot_runner import BotManager, BotRunner, target_position
from kobefinance.services.trading.paper_broker import PaperBroker


def _candles(prices: list[float]) -> list[Candle]:
    return [Candle(1000 + i * 86400, p, p, p, p, 1.0) for i, p in enumerate(prices)]


def test_target_position_long_on_uptrend():
    candles = _candles([100 + i for i in range(80)])
    assert target_position(candles, SmaCrossStrategy(fast=5, slow=20)) == 1


def test_target_position_flat_when_insufficient_history():
    candles = _candles([100, 101, 102])
    assert target_position(candles, SmaCrossStrategy(fast=20, slow=50)) == 0


def _provider_with_uptrend() -> SimulatedProvider:
    provider = SimulatedProvider(
        [Instrument("AAA", "Alpha", "NASDAQ", "USD", 100.0)], seed=1
    )
    uptrend = _candles([100 + i for i in range(80)])
    provider.history = lambda uid, range_key="3M": uptrend  # type: ignore[assignment]
    return provider


def test_bot_runner_opens_long_then_holds():
    provider = _provider_with_uptrend()
    broker = PaperBroker(provider, starting_cash=1_000_000)
    bot = BotRunner("t", "AAA.NASDAQ", SmaCrossStrategy(fast=5, slow=20), 10, broker, provider)

    action = bot.step()
    assert action == "opened LONG"
    assert bot.last_target == 1
    assert any(p.symbol == "AAA" for p in broker.positions())

    # Already aligned -> no further action.
    assert bot.step() is None


def test_bot_manager_steps_all():
    provider = _provider_with_uptrend()
    broker = PaperBroker(provider, starting_cash=1_000_000)
    mgr = BotManager()
    bot = BotRunner("t", "AAA.NASDAQ", SmaCrossStrategy(fast=5, slow=20), 10, broker, provider)
    mgr.add(bot)
    actions = mgr.step_all()
    assert actions == [("t", "opened LONG")]
    assert bot in mgr.bots()
    mgr.remove(bot)
    assert bot not in mgr.bots()


def test_inactive_bot_does_not_trade():
    provider = _provider_with_uptrend()
    broker = PaperBroker(provider, starting_cash=1_000_000)
    bot = BotRunner("t", "AAA.NASDAQ", SmaCrossStrategy(fast=5, slow=20), 10, broker, provider)
    bot.active = False
    assert bot.step() is None
    assert broker.positions() == []
