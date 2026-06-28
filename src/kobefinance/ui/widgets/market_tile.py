"""A compact quote tile: symbol, price, and signed change."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...models import Quote
from ...theme import ACTIVE_THEME
from ..formatting import arrow, fmt_change, fmt_pct, fmt_price


def _elide(text: str, limit: int) -> str:
    """Truncate *text* with an ellipsis if it exceeds *limit* characters."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


class MarketTile(QFrame):
    """Shows one instrument's live price and movement.

    Call :meth:`update_quote` on each refresh; the change figures recolor
    green/red automatically based on direction.
    """

    def __init__(self, quote: Quote, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(215)

        theme = ACTIVE_THEME
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        # Left column: symbol over (elided) company name.
        left = QVBoxLayout()
        left.setSpacing(2)
        self._symbol = QLabel(quote.symbol)
        self._symbol.setStyleSheet(
            f"color:{theme.text_primary}; font-weight:700; font-size:15px;"
        )
        self._name = QLabel(_elide(quote.name, 16))
        self._name.setToolTip(quote.name)
        self._name.setStyleSheet(f"color:{theme.text_tertiary}; font-size:11px;")
        left.addWidget(self._symbol)
        left.addWidget(self._name)

        # Right column: price over signed change, right-aligned.
        right = QVBoxLayout()
        right.setSpacing(2)
        self._price = QLabel()
        self._price.setStyleSheet(
            f"color:{theme.text_primary}; font-family:{theme.font_mono}; font-size:18px;"
        )
        self._price.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._change = QLabel()
        self._change.setStyleSheet(f"font-family:{theme.font_mono}; font-size:12px;")
        self._change.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.addWidget(self._price)
        right.addWidget(self._change)

        outer.addLayout(left, stretch=1)
        outer.addLayout(right)

        self.update_quote(quote)

    def update_quote(self, quote: Quote) -> None:
        theme = ACTIVE_THEME
        color = theme.signed_color(quote.change)
        self._price.setText(fmt_price(quote.price))
        self._change.setText(
            f"{arrow(quote.change)} {fmt_change(quote.change)}  {fmt_pct(quote.change_pct)}"
        )
        self._change.setStyleSheet(
            f"color:{color}; font-family:{theme.font_mono}; font-size:12px;"
        )
