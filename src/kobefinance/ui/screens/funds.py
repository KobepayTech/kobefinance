"""Funds: parse a fund statement PDF into a chain graph + breakdown.

Loads a fund report (local PDF, URL, or the bundled Umoja Fund sample), parses
NAV / assets / income / manager / custodian, and renders a native chain graph
(fund in the center; manager/custodian/holders/regulator left; portfolio
assets right; income drivers below) plus an asset-allocation and income
breakdown. Parsing/downloading runs off the UI thread.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ...services.funds import (
    SAMPLE_UMOJA,
    build_fund_graph,
    download_pdf,
    fmt_tzs,
    parse_fund_report,
    save_report,
)
from ...theme import ACTIVE_THEME
from ..widgets.panel import Panel
from .base import Screen

_NODE_W, _NODE_H = 184.0, 58.0
_CENTER_W, _CENTER_H = 210.0, 78.0
_HISTORY_DB = Path.home() / ".kobefinance" / "funds.sqlite"


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _LoadTask(QRunnable):
    def __init__(self, kind, source, signals):
        super().__init__()
        self._kind = kind        # "pdf" | "url" | "sample"
        self._source = source
        self._signals = signals

    def run(self):
        try:
            if self._kind == "sample":
                report = SAMPLE_UMOJA
            else:
                path = self._source
                if self._kind == "url":
                    path = download_pdf(self._source, Path(tempfile.gettempdir()) / "kobe_funds")
                report = parse_fund_report(path)
            self._signals.done.emit(report)
        except Exception as exc:
            self._signals.failed.emit(str(exc))


def _type_color(node_type: str, value: float | None) -> str:
    theme = ACTIVE_THEME
    return {
        "fund": theme.accent,
        "manager": theme.info,
        "custodian": theme.cyan,
        "investor": theme.positive,
        "regulator": theme.warning,
        "asset": theme.border_bright,
        "income": theme.signed_color(value or 0.0),
    }.get(node_type, theme.border_bright)


class FundsScreen(Screen):
    """Fund chain graph + breakdown for a parsed fund statement."""

    screen_id = "funds"
    title = "Funds"

    def __init__(self, provider=None) -> None:
        super().__init__()
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.failed.connect(self._on_failed)
        self._report = None

        self.root.addWidget(self._build_controls())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_graph_panel(), stretch=3)
        body.addWidget(self._build_detail_panel(), stretch=2)
        self.root.addLayout(body, stretch=1)

    def _build_controls(self) -> QWidget:
        theme = ACTIVE_THEME
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(8)
        self._path = QLineEdit()
        self._path.setObjectName("CommandInput")
        self._path.setPlaceholderText("Fund statement PDF path or URL…")
        load_pdf = QPushButton("Load PDF")
        load_pdf.clicked.connect(self._load_path)
        load_sample = QPushButton("Load Umoja sample")
        load_sample.setObjectName("Accent")
        load_sample.clicked.connect(self._load_sample)
        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{theme.text_tertiary}; font-size:12px;")
        row.addWidget(self._path, stretch=1)
        row.addWidget(load_pdf)
        row.addWidget(load_sample)
        row.addWidget(self._status)
        return bar

    def _build_graph_panel(self) -> Panel:
        panel = Panel("Fund Chain")
        theme = ACTIVE_THEME
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QColor(theme.bg_base))
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel.add(self._view, stretch=1)
        return panel

    def _build_detail_panel(self) -> Panel:
        panel = Panel("Breakdown")
        theme = ACTIVE_THEME
        self._detail = QLabel("Load a fund statement to see its breakdown.")
        self._detail.setTextFormat(Qt.TextFormat.RichText)
        self._detail.setWordWrap(True)
        self._detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._detail.setStyleSheet(
            f"color:{theme.text_secondary}; font-family:{theme.font_mono}; font-size:13px;"
        )
        panel.add(self._detail, stretch=1)
        return panel

    # -- loading --------------------------------------------------------------

    def _load_path(self) -> None:
        src = self._path.text().strip()
        if not src:
            return
        kind = "url" if src.lower().startswith(("http://", "https://")) else "pdf"
        self._status.setText("Loading…")
        self._pool.start(_LoadTask(kind, src, self._signals))

    def _load_sample(self) -> None:
        self._status.setText("Loading sample…")
        self._pool.start(_LoadTask("sample", None, self._signals))

    def _on_failed(self, message: str) -> None:
        self._status.setText(f"Error: {message}")

    def _on_done(self, report) -> None:
        self._report = report
        self._status.setText(f"Loaded {report.fund_name}" + (f" — {report.report_date}" if report.report_date else ""))
        self._render_graph(report)
        self._render_detail(report)
        try:
            save_report(_HISTORY_DB, report)
        except Exception:
            pass  # history is best-effort

    # -- rendering ------------------------------------------------------------

    def _render_graph(self, report) -> None:
        self._scene.clear()
        nodes, links = build_fund_graph(report)
        by_id = {n.id: n for n in nodes}
        pos: dict[str, tuple[float, float]] = {"fund": (0.0, 0.0)}

        left = [n for n in nodes if n.side == "left"]
        right = [n for n in nodes if n.side == "right"]
        bottom = [n for n in nodes if n.side == "bottom"]
        for items, x, gap in ((left, -400.0, 92.0), (right, 400.0, 84.0)):
            top = -(len(items) - 1) / 2.0 * gap
            for i, n in enumerate(items):
                pos[n.id] = (x, top + i * gap)
        if bottom:
            span = 250.0
            start = -(len(bottom) - 1) / 2.0 * span
            for i, n in enumerate(bottom):
                pos[n.id] = (start + i * span, 230.0)

        for link in links:
            if link.source in pos and link.target in pos:
                a, b = pos[link.source], pos[link.target]
                # Color edge by the non-fund endpoint's node.
                other = link.target if link.source == "fund" else link.source
                node = by_id.get(other)
                color = _type_color(node.type, node.value if node else None) if node else ACTIVE_THEME.border_med
                self._scene.addLine(a[0], a[1], b[0], b[1], QPen(QColor(color), 2.0))

        for n in nodes:
            if n.id in pos and n.id != "fund":
                self._draw_node(pos[n.id], n)
        self._draw_center(pos["fund"], by_id["fund"])

        rect = self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        self._scene.setSceneRect(rect)
        self._view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_node(self, p, node) -> None:
        theme = ACTIVE_THEME
        color = _type_color(node.type, node.value)
        rect = self._scene.addRect(
            QRectF(p[0] - _NODE_W / 2, p[1] - _NODE_H / 2, _NODE_W, _NODE_H),
            QPen(QColor(color), 2.0), QBrush(QColor(theme.bg_surface)),
        )
        rect.setToolTip(f"{node.label}\n{node.subtitle}" if node.subtitle else node.label)
        html = (
            f"<div style='font-family:{theme.font_ui}'>"
            f"<b style='color:{theme.text_primary}'>{node.label}</b><br>"
            f"<span style='color:{theme.text_tertiary};font-size:10px'>{node.subtitle}</span></div>"
        )
        text = self._scene.addText("")
        text.setHtml(html)
        text.setTextWidth(_NODE_W - 16)
        text.setPos(p[0] - _NODE_W / 2 + 8, p[1] - _NODE_H / 2 + 5)

    def _draw_center(self, p, node) -> None:
        theme = ACTIVE_THEME
        self._scene.addRect(
            QRectF(p[0] - _CENTER_W / 2, p[1] - _CENTER_H / 2, _CENTER_W, _CENTER_H),
            QPen(QColor(theme.accent), 2.6), QBrush(QColor(theme.bg_raised)),
        )
        html = (
            f"<div style='font-family:{theme.font_ui}'>"
            f"<b style='color:{theme.accent};font-size:13px'>{node.label}</b><br>"
            f"<span style='color:{theme.text_secondary};font-size:11px'>{node.subtitle}</span></div>"
        )
        text = self._scene.addText("")
        text.setHtml(html)
        text.setTextWidth(_CENTER_W - 18)
        text.setPos(p[0] - _CENTER_W / 2 + 9, p[1] - _CENTER_H / 2 + 8)

    def _render_detail(self, report) -> None:
        theme = ACTIVE_THEME
        total = report.total_assets_tzs

        def alloc_rows() -> str:
            rows = []
            for name, value in sorted(report.assets.items(), key=lambda kv: kv[1] or 0, reverse=True):
                if value is None:
                    continue
                pct = f"{value / total * 100:.1f}%" if total else "—"
                rows.append(
                    f"{name}<span style='color:{theme.text_tertiary}'> — "
                    f"{fmt_tzs(value)} ({pct})</span><br>"
                )
            return "".join(rows)

        def income_rows() -> str:
            rows = []
            for name, value in report.income.items():
                if value is None:
                    continue
                rows.append(
                    f"{name}: <span style='color:{theme.signed_color(value)}'>{fmt_tzs(value)}</span><br>"
                )
            return "".join(rows)

        nav_line = (
            f"NAV / unit: <b>{report.nav_per_unit:,.2f}</b><br>" if report.nav_per_unit else ""
        )
        self._detail.setText(
            f"<b style='color:{theme.text_primary};font-size:15px'>{report.fund_name}</b>"
            f" <span style='color:{theme.text_tertiary}'>{report.report_date or ''}</span><br><br>"
            + nav_line
            + f"Net assets: {fmt_tzs(report.net_assets_tzs)}<br>"
            f"Total assets: {fmt_tzs(report.total_assets_tzs)}<br>"
            f"Net income: <span style='color:{theme.signed_color(report.net_income_tzs or 0)}'>"
            f"{fmt_tzs(report.net_income_tzs)}</span><br>"
            f"Manager: {report.manager or '—'}<br>Custodian: {report.custodian or '—'}<br><br>"
            f"<b style='color:{theme.text_secondary}'>ASSET ALLOCATION</b><br>{alloc_rows()}<br>"
            f"<b style='color:{theme.text_secondary}'>INCOME DRIVERS</b><br>{income_rows()}"
            f"<br><span style='color:{theme.text_tertiary};font-size:11px'>"
            "Parsed from the fund statement (rule-based). Values labelled TZS '000' in source.</span>"
        )

    def on_show(self) -> None:
        if self._report is None:
            self._load_sample()
