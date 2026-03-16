#
# steam_library_manager/ui/utils/font_helper.py
# Manages the embedded Inter font for consistent UI typography.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QWidget

from steam_library_manager.utils.i18n import t

logger = logging.getLogger(__name__)

__all__ = ["FontHelper"]


class FontHelper:
    """Manages the Inter variable font for consistent UI typography."""

    _font_loaded: bool = False
    FONT_NAME: str = "Inter"
    FONT_FILE: str = "InterVariable.ttf"
    EMOJI_FONT_FILE: str = "NotoColorEmoji.ttf"
    BOLD: QFont.Weight = QFont.Weight.Bold

    @classmethod
    def load_font(cls) -> None:
        """Load Inter and optionally Noto Color Emoji into Qt's font database."""
        if cls._font_loaded:
            return

        from steam_library_manager.utils.paths import get_resources_dir

        font_dir = get_resources_dir() / "fonts"

        inter_path = font_dir / cls.FONT_FILE
        if not inter_path.exists():
            logger.error(t("logs.font.file_not_found", path=str(inter_path)))
            raise FileNotFoundError(f"Inter font not found at {inter_path}")

        font_id = QFontDatabase.addApplicationFont(str(inter_path))
        if font_id == -1:
            logger.error(t("logs.font.load_failed", path=str(inter_path)))
            raise RuntimeError(f"Failed to load Inter font from {inter_path}")

        families = QFontDatabase.applicationFontFamilies(font_id)
        logger.info(t("logs.font.loaded", family=families[0] if families else "Unknown"))

        emoji_path = font_dir / cls.EMOJI_FONT_FILE
        if emoji_path.exists():
            emoji_id = QFontDatabase.addApplicationFont(str(emoji_path))
            if emoji_id != -1:
                emoji_families = QFontDatabase.applicationFontFamilies(emoji_id)
                logger.info(t("logs.font.loaded", family=emoji_families[0] if emoji_families else "Emoji"))
            else:
                logger.warning(t("logs.font.load_failed", path=str(emoji_path)))

        cls._font_loaded = True

    @classmethod
    def get_font(cls, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        """Get Inter font with specified size and weight."""
        cls.load_font()
        font = QFont(cls.FONT_NAME, size)
        font.setWeight(weight)

        weight_map = {
            QFont.Weight.Thin: 100,
            QFont.Weight.ExtraLight: 200,
            QFont.Weight.Light: 300,
            QFont.Weight.Normal: 400,
            QFont.Weight.Medium: 500,
            QFont.Weight.DemiBold: 600,
            QFont.Weight.Bold: 700,
            QFont.Weight.ExtraBold: 800,
            QFont.Weight.Black: 900,
        }

        if weight in weight_map:
            font.setWeight(weight_map[weight])

        return font

    @classmethod
    def set_app_font(cls, app: QApplication, size: int = 10) -> None:
        """Set Inter as the application-wide default font."""
        cls.load_font()
        font = cls.get_font(size)
        app.setFont(font)
        logger.info(t("logs.font.app_font_set", name=cls.FONT_NAME, size=size))

    @classmethod
    def apply_to_widget(
        cls, widget: QWidget, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, recursive: bool = True
    ) -> None:
        """Apply Inter font to a widget and optionally its children."""
        font = cls.get_font(size, weight)
        widget.setFont(font)

        if recursive:
            for child in widget.findChildren(QWidget):
                if isinstance(child, QWidget):
                    child.setFont(font)
