"""Concrete LLM backends: template (offline), Ollama, llama.cpp, Claude.

All optional dependencies are imported lazily so the module loads everywhere.
``make_backend`` returns the requested backend, falling back to the always-
available :class:`TemplateBackend` when the requested one isn't usable.
"""

from __future__ import annotations

import json
import urllib.request

from .base import LLMConfig


class TemplateBackend:
    """Deterministic, dependency-free generator — always available, offline.

    It does not run a model; it echoes a structured strategy write-up assembled
    from the prompt. This keeps the bot designer fully functional with no model
    installed (and makes it testable).
    """

    @property
    def name(self) -> str:
        return "Template (offline)"

    @property
    def available(self) -> bool:
        return True

    @property
    def offline(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> str:
        # The bot designer renders the actual code from the parsed spec; the
        # template backend just returns a short rationale placeholder.
        return (
            "# Strategy authored by the offline template generator.\n"
            "# (Install a local model via Ollama or llama.cpp, or enable the\n"
            "#  Claude backend, for free-form natural-language authoring.)\n"
        )


class OllamaBackend:
    """Local Ollama daemon (offline). Talks to ``/api/generate`` over HTTP."""

    def __init__(self, config: LLMConfig) -> None:
        self._host = config.host.rstrip("/")
        self._model = config.model or "llama3"
        self._max_tokens = config.max_tokens

    @property
    def name(self) -> str:
        return f"Ollama · {self._model}"

    @property
    def offline(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5):
                return True
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "") -> str:
        body = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"num_predict": self._max_tokens},
            }
        ).encode()
        req = urllib.request.Request(
            f"{self._host}/api/generate", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.load(resp)
        return payload.get("response", "")


class LlamaCppBackend:
    """In-process GGUF model via ``llama-cpp-python`` (offline)."""

    def __init__(self, config: LLMConfig) -> None:
        self._model_path = config.model
        self._max_tokens = config.max_tokens
        self._llm = None

    @property
    def name(self) -> str:
        return "llama.cpp (local GGUF)"

    @property
    def offline(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        if not self._model_path:
            return False
        try:
            import llama_cpp  # type: ignore  # noqa: F401
        except Exception:
            return False
        import os

        return os.path.exists(self._model_path)

    def _ensure(self):
        if self._llm is None:
            from llama_cpp import Llama  # type: ignore

            self._llm = Llama(model_path=self._model_path, n_ctx=4096, verbose=False)
        return self._llm

    def generate(self, prompt: str, system: str = "") -> str:
        llm = self._ensure()
        full = f"{system}\n\n{prompt}" if system else prompt
        out = llm(full, max_tokens=self._max_tokens)
        return out["choices"][0]["text"]


class ClaudeBackend:
    """Anthropic Claude (cloud). Optional; requires the ``anthropic`` SDK + key."""

    def __init__(self, config: LLMConfig) -> None:
        self._model = config.model or "claude-opus-4-8"
        self._max_tokens = max(config.max_tokens, 1024)
        self._client = None

    @property
    def name(self) -> str:
        return f"Claude · {self._model}"

    @property
    def offline(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        import os

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # type: ignore  # noqa: F401
        except Exception:
            return False
        return True

    def _ensure(self):
        if self._client is None:
            import anthropic  # type: ignore

            self._client = anthropic.Anthropic()
        return self._client

    def generate(self, prompt: str, system: str = "") -> str:
        client = self._ensure()
        # Stream to stay under HTTP timeouts on longer generations.
        with client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system or "You are a quantitative trading strategy engineer.",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
        return "".join(b.text for b in message.content if b.type == "text")


def make_backend(config: LLMConfig):
    """Build the requested backend, falling back to the template generator."""
    candidate = None
    if config.backend == "ollama":
        candidate = OllamaBackend(config)
    elif config.backend == "llamacpp":
        candidate = LlamaCppBackend(config)
    elif config.backend == "claude":
        candidate = ClaudeBackend(config)
    if candidate is not None and candidate.available:
        return candidate
    return TemplateBackend()
