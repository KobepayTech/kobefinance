# KobeFinance Terminal

A native desktop **financial intelligence workspace** built with Python and
Qt (PySide6). Bloomberg-style dark UI, a live market dashboard, and a modular
screen architecture designed to grow into research, portfolio, news, and
AI-assisted analysis.

> **Independent implementation.** This is an original, clean-room codebase. It
> does not copy or include source from any other terminal project — only the
> Python standard library and PySide6 are used. The design (a tokenized theme,
> a screen registry, a provider-abstracted data layer) is our own.

---

## Status

Working foundation:

- **App shell** — command bar, scrolling ticker tape, navigation sidebar,
  status bar, and a lazy screen router.
- **Dashboard** — market-tile grid + "Market Pulse" movers panel, refreshed
  on a timer, mixing global and African listings in local currencies.
- **Markets** — browse every exchange grouped by region; live listings table
  with a per-row live/simulated source indicator.
- **Charts** — price-history line chart (native QtCharts) with 1M/3M/6M/1Y
  ranges, fetched off the UI thread; live history where available, synthetic
  history (anchored to the current price) elsewhere. Type a ticker in the
  command bar to jump straight to its chart.
- **Forex & crypto** — spot FX (majors + African pairs like USD/ZAR, USD/NGN,
  USD/KES) and major cryptocurrencies, as first-class asset classes with
  rate-aware formatting and live Yahoo quotes/history (`EURUSD=X`, `BTC-USD`).
- **Strategy Lab (AI bot designer)** — describe a strategy in plain language;
  it generates readable **Python** (for the built-in backtester) and **MQL5**
  (a MetaTrader Expert Advisor) and runs a backtest with equity curve and
  metrics (return, Sharpe, max drawdown, win rate). Pluggable LLM backends —
  **offline** Ollama / llama.cpp, optional Claude cloud — with a deterministic
  template fallback so it works with no model installed.
- **Trading desk** — broker selector (paper default; MetaTrader 5 where
  available), live account/positions, **market/limit/stop** orders with a
  buying-power check and a working-orders book, and live-order confirmation.
- **Portfolio + risk** — holdings with allocation weights and unrealized P&L,
  plus portfolio risk (annualized volatility, Sharpe, max drawdown, and a
  historical 1-day 95% VaR) from a weighted blend of holdings' return series.
- **AI Chat** — a market analyst grounded in live quotes, backed by the
  configured LLM (offline Ollama/llama.cpp or Claude), with a rule-based
  offline fallback so it answers from live data with no model installed.
- **Settings** — persists the LLM backend/model, paper starting cash &
  leverage, and MT5 connection (the MT5 password is never written to disk).
- **Trading layer** — a `Broker` abstraction with a safe **paper broker**
  (default, with margin/buying-power checks and limit/stop orders) and a
  **MetaTrader 5** adapter for live forex. *(MT5 is Windows-only and needs the
  MT5 terminal + a broker account; live orders only run there. Everything
  defaults to paper trading.)*

### Important caveats

- **"Offline LLM" = a local model runtime, not a model we trained.** Run a GGUF
  model via Ollama or llama.cpp on your machine; the terminal talks to it. With
  no model present, a deterministic template generator keeps the feature usable.
- **The backtest never executes model-generated code.** It runs a *vetted*
  strategy parsed from your description; the LLM only authors code you read and
  export. This is a deliberate safety boundary.
- **Live trading is real money.** The MT5 adapter is gated, defaults to paper,
  and is intended to be used behind explicit per-order confirmation.
- **Global + comprehensive African coverage** — 30+ exchanges (all of Africa
  plus Nasdaq/NYSE/LSE/crypto), each with country, currency, MIC and
  timezone. Quotes are currency-aware (R, ₦, KSh, ₵, ₨, E£, CFA, … with ISO
  fallback).
- **Live data** — `HybridProvider` serves **real Yahoo Finance** quotes for
  US, JSE (`.JO`), LSE (`.L`) and crypto on a background thread, and falls
  back to a deterministic `SimulatedProvider` for exchanges with no free feed
  (NGX, NSE, EGX, …). Runs fully offline with `--simulate`.

Sidebar entries not yet built (Watchlist, Equity Research, Portfolio, News,
AI Chat, Settings) are registered as placeholders on the roadmap.

---

## Architecture

```
src/kobefinance/
├── app.py                # bootstrap: provider + screen registration + Qt loop
├── theme.py              # Theme tokens + generated stylesheet
├── models.py             # Quote and other plain data types
├── services/
│   └── market_data.py    # MarketDataProvider interface + SimulatedProvider
└── ui/
    ├── main_window.py    # shell that wires the pieces together
    ├── command_bar.py    # brand + command/symbol input
    ├── ticker_bar.py     # scrolling quote marquee
    ├── nav_sidebar.py    # screen list
    ├── status_bar.py     # footer
    ├── formatting.py     # price/change formatters
    ├── widgets/          # Panel, MarketTile
    └── screens/          # Screen base + registry, Dashboard, Placeholder
```

Design principles:

- **One source of truth for navigation** — screens self-register in a
  `REGISTRY`; the sidebar and router are built from it.
- **UI never talks to a feed directly** — it depends on the
  `MarketDataProvider` interface, so providers are swappable.
- **No hard-coded colors in widgets** — everything reads from `theme.py`.

---

## Running

Requires Python 3.10+ and a desktop environment (Qt needs a display).

```bash
pip install -e .
kobefinance              # live (Yahoo) where available + simulated elsewhere
kobefinance --simulate   # fully offline, no network
# or:
python -m kobefinance
```

## Testing

The data/model logic is covered by headless tests (no display needed):

```bash
pip install -e ".[dev]"
pytest
```

---

## Roadmap

1. ~~Live data provider (Yahoo) behind `MarketDataProvider`.~~ ✅
2. ~~Price-history charts.~~ ✅
3. More feeds for African exchanges with no free Yahoo coverage (official/paid
   APIs for NGX, NSE, EGX, …).
4. Candlesticks + volume + technical indicators on the chart.
5. Watchlist screen with editable symbols.
6. Portfolio tracking and risk metrics (returns, Sharpe, drawdown, VaR).
7. News aggregation and an AI chat/analysis screen (Claude-backed).
8. Persisted layout and user settings.
