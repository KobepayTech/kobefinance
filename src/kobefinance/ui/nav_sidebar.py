"""Left navigation sidebar listing all registered screens."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from .screens.base import ScreenSpec

_ID_ROLE = 0x0100  # Qt.UserRole


class NavSidebar(QListWidget):
    """A flat list of screens; emits :attr:`navigate` with the chosen id."""

    navigate = Signal(str)

    def __init__(self, specs: list[ScreenSpec], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavList")
        self.setFixedWidth(190)

        for spec in specs:
            item = QListWidgetItem(spec.title)
            item.setData(_ID_ROLE, spec.screen_id)
            self.addItem(item)

        self.currentItemChanged.connect(self._on_change)

    def _on_change(self, current: QListWidgetItem | None, _previous) -> None:
        if current is not None:
            self.navigate.emit(current.data(_ID_ROLE))

    def select(self, screen_id: str) -> None:
        """Highlight the row for *screen_id* without emitting twice."""
        for i in range(self.count()):
            if self.item(i).data(_ID_ROLE) == screen_id:
                self.setCurrentRow(i)
                return
