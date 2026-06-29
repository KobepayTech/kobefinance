"""News: recent headlines for an instrument, via Yahoo Finance search."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QWidget,
)
from PySide6.QtCore import QUrl

from ...services.live_data import fetch_news
from ...services.universe import DASHBOARD_WATCHLIST
from ...theme import ACTIVE_THEME
from ..widgets.panel import Panel
from .base import Screen

_LINK_ROLE = Qt.ItemDataRole.UserRole


class _Signals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


class _NewsTask(QRunnable):
    def __init__(self, query, signals):
        super().__init__()
        self._query = query
        self._signals = signals

    def run(self):
        try:
            items = fetch_news(self._query)
            self._signals.done.emit(self._query, items)
        except Exception as exc:
            self._signals.failed.emit(self._query, str(exc))


def _ago(ts: int) -> str:
    if not ts:
        return ""
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(ts, timezone.utc)
    hrs = delta.total_seconds() / 3600
    if hrs < 1:
        return f"{int(delta.total_seconds() / 60)}m ago"
    if hrs < 24:
        return f"{int(hrs)}h ago"
    return f"{int(hrs / 24)}d ago"


class NewsScreen(Screen):
    """Headlines for a selected instrument (opens articles in the browser)."""

    screen_id = "news"
    title = "News"

    def __init__(self, provider) -> None:
        super().__init__()
        self._provider = provider
        self._query = ""
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.failed.connect(self._on_failed)

        self.root.addWidget(self._build_controls())
        panel = Panel("Headlines")
        theme = ACTIVE_THEME
        self._list = QListWidget()
        self._list.setStyleSheet(
            f"background:{theme.bg_base}; color:{theme.text_primary};"
            f"border:none; font-size:13px;"
        )
        self._list.itemActivated.connect(self._open)
        self._list.itemDoubleClicked.connect(self._open)
        panel.add(self._list, stretch=1)
        self._hint = QLabel("Double-click a headline to open it in your browser.")
        self._hint.setStyleSheet(f"color:{theme.text_tertiary}; font-size:11px;")
        panel.add(self._hint)
        self.root.addWidget(panel, stretch=1)

    def _build_controls(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(2, 0, 2, 0)
        self._selector = QComboBox()
        self._selector.setMinimumWidth(240)
        known = {i.uid: i for i in self._provider.instruments()}
        seen = set()
        for uid in list(DASHBOARD_WATCHLIST) + list(known):
            inst = known.get(uid)
            if inst and inst.symbol not in seen and inst.kind == "equity":
                seen.add(inst.symbol)
                self._selector.addItem(f"{inst.symbol} — {inst.name}", inst.symbol)
        self._selector.currentIndexChanged.connect(self._on_select)
        row.addWidget(QLabel("Ticker"))
        row.addWidget(self._selector)
        row.addStretch(1)
        return bar

    def _on_select(self) -> None:
        self._load()

    def _load(self) -> None:
        query = self._selector.currentData()
        if not query:
            return
        self._query = query
        self._list.clear()
        self._list.addItem(QListWidgetItem("Loading headlines…"))
        self._pool.start(_NewsTask(query, self._signals))

    def _on_done(self, query: str, items) -> None:
        if query != self._query:
            return
        theme = ACTIVE_THEME
        self._list.clear()
        if not items:
            self._list.addItem(QListWidgetItem("No recent headlines found."))
            return
        for it in items:
            meta = " · ".join(p for p in (it.get("publisher", ""), _ago(it.get("published", 0))) if p)
            entry = QListWidgetItem(f"{it['title']}\n    {meta}")
            entry.setData(_LINK_ROLE, it.get("link", ""))
            self._list.addItem(entry)

    def _on_failed(self, query: str, message: str) -> None:
        if query != self._query:
            return
        self._list.clear()
        self._list.addItem(QListWidgetItem(f"Couldn't load news: {message}"))

    def _open(self, item: QListWidgetItem) -> None:
        link = item.data(_LINK_ROLE)
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def on_show(self) -> None:
        if not self._list.count():
            self._load()
