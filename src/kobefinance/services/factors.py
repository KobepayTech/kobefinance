"""Alpha-factor library — quantitative signals over a price series.

A small, original library of classic price-based factors (momentum, rate of
change, trend, RSI, volatility, mean-reversion, MACD, acceleration), in the
spirit of Vibe-Trading's "Alpha Zoo". Each factor maps a list of closes to a
signal series aligned to the input (``None`` during warm-up). Factors are
close-only so they plug straight into the backtester's ``Strategy.prepare``.
"""

from __future__ import annotations

import math
from typing import Callable

from .backtest.strategy import ema, rsi, sma

Series = list[float | None]


def _returns(closes: list[float]) -> list[float | None]:
    out: Series = [None]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        out.append((closes[i] - prev) / prev if prev else None)
    return out


def momentum(closes: list[float], n: int = 20) -> Series:
    """Total return over the last *n* bars."""
    out: Series = [None] * len(closes)
    for i in range(len(closes)):
        if i >= n and closes[i - n]:
            out[i] = closes[i] / closes[i - n] - 1.0
    return out


def roc(closes: list[float], n: int = 10) -> Series:
    """Rate of change (shorter-horizon momentum)."""
    return momentum(closes, n)


def trend(closes: list[float], n: int = 20) -> Series:
    """Price relative to its SMA: positive above trend, negative below."""
    ma = sma(closes, n)
    return [
        (closes[i] / ma[i] - 1.0) if ma[i] else None for i in range(len(closes))
    ]


def rsi_factor(closes: list[float], n: int = 14) -> Series:
    """RSI recentered to ~[-50, 50] so >0 means bullish momentum."""
    r = rsi(closes, n)
    return [(v - 50.0) if v is not None else None for v in r]


def volatility(closes: list[float], n: int = 20) -> Series:
    """Negative rolling stdev of returns (low vol scores positive)."""
    rets = _returns(closes)
    out: Series = [None] * len(closes)
    for i in range(len(closes)):
        window = [r for r in rets[max(1, i - n + 1): i + 1] if r is not None]
        if len(window) >= max(2, n // 2):
            mean = sum(window) / len(window)
            var = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
            out[i] = -math.sqrt(var)
    return out


def mean_reversion(closes: list[float], n: int = 20) -> Series:
    """Z-score of price vs its SMA, inverted (below-mean scores positive)."""
    ma = sma(closes, n)
    out: Series = [None] * len(closes)
    for i in range(len(closes)):
        if ma[i] is None:
            continue
        window = closes[max(0, i - n + 1): i + 1]
        if len(window) < max(2, n // 2):
            continue
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
        std = math.sqrt(var)
        if std:
            out[i] = -(closes[i] - mean) / std
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26) -> Series:
    """MACD-style fast/slow EMA ratio (>0 when fast EMA leads)."""
    ef, es = ema(closes, fast), ema(closes, slow)
    return [
        (ef[i] / es[i] - 1.0) if (ef[i] and es[i]) else None for i in range(len(closes))
    ]


def acceleration(closes: list[float], n: int = 10) -> Series:
    """Change in momentum — is the trend speeding up or slowing down?"""
    m = momentum(closes, n)
    out: Series = [None] * len(closes)
    for i in range(len(closes)):
        if m[i] is not None and i >= n and m[i - n] is not None:
            out[i] = m[i] - m[i - n]
    return out


# name -> factor function (all take a list of closes)
FACTORS: dict[str, Callable[[list[float]], Series]] = {
    "momentum": momentum,
    "roc": roc,
    "trend": trend,
    "rsi": rsi_factor,
    "volatility": volatility,
    "mean_reversion": mean_reversion,
    "macd": macd,
    "acceleration": acceleration,
}


def rolling_zscore(series: Series, window: int) -> Series:
    """Standardize *series* against a trailing *window* of its own values."""
    out: Series = [None] * len(series)
    for i in range(len(series)):
        if series[i] is None:
            continue
        window_vals = [v for v in series[max(0, i - window + 1): i + 1] if v is not None]
        if len(window_vals) < max(3, window // 3):
            continue
        mean = sum(window_vals) / len(window_vals)
        var = sum((v - mean) ** 2 for v in window_vals) / (len(window_vals) - 1)
        std = math.sqrt(var)
        if std:
            out[i] = (series[i] - mean) / std
    return out


def factor_series(name: str, closes: list[float], lookback: int | None = None) -> Series:
    """Compute a named factor's signal series (``None``-filled if unknown).

    When *lookback* is given it overrides the factor's default horizon for the
    factors that take an ``n`` window (all except ``macd``, which is tuned by
    its fast/slow pair).
    """
    fn = FACTORS.get(name)
    if fn is None:
        return [None] * len(closes)
    if lookback is not None and name != "macd":
        return fn(closes, lookback)  # type: ignore[call-arg]
    return fn(closes)
