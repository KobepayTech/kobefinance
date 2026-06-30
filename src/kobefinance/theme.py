"""Theme tokens and stylesheet generation.

A theme is a flat set of named color/typography tokens. Custom widgets read
tokens directly; chrome (buttons, scrollbars, panels) is styled through a
generated Qt stylesheet so there are no hard-coded colors scattered across
the UI. Swapping ``ACTIVE_THEME`` re-skins the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    """A complete color + typography palette for one look."""

    name: str

    # Backgrounds, darkest to lightest.
    bg_base: str
    bg_surface: str
    bg_raised: str
    bg_hover: str

    # Borders / separators.
    border_dim: str
    border_med: str
    border_bright: str

    # Text hierarchy.
    text_primary: str
    text_secondary: str
    text_tertiary: str

    # Accent (the brand color of the theme).
    accent: str
    accent_dim: str
    text_on_accent: str

    # Semantic colors with consistent meaning everywhere.
    positive: str
    negative: str
    warning: str
    info: str
    cyan: str

    # Typography.
    font_ui: str
    font_mono: str
    font_size: int = 13

    # Multi-series chart palette.
    chart_series: tuple[str, ...] = field(default_factory=tuple)

    def signed_color(self, value: float) -> str:
        """Return the color that should render a signed number."""
        if value > 0:
            return self.positive
        if value < 0:
            return self.negative
        return self.text_secondary


OBSIDIAN = Theme(
    name="Obsidian",
    bg_base="#0A0B0D",
    bg_surface="#121419",
    bg_raised="#1A1D24",
    bg_hover="#232730",
    border_dim="#1E222A",
    border_med="#2A2F3A",
    border_bright="#3D4452",
    text_primary="#E6E8EC",
    text_secondary="#9AA0AC",
    text_tertiary="#5C6472",
    accent="#F5A623",
    accent_dim="#5A4316",
    text_on_accent="#0A0B0D",
    positive="#2ECC71",
    negative="#FF5252",
    warning="#FFB020",
    info="#4D9DE0",
    cyan="#34D3EB",
    font_ui='"Segoe UI", "Helvetica Neue", system-ui, sans-serif',
    font_mono='"JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo", monospace',
    font_size=13,
    chart_series=("#F5A623", "#34D3EB", "#2ECC71", "#FF5252", "#B07CF5", "#4D9DE0"),
)

# The single source of truth for the active look. Widgets import this.
ACTIVE_THEME: Theme = OBSIDIAN


def build_stylesheet(theme: Theme) -> str:
    """Generate the application-wide Qt stylesheet for *theme*."""
    return f"""
    QWidget {{
        background-color: {theme.bg_base};
        color: {theme.text_primary};
        font-family: {theme.font_ui};
        font-size: {theme.font_size}px;
    }}

    QToolTip {{
        background-color: {theme.bg_raised};
        color: {theme.text_primary};
        border: 1px solid {theme.border_bright};
        padding: 4px 6px;
    }}

    QFrame#Panel, QFrame#Card {{
        background-color: {theme.bg_surface};
        border: 1px solid {theme.border_dim};
        border-radius: 6px;
    }}

    QLabel#PanelTitle {{
        color: {theme.text_secondary};
        font-weight: 600;
        letter-spacing: 1px;
    }}

    /* ---- Navigation sidebar ---- */
    QListWidget#NavList {{
        background-color: {theme.bg_surface};
        border: none;
        border-right: 1px solid {theme.border_dim};
        outline: 0;
        padding-top: 6px;
    }}
    QListWidget#NavList::item {{
        color: {theme.text_secondary};
        padding: 9px 16px;
        border-left: 2px solid transparent;
    }}
    QListWidget#NavList::item:hover {{
        background-color: {theme.bg_hover};
        color: {theme.text_primary};
    }}
    QListWidget#NavList::item:selected {{
        background-color: {theme.bg_raised};
        color: {theme.accent};
        border-left: 2px solid {theme.accent};
    }}

    /* ---- Command bar ---- */
    QLineEdit#CommandInput {{
        background-color: {theme.bg_raised};
        color: {theme.text_primary};
        border: 1px solid {theme.border_med};
        border-radius: 4px;
        padding: 6px 10px;
        selection-background-color: {theme.accent_dim};
    }}
    QLineEdit#CommandInput:focus {{
        border: 1px solid {theme.accent};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        background-color: {theme.bg_raised};
        color: {theme.text_primary};
        border: 1px solid {theme.border_med};
        border-radius: 4px;
        padding: 5px 14px;
    }}
    QPushButton:hover {{
        background-color: {theme.bg_hover};
        border: 1px solid {theme.border_bright};
    }}
    QPushButton:pressed {{
        background-color: {theme.accent_dim};
    }}
    QPushButton#Accent {{
        background-color: {theme.accent};
        color: {theme.text_on_accent};
        border: none;
        font-weight: 600;
    }}

    /* ---- Status / ticker bars ---- */
    QFrame#StatusBar, QFrame#TickerBar {{
        background-color: {theme.bg_surface};
        border-top: 1px solid {theme.border_dim};
    }}
    QFrame#TickerBar {{
        border-top: none;
        border-bottom: 1px solid {theme.border_dim};
    }}

    /* ---- Tables ---- */
    QTableWidget, QTreeWidget {{
        background-color: {theme.bg_surface};
        alternate-background-color: {theme.bg_raised};
        color: {theme.text_primary};
        border: none;
        gridline-color: {theme.border_dim};
        selection-background-color: {theme.accent_dim};
        selection-color: {theme.text_primary};
    }}
    QTableWidget::item, QTreeWidget::item {{
        padding: 4px 6px;
    }}
    QHeaderView::section {{
        background-color: {theme.bg_raised};
        color: {theme.text_secondary};
        border: none;
        border-bottom: 1px solid {theme.border_med};
        padding: 5px 6px;
        font-weight: 600;
    }}
    QTableCornerButton::section {{
        background-color: {theme.bg_raised};
        border: none;
    }}

    /* ---- Scrollbars ---- */
    QScrollBar:vertical {{
        background: {theme.bg_base};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {theme.border_med};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {theme.border_bright}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: {theme.bg_base};
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {theme.border_med};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {theme.border_bright}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """
