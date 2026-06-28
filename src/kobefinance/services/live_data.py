"""Live market data via Yahoo Finance, with a simulated fallback.

Yahoo's free chart endpoint covers US equities, the JSE (``.JO``), the LSE
(``.L``) and crypto, but not most African exchanges (NGX, NSE, EGX, …). So
this module pairs a :class:`YahooLiveProvider` (real quotes for what Yahoo
serves) with the :class:`SimulatedProvider` (everything else) behind a single
:class:`HybridProvider`.

Network fetching happens on a background daemon thread and writes into a
locked cache; the UI thread only ever reads the cache, so quotes are
non-blocking and the app degrades gracefully when offline.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Callable

from ..models import Instrument, Quote
from .exchanges import EXCHANGE_BY_CODE
from .market_data import SimulatedProvider

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"

# Exchanges whose bare ticker is the Yahoo symbol (no suffix).
_BARE_SYMBOL_EXCHANGES = {"NASDAQ", "NYSE", "CRYPTO"}

# Yahoo reports some markets in minor units; map them to the major currency.
_MINOR_UNITS: dict[str, tuple[str, float]] = {
    "ZAc": ("ZAR", 100.0),  # South African cents
    "GBp": ("GBP", 100.0),  # British pence
    "ILA": ("ILS", 100.0),  # Israeli agorot
}


def yahoo_symbol(inst: Instrument) -> str | None:
    """Map an instrument to its Yahoo symbol, or ``None`` if unsupported."""
    exchange = EXCHANGE_BY_CODE.get(inst.exchange)
    if exchange is None:
        return None
    if inst.exchange in _BARE_SYMBOL_EXCHANGES:
        return inst.symbol
    if exchange.yahoo_suffix:
        return inst.symbol + exchange.yahoo_suffix
    return None


def normalize_minor(price: float, prev_close: float, currency: str) -> tuple[float, float, str]:
    """Convert minor-unit prices (cents/pence) to the major currency."""
    if currency in _MINOR_UNITS:
        major, divisor = _MINOR_UNITS[currency]
        return price / divisor, prev_close / divisor, major
    return price, prev_close, currency


def _fetch_chart(yahoo_sym: str, timeout: float = 12.0) -> dict:
    """Fetch and return the Yahoo chart ``meta`` block for one symbol."""
    req = urllib.request.Request(
        _CHART_URL.format(sym=urllib.parse.quote(yahoo_sym)),
        headers={"User-Agent": _UA},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    return payload["chart"]["result"][0]["meta"]


class YahooLiveProvider:
    """Background-refreshed live quotes for Yahoo-supported instruments."""

    def __init__(
        self,
        instruments: list[Instrument],
        *,
        refresh_seconds: float = 15.0,
        request_gap: float = 0.15,
        fetcher: Callable[[str], dict] = _fetch_chart,
    ) -> None:
        self._refresh_seconds = refresh_seconds
        self._request_gap = request_gap
        self._fetch = fetcher

        # uid -> yahoo symbol, only for supported instruments.
        self._live: dict[str, str] = {}
        self._inst: dict[str, Instrument] = {}
        for inst in instruments:
            ys = yahoo_symbol(inst)
            if ys is not None:
                self._live[inst.uid] = ys
                self._inst[inst.uid] = inst

        self._cache: dict[str, Quote] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def is_live(self, uid: str) -> bool:
        return uid in self._live

    def live_uids(self) -> list[str]:
        return list(self._live)

    def quote(self, uid: str) -> Quote | None:
        with self._lock:
            return self._cache.get(uid)

    # -- background refresh ---------------------------------------------------

    def refresh_once(self) -> int:
        """Fetch every live symbol once (blocking). Returns # updated."""
        updated = 0
        for uid, ysym in list(self._live.items()):
            if self._stop.is_set():
                break
            inst = self._inst[uid]
            try:
                meta = self._fetch(ysym)
                price = float(meta["regularMarketPrice"])
                prev = float(meta.get("chartPreviousClose", meta.get("previousClose", price)))
                currency = meta.get("currency", inst.currency)
                price, prev, currency = normalize_minor(price, prev, currency)
                quote = Quote(
                    symbol=inst.symbol,
                    name=inst.name,
                    price=round(price, 2),
                    prev_close=round(prev, 2),
                    currency=currency,
                    exchange=inst.exchange,
                )
                with self._lock:
                    self._cache[uid] = quote
                updated += 1
            except Exception:
                # Leave the stale/absent cache entry; the hybrid layer falls
                # back to the simulator for this uid.
                pass
            if self._request_gap:
                time.sleep(self._request_gap)
        return updated

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.refresh_once()
            self._stop.wait(self._refresh_seconds)

    def start(self) -> None:
        if self._thread is not None or not self._live:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="yahoo-live", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None


class HybridProvider:
    """Serve live quotes where available, simulated quotes everywhere else.

    Implements the same interface as :class:`SimulatedProvider`, so screens
    are unaffected. ``tick`` advances only the simulated series; live values
    arrive from the background thread.
    """

    def __init__(
        self,
        *,
        simulated: SimulatedProvider | None = None,
        live: YahooLiveProvider | None = None,
    ) -> None:
        self._sim = simulated or SimulatedProvider()
        self._live = live or YahooLiveProvider(self._sim.instruments())

    # -- universe (delegated to the simulator's full metadata) ----------------

    def symbols(self) -> list[str]:
        return self._sim.symbols()

    def instruments(self) -> list[Instrument]:
        return self._sim.instruments()

    def instruments_for(self, exchange: str) -> list[Instrument]:
        return self._sim.instruments_for(exchange)

    # -- quotes ---------------------------------------------------------------

    def quote(self, uid: str) -> Quote | None:
        if self._live.is_live(uid):
            live_quote = self._live.quote(uid)
            if live_quote is not None:
                return live_quote
        return self._sim.quote(uid)

    def quotes(self, uids: list[str]) -> list[Quote]:
        out: list[Quote] = []
        for uid in uids:
            q = self.quote(uid)
            if q is not None:
                out.append(q)
        return out

    def tick(self) -> None:
        self._sim.tick()

    def is_live(self, uid: str) -> bool:
        return self._live.is_live(uid) and self._live.quote(uid) is not None

    # -- lifecycle ------------------------------------------------------------

    def start_live(self) -> None:
        self._live.start()

    def stop_live(self) -> None:
        self._live.stop()
