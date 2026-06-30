"""Bottom status bar showing connection state and a transient message."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from .. import __version__
from ..theme import ACTIVE_THEME


class StatusBar(QFrame):
    """A thin footer: data-source indicator, flash messages, version."""

    def __init__(self, source_label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusBar")
        self.setFixedHeight(26)
        theme = ACTIVE_THEME

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{theme.positive};")
        source = QLabel(source_label)
        source.setStyleSheet(f"color:{theme.text_secondary};")

        self._message = QLabel("")
        self._message.setStyleSheet(f"color:{theme.text_tertiary};")

        version = QLabel(f"v{__version__}")
        version.setStyleSheet(f"color:{theme.text_tertiary}; font-family:{theme.font_mono};")

        row.addWidget(dot)
        row.addWidget(source)
        row.addSpacing(16)
        row.addWidget(self._message)
        row.addStretch(1)
        row.addWidget(version)

    def flash(self, text: str, msec: int = 4000) -> None:
        """Show *text* for *msec* milliseconds, then clear it."""
        self._message.setText(text)
        QTimer.singleShot(msec, lambda: self._message.setText(""))
