"""Application bootstrap: build the provider, register screens, run Qt."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import __app_name__
from .services.market_data import MarketDataProvider, SimulatedProvider
from .ui.main_window import MainWindow
from .ui.screens.base import REGISTRY, ScreenSpec, register
from .ui.screens.dashboard import DashboardScreen
from .ui.screens.markets import MarketsScreen
from .ui.screens.placeholder import PlaceholderScreen

# Sections shown in the sidebar that are not yet built. Each becomes a
# placeholder screen until its real module lands on the roadmap.
ROADMAP_SCREENS: list[tuple[str, str]] = [
    ("watchlist", "Watchlist"),
    ("equity_research", "Equity Research"),
    ("portfolio", "Portfolio"),
    ("news", "News"),
    ("ai_chat", "AI Chat"),
    ("settings", "Settings"),
]


def register_screens(provider: MarketDataProvider) -> None:
    """Populate the screen registry. Idempotent for repeated app launches."""
    REGISTRY.clear()
    register(
        ScreenSpec(
            screen_id="dashboard",
            title="Dashboard",
            factory=lambda: DashboardScreen(provider),
            section="General",
        )
    )
    register(
        ScreenSpec(
            screen_id="markets",
            title="Markets",
            factory=lambda: MarketsScreen(provider),
            section="General",
        )
    )
    for screen_id, title in ROADMAP_SCREENS:
        register(
            ScreenSpec(
                screen_id=screen_id,
                title=title,
                # Bind loop vars as defaults so each factory is distinct.
                factory=lambda sid=screen_id, t=title: PlaceholderScreen(sid, t),
            )
        )


def main(argv: list[str] | None = None) -> int:
    """Launch the terminal. Returns the Qt exit code."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)

    provider = SimulatedProvider()
    register_screens(provider)

    window = MainWindow(provider)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
