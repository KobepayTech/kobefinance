"""The application shell: command bar, ticker, sidebar, screens, status bar.

Screens are created lazily from :data:`REGISTRY` and cached in a
``QStackedWidget``. Navigation flows through one ``show_screen`` path so the
sidebar, command bar, and programmatic calls stay in sync.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__
from ..services.market_data import MarketDataProvider, SimulatedProvider
from ..theme import ACTIVE_THEME, build_stylesheet
from .command_bar import CommandBar
from .nav_sidebar import NavSidebar
from .screens.base import REGISTRY, Screen
from .status_bar import StatusBar
from .ticker_bar import TickerBar


class MainWindow(QMainWindow):
    """Top-level window hosting the whole terminal."""

    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        *,
        source_label: str = "SIMULATED FEED",
    ) -> None:
        super().__init__()
        self._provider = provider or SimulatedProvider()
        self._screens: dict[str, Screen] = {}
        self._current: Screen | None = None

        self.setWindowTitle(__app_name__)
        self.resize(1280, 800)
        self.setStyleSheet(build_stylesheet(ACTIVE_THEME))

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._command_bar = CommandBar()
        self._command_bar.command.connect(self._on_command)
        self._command_bar.lookup.connect(self._on_lookup)
        outer.addWidget(self._command_bar)

        self._ticker = TickerBar(self._provider)
        outer.addWidget(self._ticker)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = NavSidebar(REGISTRY)
        self._sidebar.navigate.connect(self.show_screen)
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        body.addWidget(self._stack, stretch=1)
        outer.addLayout(body, stretch=1)

        self._status = StatusBar(source_label)
        outer.addWidget(self._status)

        self.setCentralWidget(central)

        self._ticker.start()
        if REGISTRY:
            self._sidebar.select(REGISTRY[0].screen_id)
            self.show_screen(REGISTRY[0].screen_id)

    # -- navigation -----------------------------------------------------------

    def _get_or_create(self, screen_id: str) -> Screen | None:
        if screen_id in self._screens:
            return self._screens[screen_id]
        for spec in REGISTRY:
            if spec.screen_id == screen_id:
                screen = spec.factory()
                self._screens[screen_id] = screen
                self._stack.addWidget(screen)
                return screen
        return None

    def show_screen(self, screen_id: str) -> None:
        """Make *screen_id* the active screen, creating it if needed."""
        screen = self._get_or_create(screen_id)
        if screen is None:
            self._status.flash(f"Unknown screen: {screen_id}")
            return

        if self._current is not None and self._current is not screen:
            self._current.on_hide()

        self._stack.setCurrentWidget(screen)
        self._sidebar.select(screen_id)
        screen.on_show()
        self._current = screen
        self._status.flash(f"Opened {screen.title}")

    def _on_command(self, token: str) -> None:
        if any(s.screen_id == token for s in REGISTRY):
            self.show_screen(token)
            return
        # Not a screen — try treating it as a ticker symbol.
        uid = self._resolve_symbol(token)
        if uid:
            self._open_chart(uid)
        else:
            self._status.flash(f"No screen or symbol '{token}'")

    def _on_lookup(self, text: str) -> None:
        uid = self._resolve_symbol(text)
        if uid:
            self._open_chart(uid)
        else:
            self._status.flash(f"Symbol not found: {text}")

    def _resolve_symbol(self, text: str) -> str | None:
        """Resolve a typed symbol or uid to an instrument uid."""
        text = text.strip().upper()
        if not text:
            return None
        known = {i.uid: i for i in self._provider.instruments()}
        if text in known:  # already a uid like NPN.JSE
            return text
        for uid, inst in known.items():
            if inst.symbol.upper() == text:
                return uid
        return None

    def _open_chart(self, uid: str) -> None:
        screen = self._get_or_create("charts")
        if screen is not None and hasattr(screen, "set_symbol"):
            self.show_screen("charts")
            screen.set_symbol(uid)

    # -- lifecycle ------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._ticker.stop()
        if self._current is not None:
            self._current.on_hide()
        super().closeEvent(event)

    def provider(self) -> MarketDataProvider:
        return self._provider
