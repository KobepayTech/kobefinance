"""Equity Research: per-instrument performance stats and a price chart.

Fundamentals aren't available from the free feed, so this focuses on what we
can derive from price history — multi-horizon performance, period range, and a
chart — plus a supply-chain note when a relationship graph exists.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from ...services.relationships import GRAPHS
from ...theme import ACTIVE_THEME
from ..formatting import fmt_instrument_price, fmt_pct
from ..widgets.panel import Panel
from .base import Screen


class _Signals(QObject):
    done = Signal(object)


class _ResearchTask(QRunnable):
    def __init__(self, provider, uid, signals):
        super().__init__()
        self._provider = provider
        self._uid = uid
        self._signals = signals

    def run(self):
        try:
            candles = self._provider.history(self._uid, "1Y")
            quote = self._provider.quote(self._uid)
        except Exception:
            candles, quote = [], None
        self._signals.done.emit((self._uid, candles, quote))


def _pct(a: float, b: float) -> float | None:
    return (a / b - 1.0) * 100.0 if b else None


class EquityResearchScreen(Screen):
    """Performance research for one instrument."""

    screen_id = "equity_research"
    title = "Equity Research"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._uid: str | None = None
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)

        self.root.addWidget(self._build_controls())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_chart_panel(), stretch=3)
        body.addWidget(self._build_stats_panel(), stretch=1)
        self.root.addLayout(body, stretch=1)

        if self._selector.count():
            self._uid = self._selector.itemData(0)

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        self._selector = QComboBox()
        self._selector.setMinimumWidth(240)
        for inst in self._provider.instruments():
            self._selector.addItem(f"{inst.symbol} · {inst.exchange} — {inst.name}", inst.uid)
        self._selector.currentIndexChanged.connect(self._on_select)
        row.addWidget(QLabel("Instrument"))
        row.addWidget(self._selector)
        row.addStretch(1)
        return bar

    def _build_chart_panel(self) -> Panel:
        panel = Panel("Price — 1Y")
        theme = ACTIVE_THEME
        self._chart = QChart()
        self._chart.legend().hide()
        self._chart.setBackgroundBrush(QColor(theme.bg_surface))
        self._chart.setPlotAreaBackgroundBrush(QColor(theme.bg_surface))
        self._chart.setPlotAreaBackgroundVisible(True)
        self._series = QLineSeries()
        self._series.setPen(QPen(QColor(theme.accent), 1.6))
        self._chart.addSeries(self._series)
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MMM yy")
        self._axis_x.setLabelsColor(QColor(theme.text_tertiary))
        self._axis_x.setGridLineColor(QColor(theme.border_dim))
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        self._series.attachAxis(self._axis_x)
        self._axis_y = QValueAxis()
        self._axis_y.setLabelsColor(QColor(theme.text_tertiary))
        self._axis_y.setGridLineColor(QColor(theme.border_dim))
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._series.attachAxis(self._axis_y)
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel.add(self._view, stretch=1)
        return panel

    def _build_stats_panel(self) -> Panel:
        panel = Panel("Snapshot")
        self._stats = QLabel("Select an instrument.")
        self._stats.setTextFormat(Qt.TextFormat.RichText)
        self._stats.setWordWrap(True)
        self._stats.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._stats.setStyleSheet(
            f"color:{ACTIVE_THEME.text_secondary}; font-family:{ACTIVE_THEME.font_mono}; font-size:13px;"
        )
        panel.add(self._stats, stretch=1)
        return panel

    # -- load -----------------------------------------------------------------

    def _on_select(self, index: int) -> None:
        self._uid = self._selector.itemData(index)
        self._load()

    def _load(self) -> None:
        if not self._uid:
            return
        self._stats.setText("Loading…")
        self._pool.start(_ResearchTask(self._provider, self._uid, self._signals))

    def _on_done(self, payload) -> None:
        uid, candles, quote = payload
        if uid != self._uid:
            return
        self._render_chart(candles)
        self._render_stats(uid, candles, quote)

    def _render_chart(self, candles) -> None:
        self._series.clear()
        if not candles:
            return
        lo = min(c.close for c in candles)
        hi = max(c.close for c in candles)
        for c in candles:
            self._series.append(c.ts * 1000.0, c.close)
        self._axis_x.setRange(
            QDateTime.fromSecsSinceEpoch(candles[0].ts),
            QDateTime.fromSecsSinceEpoch(candles[-1].ts),
        )
        pad = (hi - lo) * 0.08 or 1.0
        self._axis_y.setRange(lo - pad, hi + pad)

    def _render_stats(self, uid, candles, quote) -> None:
        theme = ACTIVE_THEME
        if quote is None or not candles:
            self._stats.setText("No data available.")
            return
        closes = [c.close for c in candles]
        last = closes[-1]
        d1 = quote.change_pct
        d5 = _pct(last, closes[-6]) if len(closes) > 6 else None
        d30 = _pct(last, closes[-22]) if len(closes) > 22 else None
        d1y = _pct(last, closes[0])
        hi = max(closes)
        lo = min(closes)

        def row(label: str, val: float | None) -> str:
            if val is None:
                return f"{label}: —<br>"
            return f"{label}: <span style='color:{theme.signed_color(val)}'>{fmt_pct(val)}</span><br>"

        note = ""
        if uid in GRAPHS:
            sup = ", ".join(e.name for e in GRAPHS[uid].suppliers()[:3])
            note = (
                f"<br><span style='color:{theme.text_tertiary}'>Supply chain "
                f"(see Relationship Map): {sup}…</span>"
            )

        self._stats.setText(
            f"<b style='color:{theme.text_primary}'>{quote.name}</b> "
            f"<span style='color:{theme.text_tertiary}'>{quote.symbol} · {quote.exchange}</span>"
            f"<br><br><span style='color:{theme.text_primary};font-size:16px'>"
            f"{fmt_instrument_price(last, quote.currency, quote.kind)}</span><br><br>"
            f"{row('1D', d1)}{row('5D', d5)}{row('1M', d30)}{row('1Y', d1y)}<br>"
            f"1Y high: {fmt_instrument_price(hi, quote.currency, quote.kind)}<br>"
            f"1Y low: {fmt_instrument_price(lo, quote.currency, quote.kind)}"
            f"{note}"
            f"<br><br><span style='color:{theme.text_tertiary};font-size:11px'>"
            "Performance from price history. Fundamentals not available from the "
            "free feed.</span>"
        )

    def on_show(self) -> None:
        self._load()
