"""Number/price formatting helpers used across screens."""

from __future__ import annotations

# Display symbols for currencies the terminal quotes in. Currencies without a
# common single glyph fall back to the ISO code (handled in ``fmt_money``).
CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "GBP": "£",
    "ZAR": "R",
    "NGN": "₦",
    "KES": "KSh",
    "EGP": "E£",
    "GHS": "₵",
    "MUR": "₨",
    "MAD": "MAD ",
    "XOF": "CFA ",
    "XAF": "FCFA ",
    "TZS": "TSh",
    "UGX": "USh",
    "RWF": "FRw",
    "ZMW": "ZK",
    "BWP": "P",
    "NAD": "N$",
    "TND": "DT ",
    "DZD": "DA ",
    "MWK": "MK",
    "ZWG": "Z$",
}


def fmt_price(value: float) -> str:
    """Format a price with thousands separators and two decimals."""
    return f"{value:,.2f}"


def fmt_money(value: float, currency: str) -> str:
    """Format *value* in *currency*, prefixing a symbol when one is known.

    Falls back to a trailing ISO code (e.g. ``1,234.00 ETB``) for currencies
    without a common glyph.
    """
    amount = f"{value:,.2f}"
    symbol = CURRENCY_SYMBOLS.get(currency)
    if symbol is None:
        return f"{amount} {currency}"
    return f"{symbol}{amount}"


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
