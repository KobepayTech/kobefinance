"""Screen base class and a lightweight registry.

Screens are self-describing: each carries a stable ``screen_id`` and a
human ``title``. The :data:`REGISTRY` maps ids to specs so the navigation
sidebar and the router can be built from one list instead of hard-wiring
every screen into the main window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import QVBoxLayout, QWidget


class Screen(QWidget):
    """Base for every full-page screen in the terminal.

    Subclasses set :attr:`screen_id` / :attr:`title` and build their UI in
    ``__init__``. Override :meth:`on_show` / :meth:`on_hide` to start and
    stop work (timers, subscriptions) only while the screen is visible.
    """

    screen_id: str = ""
    title: str = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(14, 14, 14, 14)
        self.root.setSpacing(12)

    def on_show(self) -> None:  # noqa: D401 - hook
        """Called when this screen becomes the active screen."""

    def on_hide(self) -> None:  # noqa: D401 - hook
        """Called when this screen stops being the active screen."""


@dataclass(frozen=True)
class ScreenSpec:
    """Metadata + factory for a registered screen."""

    screen_id: str
    title: str
    factory: Callable[[], Screen]
    section: str = "General"


REGISTRY: list[ScreenSpec] = []


def register(spec: ScreenSpec) -> None:
    """Add a screen to the global registry (id must be unique)."""
    if any(s.screen_id == spec.screen_id for s in REGISTRY):
        raise ValueError(f"duplicate screen id: {spec.screen_id}")
    REGISTRY.append(spec)
