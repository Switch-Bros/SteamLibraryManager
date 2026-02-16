# src/ui/widgets/info_label.py

"""Reusable label components and helpers for the game details panel.

Provides InfoLabel, a grid builder for detail rows, and HTML formatters
for ProtonDB / Steam Deck ratings.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel

from src.utils.i18n import t

__all__ = [
    "InfoLabel",
    "build_detail_grid",
    "set_info_label_value",
    "update_hltb_label",
    "format_proton_html",
    "format_deck_html",
]

# ---------------------------------------------------------------------------
# Color / tier constants
# ---------------------------------------------------------------------------

PROTON_COLORS: dict[str, str] = {
    "platinum": "#B4C7D9",
    "gold": "#FDE100",
    "silver": "#C0C0C0",
    "bronze": "#CD7F32",
    "native": "#5CB85C",
    "borked": "#D9534F",
    "pending": "#1C39BB",
    "unknown": "#FE28A2",
}

DECK_COLORS: dict[str, str] = {
    "verified": "#59BF40",
    "playable": "#FDE100",
    "unsupported": "#D9534F",
    "unknown": "#808080",
}


# ---------------------------------------------------------------------------
# InfoLabel widget
# ---------------------------------------------------------------------------


class InfoLabel(QLabel):
    """Custom label displaying a key-value pair: gray title + bold value."""

    def __init__(self, title_key: str, value: str = "") -> None:
        """Initializes the label.

        Args:
            title_key: Translation key for the title.
            value: Initial value text.
        """
        super().__init__()
        title = t(title_key)
        self.setText(f"<span style='color:#888;'>{title}:</span> <b>{value}</b>")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("padding: 1px 0;")


# ---------------------------------------------------------------------------
# Grid builder
# ---------------------------------------------------------------------------


def build_detail_grid(
    title_key: str,
    label_keys: list[str],
    col_widths: dict[int, int] | None = None,
    h_spacing: int = 30,
) -> tuple[QWidget, QGridLayout, list[QLabel]]:
    """Builds a one-row QGridLayout with a bold title and InfoLabels.

    Each call creates a self-contained QWidget whose column widths are
    controlled via *col_widths*, so nothing shifts when data loads.

    Args:
        title_key: i18n key for the row title.
        label_keys: i18n keys for the value InfoLabels.
        col_widths: Mapping of column index to minimum pixel width.
        h_spacing: Horizontal spacing between columns.

    Returns:
        Tuple of (container_widget, grid_layout, list_of_InfoLabels).
    """
    container = QWidget()
    grid = QGridLayout(container)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(h_spacing)
    grid.setVerticalSpacing(2)

    title = QLabel(f"<b>{t(title_key)}:</b>")
    title.setStyleSheet("padding: 1px 0;")
    grid.addWidget(title, 0, 0)

    labels: list[QLabel] = []
    for i, key in enumerate(label_keys):
        lbl = InfoLabel(key)
        grid.addWidget(lbl, 0, i + 1)
        labels.append(lbl)

    if col_widths:
        for col, width in col_widths.items():
            grid.setColumnMinimumWidth(col, width)

    grid.setColumnStretch(len(label_keys) + 1, 1)
    return container, grid, labels


# ---------------------------------------------------------------------------
# Label value helpers
# ---------------------------------------------------------------------------


def set_info_label_value(label: QLabel, value: str, color: str = "") -> None:
    """Updates the bold value portion of an InfoLabel.

    Args:
        label: The InfoLabel to update.
        value: New value text.
        color: Optional CSS color (e.g. '#FDE100').
    """
    parts = label.text().split(":</span>")
    prefix = parts[0] + ":</span>" if len(parts) > 1 else ""
    if color:
        label.setText(f"{prefix} <b style='color:{color};'>{value}</b>")
    else:
        label.setText(f"{prefix} <b>{value}</b>")


def update_hltb_label(label: QLabel, hours: float, dash: str) -> None:
    """Updates an HLTB InfoLabel with formatted hours or a dash.

    Args:
        label: The InfoLabel to update.
        hours: Hours value (0 means no data).
        dash: Placeholder string for missing data.
    """
    parts = label.text().split(":</span>")
    prefix = parts[0] + ":</span>" if len(parts) > 1 else ""
    val = t("time.time_hours_short", hours=f"{hours:.1f}") if hours > 0 else dash
    label.setText(f"{prefix} <b>{val}</b>")


# ---------------------------------------------------------------------------
# Rating HTML formatters
# ---------------------------------------------------------------------------


def format_proton_html(tier: str) -> str:
    """Returns styled HTML string for the ProtonDB rating label.

    Args:
        tier: ProtonDB tier (platinum, gold, silver, bronze, native, borked, pending, unknown).
    """
    tier_lower = tier.lower() if tier else "unknown"
    if tier_lower not in PROTON_COLORS:
        tier_lower = "unknown"
    color = PROTON_COLORS[tier_lower]
    display = t(f"ui.game_details.proton_tiers.{tier_lower}")
    if display.startswith("["):
        display = tier_lower.title()
    title = t("ui.game_details.proton_db")
    return (
        f"<span style='color:#888;'>{title}:</span> " f"<span style='color:{color}; font-weight:bold;'>{display}</span>"
    )


def format_deck_html(status: str) -> str:
    """Returns styled HTML string for the Steam Deck status label.

    Args:
        status: Deck status (verified, playable, unsupported, unknown).
    """
    status_lower = status.lower() if status else "unknown"
    if status_lower not in DECK_COLORS:
        status_lower = "unknown"
    color = DECK_COLORS[status_lower]
    display = t(f"ui.game_details.steam_deck_status.{status_lower}")
    if display.startswith("["):
        display = status_lower.title()
    title = t("ui.game_details.steam_deck")
    return (
        f"<span style='color:#888;'>{title}:</span> " f"<span style='color:{color}; font-weight:bold;'>{display}</span>"
    )
