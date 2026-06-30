"""A 'coming soon' screen used for not-yet-built sections."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ...theme import ACTIVE_THEME
from .base import Screen


class PlaceholderScreen(Screen):
    """Renders a centered title + note for sections still on the roadmap."""

    def __init__(self, screen_id: str, title: str) -> None:
        super().__init__()
        self.screen_id = screen_id
        self.title = title
        theme = ACTIVE_THEME

        heading = QLabel(title)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet(
            f"color:{theme.text_secondary}; font-size:22px; font-weight:600;"
        )
        note = QLabel("This module is on the roadmap.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color:{theme.text_tertiary}; font-size:13px;")

        self.root.addStretch(1)
        self.root.addWidget(heading)
        self.root.addWidget(note)
        self.root.addStretch(1)
