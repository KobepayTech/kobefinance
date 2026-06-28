"""Number/price formatting helpers used across screens."""

from __future__ import annotations


def fmt_price(value: float) -> str:
    """Format a price with thousands separators and two decimals."""
    return f"{value:,.2f}"


def fmt_change(value: float) -> str:
    """Format an absolute change with an explicit sign."""
    return f"{value:+,.2f}"


def fmt_pct(value: float) -> str:
    """Format a percentage with an explicit sign and one decimal."""
    return f"{value:+.2f}%"


def arrow(value: float) -> str:
    """Return a directional glyph for a signed value."""
    if value > 0:
        return "▲"  # ▲
    if value < 0:
        return "▼"  # ▼
    return "—"  # —
