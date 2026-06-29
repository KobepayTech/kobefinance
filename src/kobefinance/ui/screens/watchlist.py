"""Watchlist: an editable, persisted list of instruments with live quotes."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ...services.settings import Settings
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..formatting import arrow, fmt_instrument_price, fmt_pct
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 1500


class WatchlistScreen(Screen):
    """User-curated quote board, persisted in settings."""

    screen_id = "watchlist"
    title = "Watchlist"

    def __init__(self, provider, settings: Settings | None = None) -> None:
        super().__init__()
        self._provider = provider
        self._settings = settings or Settings()
        known = set(provider.symbols())
        stored = self._settings.get("watchlist.uids", None)
        if isinstance(stored, list) and stored:
            self._uids = [u for u in stored if u in known]
        else:
            self._uids = [u for u in DASHBOARD_WATCHLIST if u in known]

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        self.root.addWidget(self._build_controls())
        panel = Panel("My Watchlist")
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Symbol", "Name", "Exch", "Last", "Chg %"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        panel.add(self._table, stretch=1)
        self.root.addWidget(panel, stretch=1)
        self._rebuild_rows()

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)
        self._picker = QComboBox()
        self._picker.setMinimumWidth(220)
        for inst in self._provider.instruments():
            self._picker.addItem(f"{inst.symbol} · {inst.exchange} — {inst.name}", inst.uid)
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        remove = QPushButton("Remove selected")
        remove.clicked.connect(self._remove)
        row.addWidget(self._picker, stretch=1)
        row.addWidget(add)
        row.addWidget(remove)
        return bar

    def _persist(self) -> None:
        self._settings.set("watchlist.uids", list(self._uids))

    def _add(self) -> None:
        uid = self._picker.currentData()
        if uid and uid not in self._uids:
            self._uids.append(uid)
            self._persist()
            self._rebuild_rows()

    def _remove(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._uids):
            del self._uids[row]
            self._persist()
            self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        self._table.setRowCount(len(self._uids))
        self._refresh()

    def _refresh(self) -> None:
        if hasattr(self._provider, "tick"):
            self._provider.tick()
        theme = ACTIVE_THEME
        for r, uid in enumerate(self._uids):
            q = self._provider.quote(uid)
            if q is None:
                continue
            cells = [
                (q.symbol, None, False),
                (q.name, None, False),
                (q.exchange, None, False),
                (fmt_instrument_price(q.price, q.currency, q.kind), None, True),
                (f"{arrow(q.change)} {fmt_pct(q.change_pct)}", theme.signed_color(q.change), True),
            ]
            for c, (text, color, right) in enumerate(cells):
                item = QTableWidgetItem(text)
                if right:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(QColor(color))
                self._table.setItem(r, c, item)

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
