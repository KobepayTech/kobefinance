"""Company fundamentals and history via the ``yfinance`` library.

yfinance's default ``curl_cffi`` transport doesn't honor this environment's
proxy/CA setup, so we hand it a plain ``requests`` session pointed at the CA
bundle. Everything is lazily imported and defensive: any failure returns
``None``/``[]`` so the Equity Research screen falls back to price-derived stats.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..models import Candle

_session = None  # cached requests.Session


def _ca_bundle() -> str | None:
    for var in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and os.path.exists(path):
            return path
    default = "/root/.ccr/ca-bundle.crt"
    return default if os.path.exists(default) else None


def _get_session():
    """A requests session yfinance can use (proxy + CA aware)."""
    global _session
    if _session is not None:
        return _session
    try:
        import requests
    except Exception:
        return None
    sess = requests.Session()
    bundle = _ca_bundle()
    if bundle:
        sess.verify = bundle
    sess.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    _session = sess
    return sess


def _ticker(yahoo_sym: str):
    import yfinance as yf

    session = _get_session()
    return yf.Ticker(yahoo_sym, session=session) if session else yf.Ticker(yahoo_sym)


@dataclass(frozen=True)
class Fundamentals:
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    currency: str = ""
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    year_high: float | None = None
    year_low: float | None = None
    summary: str = ""


def _num(value) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        return f if f == f else None  # drop NaN
    except (TypeError, ValueError):
        return None


def fetch_fundamentals(yahoo_sym: str) -> Fundamentals | None:
    """Fetch fundamentals for *yahoo_sym* via yfinance, or ``None`` on failure."""
    try:
        ticker = _ticker(yahoo_sym)
    except Exception:
        return None

    market_cap = year_high = year_low = None
    currency = ""
    # fast_info is the most reliable numeric source.
    try:
        fi = ticker.fast_info
        get = fi.get if hasattr(fi, "get") else lambda k, d=None: getattr(fi, k, d)
        market_cap = _num(get("market_cap", get("marketCap")))
        year_high = _num(get("year_high", get("yearHigh")))
        year_low = _num(get("year_low", get("yearLow")))
        currency = get("currency", "") or ""
    except Exception:
        pass

    info: dict = {}
    try:
        info = ticker.get_info() or {}
    except Exception:
        info = {}

    if market_cap is None:
        market_cap = _num(info.get("marketCap"))

    # yfinance (0.2.40+) already reports dividendYield as a percentage number
    # (e.g. 0.38 means 0.38%), so we store it as-is and format with a '%'.
    div = _num(info.get("dividendYield"))

    out = Fundamentals(
        symbol=yahoo_sym,
        name=info.get("longName") or info.get("shortName") or "",
        sector=info.get("sector") or "",
        industry=info.get("industry") or "",
        currency=info.get("currency") or currency or "",
        market_cap=market_cap,
        trailing_pe=_num(info.get("trailingPE")),
        forward_pe=_num(info.get("forwardPE")),
        eps=_num(info.get("trailingEps")),
        dividend_yield=div,
        beta=_num(info.get("beta")),
        year_high=year_high if year_high is not None else _num(info.get("fiftyTwoWeekHigh")),
        year_low=year_low if year_low is not None else _num(info.get("fiftyTwoWeekLow")),
        summary=(info.get("longBusinessSummary") or "")[:600],
    )
    # If we got essentially nothing, treat as a miss.
    if not out.name and out.market_cap is None and not out.summary:
        return None
    return out


def fetch_history(yahoo_sym: str, period: str = "1y", interval: str = "1d") -> list[Candle]:
    """Fetch an OHLCV history via yfinance; ``[]`` on failure."""
    try:
        frame = _ticker(yahoo_sym).history(period=period, interval=interval)
    except Exception:
        return []
    candles: list[Candle] = []
    try:
        for ts, row in frame.iterrows():
            candles.append(
                Candle(
                    ts=int(ts.timestamp()),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
    except Exception:
        return []
    return candles
