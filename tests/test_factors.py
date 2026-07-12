"""Tests for the alpha-factor library and the FactorStrategy backtest wiring."""

from __future__ import annotations

import math

from kobefinance.models import Candle
from kobefinance.services.backtest.engine import run_backtest
from kobefinance.services.backtest.library import STRATEGIES, FactorStrategy
from kobefinance.services.factors import (
    FACTORS,
    acceleration,
    factor_series,
    macd,
    mean_reversion,
    momentum,
    rolling_zscore,
    trend,
    volatility,
)


def _ramp(n: int = 120, start: float = 100.0, step: float = 0.5) -> list[float]:
    return [start + step * i for i in range(n)]


def test_registry_lists_all_factors():
    for name in ("momentum", "roc", "trend", "rsi", "volatility",
                 "mean_reversion", "macd", "acceleration"):
        assert name in FACTORS


def test_series_are_input_aligned():
    closes = _ramp(60)
    for name in FACTORS:
        s = factor_series(name, closes)
        assert len(s) == len(closes)
        # Every factor produces a defined signal once warmed up.
        assert s[-1] is not None


def test_momentum_positive_on_uptrend():
    closes = _ramp(60)
    m = momentum(closes, 20)
    assert m[-1] is not None and m[-1] > 0


def test_momentum_negative_on_downtrend():
    closes = list(reversed(_ramp(60)))
    m = momentum(closes, 20)
    assert m[-1] is not None and m[-1] < 0


def test_trend_positive_above_moving_average():
    closes = _ramp(60)
    t = trend(closes, 20)
    assert t[-1] is not None and t[-1] > 0


def test_volatility_is_nonpositive():
    closes = _ramp(60)
    v = volatility(closes, 20)
    assert v[-1] is not None and v[-1] <= 0


def test_mean_reversion_flags_stretch_below_mean():
    # Sharp drop at the end -> price below its mean -> positive (buy) signal.
    closes = _ramp(40) + [80.0]
    mr = mean_reversion(closes, 20)
    assert mr[-1] is not None and mr[-1] > 0


def test_macd_positive_when_fast_leads():
    closes = _ramp(60)
    m = macd(closes)
    assert m[-1] is not None and m[-1] > 0


def test_acceleration_defined_after_warmup():
    closes = _ramp(60)
    a = acceleration(closes, 10)
    assert a[-1] is not None


def test_rolling_zscore_standardizes():
    series = [float(i) for i in range(100)]
    z = rolling_zscore(series, 30)
    assert z[-1] is not None
    assert not math.isnan(z[-1])


def test_factor_series_unknown_name_returns_nones():
    s = factor_series("does_not_exist", _ramp(10))
    assert s == [None] * 10


def test_factor_series_lookback_override_changes_result():
    closes = _ramp(80)
    short = factor_series("momentum", closes, 5)
    long = factor_series("momentum", closes, 40)
    assert short[-1] != long[-1]


def test_factor_strategy_registered():
    assert "factor" in STRATEGIES
    assert STRATEGIES["factor"] is FactorStrategy


def test_factor_strategy_backtests_and_reports_metrics():
    prices = _ramp(150)
    candles = [Candle(i, p, p, p, p, 1.0) for i, p in enumerate(prices)]
    strat = FactorStrategy(factor="momentum", lookback=20, zwindow=40, entry=0.5)
    result = run_backtest(candles, strat)
    assert "total_return_pct" in result.metrics


def test_factor_strategy_short_side_produces_action():
    # An oscillating series drives momentum through both z-score entry bands.
    prices = [100.0 + 20.0 * math.sin(i / 8.0) for i in range(240)]
    candles = [Candle(i, p, p, p, p, 1.0) for i, p in enumerate(prices)]
    strat = FactorStrategy(factor="momentum", lookback=15, zwindow=40, entry=0.5,
                           allow_short=True)
    result = run_backtest(candles, strat)
    # A short-enabled momentum bot on a wave should open both longs and shorts.
    sides = {t.side for t in result.trades}
    assert "long" in sides and "short" in sides
