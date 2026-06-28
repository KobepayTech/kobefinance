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
2. More feeds for African exchanges with no free Yahoo coverage (official/paid
   APIs for NGX, NSE, EGX, …).
3. Price/volume charts with technical indicators.
4. Watchlist screen with editable symbols.
5. Portfolio tracking and risk metrics (returns, Sharpe, drawdown, VaR).
6. News aggregation and an AI chat/analysis screen (Claude-backed).
7. Persisted layout and user settings.
