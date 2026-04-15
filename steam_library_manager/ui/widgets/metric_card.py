#
# steam_library_manager/ui/widgets/metric_card.py
# Reusable metric card widget for statistics display
#
# Copyright 2025-2026 SwitchBros
# MIT License
#

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.utils.font_helper import FontHelper

__all__ = ["MetricCard"]


class MetricCard(QFrame):
    """Compact card showing a single metric: emoji, label, value, optional sub-info."""

    def __init__(
        self,
        emoji: str,
        label: str,
        value: str,
        sub_info: str = "",
        accent_color: str = Theme.ACCENT,
        parent=None,
    ):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "MetricCard {"
            "  background: %s;"
            "  border: 1px solid %s;"
            "  border-radius: 8px;"
            "  padding: 12px;"
            "}" % (Theme.BG_INFO, Theme.BORDER)
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        icon_lbl = QLabel(emoji)
        icon_lbl.setFont(FontHelper.get_font(24))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setFont(FontHelper.get_font(22, FontHelper.BOLD))
        val_lbl.setStyleSheet("color: %s;" % accent_color)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(val_lbl)

        desc_lbl = QLabel(label)
        desc_lbl.setStyleSheet("color: %s;" % Theme.TXT_MUTED)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(desc_lbl)

        if sub_info:
            sub_lbl = QLabel(sub_info)
            sub_lbl.setStyleSheet("color: %s; font-size: 11px;" % Theme.TXT_MUTED)
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(sub_lbl)
