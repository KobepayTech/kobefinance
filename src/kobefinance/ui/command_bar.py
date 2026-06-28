"""Top command bar: brand mark plus a command/symbol input.

Typing a bare screen id (e.g. ``dashboard``) or ``go <id>`` navigates; any
other text is emitted as a symbol lookup. This is the seed of a fuller
command palette.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget

from .. import __app_name__
from ..theme import ACTIVE_THEME


class CommandBar(QFrame):
    """Emits :attr:`command` for navigation and :attr:`lookup` for symbols."""

    command = Signal(str)
    lookup = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")  # reuse surface styling
        theme = ACTIVE_THEME

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(12)

        brand = QLabel(__app_name__.upper())
        brand.setStyleSheet(
            f"color:{theme.accent}; font-weight:800; letter-spacing:2px; font-size:14px;"
        )

        self._input = QLineEdit()
        self._input.setObjectName("CommandInput")
        self._input.setPlaceholderText(
            "Type a command (e.g. 'go dashboard') or a symbol, then Enter…"
        )
        self._input.returnPressed.connect(self._on_enter)

        row.addWidget(brand)
        row.addWidget(self._input, stretch=1)

    def _on_enter(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()

        lowered = text.lower()
        if lowered.startswith("go "):
            self.command.emit(lowered[3:].strip())
        elif " " not in lowered:
            # A single token could be a screen id or a symbol; let the window
            # decide. Prefer navigation when it matches a known screen.
            self.command.emit(lowered)
        else:
            self.lookup.emit(text.upper())
