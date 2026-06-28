"""Trading desk: account, live positions, and an order ticket.

Defaults to the safe paper broker. The MetaTrader 5 broker can be selected
where available (Windows + MT5 terminal); live orders require an explicit
confirmation before they're sent.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from ...services.trading.broker import OrderRequest, Side
from ...services.trading.metatrader import MetaTraderBroker
from ...services.trading.paper_broker import PaperBroker
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..formatting import fmt_money
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 1500


class TradingScreen(Screen):
    """Account + positions + order entry against the selected broker."""

    screen_id = "trading"
    title = "Trading"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._paper = PaperBroker(provider)
        self._mt5 = MetaTraderBroker()
        self._broker = self._paper

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        self.root.addWidget(self._build_top())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_positions_panel(), stretch=3)
        body.addWidget(self._build_ticket_panel(), stretch=1)
        self.root.addLayout(body, stretch=1)

    # -- construction ---------------------------------------------------------

    def _build_top(self) -> QWidget:
        theme = ACTIVE_THEME
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(10)

        self._broker_select = QComboBox()
        self._broker_select.addItem("Paper (simulated)", "paper")
        mt_label = "MetaTrader 5" + ("" if self._mt5.available else " — unavailable here")
        self._broker_select.addItem(mt_label, "mt5")
        if not self._mt5.available:
            # Disable the MT5 entry; keep it visible so users see the option.
            self._broker_select.model().item(1).setEnabled(False)
        self._broker_select.currentIndexChanged.connect(self._on_broker_changed)

        self._account_lbl = QLabel("")
        self._account_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._account_lbl.setStyleSheet(
            f"color:{theme.text_secondary}; font-family:{theme.font_mono};"
        )

        row.addWidget(QLabel("Broker"))
        row.addWidget(self._broker_select)
        row.addSpacing(16)
        row.addWidget(self._account_lbl)
        row.addStretch(1)
        return bar

    def _build_positions_panel(self) -> Panel:
        panel = Panel("Open Positions")
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Symbol", "Side", "Qty", "Entry", "Last", "P&L"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 6):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        panel.add(self._table, stretch=1)

        self._close_btn = QPushButton("Close selected position")
        self._close_btn.clicked.connect(self._close_selected)
        panel.add(self._close_btn)
        return panel

    def _build_ticket_panel(self) -> Panel:
        panel = Panel("Order Ticket")
        theme = ACTIVE_THEME

        self._symbol = QComboBox()
        known = {i.uid: i for i in self._provider.instruments()}
        for uid in DASHBOARD_WATCHLIST:
            inst = known.get(uid)
            if inst is not None:
                self._symbol.addItem(f"{inst.symbol} · {inst.exchange}", inst.symbol)
        panel.add(QLabel("Symbol"))
        panel.add(self._symbol)

        self._qty = QDoubleSpinBox()
        self._qty.setRange(0.01, 1_000_000.0)
        self._qty.setDecimals(2)
        self._qty.setValue(1000.0)
        panel.add(QLabel("Quantity"))
        panel.add(self._qty)

        buttons = QWidget()
        brow = QHBoxLayout(buttons)
        brow.setContentsMargins(0, 4, 0, 0)
        self._buy_btn = QPushButton("BUY")
        self._buy_btn.setStyleSheet(
            f"background:{theme.positive}; color:#06210f; font-weight:700; border:none;"
        )
        self._buy_btn.clicked.connect(lambda: self._place(Side.BUY))
        self._sell_btn = QPushButton("SELL")
        self._sell_btn.setStyleSheet(
            f"background:{theme.negative}; color:#2a0707; font-weight:700; border:none;"
        )
        self._sell_btn.clicked.connect(lambda: self._place(Side.SELL))
        brow.addWidget(self._buy_btn)
        brow.addWidget(self._sell_btn)
        panel.add(buttons)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color:{theme.text_tertiary}; font-size:12px;")
        panel.add(self._status)
        panel.add_stretch()
        return panel

    # -- broker selection -----------------------------------------------------

    def _on_broker_changed(self, _index: int) -> None:
        choice = self._broker_select.currentData()
        if choice == "mt5" and self._mt5.available:
            res = self._mt5.connect()
            if res.ok:
                self._broker = self._mt5
                self._status.setText("Connected to MetaTrader 5.")
            else:
                self._status.setText(f"MT5: {res.message}")
                self._broker_select.setCurrentIndex(0)
        else:
            self._broker = self._paper
        self._refresh()

    # -- orders ---------------------------------------------------------------

    def _place(self, side: Side) -> None:
        symbol = self._symbol.currentData()
        qty = self._qty.value()
        if not symbol:
            return
        # Live orders are real money — confirm first.
        if self._broker.is_live:
            confirm = QMessageBox.question(
                self,
                "Confirm live order",
                f"Send a LIVE {side.value.upper()} order for {qty} {symbol} "
                f"via {self._broker.name}?\n\nThis places a real trade.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        result = self._broker.place_order(OrderRequest(symbol=symbol, side=side, quantity=qty))
        verb = "LIVE" if self._broker.is_live else "Paper"
        if result.ok:
            self._status.setText(
                f"{verb} {side.value} {qty} {symbol} filled @ {result.filled_price:g}"
            )
        else:
            self._status.setText(f"Rejected: {result.message}")
        self._refresh()

    def _close_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        result = self._broker.close_position(item.text())
        self._status.setText(result.message)
        self._refresh()

    # -- refresh --------------------------------------------------------------

    def _refresh(self) -> None:
        if hasattr(self._provider, "tick"):
            self._provider.tick()
        theme = ACTIVE_THEME
        account = self._broker.account()
        tag = "● LIVE" if self._broker.is_live else "○ PAPER"
        self._account_lbl.setText(
            f"<b>{self._broker.name}</b> {tag} &nbsp;|&nbsp; "
            f"Balance {fmt_money(account.balance, account.currency)} &nbsp; "
            f"Equity {fmt_money(account.equity, account.currency)}"
        )

        positions = account.positions
        self._table.setRowCount(len(positions))
        for r, pos in enumerate(positions):
            last = self._paper._price_for(pos.symbol) or pos.entry_price
            pnl = pos.unrealized_pnl(last)
            cells = [
                (pos.symbol, None, False),
                (pos.side.value.upper(), None, False),
                (f"{pos.quantity:g}", None, True),
                (f"{pos.entry_price:g}", None, True),
                (f"{last:g}", None, True),
                (f"{pnl:+,.2f}", theme.signed_color(pnl), True),
            ]
            for c, (text, color, right) in enumerate(cells):
                item = QTableWidgetItem(text)
                if right:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(QColor(color))
                self._table.setItem(r, c, item)

    # -- lifecycle ------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
