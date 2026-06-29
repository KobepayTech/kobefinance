"""Relationship map: a company-centric supply-chain graph with live stock data.

Rendered natively with QGraphicsScene/QGraphicsView. The center company sits in
the middle; suppliers fan out left and customers right. Each public node shows
name/ticker/price/1D%, edges are colored by the supplier's trend and weighted
by importance, hover tooltips add 5D/30D and relationship detail, and a banner
fires when several suppliers fall together (supplier-stress signal).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRectF, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from ...services.relationships import (
    GRAPHS,
    IMPORTANCE_WEIGHT,
    RelationshipGraph,
    resolve_node,
    stress_signal,
)
from ...theme import ACTIVE_THEME
from ..formatting import fmt_instrument_price, fmt_pct
from ..widgets.panel import Panel
from .base import Screen

REFRESH_MS = 2000
_NODE_W, _NODE_H = 176.0, 70.0
_CENTER_W, _CENTER_H = 196.0, 82.0
_COL_X = 360.0
_ROW_GAP = 104.0


class _HistSignals(QObject):
    done = Signal(object)


class _HistTask(QRunnable):
    """Fetch 5D/30D moves for the public nodes (off the UI thread)."""

    def __init__(self, provider, uids, signals):
        super().__init__()
        self._provider = provider
        self._uids = uids
        self._signals = signals

    def run(self):
        out: dict[str, tuple[float, float]] = {}
        for uid in self._uids:
            try:
                closes = [c.close for c in self._provider.history(uid, "1M")]
            except Exception:
                closes = []
            if len(closes) > 6 and closes[-6] and closes[0]:
                out[uid] = (
                    (closes[-1] / closes[-6] - 1.0) * 100.0,
                    (closes[-1] / closes[0] - 1.0) * 100.0,
                )
        self._signals.done.emit(out)


class RelationshipMapScreen(Screen):
    """Interactive supply-chain / customer graph for a chosen company."""

    screen_id = "relationships"
    title = "Relationship Map"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._hist: dict[str, tuple[float, float]] = {}
        self._pool = QThreadPool.globalInstance()
        self._hsignals = _HistSignals()
        self._hsignals.done.connect(self._on_hist)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self._rebuild)

        self.root.addWidget(self._build_top())
        panel = Panel("Supply Chain & Customers")
        theme = ACTIVE_THEME
        self._scene = QGraphicsScene()
        self._scene.setBackgroundBrush(QColor(theme.bg_base))
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        panel.add(self._view, stretch=1)
        self.root.addWidget(panel, stretch=1)

    def _build_top(self) -> QWidget:
        theme = ACTIVE_THEME
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(10)

        self._select = QComboBox()
        for uid, graph in GRAPHS.items():
            self._select.addItem(f"{graph.center_name} ({uid.split('.')[0]})", uid)
        self._select.currentIndexChanged.connect(self._on_select)
        row.addWidget(QLabel("Center"))
        row.addWidget(self._select)

        self._stress = QLabel("")
        self._stress.setTextFormat(Qt.TextFormat.RichText)
        self._stress.setStyleSheet(f"color:{theme.warning}; font-weight:600;")
        row.addSpacing(16)
        row.addWidget(self._stress)
        row.addStretch(1)
        return bar

    # -- data -----------------------------------------------------------------

    def _current_graph(self) -> RelationshipGraph | None:
        uid = self._select.currentData()
        return GRAPHS.get(uid)

    def _on_select(self) -> None:
        self._hist = {}
        self._rebuild()
        self._fetch_history()

    def _fetch_history(self) -> None:
        graph = self._current_graph()
        if graph is None:
            return
        uids = [e.uid for e in graph.related if e.uid] + [graph.center_uid]
        self._pool.start(_HistTask(self._provider, uids, self._hsignals))

    def _on_hist(self, data: dict) -> None:
        self._hist = data
        self._rebuild()

    # -- rendering ------------------------------------------------------------

    def _rebuild(self) -> None:
        graph = self._current_graph()
        if graph is None:
            return
        self._provider.tick() if hasattr(self._provider, "tick") else None
        self._scene.clear()

        center = (0.0, 0.0)
        suppliers = graph.suppliers()
        customers = graph.customers()

        # Edges first so node boxes paint on top.
        sup_pos = self._column_positions(suppliers, -_COL_X)
        cus_pos = self._column_positions(customers, _COL_X)
        for entity, pos in list(zip(suppliers, sup_pos)) + list(zip(customers, cus_pos)):
            self._draw_edge(center, pos, entity)
        for entity, pos in zip(suppliers, sup_pos):
            self._draw_node(pos, resolve_node(self._provider, entity))
        for entity, pos in zip(customers, cus_pos):
            self._draw_node(pos, resolve_node(self._provider, entity))

        self._draw_center(center, graph)
        self._update_stress(graph)

        rect = self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        self._scene.setSceneRect(rect)
        self._view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    @staticmethod
    def _column_positions(items, x: float) -> list[tuple[float, float]]:
        n = len(items)
        top = -(n - 1) / 2.0 * _ROW_GAP
        return [(x, top + i * _ROW_GAP) for i in range(n)]

    def _trend_color(self, change: float | None) -> QColor:
        theme = ACTIVE_THEME
        if change is None:
            return QColor(theme.border_bright)
        return QColor(theme.signed_color(change))

    def _draw_edge(self, c: tuple[float, float], p: tuple[float, float], entity) -> None:
        theme = ACTIVE_THEME
        node = resolve_node(self._provider, entity)
        color = self._trend_color(node.change_1d if node.public else None)
        pen = QPen(color, IMPORTANCE_WEIGHT.get(entity.importance, 2.0))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._scene.addLine(c[0], c[1], p[0], p[1], pen)

        # Edge label biased toward the node end.
        lx = c[0] + (p[0] - c[0]) * 0.62
        ly = c[1] + (p[1] - c[1]) * 0.62
        if node.public and node.change_1d is not None:
            ticker = (entity.uid or "").split(".")[0]
            text = f"{ticker} {fmt_pct(node.change_1d)}"
            if entity.uid in self._hist:
                text += f"  ·  30D {fmt_pct(self._hist[entity.uid][1])}"
            lcolor = theme.signed_color(node.change_1d)
        else:
            text = f"{entity.relation} · {entity.confidence}%"
            lcolor = theme.text_tertiary
        label = self._scene.addText(text, QFont(theme.font_mono.split(",")[0].strip('"'), 8))
        label.setDefaultTextColor(QColor(lcolor))
        label.setPos(lx - label.boundingRect().width() / 2, ly - 22)

    @staticmethod
    def _node_width(market_cap_b: float) -> float:
        # Wider node for bigger market cap (sqrt scale, clamped).
        return _NODE_W + min(56.0, (market_cap_b ** 0.5) * 1.2)

    def _draw_node(self, pos: tuple[float, float], node) -> None:
        theme = ACTIVE_THEME
        entity = node.entity
        w = self._node_width(entity.market_cap_b)
        border = self._trend_color(node.change_1d if node.public else None)
        rect_item = self._scene.addRect(
            QRectF(pos[0] - w / 2, pos[1] - _NODE_H / 2, w, _NODE_H),
            QPen(border, 2.0),
            QBrush(QColor(theme.bg_surface)),
        )
        rect_item.setToolTip(self._tooltip(node))

        if node.public and node.price is not None:
            ticker = (entity.uid or "").split(".")[0]
            chg = node.change_1d or 0.0
            html = (
                f"<div style='font-family:{theme.font_ui}'>"
                f"<b style='color:{theme.text_primary}'>{entity.name}</b><br>"
                f"<span style='color:{theme.text_tertiary};font-size:10px'>{ticker}</span><br>"
                f"<span style='color:{theme.text_primary};font-family:{theme.font_mono}'>"
                f"{fmt_instrument_price(node.price, node.currency, node.kind)}</span> "
                f"<span style='color:{theme.signed_color(chg)};font-family:{theme.font_mono}'>"
                f"{fmt_pct(chg)}</span></div>"
            )
        else:
            html = (
                f"<div style='font-family:{theme.font_ui}'>"
                f"<b style='color:{theme.text_primary}'>{entity.name}</b><br>"
                f"<span style='color:{theme.text_tertiary};font-size:10px'>"
                f"{entity.relation} · private</span><br>"
                f"<span style='color:{theme.text_tertiary};font-size:10px'>"
                f"no market data</span></div>"
            )
        text = self._scene.addText("")
        text.setHtml(html)
        text.setTextWidth(w - 18)
        text.setPos(pos[0] - w / 2 + 9, pos[1] - _NODE_H / 2 + 6)

    def _draw_center(self, pos: tuple[float, float], graph: RelationshipGraph) -> None:
        theme = ACTIVE_THEME
        quote = self._provider.quote(graph.center_uid)
        rect_item = self._scene.addRect(
            QRectF(pos[0] - _CENTER_W / 2, pos[1] - _CENTER_H / 2, _CENTER_W, _CENTER_H),
            QPen(QColor(theme.accent), 2.6),
            QBrush(QColor(theme.bg_raised)),
        )
        ticker = graph.center_uid.split(".")[0]
        if quote is not None:
            body = (
                f"<span style='color:{theme.text_primary};font-family:{theme.font_mono};font-size:15px'>"
                f"{fmt_instrument_price(quote.price, quote.currency, quote.kind)}</span> "
                f"<span style='color:{theme.signed_color(quote.change)};font-family:{theme.font_mono}'>"
                f"{fmt_pct(quote.change_pct)}</span>"
            )
        else:
            body = f"<span style='color:{theme.text_tertiary}'>—</span>"
        html = (
            f"<div style='font-family:{theme.font_ui}'>"
            f"<b style='color:{theme.accent};font-size:14px'>{graph.center_name}</b> "
            f"<span style='color:{theme.text_tertiary};font-size:10px'>{ticker}</span><br>{body}</div>"
        )
        rect_item.setToolTip(f"{graph.center_name} ({ticker})")
        text = self._scene.addText("")
        text.setHtml(html)
        text.setTextWidth(_CENTER_W - 20)
        text.setPos(pos[0] - _CENTER_W / 2 + 10, pos[1] - _CENTER_H / 2 + 10)

    def _tooltip(self, node) -> str:
        e = node.entity
        lines = [f"{e.name}"]
        if e.uid:
            lines[0] += f" ({e.uid.split('.')[0]})"
        if node.public and node.price is not None:
            lines.append(f"Price: {fmt_instrument_price(node.price, node.currency, node.kind)}")
            lines.append(f"1D: {fmt_pct(node.change_1d or 0.0)}")
            if e.uid in self._hist:
                c5, c30 = self._hist[e.uid]
                lines.append(f"5D: {fmt_pct(c5)}   30D: {fmt_pct(c30)}")
        else:
            lines.append("Private — no public market data")
        lines.append(f"Relationship: {e.relation}  ·  importance {e.importance}")
        lines.append(f"Confidence: {e.confidence}%")
        if e.products:
            lines.append(f"Products: {e.products}")
        return "\n".join(lines)

    def _update_stress(self, graph: RelationshipGraph) -> None:
        count, movers = stress_signal(self._provider, graph)
        if count:
            detail = ", ".join(f"{t} {fmt_pct(p)}" for t, p in movers)
            self._stress.setText(f"⚠ Supply-chain stress: {count} suppliers down 3%+ today — {detail}")
        else:
            self._stress.setText("")

    # -- lifecycle ------------------------------------------------------------

    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        self._rebuild()

    def resizeEvent(self, event):  # noqa: N802 - Qt override
        super().resizeEvent(event)
        rect = self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
        if not rect.isEmpty():
            self._view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def on_show(self) -> None:
        self._rebuild()
        self._fetch_history()
        self._timer.start()

    def on_hide(self) -> None:
        self._timer.stop()
