"""Run a backtested strategy live against a broker (paper by default).

A :class:`BotRunner` re-evaluates its strategy on each step over recent
history, derives the position the strategy would hold *now*, and reconciles the
broker to match (go long / short / flat). The :class:`BotManager` steps all
active bots — call it off the UI thread since history fetches can block.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..backtest.strategy import Context, Strategy
from .broker import OrderRequest, Side


def target_position(candles, strategy: Strategy) -> int:
    """Replay *strategy* over *candles*; return the position it would hold (1/0/-1)."""
    closes = [c.close for c in candles]
    strategy.prepare(closes)
    pos = 0
    for i, candle in enumerate(candles):
        ctx = Context(index=i, price=candle.close, position=pos)
        strategy.on_bar(ctx)
        want = {"buy": 1, "sell": -1, "close": 0}.get(ctx.action) if ctx.action else None
        if want is not None:
            pos = want
    return pos


@dataclass
class BotRunner:
    """A single deployed strategy bound to one instrument and broker."""

    name: str
    uid: str
    strategy: Strategy
    quantity: float
    broker: object
    provider: object
    range_key: str = "3M"
    active: bool = True
    last_target: int = 0
    last_action: str = "deployed"
    steps: int = 0

    @property
    def symbol(self) -> str:
        return self.uid.split(".")[0]

    def _current_signed(self) -> float:
        for pos in self.broker.positions():
            if pos.symbol == self.symbol:
                return pos.quantity if pos.side is Side.BUY else -pos.quantity
        return 0.0

    def step(self) -> str | None:
        """Reconcile the broker position to the strategy's current target."""
        if not self.active:
            return None
        candles = self.provider.history(self.uid, self.range_key)
        if not candles:
            return None
        self.steps += 1
        target = target_position(candles, self.strategy)
        self.last_target = target

        cur = self._current_signed()
        cur_sign = (cur > 0) - (cur < 0)
        if target == cur_sign:
            return None  # already aligned

        if cur != 0:
            self.broker.close_position(self.symbol)
        if target == 1:
            self.broker.place_order(OrderRequest(self.symbol, Side.BUY, self.quantity))
            self.last_action = "opened LONG"
        elif target == -1:
            self.broker.place_order(OrderRequest(self.symbol, Side.SELL, self.quantity))
            self.last_action = "opened SHORT"
        else:
            self.last_action = "closed to FLAT"
        return self.last_action

    @property
    def target_label(self) -> str:
        return {1: "LONG", -1: "SHORT", 0: "FLAT"}[self.last_target]


class BotManager:
    """Holds and steps the set of deployed bots."""

    def __init__(self) -> None:
        self._bots: list[BotRunner] = []

    def add(self, bot: BotRunner) -> None:
        self._bots.append(bot)

    def remove(self, bot: BotRunner) -> None:
        if bot in self._bots:
            self._bots.remove(bot)

    def bots(self) -> list[BotRunner]:
        return list(self._bots)

    def step_all(self) -> list[tuple[str, str]]:
        """Step every active bot; return (name, action) for those that traded."""
        actions: list[tuple[str, str]] = []
        for bot in list(self._bots):
            action = bot.step()
            if action:
                actions.append((bot.name, action))
        return actions
