"""Persisted user settings.

A thin typed wrapper over a key/value store. In the app it persists via
``QSettings`` (no file management needed); tests can inject a plain dict.
Sensitive values (the MT5 password) are kept out of persistence by default.
"""

from __future__ import annotations

from typing import MutableMapping

from .llm.base import LLMConfig

ORG = "KobePayTech"
APP = "KobeFinanceTerminal"

DEFAULTS: dict[str, object] = {
    "llm.backend": "template",
    "llm.model": "",
    "llm.ollama_host": "http://localhost:11434",
    "trading.starting_cash": 100_000.0,
    "trading.max_leverage": 1.0,
    "mt5.login": "",
    "mt5.server": "",
}


def _qsettings_store() -> MutableMapping:
    """A dict-like view over QSettings (created lazily, app-side only)."""
    from PySide6.QtCore import QSettings

    qs = QSettings(ORG, APP)

    class _Store:
        def get(self, key, default=None):
            return qs.value(key, default)

        def __setitem__(self, key, value):
            qs.setValue(key, value)

        def __getitem__(self, key):
            return qs.value(key)

        def __contains__(self, key):
            return qs.contains(key)

    return _Store()  # type: ignore[return-value]


class Settings:
    """Typed accessors over a key/value store."""

    def __init__(self, store: MutableMapping | None = None) -> None:
        self._store = store if store is not None else _qsettings_store()

    def get(self, key: str, default=None):
        value = self._store.get(key, None)
        if value is None:
            return DEFAULTS.get(key, default)
        return value

    def set(self, key: str, value) -> None:
        self._store[key] = value

    # -- typed helpers --------------------------------------------------------

    def llm_config(self) -> LLMConfig:
        backend = str(self.get("llm.backend"))
        return LLMConfig(
            backend=backend,
            model=str(self.get("llm.model") or ""),
            host=str(self.get("llm.ollama_host")),
            offline=backend in ("template", "ollama", "llamacpp"),
        )

    def starting_cash(self) -> float:
        return float(self.get("trading.starting_cash"))

    def max_leverage(self) -> float:
        return float(self.get("trading.max_leverage"))
