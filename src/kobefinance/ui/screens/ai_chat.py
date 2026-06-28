"""AI Chat: a market analyst backed by the configured LLM (offline or cloud).

Each turn grounds the model with a live market-data block. With no model
installed, a deterministic rule-based analyst answers from live quotes so the
screen is useful offline. Generation runs off the UI thread.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QWidget

from ...services.analyst import ANALYST_SYSTEM, basic_answer, build_context
from ...services.llm.backends import make_backend
from ...services.settings import Settings
from ...theme import ACTIVE_THEME
from ..widgets.panel import Panel
from .base import Screen


class _Signals(QObject):
    reply = Signal(str, str)  # backend_name, text


class _ChatTask(QRunnable):
    def __init__(self, provider, settings, message, signals):
        super().__init__()
        self._provider = provider
        self._settings = settings
        self._message = message
        self._signals = signals

    def run(self):
        backend = make_backend(self._settings.llm_config())
        try:
            if backend.name.startswith("Template"):
                text = basic_answer(self._provider, self._message)
            else:
                context = build_context(self._provider, self._message)
                prompt = f"{context}\n\nUser: {self._message}" if context else self._message
                text = backend.generate(prompt, system=ANALYST_SYSTEM).strip()
                if not text:
                    text = basic_answer(self._provider, self._message)
        except Exception as exc:
            text = f"(LLM error: {exc})\n\n" + basic_answer(self._provider, self._message)
        self._signals.reply.emit(backend.name, text)


class AiChatScreen(Screen):
    """Conversational market analyst."""

    screen_id = "ai_chat"
    title = "AI Chat"

    def __init__(self, provider, settings: Settings | None = None) -> None:
        super().__init__()
        self._provider = provider
        self._settings = settings or Settings()
        self._pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.reply.connect(self._on_reply)

        panel = Panel("Market Analyst")
        theme = ACTIVE_THEME
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            f"background:{theme.bg_base}; color:{theme.text_primary}; font-size:13px;"
        )
        panel.add(self._log, stretch=1)

        entry = QWidget()
        row = QHBoxLayout(entry)
        row.setContentsMargins(0, 4, 0, 0)
        self._input = QLineEdit()
        self._input.setObjectName("CommandInput")
        self._input.setPlaceholderText(
            "Ask about a symbol or the market — e.g. 'How is AAPL doing vs NPN?' "
            "or 'What's USDZAR at?'"
        )
        self._input.returnPressed.connect(self._send)
        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("Accent")
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._input, stretch=1)
        row.addWidget(self._send_btn)
        panel.add(entry)
        self.root.addWidget(panel, stretch=1)

        self._append("Analyst", "Ask me about any symbol or the market. I use live "
                     "data; configure a local or Claude model in Settings for deeper analysis.")

    def _append(self, who: str, text: str) -> None:
        theme = ACTIVE_THEME
        color = theme.accent if who != "You" else theme.cyan
        safe = text.replace("\n", "<br>")
        self._log.append(
            f"<p><b style='color:{color}'>{who}:</b> "
            f"<span style='color:{theme.text_primary}'>{safe}</span></p>"
        )

    def _send(self) -> None:
        message = self._input.text().strip()
        if not message:
            return
        self._input.clear()
        self._append("You", message)
        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._send_btn.setText("…")
        self._pool.start(_ChatTask(self._provider, self._settings, message, self._signals))

    def _on_reply(self, backend_name: str, text: str) -> None:
        self._append(f"Analyst · {backend_name}", text)
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._send_btn.setText("Send")
        self._input.setFocus()
