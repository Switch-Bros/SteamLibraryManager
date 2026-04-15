from __future__ import annotations

from dataclasses import dataclass
from PyQt6.QtGui import QColor

__all__ = ["ChartSlice", "CHART_PALETTE", "SEMANTIC_COLORS", "CHART_TEXT", "CHART_TEXT_DIM", "CHART_OTHERS"]


@dataclass
class ChartSlice:
    """Ein Datenpunkt im Chart."""

    label: str
    value: float
    color: QColor | None = None


CHART_PALETTE: tuple[str, ...] = (
    "#4FC3F7",
    "#81C784",
    "#FFB74D",
    "#E57373",
    "#BA68C8",
    "#4DB6AC",
    "#FFD54F",
    "#F06292",
    "#AED581",
    "#7986CB",
    "#FF8A65",
    "#A1887F",
)


SEMANTIC_COLORS: dict[str, str] = {
    "verified": "#81C784",
    "playable": "#FFD54F",
    "unsupported": "#E57373",
    "unknown": "#90A4AE",
    "platinum": "#4FC3F7",
    "gold": "#FFD54F",
    "silver": "#B0BEC5",
    "bronze": "#FF8A65",
    "borked": "#E57373",
    "perfect": "#FDE100",
}

# Chart UI colors (text, labels, others bucket)
CHART_TEXT = "#cccccc"
CHART_TEXT_DIM = "#aaaaaa"
CHART_OTHERS = "#555555"
