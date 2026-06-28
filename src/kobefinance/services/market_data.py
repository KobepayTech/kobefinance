"""Market-data providers.

The UI depends only on the :class:`MarketDataProvider` interface, so a live
feed (REST/WebSocket) can be dropped in later without touching any screen.
The bundled :class:`SimulatedProvider` random-walks prices around their seed
so the terminal is fully functional offline and in tests.

Instruments are addressed by ``uid`` (``SYMBOL.EXCHANGE``) so the same ticker
on different exchanges never collides.
"""

from __future__ import annotations

import random
from typing import Protocol

from ..models import Instrument, Quote
from .universe import build_universe


class MarketDataProvider(Protocol):
    """Anything that can return current quotes for a set of instruments."""

    def symbols(self) -> list[str]:
        """Return all instrument uids this provider knows about."""
        ...

    def instruments(self) -> list[Instrument]:
        """Return all known instruments."""
        ...

    def instruments_for(self, exchange: str) -> list[Instrument]:
        """Return instruments listed on *exchange* (by code)."""
        ...

    def quote(self, uid: str) -> Quote | None:
        """Return the latest quote for *uid*, or ``None`` if unknown."""
        ...

    def quotes(self, uids: list[str]) -> list[Quote]:
        """Return latest quotes for the given uids, skipping unknown ones."""
        ...


class SimulatedProvider:
    """Offline provider that random-walks prices around their seed value.

    Each :meth:`tick` nudges every price by a small percentage with gentle
    mean-reversion toward the seed, so values stay realistic over long
    sessions. The previous close is fixed at the seed, so change/percent
    reflect drift from the session open.
    """

    def __init__(
        self,
        universe: list[Instrument] | None = None,
        *,
        volatility: float = 0.0015,
        seed: int | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._volatility = volatility
        self._instruments = list(universe if universe is not None else build_universe())
        self._by_uid: dict[str, Instrument] = {i.uid: i for i in self._instruments}
        self._seed_price = {i.uid: i.seed_price for i in self._instruments}
        self._price = dict(self._seed_price)

    def symbols(self) -> list[str]:
        return list(self._by_uid)

    def instruments(self) -> list[Instrument]:
        return list(self._instruments)

    def instruments_for(self, exchange: str) -> list[Instrument]:
        return [i for i in self._instruments if i.exchange == exchange]

    def tick(self) -> None:
        """Advance every price by one simulated step."""
        for uid, price in self._price.items():
            seed = self._seed_price[uid]
            drift = self._rng.gauss(0.0, self._volatility)
            reversion = (seed - price) / seed * 0.02
            self._price[uid] = max(0.0001, price * (1.0 + drift + reversion))

    def quote(self, uid: str) -> Quote | None:
        inst = self._by_uid.get(uid)
        if inst is None:
            return None
        return Quote(
            symbol=inst.symbol,
            name=inst.name,
            price=round(self._price[uid], 2),
            prev_close=round(inst.seed_price, 2),
            currency=inst.currency,
            exchange=inst.exchange,
        )

    def quotes(self, uids: list[str]) -> list[Quote]:
        out: list[Quote] = []
        for uid in uids:
            q = self.quote(uid)
            if q is not None:
                out.append(q)
        return out
