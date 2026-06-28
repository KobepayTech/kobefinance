"""Tests for indicators, the backtest engine, and built-in strategies."""

from __future__ import annotations

from kobefinance.models import Candle
from kobefinance.services.backtest.engine import run_backtest
from kobefinance.services.backtest.library import RsiReversionStrategy, SmaCrossStrategy
from kobefinance.services.backtest.strategy import ema, rsi, sma


def _candles(prices: list[float]) -> list[Candle]:
    return [Candle(1000 + i * 86400, p, p, p, p, 1000.0) for i, p in enumerate(prices)]


def test_sma_warmup_and_value():
    out = sma([1, 2, 3, 4, 5], 3)
    assert out[0] is None and out[1] is None
    assert out[2] == 2.0 and out[4] == 4.0


def test_ema_tracks_series():
    out = ema([10, 10, 10, 10], 3)
    assert out[0] == 10.0 and abs(out[-1] - 10.0) < 1e-9


def test_rsi_bounds_and_trend():
    rising = rsi(list(range(1, 40)), 14)
    assert rising[-1] is not None
    assert rising[-1] > 90  # steadily rising -> high RSI


def test_engine_profits_on_uptrend_with_sma():
    prices = [100 + i for i in range(120)]  # steady uptrend
    result = run_backtest(_candles(prices), SmaCrossStrategy(fast=5, slow=20))
    assert result.metrics["total_return_pct"] > 0
    assert result.metrics["final_equity"] > 10_000
    assert len(result.equity_curve) == len(prices)


def test_engine_metrics_keys_present():
    prices = [100, 101, 99, 102, 98, 103, 97, 104] * 6
    result = run_backtest(_candles(prices), RsiReversionStrategy(period=5))
    for key in ("total_return_pct", "max_drawdown_pct", "sharpe", "num_trades", "win_rate_pct"):
        assert key in result.metrics


def test_engine_handles_no_signals():
    # Slow strategy on too-short series: no trades, equity flat.
    result = run_backtest(_candles([100, 101, 102]), SmaCrossStrategy(fast=20, slow=50))
    assert result.metrics["num_trades"] == 0.0
    assert result.metrics["final_equity"] == 10_000.0
