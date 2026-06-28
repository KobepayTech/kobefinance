"""Plain data structures shared across the application."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    """A tradable listing on a specific exchange.

    ``uid`` (``SYMBOL.EXCHANGE``) is globally unique even when the same
    ticker symbol appears on multiple exchanges (e.g. MTN on both the JSE
    and the Uganda Securities Exchange).
    """

    symbol: str
    name: str
    exchange: str  # exchange code, e.g. "JSE"
    currency: str  # ISO 4217 code, e.g. "ZAR"
    seed_price: float

    @property
    def uid(self) -> str:
        return f"{self.symbol}.{self.exchange}"


@dataclass(frozen=True)
class Candle:
    """One OHLCV bar in a price history series."""

    ts: int          # POSIX timestamp (seconds) at the bar's open
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Quote:
    """A point-in-time market quote for a single instrument."""

    symbol: str
    name: str
    price: float
    prev_close: float
    currency: str = "USD"
    exchange: str = ""

    @property
    def uid(self) -> str:
        return f"{self.symbol}.{self.exchange}" if self.exchange else self.symbol

    @property
    def change(self) -> float:
        """Absolute change since the previous close."""
        return self.price - self.prev_close

    @property
    def change_pct(self) -> float:
        """Percentage change since the previous close."""
        if self.prev_close == 0:
            return 0.0
        return (self.change / self.prev_close) * 100.0
