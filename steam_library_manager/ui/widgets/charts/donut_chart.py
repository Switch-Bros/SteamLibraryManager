from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPalette

from steam_library_manager.services.chart_data import ChartSlice, CHART_TEXT, CHART_TEXT_DIM, CHART_OTHERS
from steam_library_manager.ui.widgets.charts.base_chart import BaseChart

__all__ = ["DonutChart"]


class DonutChart(BaseChart):
    """Interactive donut chart with hover effects and responsive legend."""

    _OTHERS_THRESHOLD = 8
    _LEGEND_BREAK_WIDTH = 450

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 250)
        self._default_center: tuple[str, str, str] = ("", "", "")
        self._segment_angles: list[tuple[float, float]] = []

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def set_data(self, slices: list[ChartSlice]) -> None:
        if len(slices) > self._OTHERS_THRESHOLD:
            keep = slices[: self._OTHERS_THRESHOLD]
            others_val = sum(s.value for s in slices[self._OTHERS_THRESHOLD :])
            if others_val > 0:
                keep.append(ChartSlice("Others", others_val, QColor(CHART_OTHERS)))
            slices = keep
        super().set_data(slices)
        if self._slices:
            biggest = max(self._slices, key=lambda s: s.value)
            pct = round(biggest.value / self._total() * 100, 1)
            self._default_center = (
                biggest.label,
                str(int(biggest.value)),
                "%s%%" % pct,
            )
        else:
            self._default_center = ("", "", "")

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _donut_geometry(self):
        """Return (cx, cy, outer_r, inner_r, legend_right)."""
        w, h = self.width(), self.height()
        legend_right = w >= self._LEGEND_BREAK_WIDTH
        if legend_right:
            donut_size = min(w * 0.6, h) * 0.7
            cx = w * 0.3
            cy = h / 2
        else:
            donut_size = min(w, h * 0.65) * 0.7
            cx = w / 2
            cy = h * 0.35
        outer_r = donut_size / 2
        inner_r = outer_r * 0.55
        return cx, cy, outer_r, inner_r, legend_right

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        if not self._slices:
            return
        p = self._begin_paint()
        w, h = self.width(), self.height()
        cx, cy, outer_r, inner_r, legend_right = self._donut_geometry()
        total = self._total()

        # -- segments --
        self._segment_angles = []
        start_angle = 90.0  # 12 o'clock
        rect = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

        for i, s in enumerate(self._slices):
            span = s.value / total * 360.0
            self._segment_angles.append((start_angle, span))

            if i == self._hover_idx:
                mid_angle = math.radians(start_angle + span / 2)
                dx = 6 * math.cos(mid_angle)
                dy = -6 * math.sin(mid_angle)
                seg_rect = rect.translated(dx, dy)
                color = s.color.lighter(120) if s.color else QColor("#ffffff")
            else:
                seg_rect = rect
                color = s.color if s.color else QColor("#ffffff")

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawPie(seg_rect, int(start_angle * 16), int(span * 16))
            start_angle += span

        # -- donut hole --
        bg = self.palette().color(QPalette.ColorRole.Window)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))

        # -- center text --
        if 0 <= self._hover_idx < len(self._slices):
            s = self._slices[self._hover_idx]
            pct = round(s.value / total * 100, 1)
            center = (s.label, str(int(s.value)), "%s%%" % pct)
        else:
            center = self._default_center

        max_text_w = int(inner_r * 1.4)

        label_font = QFont()
        label_font.setPointSize(10)
        label_font.setBold(True)
        p.setFont(label_font)
        p.setPen(QColor("#ffffff"))
        fm = QFontMetrics(label_font)
        elided = fm.elidedText(center[0], Qt.TextElideMode.ElideRight, max_text_w)
        p.drawText(
            QRectF(cx - inner_r, cy - 24, inner_r * 2, 20),
            Qt.AlignmentFlag.AlignCenter,
            elided,
        )

        val_font = QFont()
        val_font.setPointSize(9)
        p.setFont(val_font)
        p.drawText(
            QRectF(cx - inner_r, cy - 4, inner_r * 2, 16),
            Qt.AlignmentFlag.AlignCenter,
            center[1],
        )

        pct_font = QFont()
        pct_font.setPointSize(8)
        p.setFont(pct_font)
        p.setPen(QColor(CHART_TEXT_DIM))
        p.drawText(
            QRectF(cx - inner_r, cy + 12, inner_r * 2, 16),
            Qt.AlignmentFlag.AlignCenter,
            center[2],
        )

        # -- legend --
        self._draw_legend(p, cx, cy, outer_r, legend_right, w, h)
        p.end()

    def _draw_legend(self, p, cx, cy, outer_r, legend_right, w, h):
        sq = 12
        gap = 4
        line_h = sq + gap

        font = QFont()
        font.setPointSize(9)
        p.setFont(font)
        fm = QFontMetrics(font)
        total = self._total()

        if legend_right:
            lx = cx + outer_r + 30
            ly = cy - (len(self._slices) * line_h) / 2
            max_label_w = w - lx - sq - gap - 10
        else:
            lx = 10
            ly = cy + outer_r + 15
            max_label_w = (w - 20) // 2 - sq - gap

        for i, s in enumerate(self._slices):
            if legend_right:
                x = lx
                y = ly + i * line_h
            else:
                col = i % 2
                row = i // 2
                x = lx + col * (w // 2)
                y = ly + row * line_h

            color = s.color if s.color else QColor(CHART_OTHERS)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRect(int(x), int(y), sq, sq)

            p.setPen(QColor(CHART_TEXT))
            pct = round(s.value / total * 100, 1)
            text = "%s (%s%%)" % (s.label, pct)
            elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(max_label_w))
            p.drawText(int(x + sq + gap), int(y + sq - 2), elided)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event):
        if not self._slices or not self._segment_angles:
            return
        cx, cy, outer_r, inner_r, _ = self._donut_geometry()

        pos = event.position()
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)

        old_hover = self._hover_idx

        if dist < inner_r or dist > outer_r + 10:
            self._hover_idx = -1
        else:
            angle = math.degrees(math.atan2(-dy, dx))
            if angle < 0:
                angle += 360

            self._hover_idx = -1
            for i, (start, span) in enumerate(self._segment_angles):
                if span >= 360:
                    self._hover_idx = i
                    break
                s_norm = start % 360
                e_norm = (s_norm + span) % 360
                if s_norm <= e_norm:
                    if s_norm <= angle < e_norm:
                        self._hover_idx = i
                        break
                else:
                    if angle >= s_norm or angle < e_norm:
                        self._hover_idx = i
                        break

        if old_hover != self._hover_idx:
            self.update()

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.update()
