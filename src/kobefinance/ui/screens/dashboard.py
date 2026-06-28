"""The dashboard: a live grid of market tiles plus a market-pulse panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...services.market_data import MarketDataProvider
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..formatting import arrow, fmt_pct
from ..widgets.market_tile import MarketTile
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 1500
TILE_COLUMNS = 4


class DashboardScreen(Screen):
    """Market overview.

    A grid of :class:`MarketTile` widgets is refreshed on a timer from the
    injected provider, and a side "Market Pulse" panel ranks the biggest
    movers. The timer only runs while the screen is visible.
    """

    screen_id = "dashboard"
    title = "Dashboard"

    def __init__(
        self, provider: MarketDataProvider, watchlist: list[str] | None = None
    ) -> None:
        super().__init__()
        self._provider = provider
        # Keep only uids the provider actually knows about.
        known = set(provider.symbols())
        self._watchlist = [
            uid for uid in (watchlist or DASHBOARD_WATCHLIST) if uid in known
        ]
        self._tiles: dict[str, MarketTile] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        self.root.addWidget(self._build_header())

        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._build_grid_panel(), stretch=3)
        content.addWidget(self._build_pulse_panel(), stretch=1)
        self.root.addLayout(content, stretch=1)

        self._refresh()

    # -- construction helpers -------------------------------------------------

    def _build_header(self) -> QWidget:
        theme = ACTIVE_THEME
        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(2, 0, 2, 0)

        title = QLabel("MARKET OVERVIEW")
        title.setStyleSheet(
            f"color:{theme.text_primary}; font-size:16px; font-weight:700; letter-spacing:1px;"
        )
        self._clock = QLabel()
        self._clock.setStyleSheet(
            f"color:{theme.text_tertiary}; font-family:{theme.font_mono};"
        )
        row.addWidget(title)
        row.addStretch(1)
        row.addWidget(self._clock)
        return header

    def _build_grid_panel(self) -> Panel:
        panel = Panel("Watchlist")
        host = QWidget()
        self._grid = QGridLayout(host)
        self._grid.setContentsMargins(0, 4, 0, 0)
        self._grid.setHorizontalSpacing(10)
        self._grid.setVerticalSpacing(10)

        for index, quote in enumerate(self._provider.quotes(self._watchlist)):
            tile = MarketTile(quote)
            self._tiles[quote.uid] = tile
            self._grid.addWidget(tile, index // TILE_COLUMNS, index % TILE_COLUMNS)

        panel.add(host)
        panel.add_stretch()
        return panel

    def _build_pulse_panel(self) -> Panel:
        self._pulse = Panel("Market Pulse")
        self._pulse_rows = QVBoxLayout()
        self._pulse_rows.setSpacing(4)
        holder = QWidget()
        holder.setLayout(self._pulse_rows)
        self._pulse.add(holder)
        self._pulse.add_stretch()
        return self._pulse

    # -- refresh --------------------------------------------------------------

    def _refresh(self) -> None:
        if hasattr(self._provider, "tick"):
            self._provider.tick()

        quotes = self._provider.quotes(list(self._tiles))
        for quote in quotes:
            self._tiles[quote.uid].update_quote(quote)

        self._update_pulse(quotes)

        from datetime import datetime

        self._clock.setText(datetime.now().strftime("%H:%M:%S  •  LIVE (SIM)"))

    def _update_pulse(self, quotes: list) -> None:
        theme = ACTIVE_THEME
        # Clear existing rows.
        while self._pulse_rows.count():
            item = self._pulse_rows.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        movers = sorted(quotes, key=lambda q: abs(q.change_pct), reverse=True)[:6]
        for q in movers:
            row = QLabel(
                f"{q.symbol:<8}  {arrow(q.change)} {fmt_pct(q.change_pct)}"
            )
            row.setStyleSheet(
                f"color:{theme.signed_color(q.change)};"
                f"font-family:{theme.font_mono}; font-size:13px;"
            )
            self._pulse_rows.addWidget(row)

    # -- lifecycle ------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
