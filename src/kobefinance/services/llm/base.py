"""LLM backend interface and configuration.

A backend turns a prompt into text. The bot designer uses it only to author
human-readable strategy code; the backtest itself always runs a vetted
strategy parsed from the description, so model output is never executed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMConfig:
    backend: str = "template"   # "template" | "ollama" | "llamacpp" | "claude"
    model: str = ""             # backend-specific model name / path
    host: str = "http://localhost:11434"   # Ollama daemon
    max_tokens: int = 1500
    offline: bool = True        # whether the chosen backend runs locally


class LLMBackend(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool:
        """True if this backend can actually serve a request right now."""
        ...

    @property
    def offline(self) -> bool:
        """True if no network/cloud is involved."""
        ...

    def generate(self, prompt: str, system: str = "") -> str: ...
