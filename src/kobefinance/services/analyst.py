"""Helpers for the AI Chat screen.

Builds a live-market context block to ground LLM answers, and provides a
deterministic rule-based answer so the chat is useful even with no model
installed (the offline template backend).
"""

from __future__ import annotations

import re

from .universe import DASHBOARD_WATCHLIST

ANALYST_SYSTEM = (
    "You are KobeFinance's market analyst. Be concise and practical. Use the "
    "LIVE MARKET DATA block for current prices; never invent quotes. Add a one-"
    "line risk caveat when giving any trade-related view. This is not financial "
    "advice."
)


def _index_symbols(provider) -> dict[str, str]:
    """Map upper-case symbol and uid -> uid for quick mention lookup."""
    index: dict[str, str] = {}
    for inst in provider.instruments():
        index[inst.symbol.upper()] = inst.uid
        index[inst.uid.upper()] = inst.uid
    return index


def find_mentions(provider, message: str) -> list[str]:
    """Return uids for instruments mentioned in *message* (by symbol or uid)."""
    index = _index_symbols(provider)
    tokens = set(re.findall(r"[A-Za-z][A-Za-z0-9\-\.]{1,14}", message.upper()))
    seen: list[str] = []
    for tok in tokens:
        uid = index.get(tok)
        if uid and uid not in seen:
            seen.append(uid)
    return seen


def _fmt(provider, uid: str) -> str | None:
    q = provider.quote(uid)
    if q is None:
        return None
    return f"{q.symbol} ({q.exchange}): {q.price:g} {q.currency} ({q.change_pct:+.2f}%)"


def build_context(provider, message: str, *, max_default: int = 6) -> str:
    """A LIVE MARKET DATA block for the prompt: mentioned names, else movers."""
    uids = find_mentions(provider, message)
    if not uids:
        known = set(provider.symbols())
        uids = [u for u in DASHBOARD_WATCHLIST if u in known][:max_default]
    lines = [line for u in uids if (line := _fmt(provider, u))]
    if not lines:
        return ""
    return "LIVE MARKET DATA:\n" + "\n".join(lines)


def basic_answer(provider, message: str) -> str:
    """Deterministic offline answer used when no real LLM backend is available."""
    uids = find_mentions(provider, message)
    if uids:
        lines = [line for u in uids if (line := _fmt(provider, u))]
        body = "\n".join(lines)
        return (
            f"Here's the latest on what you mentioned:\n{body}\n\n"
            "I'm running the offline template backend, so I can quote live data "
            "but can't reason in depth. Configure a local model (Ollama or "
            "llama.cpp) or the Claude backend in Settings for full analysis. "
            "Not financial advice."
        )
    known = set(provider.symbols())
    movers = [u for u in DASHBOARD_WATCHLIST if u in known][:6]
    snapshot = "\n".join(line for u in movers if (line := _fmt(provider, u)))
    return (
        "I can pull live quotes and answer simple market questions offline. "
        "Mention a symbol (e.g. AAPL, NPN, EURUSD, BTC-USD) and I'll quote it.\n\n"
        f"A quick market snapshot:\n{snapshot}\n\n"
        "For deeper analysis, enable a local or Claude LLM backend in Settings."
    )
