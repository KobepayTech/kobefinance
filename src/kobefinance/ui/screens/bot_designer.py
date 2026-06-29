"""Strategy Lab: describe a trading bot, generate code, and backtest it.

The LLM authors readable Python + MQL5 code; the backtest runs a vetted
strategy parsed from the description (model output is never executed). Design
+ history fetch + backtest run on a worker thread so the UI stays responsive.
"""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PySide6.QtCore import QDateTime, QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from ...services.backtest.engine import run_backtest
from ...services.llm.backends import make_backend
from ...services.llm.base import LLMConfig
from ...services.llm.bot_designer import build_strategy, design
from ...services.market_data import RANGES
from ...services.trading.bot_runner import BotRunner
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..widgets.panel import Panel
from .base import Screen

_BACKENDS = [
    ("template", "Offline template"),
    ("ollama", "Ollama (local)"),
    ("llamacpp", "llama.cpp (GGUF)"),
    ("claude", "Claude (cloud)"),
]


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _DesignTask(QRunnable):
    def __init__(self, provider, description, uid, range_key, backend, signals):
        super().__init__()
        self._provider = provider
        self._description = description
        self._uid = uid
        self._range = range_key
        self._backend = backend
        self._signals = signals

    def run(self):
        try:
            symbol = self._uid.split(".")[0]
            result = design(self._description, self._backend, symbol=symbol)
            candles = self._provider.history(self._uid, self._range)
            bt = run_backtest(candles, result.strategy)
            self._signals.done.emit((result, bt, self._uid))
        except Exception as exc:  # surface to the UI rather than crash the worker
            self._signals.failed.emit(str(exc))


class BotDesignerScreen(Screen):
    """Natural-language → backtested strategy, with code export."""

    screen_id = "bots"
    title = "Strategy Lab"

    def __init__(self, provider, broker=None, bot_manager=None) -> None:
        super().__init__()
        self._provider = provider
        self._broker = broker
        self._bot_manager = bot_manager
        self._last = None  # (DesignResult, uid)
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.failed.connect(self._on_failed)

        self.root.addWidget(self._build_controls())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_left(), stretch=3)
        body.addWidget(self._build_right(), stretch=2)
        self.root.addLayout(body, stretch=1)

    # -- construction ---------------------------------------------------------

    def _build_controls(self) -> QWidget:
        theme = ACTIVE_THEME
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)

        self._symbol = QComboBox()
        self._symbol.setMinimumWidth(150)
        known = set(self._provider.symbols())
        for uid in DASHBOARD_WATCHLIST:
            if uid in known:
                self._symbol.addItem(uid.replace(".", "  ·  "), uid)

        self._range = QComboBox()
        for key in RANGES:
            self._range.addItem(key, key)
        self._range.setCurrentText("1Y")

        self._backend = QComboBox()
        for value, label in _BACKENDS:
            self._backend.addItem(label, value)

        self._run = QPushButton("Generate & Backtest")
        self._run.setObjectName("Accent")
        self._run.clicked.connect(self._start)

        for w in (QLabel("Symbol"), self._symbol, QLabel("Range"), self._range,
                  QLabel("LLM"), self._backend):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self._run)
        return bar

    def _build_left(self) -> Panel:
        panel = Panel("Describe your bot")
        theme = ACTIVE_THEME

        self._prompt = QPlainTextEdit()
        self._prompt.setPlaceholderText(
            "e.g. 'Buy when the 20-day moving average crosses above the 50-day; "
            "exit when it crosses back. No shorting.'  —  or  —  "
            "'RSI mean reversion: buy oversold under 30, sell at 70.'"
        )
        self._prompt.setPlainText(
            "Golden cross trend follower: go long when the 50-day SMA crosses "
            "above the 200-day SMA, and exit when it crosses back below."
        )
        self._prompt.setFixedHeight(80)
        panel.add(self._prompt)

        self._code_tabs = QTabWidget()
        self._py_view = self._make_code_view()
        self._mql_view = self._make_code_view()
        self._rationale = self._make_code_view()
        self._code_tabs.addTab(self._py_view, "Python")
        self._code_tabs.addTab(self._mql_view, "MQL5 (MetaTrader)")
        self._code_tabs.addTab(self._rationale, "LLM notes")
        panel.add(self._code_tabs, stretch=1)
        return panel

    def _make_code_view(self) -> QTextEdit:
        theme = ACTIVE_THEME
        view = QTextEdit()
        view.setReadOnly(True)
        view.setStyleSheet(
            f"background:{theme.bg_base}; color:{theme.text_primary};"
            f"font-family:{theme.font_mono}; font-size:12px;"
        )
        return view

    def _build_right(self) -> Panel:
        panel = Panel("Backtest")
        theme = ACTIVE_THEME

        self._metrics = QLabel("Run a backtest to see results.")
        self._metrics.setStyleSheet(
            f"color:{theme.text_secondary}; font-family:{theme.font_mono}; font-size:13px;"
        )
        self._metrics.setTextFormat(Qt.TextFormat.RichText)
        panel.add(self._metrics)

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

        # Deploy-to-paper controls (enabled after a backtest).
        deploy = QWidget()
        drow = QHBoxLayout(deploy)
        drow.setContentsMargins(0, 4, 0, 0)
        drow.addWidget(QLabel("Qty"))
        self._deploy_qty = QDoubleSpinBox()
        self._deploy_qty.setRange(0.01, 1_000_000.0)
        self._deploy_qty.setDecimals(2)
        self._deploy_qty.setValue(100.0)
        drow.addWidget(self._deploy_qty)
        self._deploy_btn = QPushButton("Deploy to paper auto-trader")
        self._deploy_btn.setObjectName("Accent")
        self._deploy_btn.setEnabled(False)
        self._deploy_btn.clicked.connect(self._deploy)
        drow.addWidget(self._deploy_btn, stretch=1)
        if self._bot_manager is None or self._broker is None:
            deploy.setVisible(False)
        panel.add(deploy)

        self._deploy_status = QLabel("")
        self._deploy_status.setWordWrap(True)
        self._deploy_status.setStyleSheet(f"color:{theme.text_tertiary}; font-size:12px;")
        panel.add(self._deploy_status)
        return panel

    def _deploy(self) -> None:
        if not self._last or self._bot_manager is None or self._broker is None:
            return
        result, uid = self._last
        strategy = build_strategy(result.spec)  # fresh, unprepared instance
        name = f"{result.spec.kind} · {uid.split('.')[0]}"
        bot = BotRunner(
            name=name,
            uid=uid,
            strategy=strategy,
            quantity=self._deploy_qty.value(),
            broker=self._broker,
            provider=self._provider,
        )
        self._bot_manager.add(bot)
        self._deploy_status.setText(
            f"Deployed '{name}' to the paper auto-trader. Watch it on the Trading "
            "desk under Auto-Traders."
        )

    # -- run ------------------------------------------------------------------

    def _start(self) -> None:
        if not self._symbol.count():
            return
        self._run.setEnabled(False)
        self._metrics.setText("Generating and backtesting…")
        config = LLMConfig(backend=self._backend.currentData())
        backend = make_backend(config)
        task = _DesignTask(
            self._provider,
            self._prompt.toPlainText().strip(),
            self._symbol.currentData(),
            self._range.currentData(),
            backend,
            self._signals,
        )
        self._pool.start(task)

    def _on_failed(self, message: str) -> None:
        self._run.setEnabled(True)
        self._metrics.setText(f"Error: {message}")

    def _on_done(self, payload) -> None:
        result, bt, uid = payload
        self._last = (result, uid)
        if self._bot_manager is not None and self._broker is not None:
            self._deploy_btn.setEnabled(True)
        self._run.setEnabled(True)
        self._py_view.setPlainText(result.python_code)
        self._mql_view.setPlainText(result.mql5_code)
        self._rationale.setPlainText(
            result.rationale or f"Backend: {result.backend_name}\n\n"
            "The offline template generated this strategy. Select Ollama, "
            "llama.cpp, or Claude (with a model/key configured) for a written "
            "rationale."
        )
        self._render_metrics(result, bt)
        self._render_equity(bt)

    def _render_metrics(self, result, bt) -> None:
        theme = ACTIVE_THEME
        m = bt.metrics
        if not m:
            self._metrics.setText("No data to backtest.")
            return
        ret = m["total_return_pct"]
        color = theme.signed_color(ret)
        self._metrics.setText(
            f"<b>{result.spec.kind}</b> &nbsp; "
            f"<span style='color:{theme.text_tertiary}'>via {result.backend_name}</span><br><br>"
            f"Total return: <span style='color:{color}'>{ret:+.2f}%</span> &nbsp; "
            f"Sharpe: {m['sharpe']:.2f}<br>"
            f"Max drawdown: <span style='color:{theme.negative}'>{m['max_drawdown_pct']:.2f}%</span><br>"
            f"Trades: {int(m['num_trades'])} &nbsp; Win rate: {m['win_rate_pct']:.1f}%<br>"
            f"Final equity: ${m['final_equity']:,.0f}"
        )

    def _render_equity(self, bt) -> None:
        self._series.clear()
        curve = bt.equity_curve
        if not curve:
            return
        lo = min(e for _, e in curve)
        hi = max(e for _, e in curve)
        for ts, eq in curve:
            self._series.append(ts * 1000.0, eq)
        self._axis_x.setRange(
            QDateTime.fromSecsSinceEpoch(curve[0][0]),
            QDateTime.fromSecsSinceEpoch(curve[-1][0]),
        )
        pad = (hi - lo) * 0.08 or 1.0
        self._axis_y.setRange(lo - pad, hi + pad)
