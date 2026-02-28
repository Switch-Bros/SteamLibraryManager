# src/ui/dialogs/about_dialog.py

"""Professional About dialog with Photoshop-style two-column layout.

Dark Steam-inspired design with app logo, version info, credits,
license, and a clickable GitHub link.  All content strings are
intentionally hardcoded (project metadata, not user-facing i18n).
"""

from __future__ import annotations

from typing import NamedTuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
)

from src.config import config
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.base_dialog import BaseDialog
from src.utils.i18n import get_language, t
from src.utils.open_url import open_url
from src.version import __app_name__, __version__, __release_date__, __author__, __license__

__all__ = ["AboutDialog"]

# -- Hardcoded project metadata (NOT i18n — intentional) --------------------
# These are curated by SwitchBros, not pulled from i18n files.

_GITHUB_URL = "https://github.com/Switch-Bros/SteamLibraryManager"


class AboutTexts(NamedTuple):
    """Curated About dialog texts — controlled by SwitchBros, not i18n."""

    description: str
    credits: str
    built_with: str


_ABOUT_EN = AboutTexts(
    description=(
        "The ultimate Steam library organizer for Linux.\n"
        "Manage thousands of games with smart collections,\n"
        "auto-categorization, and cloud sync."
    ),
    credits="Contributors will be listed here.",
    built_with="Built with Python, PyQt6 & 💛🖤💛",
)

_ABOUT_DE = AboutTexts(
    description=(
        "Der ultimative Steam-Bibliotheksmanager für Linux.\n"
        "Verwalte tausende Spiele mit smarten Kollektionen,\n"
        "Auto-Kategorisierung und Cloud-Sync."
    ),
    credits="Mitwirkende werden hier aufgeführt.",
    built_with="Erstellt mit Python, PyQt6 & 💛🖤💛",
)


def _get_about_texts() -> AboutTexts:
    """Returns curated About texts — DE or EN (fallback)."""
    if get_language() == "de":
        return _ABOUT_DE
    return _ABOUT_EN


# -- Colors -----------------------------------------------------------------

_BG_DARK = "#1b2838"
_TEXT_PRIMARY = "#c7d5e0"
_TEXT_MUTED = "#8f98a0"
_TEXT_LINK = "#66c0f4"
_DIVIDER = "#2a475e"
_BTN_BG = "#2a475e"
_BTN_BORDER = "#3d6c8e"


class _ClickableLabel(QLabel):
    """QLabel that emits a clicked signal on mouse press."""

    clicked = pyqtSignal()

    def mousePressEvent(self, ev) -> None:
        """Emits clicked signal on any mouse press."""
        self.clicked.emit()
        super().mousePressEvent(ev)


class AboutDialog(BaseDialog):
    """Professional About dialog inspired by Adobe Photoshop's splash screen.

    Two-column layout: app logo on the left, version/credits/license on the
    right, separated by a thin vertical divider.  Dark Steam theme.
    """

    def __init__(self, parent=None) -> None:
        """Initializes the About dialog.

        Args:
            parent: Optional parent widget.
        """
        self._click_count = 0

        super().__init__(
            parent,
            title_text=f"{t('menu.help.about')} — {__app_name__}",
            min_width=650,
            show_title_label=False,
            buttons="none",
        )
        self.setFixedSize(650, 400)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the two-column dialog layout."""
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        root = QHBoxLayout()
        root.setSpacing(0)

        # --- Left: Logo ---
        root.addLayout(self._build_logo_column())

        # --- Vertical divider ---
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet(f"color: {_DIVIDER};")
        divider.setFixedWidth(1)
        root.addSpacing(20)
        root.addWidget(divider)
        root.addSpacing(20)

        # --- Right: Info ---
        root.addLayout(self._build_info_column(), stretch=1)

        layout.addLayout(root)

        # --- Global stylesheet ---
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_BG_DARK};
            }}
            QLabel {{
                color: {_TEXT_PRIMARY};
                background: transparent;
            }}
            QPushButton {{
                background-color: {_BTN_BG};
                color: {_TEXT_PRIMARY};
                border: 1px solid {_BTN_BORDER};
                border-radius: 3px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{
                background-color: {_BTN_BORDER};
            }}
        """)

    def _build_logo_column(self) -> QVBoxLayout:
        """Builds the left column containing the app logo."""
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = _ClickableLabel()
        logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        logo_label.setToolTip("SwitchBros")

        logo_path = config.RESOURCES_DIR / "images" / "default_icons.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(
                pixmap.scaled(
                    200,
                    200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            logo_label.setText(__app_name__)
            logo_label.setFont(FontHelper.get_font(16, FontHelper.BOLD))

        logo_label.clicked.connect(self._on_logo_clicked)
        col.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        return col

    def _build_info_column(self) -> QVBoxLayout:
        """Builds the right column with version, description, credits, links."""
        col = QVBoxLayout()
        col.setSpacing(6)

        # App name
        name_label = QLabel(__app_name__)
        name_label.setFont(FontHelper.get_font(18, FontHelper.BOLD))
        name_label.setStyleSheet("color: white;")
        col.addWidget(name_label)

        # Version + Release date
        version_label = QLabel(f"Version {__version__}  —  Release: {__release_date__}")
        version_label.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 12px;")
        col.addWidget(version_label)

        col.addSpacing(8)

        # Description
        about = _get_about_texts()
        desc_label = QLabel(about.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px;")
        col.addWidget(desc_label)

        col.addSpacing(4)
        col.addWidget(self._h_line())

        # Credits
        credits_header = QLabel("Credits")
        credits_header.setFont(FontHelper.get_font(11, FontHelper.BOLD))
        col.addWidget(credits_header)

        credits_text = QLabel(about.credits)
        credits_text.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 12px;")
        credits_text.setWordWrap(True)
        col.addWidget(credits_text)

        col.addWidget(self._h_line())

        # License + GitHub
        license_label = QLabel(f"License: {__license__}  |  Author: {__author__}")
        license_label.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 12px;")
        col.addWidget(license_label)

        github_label = QLabel(f'GitHub: <a href="{_GITHUB_URL}" style="color: {_TEXT_LINK};">{_GITHUB_URL}</a>')
        github_label.setTextFormat(Qt.TextFormat.RichText)
        github_label.setCursor(Qt.CursorShape.PointingHandCursor)
        github_label.linkActivated.connect(lambda url: open_url(url))
        github_label.setStyleSheet("font-size: 12px;")
        col.addWidget(github_label)

        col.addStretch()

        # Built-with tagline
        built_label = QLabel(about.built_with)
        built_label.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 11px;")
        built_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(built_label)

        col.addSpacing(4)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(t("common.close"))
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        col.addLayout(btn_row)

        return col

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _h_line() -> QFrame:
        """Creates a subtle horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {_DIVIDER};")
        line.setFixedHeight(1)
        return line

    def _on_logo_clicked(self) -> None:
        """Hidden interactions based on click count.

        3 clicks opens GitHub, 5 clicks shows SwitchBros tribute.
        """
        self._click_count += 1

        if self._click_count == 3:
            open_url(_GITHUB_URL)

        elif self._click_count >= 5:
            from src.utils.enigma import load_easter_egg
            from src.ui.widgets.ui_helper import UIHelper

            egg = load_easter_egg("logo_tribute")
            if egg:
                UIHelper.show_info(
                    self,
                    egg.get("message", ""),
                    title=egg.get("title", ""),
                )
            self._click_count = 0
