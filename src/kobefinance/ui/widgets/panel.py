"""A titled surface that other content sits inside."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Panel(QFrame):
    """A bordered card with an uppercase title and a content area.

    Add child widgets with :meth:`add` — they stack vertically below the
    title. The frame is named ``Panel`` so the global stylesheet styles it.
    """

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 12)
        self._layout.setSpacing(8)

        self._title = QLabel(title.upper())
        self._title.setObjectName("PanelTitle")
        self._layout.addWidget(self._title)

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        """Append *widget* to the panel body."""
        self._layout.addWidget(widget, stretch)

    def add_stretch(self) -> None:
        """Push subsequent content to the top."""
        self._layout.addStretch(1)

    def set_title(self, title: str) -> None:
        self._title.setText(title.upper())

    @property
    def body(self) -> QVBoxLayout:
        """The vertical layout holding panel content."""
        return self._layout
