"""Price chart screen: a line chart of historical closes for one instrument.

History is fetched on a background thread (live via Yahoo where available,
otherwise synthesised) and rendered with native QtCharts, so selecting a
symbol or range never blocks the UI.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ...models import Candle
from ...services.market_data import RANGES
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..formatting import arrow, fmt_instrument_price, fmt_pct
from ..widgets.panel import Panel
from .base import Screen

_RANGE_ORDER = ["1M", "3M", "6M", "1Y"]


class _HistorySignals(QObject):
    done = Signal(str, str, list)  # uid, range_key, candles


class _HistoryTask(QRunnable):
    """Fetch history off the UI thread and emit the result."""

    def __init__(self, provider, uid: str, range_key: str, signals: _HistorySignals) -> None:
        super().__init__()
        self._provider = provider
        self._uid = uid
        self._range = range_key
        self._signals = signals

    def run(self) -> None:
        try:
            candles = self._provider.history(self._uid, self._range)
        except Exception:
            candles = []
        self._signals.done.emit(self._uid, self._range, candles)


class ChartsScreen(Screen):
    """Pick an instrument and range; see its price history."""

    screen_id = "charts"
    title = "Charts"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._uid: str | None = None
        self._range = "6M"
        self._pool = QThreadPool.globalInstance()
        self._signals = _HistorySignals()
        self._signals.done.connect(self._on_history)

        self.root.addWidget(self._build_controls())
        self.root.addWidget(self._build_chart_panel(), stretch=1)

        # Seed the selector with the dashboard watchlist, restricted to known uids.
        known = set(provider.symbols())
        for uid in DASHBOARD_WATCHLIST:
            if uid in known:
                self._selector.addItem(uid.split(".")[0] + "  ·  " + uid.split(".")[1], uid)
        if self._selector.count():
            self._uid = self._selector.itemData(0)

    # -- construction ---------------------------------------------------------

    def _build_controls(self) -> QWidget:
        theme = ACTIVE_THEME
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(10)

        self._selector = QComboBox()
        self._selector.setMinimumWidth(200)
        self._selector.currentIndexChanged.connect(self._on_symbol_changed)
        row.addWidget(self._selector)

        self._summary = QLabel("")
        self._summary.setStyleSheet(f"color:{theme.text_secondary}; font-family:{theme.font_mono};")
        row.addWidget(self._summary)
        row.addStretch(1)

        self._range_buttons: dict[str, QPushButton] = {}
        for key in _RANGE_ORDER:
            btn = QPushButton(key)
            btn.setCheckable(True)
            btn.setFixedWidth(46)
            btn.clicked.connect(lambda _checked, k=key: self._set_range(k))
            self._range_buttons[key] = btn
            row.addWidget(btn)
        self._range_buttons[self._range].setChecked(True)
        return bar

    def _build_chart_panel(self) -> Panel:
        panel = Panel("Price")
        theme = ACTIVE_THEME

        self._chart = QChart()
        self._chart.legend().hide()
        self._chart.setBackgroundBrush(QColor(theme.bg_surface))
        self._chart.setPlotAreaBackgroundBrush(QColor(theme.bg_surface))
        self._chart.setPlotAreaBackgroundVisible(True)
        self._chart.setTitleBrush(QColor(theme.text_secondary))

        self._series = QLineSeries()
        self._series.setPen(QPen(QColor(theme.accent), 1.6))
        self._chart.addSeries(self._series)

        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM dd")
        self._axis_x.setLabelsColor(QColor(theme.text_tertiary))
        self._axis_x.setGridLineColor(QColor(theme.border_dim))
        self._axis_x.setLinePenColor(QColor(theme.border_med))
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._series.attachAxis(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setLabelsColor(QColor(theme.text_tertiary))
        self._axis_y.setGridLineColor(QColor(theme.border_dim))
        self._axis_y.setLinePenColor(QColor(theme.border_med))
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._series.attachAxis(self._axis_y)

        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel.add(self._view, stretch=1)
        return panel

    # -- selection / loading --------------------------------------------------

    def _on_symbol_changed(self, index: int) -> None:
        uid = self._selector.itemData(index)
        if uid:
            self._uid = uid
            self._load()

    def _set_range(self, key: str) -> None:
        self._range = key
        for k, btn in self._range_buttons.items():
            btn.setChecked(k == key)
        self._load()

    def set_symbol(self, uid: str) -> None:
        """Select *uid* (adding it to the selector if needed) and load it."""
        idx = self._selector.findData(uid)
        if idx < 0:
            parts = uid.split(".")
            label = parts[0] + ("  ·  " + parts[1] if len(parts) > 1 else "")
            self._selector.addItem(label, uid)
            idx = self._selector.count() - 1
        self._selector.setCurrentIndex(idx)

    def _load(self) -> None:
        if not self._uid:
            return
        self._chart.setTitle("Loading…")
        self._apply_summary()
        task = _HistoryTask(self._provider, self._uid, self._range, self._signals)
        self._pool.start(task)

    def _apply_summary(self) -> None:
        theme = ACTIVE_THEME
        q = self._provider.quote(self._uid) if self._uid else None
        if q is None:
            self._summary.setText("")
            return
        is_live = getattr(self._provider, "is_live", None)
        src = "LIVE" if (is_live and is_live(self._uid)) else "SIM"
        color = theme.signed_color(q.change)
        self._summary.setText(
            f"<span style='color:{theme.text_primary}'>{q.name}</span> &nbsp; "
            f"<span style='color:{theme.text_primary}'>{fmt_instrument_price(q.price, q.currency, q.kind)}</span> &nbsp; "
            f"<span style='color:{color}'>{arrow(q.change)} {fmt_pct(q.change_pct)}</span> &nbsp; "
            f"<span style='color:{theme.text_tertiary}'>· {src}</span>"
        )

    # -- render ---------------------------------------------------------------

    def _on_history(self, uid: str, range_key: str, candles: list) -> None:
        # Ignore results that arrived after the user moved on.
        if uid != self._uid or range_key != self._range:
            return
        self._render(candles)

    def _render(self, candles: list[Candle]) -> None:
        theme = ACTIVE_THEME
        self._series.clear()
        if not candles:
            self._chart.setTitle("No data available")
            return
        self._chart.setTitle("")

        lo = min(c.close for c in candles)
        hi = max(c.close for c in candles)
        for c in candles:
            self._series.append(c.ts * 1000.0, c.close)

        # Color the line by net direction over the window.
        rising = candles[-1].close >= candles[0].close
        self._series.setPen(QPen(QColor(theme.positive if rising else theme.negative), 1.6))

        self._axis_x.setRange(
            QDateTime.fromSecsSinceEpoch(candles[0].ts),
            QDateTime.fromSecsSinceEpoch(candles[-1].ts),
        )
        pad = (hi - lo) * 0.08 or hi * 0.02 or 1.0
        self._axis_y.setRange(lo - pad, hi + pad)
        self._apply_summary()

    # -- lifecycle ------------------------------------------------------------

    def on_show(self) -> None:
        if self._uid:
            self._load()
