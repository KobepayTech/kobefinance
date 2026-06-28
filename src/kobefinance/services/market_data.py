"""Market-data providers.

The UI depends only on the :class:`MarketDataProvider` interface, so a live
feed (REST/WebSocket) can be dropped in later without touching any screen.
The bundled :class:`SimulatedProvider` generates a deterministic-ish random
walk so the terminal is fully functional offline and in tests.
"""

from __future__ import annotations

import random
from typing import Protocol

from ..models import Quote

# Default instrument universe: symbol -> (display name, seed price).
DEFAULT_UNIVERSE: dict[str, tuple[str, float]] = {
    "AAPL": ("Apple Inc.", 228.50),
    "MSFT": ("Microsoft Corp.", 462.10),
    "NVDA": ("NVIDIA Corp.", 138.75),
    "GOOGL": ("Alphabet Inc.", 191.20),
    "AMZN": ("Amazon.com Inc.", 219.40),
    "META": ("Meta Platforms", 612.80),
    "TSLA": ("Tesla Inc.", 345.60),
    "SPY": ("S&P 500 ETF", 598.30),
    "QQQ": ("Nasdaq 100 ETF", 524.10),
    "BTC-USD": ("Bitcoin", 96250.00),
    "ETH-USD": ("Ethereum", 3380.00),
    "GLD": ("Gold ETF", 244.70),
}


class MarketDataProvider(Protocol):
    """Anything that can return current quotes for a set of symbols."""

    def symbols(self) -> list[str]:
        """Return the symbols this provider knows about."""
        ...

    def quote(self, symbol: str) -> Quote | None:
        """Return the latest quote for *symbol*, or ``None`` if unknown."""
        ...

    def quotes(self, symbols: list[str]) -> list[Quote]:
        """Return latest quotes for the given symbols, skipping unknown ones."""
        ...


class SimulatedProvider:
    """Offline provider that random-walks prices around their seed value.

    Each :meth:`tick` nudges every price by a small percentage, keeping it
    tethered to the seed so values stay realistic over long sessions. The
    previous close is fixed at the seed, so change/percent reflect drift from
    the session open.
    """

    def __init__(
        self,
        universe: dict[str, tuple[str, float]] | None = None,
        *,
        volatility: float = 0.0015,
        seed: int | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._volatility = volatility
        self._universe = dict(universe or DEFAULT_UNIVERSE)
        self._seed_price = {s: p for s, (_, p) in self._universe.items()}
        self._price = dict(self._seed_price)

    def symbols(self) -> list[str]:
        return list(self._universe)

    def tick(self) -> None:
        """Advance every price by one simulated step."""
        for symbol, price in self._price.items():
            seed = self._seed_price[symbol]
            # Random walk with mean-reversion toward the seed price.
            drift = self._rng.gauss(0.0, self._volatility)
            reversion = (seed - price) / seed * 0.02
            self._price[symbol] = max(0.01, price * (1.0 + drift + reversion))

    def quote(self, symbol: str) -> Quote | None:
        symbol = symbol.upper()
        if symbol not in self._universe:
            return None
        name, _ = self._universe[symbol]
        return Quote(
            symbol=symbol,
            name=name,
            price=round(self._price[symbol], 2),
            prev_close=round(self._seed_price[symbol], 2),
        )

    def quotes(self, symbols: list[str]) -> list[Quote]:
        out: list[Quote] = []
        for symbol in symbols:
            q = self.quote(symbol)
            if q is not None:
                out.append(q)
        return out
