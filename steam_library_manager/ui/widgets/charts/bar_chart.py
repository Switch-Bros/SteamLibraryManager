from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QFontMetrics

from steam_library_manager.services.chart_data import CHART_PALETTE, CHART_TEXT, CHART_TEXT_DIM, ChartSlice
from steam_library_manager.ui.widgets.charts.base_chart import BaseChart

__all__ = ["BarChart"]


class BarChart(BaseChart):
    """Horizontal bar chart with themed colors and hover effects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self._bar_height = 24
        self._bar_gap = 4
        self._label_min = 120
        self._label_max = 200

    def set_data(self, slices: list[ChartSlice]) -> None:
        super().set_data(slices)
        needed = len(slices) * (self._bar_height + self._bar_gap) + 20
        if needed > 200:
            self.setMinimumHeight(needed)

    def _format_value(self, value: float) -> str:
        if value == int(value):
            return str(int(value))
        return "%.1f" % value

    def paintEvent(self, event):
        if not self._slices:
            return
        p = self._begin_paint()

        w = self.width()
        max_val = max(s.value for s in self._slices)
        if max_val <= 0:
            max_val = 1.0

        # label font
        label_font = QFont()
        label_font.setPointSize(10)
        p.setFont(label_font)
        label_fm = QFontMetrics(label_font)

        # compute label column width from actual data
        label_w = self._label_min
        for s in self._slices:
            tw = label_fm.horizontalAdvance(s.label) + 10
            label_w = max(label_w, min(tw, self._label_max))

        # value font
        val_font = QFont()
        val_font.setPointSize(9)
        val_fm = QFontMetrics(val_font)

        # reserve space for widest value text
        max_val_text = self._format_value(max_val)
        val_w = val_fm.horizontalAdvance(max_val_text) + 20

        bar_area_w = w - label_w - val_w - 20

        y = 10.0
        for i, s in enumerate(self._slices):
            bh = self._bar_height
            y_offset = 0.0

            if i == self._hover_idx:
                bh += 2
                y_offset = -1.0

            # draw label
            p.setFont(label_font)
            p.setPen(QColor(CHART_TEXT))
            elided = label_fm.elidedText(s.label, Qt.TextElideMode.ElideRight, int(label_w))
            p.drawText(
                QRectF(5, y + y_offset, label_w, bh),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                elided,
            )

            # draw bar
            bar_w = s.value / max_val * bar_area_w
            bar_x = label_w + 5

            color = s.color if s.color else QColor(CHART_PALETTE[0])
            if i == self._hover_idx:
                color = color.lighter(120)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(bar_x, y + y_offset, bar_w, bh), 4, 4)

            # draw value text
            p.setFont(val_font)
            p.setPen(QColor(CHART_TEXT_DIM))
            p.drawText(
                QRectF(bar_x + bar_w + 5, y + y_offset, val_w, bh),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self._format_value(s.value),
            )

            y += self._bar_height + self._bar_gap

        p.end()

    def mouseMoveEvent(self, event):
        if not self._slices:
            return

        pos = event.position()
        y_pos = pos.y() - 10  # top padding offset
        step = self._bar_height + self._bar_gap
        idx = int(y_pos / step)
        in_bar = (y_pos % step) < self._bar_height
        old_hover = self._hover_idx

        if 0 <= idx < len(self._slices) and in_bar:
            self._hover_idx = idx
            s = self._slices[idx]
            self.setToolTip("%s: %s" % (s.label, self._format_value(s.value)))
        else:
            self._hover_idx = -1
            self.setToolTip("")

        if old_hover != self._hover_idx:
            self.update()

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.setToolTip("")
        self.update()
