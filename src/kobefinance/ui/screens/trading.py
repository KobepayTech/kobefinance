"""Trading desk: account, positions, working orders, and an order ticket.

Defaults to the safe paper broker (shared with the Portfolio screen). The
MetaTrader 5 broker can be selected where available; live orders require an
explicit confirmation. Supports market, limit, and stop orders with a
buying-power check.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
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

from ...services.trading.broker import OrderRequest, OrderType, Side
from ...services.trading.metatrader import MetaTraderBroker
from ...services.trading.paper_broker import PaperBroker
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..formatting import fmt_money
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 1500
BOT_STEP_MS = 6000


class _BotSignals(QObject):
    done = Signal()


class _BotStepTask(QRunnable):
    """Step all deployed bots off the UI thread (history fetches can block)."""

    def __init__(self, manager, signals):
        super().__init__()
        self._manager = manager
        self._signals = signals

    def run(self):
        try:
            self._manager.step_all()
        except Exception:
            pass
        self._signals.done.emit()


class TradingScreen(Screen):
    """Account + positions + working orders + order entry + auto-traders."""

    screen_id = "trading"
    title = "Trading"

    def __init__(self, provider, broker=None, settings=None, bot_manager=None) -> None:
        super().__init__()
        self._provider = provider
        self._paper = broker or PaperBroker(provider)
        self._mt5 = MetaTraderBroker()
        self._broker = self._paper
        self._bot_manager = bot_manager
        self._pool = QThreadPool.globalInstance()
        self._bot_signals = _BotSignals()
        self._bot_signals.done.connect(self._refresh)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._refresh)

        self._bot_timer = QTimer(self)
        self._bot_timer.setInterval(BOT_STEP_MS)
        self._bot_timer.timeout.connect(self._step_bots)

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
        self._table.setHorizontalHeaderLabels(["Symbol", "Side", "Qty", "Entry", "Last", "P&L"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 6):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        panel.add(self._table, stretch=2)

        self._close_btn = QPushButton("Close selected position")
        self._close_btn.clicked.connect(self._close_selected)
        panel.add(self._close_btn)

        self._working_lbl = QLabel("WORKING ORDERS")
        self._working_lbl.setObjectName("PanelTitle")
        panel.add(self._working_lbl)
        self._working = QTableWidget(0, 5)
        self._working.setHorizontalHeaderLabels(["ID", "Symbol", "Type", "Qty", "Price"])
        self._working.verticalHeader().setVisible(False)
        self._working.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._working.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._working.setShowGrid(False)
        self._working.setMaximumHeight(140)
        wheader = self._working.horizontalHeader()
        wheader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        panel.add(self._working)
        self._cancel_btn = QPushButton("Cancel selected order")
        self._cancel_btn.clicked.connect(self._cancel_selected)
        panel.add(self._cancel_btn)
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

        self._otype = QComboBox()
        for label, value in (("Market", OrderType.MARKET), ("Limit", OrderType.LIMIT), ("Stop", OrderType.STOP)):
            self._otype.addItem(label, value)
        self._otype.currentIndexChanged.connect(self._sync_price_enabled)
        panel.add(QLabel("Order type"))
        panel.add(self._otype)

        self._qty = QDoubleSpinBox()
        self._qty.setRange(0.01, 1_000_000.0)
        self._qty.setDecimals(2)
        self._qty.setValue(1000.0)
        panel.add(QLabel("Quantity"))
        panel.add(self._qty)

        self._price = QDoubleSpinBox()
        self._price.setRange(0.0, 10_000_000.0)
        self._price.setDecimals(4)
        self._price.setEnabled(False)
        panel.add(QLabel("Trigger / limit price"))
        panel.add(self._price)

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

        self._bots_title = QLabel("AUTO-TRADERS")
        self._bots_title.setObjectName("PanelTitle")
        panel.add(self._bots_title)
        self._bots = QTableWidget(0, 3)
        self._bots.setHorizontalHeaderLabels(["Bot", "Target", "Last action"])
        self._bots.verticalHeader().setVisible(False)
        self._bots.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._bots.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._bots.setShowGrid(False)
        self._bots.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        panel.add(self._bots)
        self._stop_bot = QPushButton("Stop selected bot")
        self._stop_bot.clicked.connect(self._stop_selected_bot)
        panel.add(self._stop_bot)
        if self._bot_manager is None:
            for w in (self._bots_title, self._bots, self._stop_bot):
                w.setVisible(False)

        panel.add_stretch()
        return panel

    def _step_bots(self) -> None:
        if self._bot_manager and self._bot_manager.bots():
            self._pool.start(_BotStepTask(self._bot_manager, self._bot_signals))

    def _stop_selected_bot(self) -> None:
        if self._bot_manager is None:
            return
        row = self._bots.currentRow()
        bots = self._bot_manager.bots()
        if 0 <= row < len(bots):
            self._bot_manager.remove(bots[row])
            self._refresh()

    def _sync_price_enabled(self) -> None:
        self._price.setEnabled(OrderType(self._otype.currentData()) is not OrderType.MARKET)

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
        if not symbol:
            return
        qty = self._qty.value()
        otype = OrderType(self._otype.currentData())  # combo may store the raw str
        price = self._price.value() if otype is not OrderType.MARKET else None

        if self._broker.is_live:
            confirm = QMessageBox.question(
                self,
                "Confirm live order",
                f"Send a LIVE {otype.value} {side.value.upper()} order for {qty} "
                f"{symbol} via {self._broker.name}?\n\nThis places a real trade.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

        result = self._broker.place_order(
            OrderRequest(symbol=symbol, side=side, quantity=qty, order_type=otype, limit_price=price)
        )
        venue = "LIVE" if self._broker.is_live else "Paper"
        if result.ok and result.working:
            self._status.setText(f"{venue} {otype.value} {side.value} {qty} {symbol} resting @ {price:g}")
        elif result.ok:
            self._status.setText(f"{venue} {side.value} {qty} {symbol} filled @ {result.filled_price:g}")
        else:
            self._status.setText(f"Rejected: {result.message}")
        self._refresh()

    def _close_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0 or self._table.item(row, 0) is None:
            return
        result = self._broker.close_position(self._table.item(row, 0).text())
        self._status.setText(result.message)
        self._refresh()

    def _cancel_selected(self) -> None:
        row = self._working.currentRow()
        if row < 0 or self._working.item(row, 0) is None:
            return
        if hasattr(self._broker, "cancel_order"):
            result = self._broker.cancel_order(self._working.item(row, 0).text())
            self._status.setText(result.message)
        self._refresh()

    # -- refresh --------------------------------------------------------------

    def _refresh(self) -> None:
        if hasattr(self._provider, "tick"):
            self._provider.tick()
        if hasattr(self._broker, "poll"):
            self._broker.poll()  # fill any triggered working orders

        theme = ACTIVE_THEME
        account = self._broker.account()
        tag = "● LIVE" if self._broker.is_live else "○ PAPER"
        bp = ""
        if hasattr(self._broker, "buying_power"):
            bp = f" &nbsp; Buying power {fmt_money(self._broker.buying_power(), account.currency)}"
        self._account_lbl.setText(
            f"<b>{self._broker.name}</b> {tag} &nbsp;|&nbsp; "
            f"Balance {fmt_money(account.balance, account.currency)} &nbsp; "
            f"Equity {fmt_money(account.equity, account.currency)}{bp}"
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

        working = self._broker.working_orders() if hasattr(self._broker, "working_orders") else []
        self._working.setRowCount(len(working))
        for r, wo in enumerate(working):
            for c, text in enumerate(
                [wo.order_id, wo.symbol, f"{wo.order_type.value} {wo.side.value}", f"{wo.quantity:g}", f"{wo.price:g}"]
            ):
                self._working.setItem(r, c, QTableWidgetItem(text))

        if self._bot_manager is not None:
            bots = self._bot_manager.bots()
            self._bots.setRowCount(len(bots))
            for r, bot in enumerate(bots):
                for c, text in enumerate([bot.name, bot.target_label, bot.last_action]):
                    self._bots.setItem(r, c, QTableWidgetItem(text))

    def on_show(self) -> None:
        self._refresh()
        self._timer.start()
        self._bot_timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
        self._bot_timer.stop()
