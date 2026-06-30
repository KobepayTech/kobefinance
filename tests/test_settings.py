"""Tests for the settings store and derived LLM config."""

from __future__ import annotations

from kobefinance.services.settings import Settings


def test_defaults_apply_when_unset():
    s = Settings(store={})
    assert s.get("llm.backend") == "template"
    assert s.starting_cash() == 100_000.0
    assert s.max_leverage() == 1.0


def test_set_and_get_roundtrip():
    store: dict = {}
    s = Settings(store=store)
    s.set("llm.backend", "ollama")
    s.set("trading.starting_cash", 25_000.0)
    assert s.get("llm.backend") == "ollama"
    assert s.starting_cash() == 25_000.0
    # Persisted into the injected store.
    assert store["llm.backend"] == "ollama"


def test_llm_config_marks_cloud_as_online():
    s = Settings(store={"llm.backend": "claude", "llm.model": "claude-opus-4-8"})
    cfg = s.llm_config()
    assert cfg.backend == "claude"
    assert cfg.model == "claude-opus-4-8"
    assert cfg.offline is False


def test_llm_config_offline_for_local_backends():
    assert Settings(store={"llm.backend": "ollama"}).llm_config().offline is True
    assert Settings(store={"llm.backend": "template"}).llm_config().offline is True
