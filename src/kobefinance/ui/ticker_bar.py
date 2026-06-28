"""A horizontally scrolling ticker tape of live quotes."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from ..services.market_data import MarketDataProvider
from ..services.universe import DASHBOARD_WATCHLIST
from ..theme import ACTIVE_THEME
from .formatting import arrow, fmt_money, fmt_pct

SCROLL_MS = 30
REFRESH_MS = 2000
STEP_PX = 1


class TickerBar(QFrame):
    """Marquee of symbol/price/change cells that scrolls right-to-left."""

    def __init__(
        self,
        provider: MarketDataProvider,
        uids: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TickerBar")
        self.setFixedHeight(30)
        self._provider = provider

        self._track = QWidget(self)
        self._row = QHBoxLayout(self._track)
        self._row.setContentsMargins(10, 0, 10, 0)
        self._row.setSpacing(22)
        self._cells: dict[str, QLabel] = {}

        known = set(provider.symbols())
        chosen = [u for u in (uids or DASHBOARD_WATCHLIST) if u in known]
        for uid in chosen:
            cell = QLabel()
            cell.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self._cells[uid] = cell
            self._row.addWidget(cell)
        self._track.adjustSize()

        self._offset = 0
        self._scroll = QTimer(self)
        self._scroll.setInterval(SCROLL_MS)
        self._scroll.timeout.connect(self._advance)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(REFRESH_MS)
        self._refresh_timer.timeout.connect(self._refresh)

        self._refresh()

    def start(self) -> None:
        self._scroll.start()
        self._refresh_timer.start()

    def stop(self) -> None:
        self._scroll.stop()
        self._refresh_timer.stop()

    def _refresh(self) -> None:
        theme = ACTIVE_THEME
        for quote in self._provider.quotes(list(self._cells)):
            color = theme.signed_color(quote.change)
            self._cells[quote.uid].setText(
                f"<span style='color:{theme.text_secondary}'>{quote.symbol}</span> "
                f"<span style='color:{theme.text_primary};font-family:{theme.font_mono}'>"
                f"{fmt_money(quote.price, quote.currency)}</span> "
                f"<span style='color:{color}'>{arrow(quote.change)} {fmt_pct(quote.change_pct)}</span>"
            )
        self._track.adjustSize()

    def _advance(self) -> None:
        width = self._track.width()
        self._offset += STEP_PX
        if self._offset > width:
            self._offset = -self.width()
        self._track.move(-self._offset, 0)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._track.setFixedHeight(self.height())
