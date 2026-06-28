"""Strategy API + technical indicators for the backtester.

A strategy precomputes indicators in :meth:`Strategy.prepare` and emits one
action per bar in :meth:`Strategy.on_bar` via the :class:`Context`. Indicators
are plain functions returning lists aligned to the input (``None`` during the
warm-up period), so they're easy to test and reuse.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# -- indicators ---------------------------------------------------------------


def sma(values: list[float], period: int) -> list[float | None]:
    """Simple moving average; ``None`` for the first ``period-1`` bars."""
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    """Exponential moving average, seeded with the first value."""
    out: list[float | None] = [None] * len(values)
    if not values or period <= 0:
        return out
    k = 2.0 / (period + 1.0)
    prev = values[0]
    out[0] = prev
    for i in range(1, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Wilder's Relative Strength Index in the range 0–100."""
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = _rsi_from(avg_gain, avg_loss)
    return out


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# -- strategy framework -------------------------------------------------------


@dataclass
class Context:
    """Per-bar interface handed to a strategy.

    The strategy calls exactly one of :meth:`buy` / :meth:`sell` / :meth:`close`
    (or nothing) per bar; the engine reads :attr:`action` afterwards.
    """

    index: int
    price: float
    position: int  # 1 long, -1 short, 0 flat
    action: str | None = field(default=None)

    def buy(self) -> None:
        self.action = "buy"

    def sell(self) -> None:
        self.action = "sell"

    def close(self) -> None:
        self.action = "close"


class Strategy:
    """Base class for backtestable strategies."""

    name: str = "strategy"

    def __init__(self, **params) -> None:
        self.params = params

    def prepare(self, closes: list[float]) -> None:  # noqa: D401 - hook
        """Precompute indicators over the full close series."""

    def on_bar(self, ctx: Context) -> None:  # noqa: D401 - hook
        """Emit an action for the bar at ``ctx.index``."""
