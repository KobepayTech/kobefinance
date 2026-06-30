"""Tests for the LLM bot designer (offline/template path) and backend factory."""

from __future__ import annotations

from kobefinance.models import Candle
from kobefinance.services.backtest.engine import run_backtest
from kobefinance.services.backtest.library import RsiReversionStrategy, SmaCrossStrategy
from kobefinance.services.llm.backends import TemplateBackend, make_backend
from kobefinance.services.llm.base import LLMConfig
from kobefinance.services.llm.bot_designer import build_strategy, design, parse_spec


def test_parse_spec_detects_rsi():
    spec = parse_spec("Buy when RSI 14 is oversold below 30, sell at 70")
    assert spec.kind == "rsi_reversion"
    assert spec.params["period"] == 14.0


def test_parse_spec_detects_sma_crossover_with_periods():
    spec = parse_spec("golden cross: 50 day moving average crosses the 200 day")
    assert spec.kind == "sma_cross"
    assert spec.params["fast"] == 50.0
    assert spec.params["slow"] == 200.0


def test_parse_spec_defaults_to_sma():
    spec = parse_spec("something vague about trends")
    assert spec.kind == "sma_cross"


def test_build_strategy_returns_correct_types():
    assert isinstance(build_strategy(parse_spec("rsi oversold")), RsiReversionStrategy)
    assert isinstance(build_strategy(parse_spec("20/50 sma cross")), SmaCrossStrategy)


def test_design_offline_produces_runnable_strategy_and_code():
    result = design("SMA crossover 10 and 30", TemplateBackend())
    assert "GeneratedBot" in result.python_code
    assert "OnTick" in result.mql5_code  # MQL5 EA
    # The vetted strategy actually backtests.
    prices = [100 + i for i in range(80)]
    candles = [Candle(i, p, p, p, p, 1.0) for i, p in enumerate(prices)]
    bt = run_backtest(candles, result.strategy)
    assert "total_return_pct" in bt.metrics


def test_make_backend_falls_back_to_template_when_unavailable():
    # Ollama almost certainly isn't running in the test env -> template fallback.
    backend = make_backend(LLMConfig(backend="ollama"))
    assert backend.available
    # Claude without an API key also falls back.
    backend2 = make_backend(LLMConfig(backend="claude"))
    assert backend2.available


def test_template_backend_is_offline_and_available():
    b = TemplateBackend()
    assert b.available and b.offline
