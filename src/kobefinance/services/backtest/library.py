"""Built-in strategies the bot designer can parameterize and backtest."""

from __future__ import annotations

from ..factors import factor_series, rolling_zscore
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


class FactorStrategy(Strategy):
    """Trade a named alpha factor by its rolling z-score.

    The factor's signal series (momentum, macd, mean_reversion, …) is
    standardized against a trailing window; the bot goes long when the z-score
    is convincingly high, short (if allowed) when convincingly low, and flat in
    between. This is the clean-room "Alpha Zoo" style signal-driven bot.
    """

    name = "factor"

    def __init__(
        self,
        factor: str = "momentum",
        lookback: int = 20,
        zwindow: int = 60,
        entry: float = 1.0,
        allow_short: bool = False,
    ) -> None:
        super().__init__(
            factor=factor,
            lookback=lookback,
            zwindow=zwindow,
            entry=entry,
            allow_short=allow_short,
        )
        self.factor = factor
        self.lookback = lookback
        self.zwindow = zwindow
        self.entry = entry
        self.allow_short = allow_short
        self._z: list[float | None] = []

    def prepare(self, closes: list[float]) -> None:
        raw = factor_series(self.factor, closes, self.lookback)
        self._z = rolling_zscore(raw, self.zwindow)

    def on_bar(self, ctx: Context) -> None:
        z = self._z[ctx.index]
        if z is None:
            return
        if z >= self.entry:
            ctx.buy()
        elif z <= -self.entry:
            if self.allow_short:
                ctx.sell()
            else:
                ctx.close()
        else:
            ctx.close()


# Registry by name, for the designer and tests.
STRATEGIES: dict[str, type[Strategy]] = {
    SmaCrossStrategy.name: SmaCrossStrategy,
    RsiReversionStrategy.name: RsiReversionStrategy,
    FactorStrategy.name: FactorStrategy,
}
