"""Broker abstraction shared by the paper broker and live adapters.

Screens and bots depend only on :class:`Broker`, so a paper broker (default,
safe) and a live MetaTrader 5 adapter are interchangeable. Live order
placement always flows through the same method, which makes it easy to gate
behind confirmation and to default everything to paper trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(frozen=True)
class OrderRequest:
    symbol: str           # broker symbol, e.g. "EURUSD"
    side: Side
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    comment: str = ""


@dataclass(frozen=True)
class OrderResult:
    ok: bool
    order_id: str = ""
    filled_price: float = 0.0
    message: str = ""


@dataclass
class Position:
    symbol: str
    side: Side
    quantity: float
    entry_price: float

    def unrealized_pnl(self, price: float) -> float:
        direction = 1.0 if self.side is Side.BUY else -1.0
        return (price - self.entry_price) * self.quantity * direction


@dataclass
class Account:
    currency: str = "USD"
    balance: float = 0.0
    equity: float = 0.0
    positions: list[Position] = field(default_factory=list)


class Broker(Protocol):
    """Anything that can report an account and place/close orders."""

    @property
    def name(self) -> str: ...

    @property
    def is_live(self) -> bool:
        """True only for adapters that route to a real market."""
        ...

    def account(self) -> Account: ...

    def positions(self) -> list[Position]: ...

    def place_order(self, request: OrderRequest) -> OrderResult: ...

    def close_position(self, symbol: str) -> OrderResult: ...
