"""Application bootstrap: build the provider, register screens, run Qt."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from . import __app_name__
from .services.live_data import HybridProvider
from .services.market_data import MarketDataProvider, SimulatedProvider
from .services.settings import Settings
from .services.trading.bot_runner import BotManager
from .services.trading.paper_broker import PaperBroker
from .ui.main_window import MainWindow
from .ui.screens.ai_chat import AiChatScreen
from .ui.screens.base import REGISTRY, ScreenSpec, register
from .ui.screens.bot_designer import BotDesignerScreen
from .ui.screens.charts import ChartsScreen
from .ui.screens.dashboard import DashboardScreen
from .ui.screens.equity_research import EquityResearchScreen
from .ui.screens.funds import FundsScreen
from .ui.screens.markets import MarketsScreen
from .ui.screens.news import NewsScreen
from .ui.screens.portfolio import PortfolioScreen
from .ui.screens.relationship_map import RelationshipMapScreen
from .ui.screens.settings_screen import SettingsScreen
from .ui.screens.trading import TradingScreen
from .ui.screens.watchlist import WatchlistScreen


def register_screens(provider: MarketDataProvider, settings: Settings | None = None) -> None:
    """Populate the screen registry. Idempotent for repeated app launches."""
    REGISTRY.clear()
    settings = settings or Settings()
    # One paper broker + bot manager shared across Trading, Portfolio, and the
    # Strategy Lab (so a designed bot can auto-trade and show up on the desk).
    broker = PaperBroker(
        provider,
        starting_cash=settings.starting_cash(),
        max_leverage=settings.max_leverage(),
    )
    bot_manager = BotManager()
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
    register(
        ScreenSpec(
            screen_id="charts",
            title="Charts",
            factory=lambda: ChartsScreen(provider),
            section="General",
        )
    )
    register(
        ScreenSpec(
            screen_id="watchlist",
            title="Watchlist",
            factory=lambda: WatchlistScreen(provider, settings),
            section="General",
        )
    )
    register(
        ScreenSpec(
            screen_id="trading",
            title="Trading",
            factory=lambda: TradingScreen(provider, broker, settings, bot_manager),
            section="Trading",
        )
    )
    register(
        ScreenSpec(
            screen_id="portfolio",
            title="Portfolio",
            factory=lambda: PortfolioScreen(provider, broker, settings),
            section="Trading",
        )
    )
    register(
        ScreenSpec(
            screen_id="bots",
            title="Strategy Lab",
            factory=lambda: BotDesignerScreen(provider, broker, bot_manager),
            section="Trading",
        )
    )
    register(
        ScreenSpec(
            screen_id="equity_research",
            title="Equity Research",
            factory=lambda: EquityResearchScreen(provider),
            section="Intelligence",
        )
    )
    register(
        ScreenSpec(
            screen_id="relationships",
            title="Relationship Map",
            factory=lambda: RelationshipMapScreen(provider),
            section="Intelligence",
        )
    )
    register(
        ScreenSpec(
            screen_id="funds",
            title="Funds",
            factory=lambda: FundsScreen(provider),
            section="Intelligence",
        )
    )
    register(
        ScreenSpec(
            screen_id="news",
            title="News",
            factory=lambda: NewsScreen(provider),
            section="Intelligence",
        )
    )
    register(
        ScreenSpec(
            screen_id="ai_chat",
            title="AI Chat",
            factory=lambda: AiChatScreen(provider, settings),
            section="Intelligence",
        )
    )
    register(
        ScreenSpec(
            screen_id="settings",
            title="Settings",
            factory=lambda: SettingsScreen(provider, settings),
            section="System",
        )
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kobefinance", description=__app_name__)
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use only the offline simulated feed (no network).",
    )
    # Drop Qt-specific flags Qt itself consumes; parse only what we know.
    known, _ = parser.parse_known_args(argv[1:])
    return known


def main(argv: list[str] | None = None) -> int:
    """Launch the terminal. Returns the Qt exit code."""
    argv = argv if argv is not None else sys.argv
    args = _parse_args(argv)

    app = QApplication(argv)
    app.setApplicationName(__app_name__)

    if args.simulate:
        provider: MarketDataProvider = SimulatedProvider()
        source_label = "SIMULATED FEED"
    else:
        provider = HybridProvider()
        provider.start_live()
        app.aboutToQuit.connect(provider.stop_live)
        source_label = "LIVE (Yahoo) + SIMULATED"

    register_screens(provider)

    window = MainWindow(provider, source_label=source_label)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
