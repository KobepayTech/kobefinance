"""Built-in strategies the bot designer can parameterize and backtest."""

from __future__ import annotations

from .strategy import Context, Strategy, rsi, sma


class SmaCrossStrategy(Strategy):
    """Go long when a fast SMA crosses above a slow SMA; flat/short otherwise."""

    name = "sma_cross"

    def __init__(self, fast: int = 20, slow: int = 50, allow_short: bool = False) -> None:
        super().__init__(fast=fast, slow=slow, allow_short=allow_short)
        self.fast = fast
        self.slow = slow
        self.allow_short = allow_short
        self._fast: list[float | None] = []
        self._slow: list[float | None] = []

    def prepare(self, closes: list[float]) -> None:
        self._fast = sma(closes, self.fast)
        self._slow = sma(closes, self.slow)

    def on_bar(self, ctx: Context) -> None:
        i = ctx.index
        f, s = self._fast[i], self._slow[i]
        if f is None or s is None:
            return
        if f > s:
            ctx.buy()
        elif self.allow_short:
            ctx.sell()
        else:
            ctx.close()


class RsiReversionStrategy(Strategy):
    """Buy when RSI is oversold, exit when it returns to neutral/overbought."""

    name = "rsi_reversion"

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0) -> None:
        super().__init__(period=period, oversold=oversold, overbought=overbought)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self._rsi: list[float | None] = []

    def prepare(self, closes: list[float]) -> None:
        self._rsi = rsi(closes, self.period)

    def on_bar(self, ctx: Context) -> None:
        value = self._rsi[ctx.index]
        if value is None:
            return
        if value <= self.oversold:
            ctx.buy()
        elif value >= self.overbought:
            ctx.close()


# Registry by name, for the designer and tests.
STRATEGIES: dict[str, type[Strategy]] = {
    SmaCrossStrategy.name: SmaCrossStrategy,
    RsiReversionStrategy.name: RsiReversionStrategy,
}
