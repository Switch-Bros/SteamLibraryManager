"""Badge overlay system for ClickableImage (SteamGridDB-style).

Provides an animated badge strip that sits above image covers.
Normal state: thin colored stripes at top edge.
On hover: badges expand downward to reveal full icons.
"""

from __future__ import annotations

from typing import cast

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.config import config
from src.utils.i18n import t

__all__ = ["ImageBadgeOverlay"]

_STRIPE_HEIGHT: int = 5
_ICON_HEIGHT: int = 28
_BADGE_GAP: int = 2
_EXPANDED_HEIGHT: int = _STRIPE_HEIGHT + _BADGE_GAP + _ICON_HEIGHT
_STRIPE_WIDTH: int = 28
_STRIPE_GAP: int = 2


class ImageBadgeOverlay(QWidget):
    """Animated badge overlay widget for image covers.

    Creates colored stripe hints at the top of a cover image that
    expand into full badge icons on mouse hover.

    Attributes:
        badges: List of badge icon widgets currently displayed.
    """

    def __init__(self, parent: QWidget, width: int) -> None:
        """Initializes the badge overlay.

        Args:
            parent: Parent widget (the ClickableImage).
            width: Width of the parent image widget.
        """
        super().__init__(parent)
        self._width = width
        self.badges: list[QWidget] = []
        self._badge_colors: list[str] = []

        # Positioned 6px above the image top edge
        self.setGeometry(0, -6, width, _EXPANDED_HEIGHT)
        self.raise_()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        overlay_layout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(5, 0, 0, 0)
        overlay_layout.setSpacing(_BADGE_GAP)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Stripe row — always visible (thin colored bars)
        self._stripe_container = QWidget()
        stripe_layout = QHBoxLayout(self._stripe_container)
        stripe_layout.setContentsMargins(0, 0, 0, 0)
        stripe_layout.setSpacing(_STRIPE_GAP)
        stripe_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._stripe_container.setFixedHeight(_STRIPE_HEIGHT)
        overlay_layout.addWidget(self._stripe_container)

        # Icon row — only visible on hover
        self._icon_container = QWidget()
        icon_layout = QHBoxLayout(self._icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(_STRIPE_GAP)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        overlay_layout.addWidget(self._icon_container)

        # Geometry animation for expand/collapse
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setDuration(180)

    def create_badges(self, metadata: dict | None, is_animated: bool = False) -> None:
        """Creates badge stripes and icons from metadata.

        Args:
            metadata: Game metadata dict with optional 'tags', 'nsfw',
                'humor', 'epilepsy' keys.
            is_animated: Whether the loaded image is animated (GIF/APNG/WEBM).
        """
        self.clear_badges()
        if not metadata:
            return

        tags: list[str] = metadata.get("tags", [])

        # Badge definitions: (type_key, text, bg_color, active)
        badge_defs: list[tuple[str, str, str, bool]] = [
            (
                "nsfw",
                f"{t('emoji.nsfw')} {t('ui.badges.nsfw')}",
                "#d9534f",
                bool(metadata.get("nsfw") or "nsfw" in tags),
            ),
            (
                "humor",
                f"{t('emoji.humor')} {t('ui.badges.humor')}",
                "#f0ad4e",
                bool(metadata.get("humor") or "humor" in tags),
            ),
            (
                "epilepsy",
                f"{t('emoji.blitz')} {t('ui.badges.epilepsy')}",
                "#0275d8",
                bool(metadata.get("epilepsy") or "epilepsy" in tags),
            ),
            ("animated", f"{t('emoji.animated')} {t('ui.badges.animated')}", "#5cb85c", is_animated),
        ]

        active_badges: list[tuple[str, str, str]] = [
            (key, text, color) for key, text, color, active in badge_defs if active
        ]

        if not active_badges:
            self.setGeometry(0, 0, self._width, 0)
            return

        stripe_layout: QHBoxLayout = cast(QHBoxLayout, self._stripe_container.layout())
        icon_layout: QHBoxLayout = cast(QHBoxLayout, self._icon_container.layout())

        for type_key, text, bg_color in active_badges:
            # Stripe (always visible, square)
            stripe = QWidget()
            stripe.setFixedSize(_STRIPE_WIDTH, _STRIPE_HEIGHT)
            stripe.setStyleSheet(f"background-color: {bg_color};")
            stripe_layout.addWidget(stripe)

            # Icon (visible on hover)
            icon_path = config.ICONS_DIR / f"flag_{type_key}.png"
            if icon_path.exists():
                lbl = QLabel()
                pix = QPixmap(str(icon_path)).scaledToHeight(_ICON_HEIGHT, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(pix)
                lbl.setFixedWidth(_STRIPE_WIDTH)
                lbl.setStyleSheet(
                    "QLabel { "
                    "  border: 1px solid rgba(0, 0, 0, 0.45); "
                    "  border-radius: 0px 0px 3px 3px; "
                    "  background-color: rgba(0, 0, 0, 0.25); "
                    "  padding: 1px; "
                    "}"
                )
            else:
                # Fallback: text badge when no PNG available
                lbl = QLabel(text)
                lbl.setFixedSize(_STRIPE_WIDTH, _ICON_HEIGHT)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    f"background-color: {bg_color}; color: white; "
                    f"border-radius: 0px 0px 4px 4px; "
                    f"font-weight: bold; font-size: 9px; "
                    f"border: 1px solid rgba(255,255,255,0.3);"
                )
            icon_layout.addWidget(lbl)

            self._badge_colors.append(bg_color)
            self.badges.append(lbl)

        # Start collapsed — only stripes visible
        self.setGeometry(0, 0, self._width, _STRIPE_HEIGHT)

    def clear_badges(self) -> None:
        """Removes all badges, stripes, and hides the overlay."""
        icon_layout: QHBoxLayout = cast(QHBoxLayout, self._icon_container.layout())
        for b in self.badges:
            icon_layout.removeWidget(b)
            b.deleteLater()
        self.badges = []

        stripe_layout: QHBoxLayout = cast(QHBoxLayout, self._stripe_container.layout())
        while stripe_layout.count():
            item = stripe_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._badge_colors = []
        self.setGeometry(0, 0, self._width, 0)

    def expand(self) -> None:
        """Expands overlay to show full badge icons."""
        if self.badges:
            self._animate_to(_EXPANDED_HEIGHT)

    def collapse(self) -> None:
        """Collapses overlay to show only stripe hints."""
        if self.badges:
            self._animate_to(_STRIPE_HEIGHT)

    def _animate_to(self, target_height: int) -> None:
        """Animates overlay geometry to target height.

        Args:
            target_height: The target height in pixels.
        """
        self._animation.stop()
        current: QRect = self.geometry()
        self._animation.setStartValue(current)
        self._animation.setEndValue(QRect(0, 0, self._width, target_height))
        self._animation.start()
