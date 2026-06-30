"""Portfolio screen: holdings, allocation, and risk metrics.

Reads positions from the shared broker and computes risk off the UI thread
(history fetches may hit the network).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from ...services.portfolio import build_snapshot
from ...theme import ACTIVE_THEME
from ..formatting import fmt_money
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 4000


class _Signals(QObject):
    done = Signal(object)


class _SnapshotTask(QRunnable):
    def __init__(self, broker, provider, signals):
        super().__init__()
        self._broker = broker
        self._provider = provider
        self._signals = signals

    def run(self):
        try:
            snap = build_snapshot(self._broker, self._provider)
        except Exception:
            snap = None
        self._signals.done.emit(snap)


class PortfolioScreen(Screen):
    """Live holdings table with allocation weights and portfolio risk."""

    screen_id = "portfolio"
    title = "Portfolio"

    def __init__(self, provider, broker, settings=None) -> None:
        super().__init__()
        self._provider = provider
        self._broker = broker
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._render)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._reload)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_holdings_panel(), stretch=3)
        body.addWidget(self._build_risk_panel(), stretch=1)
        self.root.addLayout(body, stretch=1)

    def _build_holdings_panel(self) -> Panel:
        panel = Panel("Holdings")
        self._summary = QLabel("No open positions yet — trade on the Trading desk.")
        self._summary.setStyleSheet(
            f"color:{ACTIVE_THEME.text_secondary}; font-family:{ACTIVE_THEME.font_mono};"
        )
        panel.add(self._summary)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Symbol", "Side", "Qty", "Value", "Weight", "P&L"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in range(1, 6):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        panel.add(self._table, stretch=1)
        return panel

    def _build_risk_panel(self) -> Panel:
        panel = Panel("Risk")
        self._risk = QLabel("—")
        self._risk.setTextFormat(Qt.TextFormat.RichText)
        self._risk.setWordWrap(True)
        self._risk.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._risk.setStyleSheet(
            f"color:{ACTIVE_THEME.text_secondary}; font-family:{ACTIVE_THEME.font_mono}; font-size:13px;"
        )
        panel.add(self._risk, stretch=1)
        return panel

    # -- data -----------------------------------------------------------------

    def _reload(self) -> None:
        self._pool.start(_SnapshotTask(self._broker, self._provider, self._signals))

    def _render(self, snap) -> None:
        theme = ACTIVE_THEME
        if snap is None or not snap.holdings:
            self._summary.setText("No open positions yet — trade on the Trading desk.")
            self._table.setRowCount(0)
            self._risk.setText("Open a position to see portfolio risk.")
            return

        total_pnl = sum(h.unrealized_pnl for h in snap.holdings)
        self._summary.setText(
            f"Total value {fmt_money(snap.total_value, 'USD')} &nbsp; "
            f"Unrealized P&L "
            f"<span style='color:{theme.signed_color(total_pnl)}'>{total_pnl:+,.2f}</span> &nbsp; "
            f"({len(snap.holdings)} holdings)"
        )

        self._table.setRowCount(len(snap.holdings))
        for r, h in enumerate(snap.holdings):
            cells = [
                (h.symbol, None, False),
                (h.side.upper(), None, False),
                (f"{h.quantity:g}", None, True),
                (f"{h.market_value:,.0f}", None, True),
                (f"{h.weight_pct:.1f}%", None, True),
                (f"{h.unrealized_pnl:+,.2f}", theme.signed_color(h.unrealized_pnl), True),
            ]
            for c, (text, color, right) in enumerate(cells):
                item = QTableWidgetItem(text)
                if right:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if color:
                    item.setForeground(QColor(color))
                self._table.setItem(r, c, item)

        risk = snap.risk
        if not risk:
            self._risk.setText("Not enough history to estimate risk.")
            return
        self._risk.setText(
            "<b>Portfolio risk</b><br><br>"
            f"Annualized volatility: {risk['annual_vol_pct']:.2f}%<br>"
            f"Sharpe (hist.): {risk['sharpe']:.2f}<br>"
            f"Max drawdown: <span style='color:{theme.negative}'>"
            f"{risk['max_drawdown_pct']:.2f}%</span><br><br>"
            f"<b>1-day VaR (95%)</b><br>"
            f"{risk['var95_pct']:.2f}% &nbsp; "
            f"(<span style='color:{theme.negative}'>"
            f"-{fmt_money(risk['var95_cash'], 'USD')}</span>)<br><br>"
            f"<span style='color:{theme.text_tertiary}'>Historical estimate from "
            "6-month return series. Not a guarantee of future loss.</span>"
        )

    def on_show(self) -> None:
        self._reload()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
