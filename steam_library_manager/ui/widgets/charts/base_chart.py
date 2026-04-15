from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor

from steam_library_manager.services.chart_data import ChartSlice, CHART_PALETTE

__all__ = ["BaseChart"]


class BaseChart(QWidget):
    """Base for all chart widgets. Provides palette, anti-aliasing, data management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slices: list[ChartSlice] = []
        self._hover_idx: int = -1
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

    def set_data(self, slices: list[ChartSlice]) -> None:
        for i, s in enumerate(slices):
            if s.color is None:
                s.color = QColor(CHART_PALETTE[i % len(CHART_PALETTE)])
        self._slices = slices
        self._hover_idx = -1
        self.update()

    def _total(self) -> float:
        return sum(s.value for s in self._slices) or 1.0

    def _begin_paint(self) -> QPainter:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        return p
