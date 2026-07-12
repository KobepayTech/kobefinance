# Porting Vibe-Trading — feature roadmap

[Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) (MIT) is an LLM-driven
quant-research toolkit. We are **not** copying its code — everything below is a
clean-room reimplementation in KobeFinance's own Python/PySide6 stack, adapted
to our provider, backtester, and bot-designer APIs. This file tracks which of
its capabilities have landed and what remains.

## Status legend
- ✅ done — implemented and covered by tests
- 🚧 in progress
- ⬜ planned

## Feature map

| Vibe-Trading capability | KobeFinance equivalent | Status |
| --- | --- | --- |
| Alpha "zoo" of price factors | `services/factors.py` — momentum, roc, trend, rsi, volatility, mean_reversion, macd, acceleration + `rolling_zscore` | ✅ |
| Factor-driven signal bot | `FactorStrategy` in `backtest/library.py` (z-score entry/exit, long/short) | ✅ |
| NL → strategy synthesis | `llm/bot_designer.py` — factor keyword detection routes to `FactorStrategy`; renders Python + MQL5 | ✅ |
| Backtest engine (returns, Sharpe, drawdown, VaR) | `backtest/engine.py` | ✅ |
| Pluggable LLM backends | `llm/backends.py` (template/ollama/llamacpp/claude) | ✅ |
| Factor combination / weighted multi-factor alpha | composite factor blender (weighted z-score sum) | ⬜ |
| Factor evaluation / IC ranking | information-coefficient + rank-IC report over a universe | ⬜ |
| Portfolio construction from factor scores | cross-sectional ranker → long/short book in `services/portfolio.py` | ⬜ |
| Walk-forward / rolling backtest | rolling-window driver around `run_backtest` | ⬜ |
| LLM research agent (idea → factor → eval loop) | `bot_designer` + eval loop, gated behind a configured backend | ⬜ |
| Data ingestion adapters | already covered by our `HybridProvider` / yfinance layer | ✅ |

## Design notes

- **Close-only factors.** Every factor maps `list[float]` closes to a signal
  series aligned to the input (`None` during warm-up), so they plug straight
  into `Strategy.prepare(closes)` with no OHLC plumbing.
- **Safety.** The bot designer never executes model output. A description is
  parsed deterministically into a vetted `StrategySpec`; only vetted library
  strategies run. The LLM authors *readable* code and rationale for export.
- **z-score entry.** `FactorStrategy` standardizes a factor against a trailing
  window and trades the band: long at `z ≥ entry`, short at `z ≤ -entry` (when
  `allow_short`), flat otherwise.

## Next up

1. Composite multi-factor blender (weighted z-scores) + a `blend` spec kind.
2. Factor IC / rank-IC evaluation report surfaced in the Strategy Lab screen.
3. Cross-sectional ranker feeding the portfolio book.
