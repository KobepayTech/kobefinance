"""Settings: persist LLM backend, trading defaults, and MT5 connection."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ...services.llm.backends import make_backend
from ...services.settings import Settings
from ...theme import ACTIVE_THEME
from ..widgets.panel import Panel
from .base import Screen

_BACKENDS = [
    ("template", "Offline template (no model)"),
    ("ollama", "Ollama (local daemon)"),
    ("llamacpp", "llama.cpp (local GGUF file)"),
    ("claude", "Claude (cloud API)"),
]


class SettingsScreen(Screen):
    """A small form persisting user preferences via :class:`Settings`."""

    screen_id = "settings"
    title = "Settings"

    def __init__(self, provider=None, settings: Settings | None = None) -> None:
        super().__init__()
        self._settings = settings or Settings()
        theme = ACTIVE_THEME

        panel = Panel("Preferences")
        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setSpacing(8)

        self._backend = QComboBox()
        for value, label in _BACKENDS:
            self._backend.addItem(label, value)
        self._set_combo(self._backend, str(self._settings.get("llm.backend")))
        form.addRow("LLM backend", self._backend)

        self._model = QLineEdit(str(self._settings.get("llm.model") or ""))
        self._model.setPlaceholderText("e.g. llama3, /path/model.gguf, or claude-opus-4-8")
        form.addRow("LLM model", self._model)

        self._ollama = QLineEdit(str(self._settings.get("llm.ollama_host")))
        form.addRow("Ollama host", self._ollama)

        self._cash = QDoubleSpinBox()
        self._cash.setRange(100.0, 100_000_000.0)
        self._cash.setDecimals(0)
        self._cash.setValue(self._settings.starting_cash())
        form.addRow("Paper starting cash", self._cash)

        self._leverage = QDoubleSpinBox()
        self._leverage.setRange(1.0, 100.0)
        self._leverage.setDecimals(1)
        self._leverage.setValue(self._settings.max_leverage())
        form.addRow("Max leverage", self._leverage)

        self._mt5_login = QLineEdit(str(self._settings.get("mt5.login") or ""))
        form.addRow("MT5 login", self._mt5_login)
        self._mt5_server = QLineEdit(str(self._settings.get("mt5.server") or ""))
        form.addRow("MT5 server", self._mt5_server)

        panel.add(form_host)

        self._save = QPushButton("Save and test backend")
        self._save.setObjectName("Accent")
        self._save.clicked.connect(self._save_clicked)
        panel.add(self._save)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{theme.text_tertiary};")
        panel.add(self._status)

        note = QLabel(
            "The MT5 password is never persisted to disk — enter it in the MT5 "
            "terminal. 'Offline template' needs no model and always works."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{theme.text_tertiary}; font-size:12px;")
        panel.add(note)
        panel.add_stretch()
        self.root.addWidget(panel, stretch=1)

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _save_clicked(self) -> None:
        self._settings.set("llm.backend", self._backend.currentData())
        self._settings.set("llm.model", self._model.text().strip())
        self._settings.set("llm.ollama_host", self._ollama.text().strip())
        self._settings.set("trading.starting_cash", self._cash.value())
        self._settings.set("trading.max_leverage", self._leverage.value())
        self._settings.set("mt5.login", self._mt5_login.text().strip())
        self._settings.set("mt5.server", self._mt5_server.text().strip())

        backend = make_backend(self._settings.llm_config())
        kind = "offline" if backend.offline else "cloud"
        self._status.setText(
            f"Saved. Active LLM backend: {backend.name} ({kind}). "
            "Trading defaults apply to new sessions."
        )
