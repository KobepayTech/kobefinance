"""Equity Research: fundamentals + performance + price chart, powered by yfinance.

Fundamentals (market cap, P/E, EPS, dividend yield, beta, 52-week range,
sector, business summary) and the price history come from yfinance for
Yahoo-supported instruments. Everything runs off the UI thread; when yfinance
can't serve a symbol, it falls back to the provider's price history and
price-derived performance stats.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from ...services.fundamentals import fetch_fundamentals, fetch_history
from ...services.live_data import yahoo_symbol
from ...services.relationships import GRAPHS
from ...theme import ACTIVE_THEME
from ..formatting import fmt_compact, fmt_instrument_price, fmt_pct
from ..widgets.panel import Panel
from .base import Screen


class _Signals(QObject):
    done = Signal(object)


class _ResearchTask(QRunnable):
    """Fetch yfinance fundamentals + history off the UI thread (with fallback)."""

    def __init__(self, provider, uid, yahoo_sym, signals):
        super().__init__()
        self._provider = provider
        self._uid = uid
        self._yahoo = yahoo_sym
        self._signals = signals

    def run(self):
        fundamentals = fetch_fundamentals(self._yahoo) if self._yahoo else None
        candles = fetch_history(self._yahoo, "1y") if self._yahoo else []
        if not candles:  # fall back to the provider's (Yahoo/synthetic) history
            try:
                candles = self._provider.history(self._uid, "1Y")
            except Exception:
                candles = []
        try:
            quote = self._provider.quote(self._uid)
        except Exception:
            quote = None
        self._signals.done.emit((self._uid, candles, quote, fundamentals))


def _pct(a: float, b: float) -> float | None:
    return (a / b - 1.0) * 100.0 if b else None


class EquityResearchScreen(Screen):
    """Fundamentals + performance research for one instrument."""

    screen_id = "equity_research"
    title = "Equity Research"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._by_uid = {i.uid: i for i in provider.instruments()}
        self._uid: str | None = None
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)

        self.root.addWidget(self._build_controls())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_chart_panel(), stretch=3)
        body.addWidget(self._build_stats_panel(), stretch=2)
        self.root.addLayout(body, stretch=1)

        if self._selector.count():
            self._uid = self._selector.itemData(0)

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        self._selector = QComboBox()
        self._selector.setMinimumWidth(260)
        for inst in self._provider.instruments():
            self._selector.addItem(f"{inst.symbol} · {inst.exchange} — {inst.name}", inst.uid)
        self._selector.currentIndexChanged.connect(self._on_select)
        row.addWidget(QLabel("Instrument"))
        row.addWidget(self._selector)
        self._source = QLabel("")
        self._source.setStyleSheet(f"color:{ACTIVE_THEME.text_tertiary}; font-size:11px;")
        row.addSpacing(12)
        row.addWidget(self._source)
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
        theme = ACTIVE_THEME

        host = QWidget()
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)

        self._stats = QLabel("Select an instrument.")
        self._stats.setTextFormat(Qt.TextFormat.RichText)
        self._stats.setWordWrap(True)
        self._stats.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._stats.setStyleSheet(
            f"color:{theme.text_secondary}; font-family:{theme.font_mono}; font-size:13px;"
        )
        col.addWidget(self._stats)

        self._summary = QTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setStyleSheet(
            f"background:{theme.bg_base}; color:{theme.text_tertiary};"
            f"border:1px solid {theme.border_dim}; font-size:12px;"
        )
        self._summary.setFixedHeight(170)
        col.addWidget(self._summary)
        col.addStretch(1)

        panel.add(host, stretch=1)
        return panel

    # -- load -----------------------------------------------------------------

    def _on_select(self, index: int) -> None:
        self._uid = self._selector.itemData(index)
        self._load()

    def _load(self) -> None:
        if not self._uid:
            return
        self._stats.setText("Loading from yfinance…")
        self._summary.setPlainText("")
        inst = self._by_uid.get(self._uid)
        ysym = yahoo_symbol(inst) if inst else None
        self._pool.start(_ResearchTask(self._provider, self._uid, ysym, self._signals))

    def _on_done(self, payload) -> None:
        uid, candles, quote, fundamentals = payload
        if uid != self._uid:
            return
        self._render_chart(candles)
        self._render_stats(uid, candles, quote, fundamentals)

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

    def _render_stats(self, uid, candles, quote, f) -> None:
        theme = ACTIVE_THEME
        self._source.setText("source: yfinance" if f else "source: price feed (yfinance unavailable)")
        if quote is None and not candles:
            self._stats.setText("No data available.")
            return

        name = (f.name if f and f.name else (quote.name if quote else uid))
        ccy = (f.currency if f and f.currency else (quote.currency if quote else ""))
        header = (
            f"<b style='color:{theme.text_primary}'>{name}</b> "
            f"<span style='color:{theme.text_tertiary}'>{uid.split('.')[0]} · {uid.split('.')[-1]}</span>"
        )
        if f and (f.sector or f.industry):
            header += f"<br><span style='color:{theme.text_tertiary};font-size:11px'>{f.sector}{' · ' + f.industry if f.industry else ''}</span>"

        # Performance from history.
        closes = [c.close for c in candles] if candles else []
        perf = ""
        if closes:
            last = closes[-1]
            d1 = quote.change_pct if quote else None
            d5 = _pct(last, closes[-6]) if len(closes) > 6 else None
            d30 = _pct(last, closes[-22]) if len(closes) > 22 else None
            d1y = _pct(last, closes[0])

            def row(label, val):
                if val is None:
                    return f"{label}: —  "
                return f"{label}: <span style='color:{theme.signed_color(val)}'>{fmt_pct(val)}</span>  "

            perf = (
                f"<br><br><span style='color:{theme.text_primary};font-size:15px'>"
                f"{fmt_instrument_price(last, ccy or 'USD', quote.kind if quote else 'equity')}</span>"
                f"<br><br>{row('1D', d1)}{row('5D', d5)}<br>{row('1M', d30)}{row('1Y', d1y)}"
            )

        # Fundamentals from yfinance.
        fund = ""
        if f:
            def stat(label, val, fmt=lambda v: f"{v:,.2f}"):
                return f"{label}: {fmt(val) if val is not None else '—'}<br>"
            fund = (
                "<br><br><b style='color:" + theme.text_secondary + "'>FUNDAMENTALS</b><br>"
                + stat("Market cap", f.market_cap, lambda v: fmt_compact(v, ccy or "USD"))
                + stat("P/E (ttm)", f.trailing_pe)
                + stat("P/E (fwd)", f.forward_pe)
                + stat("EPS (ttm)", f.eps)
                + stat("Div yield", f.dividend_yield, lambda v: f"{v:.2f}%")
                + stat("Beta", f.beta)
                + stat("52w high", f.year_high, lambda v: fmt_instrument_price(v, ccy or "USD", "equity"))
                + stat("52w low", f.year_low, lambda v: fmt_instrument_price(v, ccy or "USD", "equity"))
            )
        else:
            fund = (
                f"<br><br><span style='color:{theme.text_tertiary};font-size:11px'>"
                "Fundamentals unavailable for this instrument (no yfinance data).</span>"
            )

        # Analyst coverage (yfinance).
        analyst = ""
        if f and (f.target_mean or f.recommendation or f.earnings_date):
            parts = ["<br><br><b style='color:" + theme.text_secondary + "'>ANALYSTS</b><br>"]
            if f.target_mean:
                upside = None
                if closes:
                    upside = _pct(f.target_mean, closes[-1])
                up_txt = ""
                if upside is not None:
                    up_txt = f" <span style='color:{theme.signed_color(upside)}'>({fmt_pct(upside)})</span>"
                parts.append(
                    f"Target (mean): {fmt_instrument_price(f.target_mean, ccy or 'USD', 'equity')}{up_txt}<br>"
                )
            if f.target_low and f.target_high:
                parts.append(
                    f"Target range: {fmt_instrument_price(f.target_low, ccy or 'USD', 'equity')}"
                    f" – {fmt_instrument_price(f.target_high, ccy or 'USD', 'equity')}<br>"
                )
            if f.recommendation:
                extra = f" ({f.num_analysts} analysts)" if f.num_analysts else ""
                parts.append(f"Consensus: {f.recommendation.title()}{extra}<br>")
            if f.earnings_date:
                parts.append(f"Next earnings: {f.earnings_date}<br>")
            analyst = "".join(parts)

        # Supply-chain cross-link.
        note = ""
        if uid in GRAPHS:
            sup = ", ".join(e.name for e in GRAPHS[uid].suppliers()[:3])
            note = (
                f"<br><span style='color:{theme.text_tertiary};font-size:11px'>"
                f"Supply chain (Relationship Map): {sup}…</span>"
            )

        self._stats.setText(header + perf + fund + analyst + note)
        self._summary.setPlainText(f.summary if f and f.summary else "")

    def on_show(self) -> None:
        self._load()
