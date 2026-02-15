"""Font helper for Steam Library Manager.

Manages the embedded Inter font to provide consistent Steam-like typography
across all platforms.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QWidget

from src.utils.i18n import t

logger = logging.getLogger(__name__)

__all__ = ["FontHelper"]


class FontHelper:
    """Manages the Inter variable font for consistent UI typography.

    This helper loads and manages the embedded Inter variable font, which provides
    a Steam-like appearance across all platforms. Inter was chosen for its close
    similarity to Valve's Motiva Sans while being freely licensed (OFL 1.1).

    The variable font format allows all weights (100-900) in a single 860KB file,
    making it ideal for desktop applications.
    """

    _font_loaded: bool = False
    FONT_NAME: str = "Inter"
    FONT_FILE: str = "InterVariable.ttf"

    @classmethod
    def load_font(cls) -> None:
        """Load the embedded Inter variable font.

        Loads InterVariable.ttf from resources/fonts/ into Qt's font database.
        This method is idempotent - calling it multiple times has no effect.

        Raises:
            FileNotFoundError: If InterVariable.ttf is not found in resources/fonts/
        """
        if cls._font_loaded:
            return

        # Get path to embedded font
        font_path = Path(__file__).parent.parent.parent.parent / "resources" / "fonts" / cls.FONT_FILE

        if not font_path.exists():
            logger.error(t("logs.font.file_not_found", path=str(font_path)))
            raise FileNotFoundError(f"Inter font not found at {font_path}")

        # Load font into Qt font database
        font_id = QFontDatabase.addApplicationFont(str(font_path))

        if font_id == -1:
            logger.error(t("logs.font.load_failed", path=str(font_path)))
            raise RuntimeError(f"Failed to load Inter font from {font_path}")

        # Get loaded font families for logging
        families = QFontDatabase.applicationFontFamilies(font_id)
        family_name = families[0] if families else "Unknown"
        logger.info(t("logs.font.loaded", family=family_name))

        cls._font_loaded = True

    @classmethod
    def get_font(cls, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        """Get Inter font with specified size and weight.

        Returns a QFont instance configured with the Inter variable font.
        Automatically loads the font if not already loaded.

        Args:
            size: Font size in points. Defaults to 10pt (standard UI size).
            weight: Font weight from QFont.Weight enum. Inter supports all
                weights from Thin (100) to Black (900).

        Returns:
            QFont instance configured with Inter at the requested size and weight.

        Raises:
            FileNotFoundError: If font file is missing.
            RuntimeError: If font loading fails.
        """
        # Ensure font is loaded
        cls.load_font()

        # Create font with specified parameters
        font = QFont(cls.FONT_NAME, size)
        font.setWeight(weight)

        # Inter is a variable font supporting exact weight values 100-900
        # Map QFont.Weight enum to exact numeric weights for optimal rendering
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
        """Set Inter as the application-wide default font.

        Configures the entire application to use Inter at the specified size.
        This should be called once during application initialization, before
        any windows are created.

        Args:
            app: The QApplication instance.
            size: Default font size in points for the entire application.

        Raises:
            FileNotFoundError: If font file is missing.
            RuntimeError: If font loading fails.
        """
        cls.load_font()
        font = cls.get_font(size)
        app.setFont(font)
        logger.info(t("logs.font.app_font_set", name=cls.FONT_NAME, size=size))

    @classmethod
    def apply_to_widget(
        cls, widget: QWidget, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, recursive: bool = True
    ) -> None:
        """Apply Inter font to a specific widget.

        Applies the Inter font to the given widget and optionally to all its
        child widgets. Useful for applying different font sizes to specific
        parts of the UI.

        Args:
            widget: The widget to apply the font to.
            size: Font size in points.
            weight: Font weight.
            recursive: If True, also apply to all child widgets.

        Raises:
            FileNotFoundError: If font file is missing.
            RuntimeError: If font loading fails.
        """
        font = cls.get_font(size, weight)
        widget.setFont(font)

        if recursive:
            # Apply to all children recursively
            for child in widget.findChildren(QWidget):
                if isinstance(child, QWidget):
                    child.setFont(font)
