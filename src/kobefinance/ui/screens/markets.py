"""Markets browser: pick an exchange, see its listings with live prices."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...services.exchanges import EXCHANGE_BY_CODE, REGIONS, exchanges_in_region
from ...services.market_data import MarketDataProvider
from ...theme import ACTIVE_THEME
from ..formatting import arrow, fmt_money, fmt_pct
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 1500
_CODE_ROLE = Qt.ItemDataRole.UserRole


class MarketsScreen(Screen):
    """A two-pane exchange explorer.

    Left: every exchange grouped by region. Right: the selected exchange's
    listings in a live table. The refresh timer runs only while visible.
    """

    screen_id = "markets"
    title = "Markets"

    def __init__(self, provider: MarketDataProvider) -> None:
        super().__init__()
        self._provider = provider
        self._current_exchange: str | None = None
        self._row_uids: list[str] = []

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_tree_panel(), stretch=1)
        body.addWidget(self._build_table_panel(), stretch=3)
        self.root.addLayout(body, stretch=1)

        self._select_first_exchange()

    # -- construction ---------------------------------------------------------

    def _build_tree_panel(self) -> Panel:
        panel = Panel("Exchanges")
        self._tree = QTreeWidget()
        self._tree.setObjectName("NavList")
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(12)

        for region in REGIONS:
            exchanges = exchanges_in_region(region)
            if not exchanges:
                continue
            parent = QTreeWidgetItem([region])
            parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._tree.addTopLevelItem(parent)
            for ex in exchanges:
                child = QTreeWidgetItem([f"{ex.code} · {ex.country}"])
                child.setData(0, _CODE_ROLE, ex.code)
                child.setToolTip(0, ex.name)
                parent.addChild(child)
            parent.setExpanded(region != "Global")

        self._tree.currentItemChanged.connect(self._on_tree_change)
        panel.add(self._tree, stretch=1)
        return panel

    def _build_table_panel(self) -> Panel:
        panel = Panel("Listings")
        theme = ACTIVE_THEME

        self._heading = QLabel("")
        self._heading.setStyleSheet(
            f"color:{theme.text_primary}; font-size:15px; font-weight:700;"
        )
        self._subheading = QLabel("")
        self._subheading.setStyleSheet(f"color:{theme.text_tertiary}; font-size:12px;")
        panel.add(self._heading)
        panel.add(self._subheading)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Symbol", "Company", "Last", "Chg %", "Src"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        panel.add(self._table, stretch=1)
        return panel

    # -- selection ------------------------------------------------------------

    def _select_first_exchange(self) -> None:
        # Pick the first exchange that actually has listings.
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                code = child.data(0, _CODE_ROLE)
                if self._provider.instruments_for(code):
                    self._tree.setCurrentItem(child)
                    return

    def _on_tree_change(self, current: QTreeWidgetItem | None, _previous) -> None:
        if current is None:
            return
        code = current.data(0, _CODE_ROLE)
        if code:
            self._load_exchange(code)

    def _load_exchange(self, code: str) -> None:
        self._current_exchange = code
        ex = EXCHANGE_BY_CODE.get(code)
        instruments = self._provider.instruments_for(code)
        self._row_uids = [i.uid for i in instruments]

        if ex is not None:
            self._heading.setText(ex.name)
            mic = f" · MIC {ex.mic}" if ex.mic else ""
            self._subheading.setText(
                f"{ex.city}, {ex.country} · {ex.currency}{mic} · {len(instruments)} listings"
            )

        self._table.setRowCount(len(instruments))
        for row, inst in enumerate(instruments):
            self._set_text(row, 0, inst.symbol, bold=True)
            self._set_text(row, 1, inst.name)
            self._set_text(row, 2, "", align_right=True)
            self._set_text(row, 3, "", align_right=True)
            self._set_text(row, 4, "", align_right=True)
        self._refresh()

    # -- refresh --------------------------------------------------------------

    def _set_text(
        self,
        row: int,
        col: int,
        text: str,
        *,
        bold: bool = False,
        align_right: bool = False,
        color: str | None = None,
    ) -> None:
        item = self._table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self._table.setItem(row, col, item)
        item.setText(text)
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        if align_right:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if color:
            item.setForeground(QColor(color))

    def _refresh(self) -> None:
        if hasattr(self._provider, "tick"):
            self._provider.tick()
        theme = ACTIVE_THEME
        is_live = getattr(self._provider, "is_live", None)
        for row, uid in enumerate(self._row_uids):
            q = self._provider.quote(uid)
            if q is None:
                continue
            self._set_text(row, 2, fmt_money(q.price, q.currency), align_right=True)
            self._set_text(
                row,
                3,
                f"{arrow(q.change)} {fmt_pct(q.change_pct)}",
                align_right=True,
                color=theme.signed_color(q.change),
            )
            live = bool(is_live and is_live(uid))
            self._set_text(
                row,
                4,
                "● live" if live else "sim",
                align_right=True,
                color=theme.positive if live else theme.text_tertiary,
            )

    # -- lifecycle ------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
