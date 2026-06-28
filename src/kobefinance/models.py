"""Plain data structures shared across the application."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    """A point-in-time market quote for a single instrument."""

    symbol: str
    name: str
    price: float
    prev_close: float

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
